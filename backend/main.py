"""
Vanna Oracle Database Agent Application

This application connects to an Oracle database and provides a natural language
interface for querying data using the Vanna AI framework.

Configuration:
    - Oracle DB: localhost:1521 with user 'hr'
    - LLM: Ollama with model 'gpt-oss:20b' at localhost:11434
    - Agent Memory: ChromaDB for persistent memory storage

Usage:
    python -m app.main
    
    Then access the web interface at http://localhost:8000
    
Environment Variables (optional):
    See app/config.py for all available configuration options.
    You can also create a .env file in the project root.
"""

from vanna import Agent
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.tool import Tool, ToolContext, ToolResult
from vanna.tools import RunSqlTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from vanna.tools.visualize_data import VisualizeDataArgs
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.integrations.ollama import OllamaLlmService
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.oracle import OracleRunner
from vanna.integrations.chromadb import ChromaAgentMemory
from vanna.integrations.plotly import PlotlyChartGenerator
import pandas as pd
from typing import Optional
from pydantic import BaseModel

from .config import config


# =============================================================================
# User Authentication
# =============================================================================

import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException


class LdapUserResolver(UserResolver):
    """LDAP-based user resolver for enterprise authentication.
    
    This implementation authenticates users against an LDAP server:
    - Validates credentials via LDAP bind
    - Checks group membership for admin privileges
    - Reads user attributes (email, uid) from LDAP
    
    Requires 'Authorization' header with Basic auth or cookies for session.
    """
    
    def __init__(self, ldap_config):
        self.config = ldap_config
        self._server = None
    
    @property
    def server(self) -> Server:
        """Lazy-initialize LDAP server connection."""
        if self._server is None:
            self._server = Server(
                f"{'ldaps' if self.config.use_ssl else 'ldap'}://{self.config.host}:{self.config.port}",
                get_info=ALL
            )
        return self._server
    
    def _get_user_groups(self, conn: Connection, user_dn: str) -> list[str]:
        """Get groups the user belongs to."""
        groups = []
        try:
            # Search for groups that have this user as a member
            conn.search(
                search_base=self.config.base_dn,
                search_filter=f"(&(objectClass=groupOfNames)(member={user_dn}))",
                search_scope=SUBTREE,
                attributes=['cn']
            )
            for entry in conn.entries:
                groups.append(str(entry.cn))
        except LDAPException:
            pass
        return groups
    
    def _authenticate_user(self, username: str, password: str) -> tuple[bool, dict]:
        """Authenticate user against LDAP and return user info."""
        user_dn = self.config.user_dn_template.format(username=username)
        
        try:
            # Try to bind as the user
            conn = Connection(self.server, user=user_dn, password=password, auto_bind=True)
            
            # Search for user attributes
            conn.search(
                search_base=user_dn,
                search_filter="(objectClass=*)",
                search_scope=SUBTREE,
                attributes=['mail', 'uid', 'cn', 'sn']
            )
            
            user_info = {
                'dn': user_dn,
                'username': username,
                'email': None,
                'groups': []
            }
            
            if conn.entries:
                entry = conn.entries[0]
                user_info['email'] = str(entry.mail) if hasattr(entry, 'mail') and entry.mail else f"{username}@{self.config.email_domain}"
            
            # Get user's group memberships
            user_info['groups'] = self._get_user_groups(conn, user_dn)
            
            conn.unbind()
            return True, user_info
            
        except LDAPException as e:
            print(f"LDAP authentication failed for {username}: {e}")
            return False, {}
    
    async def resolve_user(self, request_context: RequestContext) -> User:
        """Resolve user from request context using LDAP authentication."""
        import base64
        
        # Try to get credentials from Authorization header (Basic auth)
        auth_header = request_context.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Basic '):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = credentials.split(':', 1)
                
                authenticated, user_info = self._authenticate_user(username, password)
                
                if authenticated:
                    # Determine groups - add 'admin' if user is in admin LDAP group
                    groups = ['user']
                    if 'admin' in user_info.get('groups', []):
                        groups = ['admin', 'user']
                    
                    return User(
                        id=username,
                        email=user_info.get('email', f"{username}@{self.config.email_domain}"),
                        username=username,
                        group_memberships=groups
                    )
            except Exception as e:
                print(f"Error processing auth header: {e}")
        
        # Check for session cookie (for already authenticated users)
        session_user = request_context.get_cookie('vanna_user')
        session_groups = request_context.get_cookie('vanna_groups')
        
        if session_user:
            groups = session_groups.split(',') if session_groups else ['user']
            return User(
                id=session_user,
                email=f"{session_user}@{self.config.email_domain}",
                username=session_user,
                group_memberships=groups
            )
        
        # Default to guest user
        return User(
            id=self.config.guest_username,
            email=self.config.guest_email,
            username=self.config.guest_username,
            group_memberships=['user']
        )


# =============================================================================
# Custom Visualization Tool
# =============================================================================

# Global store to hold recent query results (dataframes) by filename
_query_results_store: dict[str, pd.DataFrame] = {}


class DataframeVisualizeDataArgs(BaseModel):
    """Arguments for visualizing data from query results.
    
    Use this tool to create charts from the most recent SQL query results.
    The filename parameter should be set to 'latest_query_results.csv' to use
    the most recent query, or any query_results_*.csv filename from a recent query.
    """
    filename: str = "latest_query_results.csv"
    title: Optional[str] = None


class DataframeVisualizeDataTool(Tool[DataframeVisualizeDataArgs]):
    """Create interactive Plotly charts from SQL query results stored in memory.
    
    This tool automatically generates appropriate chart types (bar, line, scatter, etc.)
    based on the data structure. Use this tool after running a SQL query to visualize
    the results. The tool works with dataframes stored in memory - no CSV files needed.
    """
    
    def __init__(self, plotly_generator: Optional[PlotlyChartGenerator] = None):
        """Initialize the dataframe visualization tool.
        
        Args:
            plotly_generator: Optional PlotlyChartGenerator instance. If None, creates a new one.
        """
        self.plotly_generator = plotly_generator or PlotlyChartGenerator()
    
    @property
    def name(self) -> str:
        return "visualize_query_results"
    
    @property
    def description(self) -> str:
        return (
            "Create charts from SQL query results. "
            "Use after running a SQL query to visualize the results. "
            "Set filename to 'latest_query_results.csv' for the most recent query. "
            "Automatically selects the best chart type based on the data."
        )
    
    def get_args_schema(self):
        return DataframeVisualizeDataArgs
    
    async def execute(self, context: ToolContext, args: DataframeVisualizeDataArgs) -> ToolResult:
        """Execute visualization on dataframe from query results store."""
        try:
            # Try to find the dataframe in the store
            df = None
            
            # Check if filename matches a stored query result
            if args.filename in _query_results_store:
                df = _query_results_store[args.filename]
            else:
                # Try to find by partial match (e.g., "query_results_" prefix)
                for key, stored_df in _query_results_store.items():
                    if args.filename in key or key in args.filename:
                        df = stored_df
                        break
            
            if df is None or df.empty:
                return ToolResult(
                    success=False,
                    result_for_llm=f"Could not find query results for '{args.filename}'. Please run a SQL query first to generate the data.",
                )
            
            # Generate chart using PlotlyChartGenerator
            import time
            title = args.title or f"Chart: {args.filename}"
            chart_data = self.plotly_generator.generate_chart(df, title=title)
            
            # PlotlyChartGenerator returns a dict with 'data' (traces), 'layout', etc.
            # Ensure it has the structure expected by the frontend ChartComponentRenderer
            if isinstance(chart_data, dict):
                # The chart_data should already have 'data' and 'layout'
                # Add title if not present
                if 'title' not in chart_data:
                    chart_data['title'] = title
                if 'layout' in chart_data and 'title' not in chart_data['layout']:
                    chart_data['layout']['title'] = title
            
            # Return the chart data as a result
            # Create a proper chart component structure that Vanna can render
            from vanna.components import ChartComponent
            
            try:
                # Try to create a ChartComponent if available
                chart_component = ChartComponent(
                    id=f"chart_{int(time.time() * 1000)}",
                    chart_type="plotly",
                    data=chart_data,
                    title=title,
                )
                return ToolResult(
                    success=True,
                    result_for_llm=f"Generated visualization chart for {len(df)} rows of data.",
                    rich_component=chart_component,
                )
            except (ImportError, AttributeError):
                # Fallback to dict format if ChartComponent not available
                return ToolResult(
                    success=True,
                    result_for_llm=f"Generated visualization chart for {len(df)} rows of data.",
                    rich_component={
                        "type": "chart",
                        "id": f"chart_{int(time.time() * 1000)}",
                        "data": chart_data,
                        "title": title,
                        "lifecycle": "create",
                    }
                )
            
        except Exception as e:
            return ToolResult(
                success=False,
                result_for_llm=f"Error generating visualization: {str(e)}",
            )


# Custom SQL Runner wrapper to capture query results
class QueryResultCapturingOracleRunner(OracleRunner):
    """Wrapper around OracleRunner that captures query results in memory."""
    
    def run_sql(self, sql: str) -> pd.DataFrame:
        """Execute SQL query and store results in memory."""
        # Call the parent run_sql method to execute the query
        df = super().run_sql(sql)
        
        # Store the dataframe in the global store
        if df is not None and not df.empty:
            import time
            filename = f"query_results_{int(time.time() * 1000)}.csv"
            _query_results_store[filename] = df
            
            # Also store with a generic name for easier access
            _query_results_store["latest_query_results.csv"] = df
        
        return df




# =============================================================================
# Application Setup
# =============================================================================

def create_agent() -> Agent:
    """Create and configure the Vanna Agent with Oracle database connection.
    
    Returns:
        Configured Agent ready to handle natural language database queries
    """
    
    # 1. Configure the LLM service (OpenAI or Ollama)
    # Prefer OpenAI if configured, otherwise fall back to Ollama
    if config.openai.is_configured:
        # Use Vanna's built-in OpenAILlmService with custom base_url support
        # OpenAILlmService accepts: model, api_key, organization, base_url, and **extra_client_kwargs
        llm_kwargs = {
            "api_key": config.openai.api_key,
            "model": config.openai.model,
        }
        
        # Add base_url only if provided (allows using default OpenAI API)
        if config.openai.base_url:
            llm_kwargs["base_url"] = config.openai.base_url
        
        # For gpt-oss-120b, use lower temperature for better function calling
        # This model has known issues with function calling according to:
        # https://github.com/langchain-ai/langchain/issues/32621
        # https://gitlab.com/gitlab-org/gitlab/-/issues/563341
        # Lower temperature helps with more deterministic outputs
        if "gpt-oss-120b" in config.openai.model.lower():
            # Use very low temperature for more deterministic tool calling
            # The model has known issues, so we need to be more strict
            effective_temperature = 0.1
        else:
            effective_temperature = config.openai.temperature
        
        # Note: OpenAILlmService passes temperature per-request, not as client config
        # The temperature from config.openai.temperature should be used, but for gpt-oss-120b
        # we override it. However, Vanna's OpenAILlmService may not expose this directly.
        # The temperature is typically set in the generate/stream_request methods.
        # We'll rely on the config value being read correctly.
        
        llm = OpenAILlmService(**llm_kwargs)
    else:
        # Fall back to Ollama
        llm = OllamaLlmService(
            model=config.ollama.model,
            host=config.ollama.host,
            timeout=config.ollama.timeout,
            num_ctx=config.ollama.num_ctx,
            temperature=config.ollama.temperature,
        )
    
    # 2. Configure the Oracle database runner with result capturing
    oracle_runner = QueryResultCapturingOracleRunner(
        user=config.oracle.user,
        password=config.oracle.password,
        dsn=config.oracle.dsn
    )
    
    # 3. Configure agent memory (ChromaDB)
    agent_memory = ChromaAgentMemory(
        collection_name=config.chroma.collection_name,
        persist_directory=config.chroma.persist_directory
    )
    
    # 4. Create the SQL execution tool
    db_tool = RunSqlTool(sql_runner=oracle_runner)
    
    # 5. Configure user resolver (LDAP-based)
    user_resolver = LdapUserResolver(ldap_config=config.ldap)
    
    # 6. Set up the tool registry with access controls
    tools = ToolRegistry()
    
    # Register database tool - accessible to both admin and user groups
    tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
    
    # Register memory tools for saving and searching tool usage patterns
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin'])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'user'])
    tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'user'])
    
    # Register custom visualization tool that works directly with dataframes
    # This tool reads from the query results store, avoiding CSV file requirements
    visualize_tool = DataframeVisualizeDataTool()
    tools.register_local_tool(visualize_tool, access_groups=['admin', 'user'])
    
    # 7. Create and return the agent
    agent = Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=user_resolver,
        agent_memory=agent_memory
    )
    
    return agent


def main():
    """Main entry point for the application."""
    print("=" * 60)
    print("Vanna Oracle Database Agent")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Oracle Database: {config.oracle.user}@{config.oracle.dsn}")
    if config.openai.is_configured:
        base_url_info = f" at {config.openai.base_url}" if config.openai.base_url else " (default OpenAI API)"
        print(f"  LLM Service: OpenAI ({config.openai.model}){base_url_info}")
    else:
        print(f"  LLM Service: Ollama ({config.ollama.model}) at {config.ollama.host}")
    print(f"  Agent Memory: ChromaDB ({config.chroma.collection_name})")
    print(f"  Server: {config.server.host}:{config.server.port}")
    print()
    
    # Create the agent
    agent = create_agent()
    
    # Create and run the FastAPI server
    server = VannaFastAPIServer(agent)
    server.run(
        host=config.server.host,
        port=config.server.port,
        log_level=config.server.log_level,
    )


if __name__ == "__main__":
    main()

