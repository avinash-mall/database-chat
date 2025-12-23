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
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.integrations.ollama import OllamaLlmService
from vanna.integrations.oracle import OracleRunner
from vanna.integrations.chromadb import ChromaAgentMemory

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
# Application Setup
# =============================================================================

def create_agent() -> Agent:
    """Create and configure the Vanna Agent with Oracle database connection.
    
    Returns:
        Configured Agent ready to handle natural language database queries
    """
    
    # 1. Configure the LLM service (Ollama)
    llm = OllamaLlmService(
        model=config.ollama.model,
        host=config.ollama.host,
        timeout=config.ollama.timeout,
        num_ctx=config.ollama.num_ctx,
        temperature=config.ollama.temperature,
    )
    
    # 2. Configure the Oracle database runner
    oracle_runner = OracleRunner(
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
    
    # Register visualization tool for creating charts from query results
    tools.register_local_tool(VisualizeDataTool(), access_groups=['admin', 'user'])
    
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

