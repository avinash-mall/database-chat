"""
Vanna Oracle Database Agent Application

This application connects to an Oracle database and provides a natural language
interface for querying data using the Vanna AI framework.

Configuration:
    - Oracle DB: localhost:1521 with user 'hr'
    - LLM: Ollama with model 'gpt-oss:20b' at localhost:11434
    - Agent Memory: Milvus for persistent memory storage

Usage:
    python -m app.main
    
    Then access the web interface at http://localhost:8000
    
Environment Variables (optional):
    See app/config.py for all available configuration options.
    You can also create a .env file in the project root.
"""

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.file_system import WriteFileTool
from vanna.integrations.local import LocalFileSystem
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from vanna.servers.flask.app import VannaFlaskServer as BaseVannaFlaskServer
from vanna.servers.base import ChatHandler
from vanna.servers.flask.routes import register_chat_routes
from vanna.core.user.request_context import RequestContext
from flask import Flask, request, jsonify
from flask_cors import CORS

from .templates import get_ldap_login_html
from vanna.integrations.ollama import OllamaLlmService
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.oracle import OracleRunner
from vanna.integrations.milvus import MilvusAgentMemory

from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException

import oracledb

from .config import config
from .rls_service import RowLevelSecurityService, RLSConfig
from .secure_sql_tool import SecureRunSqlTool
from .system_prompt_builder import UserAwareSystemPromptBuilder
from .schema_trainer import SchemaTrainer


# =============================================================================
# Custom Flask Server with LDAP Authentication
# =============================================================================

class VannaFlaskServer(BaseVannaFlaskServer):
    """Custom Flask server with LDAP authentication support."""
    
    def create_app(self) -> Flask:
        """Create configured Flask app with LDAP login."""
        app = Flask(__name__, static_url_path="/static")
        app.config.update(self.config.get("flask", {}))
        
        # Serve assets folder as static files
        import os
        from pathlib import Path
        assets_path = Path(__file__).parent.parent / "assets"
        if assets_path.exists():
            from flask import send_from_directory, abort
            @app.route("/assets/<path:filepath>")
            def assets(filepath):
                """Serve files from the assets directory."""
                # Normalize path separators
                filepath = filepath.replace('\\', '/')
                # Build the full path
                full_path = assets_path / filepath
                # Resolve to absolute path to prevent directory traversal
                try:
                    full_path = full_path.resolve()
                    assets_path_resolved = assets_path.resolve()
                    # Ensure the file is within the assets directory
                    if not str(full_path).startswith(str(assets_path_resolved)):
                        abort(404)
                    if full_path.exists() and full_path.is_file():
                        directory = str(full_path.parent)
                        filename = full_path.name
                        return send_from_directory(directory, filename)
                except (ValueError, OSError):
                    pass
                abort(404)
        
        # Enable CORS
        cors_config = self.config.get("cors", {})
        if cors_config.get("enabled", True):
            CORS(app, **{k: v for k, v in cors_config.items() if k != "enabled"})
        
        # Register chat routes FIRST (includes default index)
        register_chat_routes(app, self.chat_handler, self.config)
        
        # Define custom LDAP login view function
        def custom_index() -> str:
            api_base_url = self.config.get("api_base_url", "")
            show_api_endpoints = config.ui.show_api_endpoints
            ui_text = config.ui.text
            return get_ldap_login_html(
                api_base_url=api_base_url,
                show_api_endpoints=show_api_endpoints,
                ui_text=ui_text
            )
        
        # Override the default index view function with our custom one
        app.view_functions['index'] = custom_index
        
        # Auth test endpoint for LDAP validation
        @app.route("/api/vanna/v2/auth_test", methods=["POST"])
        def auth_test():
            """Test LDAP authentication and return user info."""
            import asyncio
            
            # Create request context
            request_context = RequestContext(
                cookies=dict(request.cookies),
                headers=dict(request.headers),
                remote_addr=request.remote_addr,
                query_params=dict(request.args),
            )
            
            # Resolve user using the agent's user resolver
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                user = loop.run_until_complete(
                    self.agent.user_resolver.resolve_user(request_context)
                )
                
                # Check if user is guest (auth failed)
                if user.id == config.ldap.guest_username:
                    return jsonify({"error": "Invalid username or password. Please check your credentials and try again."}), 401
                
                return jsonify({
                    "success": True,
                    "user": user.id,
                    "email": user.email,
                    "groups": user.group_memberships,
                    "is_admin": 'admin' in user.group_memberships
                })
            except LDAPException as e:
                # LDAP-specific errors
                error_msg = f"LDAP authentication error: {str(e)}"
                print(f"LDAP error in auth_test: {error_msg}")
                return jsonify({"error": "Unable to connect to authentication server. Please try again later."}), 401
            except Exception as e:
                # Other errors
                error_msg = str(e)
                print(f"Error in auth_test: {error_msg}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": f"Authentication failed: {error_msg}"}), 401
            finally:
                loop.close()
        
        # Health check (override)
        @app.route("/health")
        def health_check():
            return {"status": "healthy", "service": "vanna"}
        
        return app


# =============================================================================
# User Authentication
# =============================================================================

class HybridUserResolver(UserResolver):
    """Hybrid user resolver: LDAP authentication + Database role resolution.
    
    This implementation:
    - Authenticates users against an LDAP server (validates credentials)
    - Reads user attributes (email, uid) from LDAP
    - Queries AI_USERS table in Oracle database for role/group membership
    
    AI_USERS table structure:
    - USERNAME: VARCHAR2(50) - Primary key, matches LDAP username
    - IS_ADMIN: NUMBER - 1 = admin group membership
    - IS_SUPERUSER: NUMBER - 1 = superuser group membership  
    - IS_NORMALUSER: NUMBER - 1 = user group membership (default)
    
    Requires 'Authorization' header with Basic auth or cookies for session.
    """
    
    def __init__(self, ldap_config, oracle_config):
        self.config = ldap_config
        self.oracle_config = oracle_config
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
    
    def _get_user_roles_from_db(self, username: str) -> list[str]:
        """Get user roles from AI_USERS database table.
        
        Args:
            username: The username to look up in AI_USERS table
            
        Returns:
            List of group names based on database flags:
            - 'admin' if IS_ADMIN = 1
            - 'superuser' if IS_SUPERUSER = 1
            - 'user' if IS_NORMALUSER = 1 or as default fallback
            
        Raises:
            RuntimeError: If database connection or query fails
        """
        groups = []
        
        try:
            # Connect to Oracle database
            connection = oracledb.connect(
                user=self.oracle_config.user,
                password=self.oracle_config.password,
                dsn=self.oracle_config.dsn
            )
            
            cursor = connection.cursor()
            
            # Query the AI_USERS table for role flags
            cursor.execute(
                """
                SELECT IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER 
                FROM AI_USERS 
                WHERE UPPER(USERNAME) = UPPER(:username)
                """,
                {"username": username}
            )
            
            row = cursor.fetchone()
            
            if row:
                is_admin, is_superuser, is_normaluser = row
                
                # Map database flags to group memberships
                if is_admin and is_admin == 1:
                    groups.append('admin')
                if is_superuser and is_superuser == 1:
                    groups.append('superuser')
                if is_normaluser and is_normaluser == 1:
                    groups.append('user')
                
                # Ensure at least 'user' group if no flags are set
                if not groups:
                    groups.append('user')
                    
                print(f"DB: User '{username}' has roles: {groups}")
            else:
                # User not found in AI_USERS table - raise error, do not fallback
                cursor.close()
                connection.close()
                raise RuntimeError(f"User '{username}' not found in AI_USERS table. Access denied.")
            
            cursor.close()
            connection.close()
            
        except oracledb.Error as e:
            # On database error, raise exception instead of falling back
            error_msg = f"Database error querying AI_USERS for '{username}': {e}"
            print(f"DB: {error_msg}")
            raise RuntimeError(error_msg)
        
        return groups
    
    def _authenticate_user(self, username: str, password: str) -> tuple[bool, dict]:
        """Authenticate user against LDAP and return user info."""
        user_dn = self.config.user_dn_template.format(username=username)
        
        try:
            conn = Connection(self.server, user=user_dn, password=password, auto_bind=True)
            
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
            }
            
            if conn.entries:
                entry = conn.entries[0]
                user_info['email'] = str(entry.mail) if hasattr(entry, 'mail') and entry.mail else f"{username}@{self.config.email_domain}"
            
            conn.unbind()
            return True, user_info
            
        except LDAPException as e:
            print(f"LDAP authentication failed for {username}: {e}")
            return False, {}
    
    async def resolve_user(self, request_context: RequestContext) -> User:
        """Resolve user from request context using LDAP auth + DB roles.
        
        Raises:
            RuntimeError: If authentication fails or user not authorized
        """
        import base64
        
        auth_header = request_context.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Basic '):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = credentials.split(':', 1)
                
                authenticated, user_info = self._authenticate_user(username, password)
                
                if authenticated:
                    # Get roles from database - will raise if user not in AI_USERS
                    groups = self._get_user_roles_from_db(username)
                    
                    return User(
                        id=username,
                        email=user_info.get('email', f"{username}@{self.config.email_domain}"),
                        username=username,
                        group_memberships=groups
                    )
                else:
                    # LDAP authentication failed - raise exception
                    raise RuntimeError(f"LDAP authentication failed for user '{username}'")
            except RuntimeError:
                # Re-raise RuntimeError (from _get_user_roles_from_db or explicit raise)
                raise
            except Exception as e:
                print(f"Error processing auth header: {e}")
                raise RuntimeError(f"Authentication error: {e}")
        
        session_user = request_context.get_cookie('vanna_user')
        session_auth = request_context.get_cookie('vanna_auth')
        
        if session_user and session_auth:
            # If we have session cookies, try to re-authenticate with LDAP
            # and get fresh role information from database
            try:
                credentials = base64.b64decode(session_auth).decode('utf-8')
                username, password = credentials.split(':', 1)
                
                # Only re-authenticate if username matches
                if username == session_user:
                    authenticated, user_info = self._authenticate_user(username, password)
                    
                    if authenticated:
                        # Get roles from database - will raise if user not in AI_USERS
                        groups = self._get_user_roles_from_db(username)
                        
                        return User(
                            id=username,
                            email=user_info.get('email', f"{username}@{self.config.email_domain}"),
                            username=username,
                            group_memberships=groups
                        )
                    else:
                        raise RuntimeError(f"Session re-authentication failed for user '{username}'")
            except RuntimeError:
                # Re-raise RuntimeError
                raise
            except Exception as e:
                print(f"LDAP: Error re-authenticating session user {session_user}: {e}")
                raise RuntimeError(f"Session authentication error: {e}")
        
        # No valid authentication provided - this is an unauthenticated request
        # Return guest user only for unauthenticated requests (no auth header, no session)
        # This allows the login page to load
        return User(
            id=self.config.guest_username,
            email=self.config.guest_email,
            username=self.config.guest_username,
            group_memberships=['user']
        )


# =============================================================================
# Application Setup
# =============================================================================

def create_agent() -> Agent:
    """Create and configure the Vanna Agent with Oracle database connection."""
    
    # Configure the LLM service (OpenAI or Ollama) based on INFERENCE_PROVIDER
    if config.inference_provider == "openai":
        if not config.openai.is_configured:
            raise ValueError(
                "INFERENCE_PROVIDER is set to 'openai' but OpenAI is not properly configured. "
                "Please set OPENAI_API_KEY and OPENAI_MODEL in your environment variables."
            )
        
        llm_kwargs = {
            "api_key": config.openai.api_key,
            "model": config.openai.model,
        }
        if config.openai.base_url:
            llm_kwargs["base_url"] = config.openai.base_url
        
        if config.openai.timeout:
            llm_kwargs["timeout"] = config.openai.timeout
        
        llm = OpenAILlmService(**llm_kwargs)
    else:
        # Default to Ollama
        if not config.ollama.is_configured:
            raise ValueError(
                "INFERENCE_PROVIDER is set to 'ollama' but Ollama is not properly configured. "
                "Please set OLLAMA_MODEL and OLLAMA_HOST in your environment variables."
            )
        
        llm = OllamaLlmService(
            model=config.ollama.model,
            host=config.ollama.host,
            timeout=config.ollama.timeout,
            num_ctx=config.ollama.num_ctx,
            temperature=config.ollama.temperature,
        )
    
    # Configure the Oracle database runner
    oracle_runner = OracleRunner(
        user=config.oracle.user,
        password=config.oracle.password,
        dsn=config.oracle.dsn
    )
    
    # Configure agent memory (Milvus)
    agent_memory = MilvusAgentMemory(
        host=config.milvus.host,
        port=config.milvus.port,
        collection_name=config.milvus.collection_name
    )
    
    # ==========================================================================
    # Row-Level Security (RLS) Setup
    # ==========================================================================
    # Create RLS service for filtering query results based on user context
    rls_config = RLSConfig(
        enabled=config.rls.enabled,
        cache_ttl=config.rls.cache_ttl,
        excluded_tables=config.rls.excluded_tables_list
    )
    rls_service = RowLevelSecurityService(
        oracle_config=config.oracle,
        rls_config=rls_config
    )
    
    # Create the secure SQL execution tool with RLS filtering
    # This replaces the standard RunSqlTool
    # Note: The SecureRunSqlTool handles caching internally
    db_tool = SecureRunSqlTool(
        sql_runner=oracle_runner,
        rls_service=rls_service
    )
    
    print(f"RLS: Enabled={config.rls.enabled}, CacheTTL={config.rls.cache_ttl}s")
    if config.rls.excluded_tables_list:
        print(f"RLS: Excluded tables: {config.rls.excluded_tables_list}")
    
    # Configure user resolver (LDAP auth + Database role resolution)
    user_resolver = HybridUserResolver(ldap_config=config.ldap, oracle_config=config.oracle)
    
    # ==========================================================================
    # Schema Training (Vanna Native Approach)
    # ==========================================================================
    # Train the agent with database schema information
    # This provides the LLM with table/column/relationship context
    schema_trainer = SchemaTrainer(
        oracle_config=config.oracle,
        agent_memory=agent_memory
    )
    schema_trainer.train_schema()
    schema_summary = schema_trainer.get_schema_summary()
    print(f"Schema Training: Loaded {len(schema_trainer._schema_info)} tables/views")
    
    # Set up the tool registry with access controls
    # Roles from AI_USERS table: admin, superuser, user
    tools = ToolRegistry()
    tools.register_local_tool(db_tool, access_groups=['admin', 'superuser', 'user'])
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin', 'superuser'])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'superuser', 'user'])
    tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'superuser', 'user'])
    
    # Create a shared LocalFileSystem instance for both VisualizeDataTool and WriteFileTool
    # This ensures both tools can access the same files
    # LocalFileSystem doesn't take parameters - it uses the current working directory
    file_system = LocalFileSystem()
    
    # Create VisualizeDataTool with the shared file system
    # According to Vanna docs: VisualizeDataTool(file_system=LocalFileSystem())
    visualize_tool = VisualizeDataTool(file_system=file_system)
    tools.register_local_tool(visualize_tool, access_groups=['admin', 'superuser', 'user'])
    
    # Register WriteFileTool with the same file system
    # This allows the agent to save CSV files that VisualizeDataTool can read
    write_file_tool = WriteFileTool(file_system=file_system)
    tools.register_local_tool(write_file_tool, access_groups=['admin', 'superuser', 'user'])
    
    # Create agent configuration
    agent_config = AgentConfig(
        max_tool_iterations=config.agent.max_tool_iterations
    )
    
    # Create user-aware system prompt builder
    # This injects user identity, RLS filter values, AND schema info into the LLM prompt
    system_prompt_builder = UserAwareSystemPromptBuilder(
        rls_service=rls_service,
        company_name="Database Chat",
        include_rls_values=True,
        schema_summary=schema_summary
    )
    
    # Create and return the agent
    # Note: workflow_handler=None disables the default handler that shows "Admin View"
    # message based on group membership
    agent = Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=agent_config,
        workflow_handler=None,  # Disable default workflow handler
        system_prompt_builder=system_prompt_builder  # User-aware prompts
    )
    
    return agent


def main():
    """Main entry point for the application."""
    print("=" * 60)
    print("Vanna Oracle Database Agent")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Oracle Database: {config.oracle.user}@{config.oracle.dsn}")
    if config.inference_provider == "openai":
        base_url_info = f" at {config.openai.base_url}" if config.openai.base_url else " (default OpenAI API)"
        temp_info = f", temperature={config.openai.temperature}" if config.openai.temperature is not None else ""
        print(f"  LLM Service: OpenAI ({config.openai.model}){base_url_info}{temp_info}")
    else:
        print(f"  LLM Service: Ollama ({config.ollama.model}) at {config.ollama.host}")
    print(f"  Agent Memory: Milvus ({config.milvus.host}:{config.milvus.port}/{config.milvus.collection_name})")
    print(f"  Server: {config.server.host}:{config.server.port}")
    print()
    
    agent = create_agent()
    
    server = VannaFlaskServer(agent)
    server.run(
        host=config.server.host,
        port=config.server.port,
        debug=(config.server.log_level == 'debug'),
    )


if __name__ == "__main__":
    main()
