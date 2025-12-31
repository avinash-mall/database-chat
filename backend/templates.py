"""
HTML Templates for Database Chat Application.

This module provides template generation for the LDAP authentication UI.
It loads base templates from the assets directory and injects dynamic
content including UI text strings and API endpoint information.
"""

from pathlib import Path
from typing import Optional, Any


def _load_template_file(filename: str) -> str:
    """Load a template file from the assets directory.
    
    Args:
        filename: Name of the file to load (e.g., 'base.html', 'styles.css').
        
    Returns:
        Contents of the template file.
        
    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    assets_dir = Path(__file__).parent.parent / "assets"
    
    if filename.endswith('.css'):
        file_path = assets_dir / "css" / filename
    elif filename.endswith('.js'):
        file_path = assets_dir / "js" / filename
    elif filename.endswith('.html'):
        file_path = assets_dir / filename
    else:
        file_path = assets_dir / filename
    
    if file_path.exists():
        return file_path.read_text(encoding='utf-8')
    raise FileNotFoundError(f"Template file not found: {file_path}")


def get_ldap_login_html(
    api_base_url: str = "",
    show_api_endpoints: bool = True,
    ui_text: Optional[Any] = None,
) -> str:
    """Generate the LDAP login page HTML.
    
    Loads base HTML, CSS, and JavaScript templates from the assets directory
    and injects dynamic UI text and configuration.
    
    Args:
        api_base_url: Base URL for API endpoints display.
        show_api_endpoints: Whether to show the API endpoints section.
        ui_text: UI text configuration object with customizable strings.
        
    Returns:
        Complete HTML page as a string.
    """
    # Load template files
    base_html = _load_template_file("base.html")
    styles_css = _load_template_file("styles.css")
    auth_js = _load_template_file("auth.js")
    chat_js = _load_template_file("chat.js")
    
    # Component script - load from local assets only
    component_script = '<script type="module" src="/assets/js/vanna-components.js"></script>'
    
    # Helper to get UI text with defaults
    def get_text(key, default):
        return getattr(ui_text, key, default) if ui_text and hasattr(ui_text, key) else default
    
    # Replace placeholders in JavaScript
    auth_js = auth_js.replace('{{LOGIN_ERROR_MISSING_FIELDS}}', get_text('login_error_missing_fields', 'Please enter both username and password.'))
    auth_js = auth_js.replace('{{LOGIN_ERROR_INVALID_CREDENTIALS}}', get_text('login_error_invalid_credentials', 'Authentication failed. Please check your credentials and try again.'))
    auth_js = auth_js.replace('{{AUTHENTICATING_TEXT}}', get_text('authenticating_text', 'Authenticating...'))
    auth_js = auth_js.replace('{{LOGIN_BUTTON}}', get_text('login_button', 'Login'))
    
    # Replace placeholders in HTML
    replacements = {
        '{{PAGE_TITLE}}': get_text('page_title', 'Agents Chat'),
        '{{STYLES}}': styles_css,
        '{{COMPONENT_SCRIPT}}': component_script,
        '{{HEADER_TITLE}}': get_text('header_title', 'Agents'),
        '{{HEADER_SUBTITLE}}': get_text('header_subtitle', 'DATA-FIRST AGENTS'),
        '{{HEADER_DESCRIPTION}}': get_text('header_description', 'Interactive AI Assistant powered by Agents Framework'),
        '{{DEV_MODE_MESSAGE}}': '',
        '{{LOGIN_TITLE}}': get_text('login_title', 'Login to Continue'),
        '{{LOGIN_DESCRIPTION}}': get_text('login_description', 'Enter your credentials to access the chat'),
        '{{LOGIN_FAILED_LABEL}}': get_text('login_failed_label', 'Login Failed:'),
        '{{USERNAME_LABEL}}': get_text('username_label', 'Username'),
        '{{USERNAME_PLACEHOLDER}}': get_text('username_placeholder', 'Enter your username'),
        '{{PASSWORD_LABEL}}': get_text('password_label', 'Password'),
        '{{PASSWORD_PLACEHOLDER}}': get_text('password_placeholder', 'Enter your password'),
        '{{LOGIN_BUTTON}}': get_text('login_button', 'Login'),
        '{{LDAP_AUTH_NOTE}}': get_text('ldap_auth_note', 'LDAP Authentication: Use your organizational credentials to log in.'),
        '{{LOGGED_IN_PREFIX}}': get_text('logged_in_prefix', 'Logged in as'),
        '{{LOGOUT_BUTTON}}': get_text('logout_button', 'Logout'),
        '{{CHAT_TITLE}}': get_text('chat_title', 'Vanna AI Chat'),
        '{{API_BASE_URL}}': api_base_url,
        '{{API_ENDPOINTS_SECTION}}': _build_api_endpoints_section(api_base_url, show_api_endpoints, ui_text),
        '{{AUTH_JS}}': auth_js,
        '{{CHAT_JS}}': chat_js,
    }
    
    html = base_html
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    
    return html


def _build_api_endpoints_section(
    api_base_url: str, 
    show_api_endpoints: bool, 
    ui_text: Optional[Any]
) -> str:
    """Build the API endpoints section HTML.
    
    Args:
        api_base_url: Base URL prefix for the API endpoints.
        show_api_endpoints: If False, returns empty string.
        ui_text: UI text configuration for labels.
        
    Returns:
        HTML string for the API endpoints section.
    """
    if not show_api_endpoints:
        return ''
    
    def get_text(key, default):
        return getattr(ui_text, key, default) if ui_text and hasattr(ui_text, key) else default
    
    return f'''
        <div class="api-endpoints-section mt-8 p-5 bg-white/80 backdrop-blur-sm rounded-lg shadow-sm border border-vanna-teal/20">
            <h3 class="text-lg font-semibold text-vanna-navy mb-3 font-serif">{get_text('api_endpoints_title', 'API Endpoints')}</h3>
            <ul class="space-y-2">
                <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                    <span class="font-bold text-vanna-teal mr-2">POST</span>{api_base_url}/api/vanna/v2/chat_sse - {get_text('api_sse_description', 'Server-Sent Events streaming')}
                </li>
                <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                    <span class="font-bold text-vanna-teal mr-2">WS</span>{api_base_url}/api/vanna/v2/chat_websocket - {get_text('api_ws_description', 'WebSocket real-time chat')}
                </li>
                <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                    <span class="font-bold text-vanna-teal mr-2">POST</span>{api_base_url}/api/vanna/v2/chat_poll - {get_text('api_poll_description', 'Request/response polling')}
                </li>
                <li class="p-2 bg-vanna-cream/50 rounded font-mono text-sm">
                    <span class="font-bold text-vanna-teal mr-2">GET</span>{api_base_url}/health - {get_text('api_health_description', 'Health check')}
                </li>
            </ul>
        </div>
    '''
