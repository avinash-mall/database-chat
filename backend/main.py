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
from vanna.integrations.chromadb import ChromaAgentMemory

from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException

from .config import config


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
                    "groups": user.group_memberships
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
                'groups': []
            }
            
            if conn.entries:
                entry = conn.entries[0]
                user_info['email'] = str(entry.mail) if hasattr(entry, 'mail') and entry.mail else f"{username}@{self.config.email_domain}"
            
            user_info['groups'] = self._get_user_groups(conn, user_dn)
            
            conn.unbind()
            return True, user_info
            
        except LDAPException as e:
            print(f"LDAP authentication failed for {username}: {e}")
            return False, {}
    
    async def resolve_user(self, request_context: RequestContext) -> User:
        """Resolve user from request context using LDAP authentication."""
        import base64
        
        auth_header = request_context.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Basic '):
            try:
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = credentials.split(':', 1)
                
                authenticated, user_info = self._authenticate_user(username, password)
                
                if authenticated:
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
    
    # Configure agent memory (ChromaDB)
    agent_memory = ChromaAgentMemory(
        collection_name=config.chroma.collection_name,
        persist_directory=config.chroma.persist_directory
    )
    
    # Create the SQL execution tool
    db_tool = RunSqlTool(sql_runner=oracle_runner)
    
    # Configure user resolver (LDAP-based)
    user_resolver = LdapUserResolver(ldap_config=config.ldap)
    
    # Set up the tool registry with access controls
    tools = ToolRegistry()
    tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin'])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'user'])
    tools.register_local_tool(SaveTextMemoryTool(), access_groups=['admin', 'user'])
    tools.register_local_tool(VisualizeDataTool(), access_groups=['admin', 'user'])
    
    # Create and return the agent
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
    if config.inference_provider == "openai":
        base_url_info = f" at {config.openai.base_url}" if config.openai.base_url else " (default OpenAI API)"
        temp_info = f", temperature={config.openai.temperature}" if config.openai.temperature is not None else ""
        print(f"  LLM Service: OpenAI ({config.openai.model}){base_url_info}{temp_info}")
    else:
        print(f"  LLM Service: Ollama ({config.ollama.model}) at {config.ollama.host}")
    print(f"  Agent Memory: ChromaDB ({config.chroma.collection_name})")
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
