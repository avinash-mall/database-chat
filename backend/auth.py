"""
Authentication Module for Database Chat Application.

This module provides hybrid authentication combining LDAP for credential
validation and Oracle database for role/permission resolution.
"""

import base64
from typing import List, Tuple, Dict, Optional

import oracledb
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException
from vanna.core.user import UserResolver, User
from vanna.core.user.request_context import RequestContext


class HybridUserResolver(UserResolver):
    """Hybrid user resolver combining LDAP authentication with database role resolution.
    
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
        """Initialize the hybrid user resolver.
        
        Args:
            ldap_config: LDAP configuration with host, port, base_dn, etc.
            oracle_config: Oracle database configuration with user, password, dsn.
        """
        self.config = ldap_config
        self.oracle_config = oracle_config
        self._server: Optional[Server] = None
    
    @property
    def server(self) -> Server:
        """Lazy-initialize LDAP server connection.
        
        Returns:
            Configured LDAP Server instance.
        """
        if self._server is None:
            protocol = 'ldaps' if self.config.use_ssl else 'ldap'
            self._server = Server(
                f"{protocol}://{self.config.host}:{self.config.port}",
                get_info=ALL
            )
        return self._server
    
    def _get_user_roles_from_db(self, username: str) -> List[str]:
        """Get user roles from AI_USERS database table.
        
        Args:
            username: The username to look up in AI_USERS table.
            
        Returns:
            List of group names based on database flags:
            - 'admin' if IS_ADMIN = 1
            - 'superuser' if IS_SUPERUSER = 1
            - 'user' if IS_NORMALUSER = 1 or as default fallback
            
        Raises:
            RuntimeError: If user not found or database connection fails.
        """
        groups = []
        
        try:
            connection = oracledb.connect(
                user=self.oracle_config.user,
                password=self.oracle_config.password,
                dsn=self.oracle_config.dsn
            )
            
            cursor = connection.cursor()
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
                
                if is_admin and is_admin == 1:
                    groups.append('admin')
                if is_superuser and is_superuser == 1:
                    groups.append('superuser')
                if is_normaluser and is_normaluser == 1:
                    groups.append('user')
                
                if not groups:
                    groups.append('user')
                    
                print(f"DB: User '{username}' has roles: {groups}")
            else:
                cursor.close()
                connection.close()
                raise RuntimeError(
                    f"User '{username}' not found in AI_USERS table. Access denied."
                )
            
            cursor.close()
            connection.close()
            
        except oracledb.Error as e:
            error_msg = f"Database error querying AI_USERS for '{username}': {e}"
            print(f"DB: {error_msg}")
            raise RuntimeError(error_msg)
        
        return groups
    
    def _authenticate_user(self, username: str, password: str) -> Tuple[bool, Dict]:
        """Authenticate user against LDAP and return user info.
        
        Args:
            username: The username to authenticate.
            password: The password to validate.
            
        Returns:
            Tuple of (success, user_info) where user_info contains
            dn, username, and email if authentication succeeded.
        """
        user_dn = self.config.user_dn_template.format(username=username)
        
        try:
            conn = Connection(
                self.server, 
                user=user_dn, 
                password=password, 
                auto_bind=True
            )
            
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
                if hasattr(entry, 'mail') and entry.mail:
                    user_info['email'] = str(entry.mail)
                else:
                    user_info['email'] = f"{username}@{self.config.email_domain}"
            
            conn.unbind()
            return True, user_info
            
        except LDAPException as e:
            print(f"LDAP authentication failed for {username}: {e}")
            return False, {}
    
    async def resolve_user(self, request_context: RequestContext) -> User:
        """Resolve user from request context using LDAP auth + DB roles.
        
        Args:
            request_context: The request context containing headers and cookies.
            
        Returns:
            User object with id, email, username, and group_memberships.
            
        Raises:
            RuntimeError: If authentication fails or user not authorized.
        """
        # Try Authorization header first
        auth_header = request_context.get_header('Authorization')
        
        if auth_header and auth_header.startswith('Basic '):
            return await self._resolve_from_auth_header(auth_header)
        
        # Try session cookies
        session_user = request_context.get_cookie('vanna_user')
        session_auth = request_context.get_cookie('vanna_auth')
        
        if session_user and session_auth:
            return await self._resolve_from_session(session_user, session_auth)
        
        # Return guest user for unauthenticated requests (allows login page to load)
        return User(
            id=self.config.guest_username,
            email=self.config.guest_email,
            username=self.config.guest_username,
            group_memberships=['user']
        )
    
    async def _resolve_from_auth_header(self, auth_header: str) -> User:
        """Resolve user from Authorization header.
        
        Args:
            auth_header: The Authorization header value (Basic base64...).
            
        Returns:
            Authenticated User object.
            
        Raises:
            RuntimeError: If authentication fails.
        """
        try:
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)
            
            authenticated, user_info = self._authenticate_user(username, password)
            
            if authenticated:
                groups = self._get_user_roles_from_db(username)
                return User(
                    id=username,
                    email=user_info.get('email', f"{username}@{self.config.email_domain}"),
                    username=username,
                    group_memberships=groups
                )
            else:
                raise RuntimeError(f"LDAP authentication failed for user '{username}'")
        except RuntimeError:
            raise
        except Exception as e:
            print(f"Error processing auth header: {e}")
            raise RuntimeError(f"Authentication error: {e}")
    
    async def _resolve_from_session(self, session_user: str, session_auth: str) -> User:
        """Resolve user from session cookies.
        
        Args:
            session_user: The vanna_user cookie value.
            session_auth: The vanna_auth cookie value (base64 encoded credentials).
            
        Returns:
            Authenticated User object.
            
        Raises:
            RuntimeError: If session re-authentication fails.
        """
        try:
            credentials = base64.b64decode(session_auth).decode('utf-8')
            username, password = credentials.split(':', 1)
            
            if username != session_user:
                raise RuntimeError("Session username mismatch")
            
            authenticated, user_info = self._authenticate_user(username, password)
            
            if authenticated:
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
            raise
        except Exception as e:
            print(f"LDAP: Error re-authenticating session user {session_user}: {e}")
            raise RuntimeError(f"Session authentication error: {e}")
