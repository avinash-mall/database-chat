"""
Flask Server for Database Chat Application.

This module provides a custom Flask server that extends the Vanna framework's
base server with LDAP authentication support and custom routes.
"""

import asyncio
import os
import traceback
from pathlib import Path
from typing import Any, Dict

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from ldap3.core.exceptions import LDAPException
from vanna.servers.flask.app import VannaFlaskServer as BaseVannaFlaskServer
from vanna.servers.flask.routes import register_chat_routes
from vanna.core.user.request_context import RequestContext

from .config import config
from .templates import get_ldap_login_html


class VannaFlaskServer(BaseVannaFlaskServer):
    """Custom Flask server with LDAP authentication support.
    
    This server extends the base Vanna Flask server to provide:
    - Custom LDAP login page
    - Static asset serving from /assets
    - Generated file serving from /api/files
    - Auth test endpoint for LDAP validation
    - Health check endpoint
    """
    
    def create_app(self) -> Flask:
        """Create and configure the Flask application.
        
        Returns:
            Configured Flask application with all routes registered.
        """
        app = Flask(__name__, static_url_path="/static")
        app.config.update(self.config.get("flask", {}))
        
        # Register asset serving routes
        self._register_asset_routes(app)
        
        # Enable CORS
        self._configure_cors(app)
        
        # Register chat routes (includes default index)
        register_chat_routes(app, self.chat_handler, self.config)
        
        # Override index with custom LDAP login
        app.view_functions['index'] = self._create_custom_index()
        
        # Register additional endpoints
        self._register_auth_endpoint(app)
        self._register_health_endpoint(app)
        
        return app
    
    def _register_asset_routes(self, app: Flask) -> None:
        """Register routes for serving static assets and generated files.
        
        Args:
            app: Flask application instance.
        """
        assets_path = Path(__file__).parent.parent / "assets"
        
        if assets_path.exists():
            @app.route("/assets/<path:filepath>")
            def assets(filepath: str):
                """Serve files from the assets directory."""
                filepath = filepath.replace('\\', '/')
                full_path = assets_path / filepath
                
                try:
                    full_path = full_path.resolve()
                    assets_path_resolved = assets_path.resolve()
                    
                    if not str(full_path).startswith(str(assets_path_resolved)):
                        abort(404)
                    if full_path.exists() and full_path.is_file():
                        return send_from_directory(
                            str(full_path.parent), 
                            full_path.name
                        )
                except (ValueError, OSError):
                    pass
                abort(404)
        
        @app.route("/api/files/<filename>")
        def serve_file(filename: str):
            """Serve generated files (images, CSVs) from the working directory."""
            cwd = Path(os.getcwd())
            
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.svg', '.csv', '.json'}
            _, ext = os.path.splitext(filename)
            if ext.lower() not in allowed_extensions:
                abort(404)
            
            # Check root directory
            filepath = cwd / filename
            if filepath.exists() and filepath.is_file():
                return send_from_directory(str(cwd), filename)
            
            # Check subdirectories (one level deep)
            for subdir in cwd.iterdir():
                if subdir.is_dir():
                    filepath = subdir / filename
                    if filepath.exists() and filepath.is_file():
                        return send_from_directory(str(subdir), filename)
            
            print(f"File not found: {filename} in {cwd} or subdirectories")
            abort(404)
    
    def _configure_cors(self, app: Flask) -> None:
        """Configure CORS for the Flask application.
        
        Args:
            app: Flask application instance.
        """
        cors_config = self.config.get("cors", {})
        if cors_config.get("enabled", True):
            CORS(app, **{k: v for k, v in cors_config.items() if k != "enabled"})
    
    def _create_custom_index(self):
        """Create the custom LDAP login page view function.
        
        Returns:
            View function that renders the LDAP login page.
        """
        def custom_index() -> str:
            api_base_url = self.config.get("api_base_url", "")
            return get_ldap_login_html(
                api_base_url=api_base_url,
                show_api_endpoints=config.ui.show_api_endpoints,
                ui_text=config.ui.text
            )
        return custom_index
    
    def _register_auth_endpoint(self, app: Flask) -> None:
        """Register the authentication test endpoint.
        
        Args:
            app: Flask application instance.
        """
        @app.route("/api/vanna/v2/auth_test", methods=["POST"])
        def auth_test():
            """Test LDAP authentication and return user info."""
            request_context = RequestContext(
                cookies=dict(request.cookies),
                headers=dict(request.headers),
                remote_addr=request.remote_addr,
                query_params=dict(request.args),
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                user = loop.run_until_complete(
                    self.agent.user_resolver.resolve_user(request_context)
                )
                
                if user.id == config.ldap.guest_username:
                    return jsonify({
                        "error": "Invalid username or password. Please check your credentials and try again."
                    }), 401
                
                return jsonify({
                    "success": True,
                    "user": user.id,
                    "email": user.email,
                    "groups": user.group_memberships,
                    "is_admin": 'admin' in user.group_memberships
                })
            except LDAPException as e:
                print(f"LDAP error in auth_test: {e}")
                return jsonify({
                    "error": "Unable to connect to authentication server. Please try again later."
                }), 401
            except Exception as e:
                print(f"Error in auth_test: {e}")
                traceback.print_exc()
                return jsonify({"error": f"Authentication failed: {e}"}), 401
            finally:
                loop.close()
    
    def _register_health_endpoint(self, app: Flask) -> None:
        """Register the health check endpoint.
        
        Args:
            app: Flask application instance.
        """
        @app.route("/health")
        def health_check() -> Dict[str, str]:
            return {"status": "healthy", "service": "vanna"}
