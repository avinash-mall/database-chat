"""
Configuration management for the Oracle Database Application.

This module loads configuration from environment variables.
All required variables must be set - no fallbacks are provided.

Required Environment Variables:
    ORACLE_USER: Oracle database username
    ORACLE_PASSWORD: Oracle database password
    ORACLE_DSN: Oracle Database connection string
    
    OLLAMA_MODEL: Ollama model name (required if INFERENCE_PROVIDER=ollama)
    OLLAMA_HOST: Ollama server URL (required if INFERENCE_PROVIDER=ollama)
    
    OPENAI_API_KEY: OpenAI API key (required if INFERENCE_PROVIDER=openai)
    OPENAI_MODEL: OpenAI model name (required if INFERENCE_PROVIDER=openai)
    
    CHROMA_COLLECTION: ChromaDB collection name
    CHROMA_PERSIST_DIR: ChromaDB persistence directory
    
    VANNA_HOST: Server host
    VANNA_PORT: Server port
    
    LDAP_HOST: LDAP server host
    LDAP_PORT: LDAP server port
    LDAP_BASE_DN: LDAP base DN
    LDAP_USER_DN_TEMPLATE: LDAP user DN template
    LDAP_ADMIN_GROUP_DN: LDAP admin group DN
    LDAP_BIND_DN: LDAP bind DN
    LDAP_BIND_PASSWORD: LDAP bind password
    
Optional Environment Variables:
    All UI_* variables have defaults and are optional
    EMAIL_DOMAIN, GUEST_USERNAME, GUEST_EMAIL have defaults
    OLLAMA_TIMEOUT, OLLAMA_NUM_CTX, OLLAMA_TEMPERATURE have defaults
    OPENAI_BASE_URL, OPENAI_TEMPERATURE, OPENAI_TIMEOUT have defaults
    VANNA_LOG_LEVEL has default
    LDAP_USE_SSL has default

Usage:
    from backend.config import config
    
    # Access configuration values
    print(config.oracle.user)
    print(config.ollama.model)
"""

import os
from dataclasses import dataclass
from typing import Optional


def _require_env(key: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def _get_env(key: str, default: str = None) -> Optional[str]:
    """Get optional environment variable."""
    return os.getenv(key, default)


@dataclass
class OracleConfig:
    """Oracle database connection configuration."""
    user: str
    password: str
    dsn: str
    
    @classmethod
    def from_env(cls) -> "OracleConfig":
        """Load Oracle Database configuration from environment variables."""
        return cls(
            user=_require_env("ORACLE_USER"),
            password=_require_env("ORACLE_PASSWORD"),
            dsn=_require_env("ORACLE_DSN"),
        )


@dataclass
class OllamaConfig:
    """Ollama LLM service configuration."""
    model: Optional[str]
    host: Optional[str]
    timeout: float = 240.0
    num_ctx: int = 8192
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Load Ollama configuration from environment variables."""
        return cls(
            model=_get_env("OLLAMA_MODEL"),
            host=_get_env("OLLAMA_HOST"),
            timeout=float(_get_env("OLLAMA_TIMEOUT", "240.0")),
            num_ctx=int(_get_env("OLLAMA_NUM_CTX", "8192")),
            temperature=float(_get_env("OLLAMA_TEMPERATURE", "0.7")),
        )
    
    @property
    def is_configured(self) -> bool:
        """Check if Ollama is properly configured."""
        return self.model is not None and self.host is not None


@dataclass
class OpenAIConfig:
    """OpenAI LLM service configuration."""
    api_key: Optional[str]
    base_url: Optional[str]
    model: str
    temperature: float = 0.7
    timeout: float = 60.0
    
    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        """Load OpenAI configuration from environment variables."""
        api_key = _get_env("OPENAI_API_KEY")
        model = _get_env("OPENAI_MODEL", "gpt-4")
        default_temp = "0.1" if "gpt-oss-120b" in model.lower() else "0.7"
        
        return cls(
            api_key=api_key,
            base_url=_get_env("OPENAI_BASE_URL") or _get_env("OPENAI_API_BASE"),
            model=model,
            temperature=float(_get_env("OPENAI_TEMPERATURE", default_temp)),
            timeout=float(_get_env("OPENAI_TIMEOUT", "60.0")),
        )
    
    @property
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured."""
        return self.api_key is not None and self.api_key.strip() != ""


@dataclass
class ChromaConfig:
    """ChromaDB agent memory configuration."""
    collection_name: str
    persist_directory: str
    
    @classmethod
    def from_env(cls) -> "ChromaConfig":
        """Load ChromaDB configuration from environment variables."""
        return cls(
            collection_name=_require_env("CHROMA_COLLECTION"),
            persist_directory=_require_env("CHROMA_PERSIST_DIR"),
        )


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str
    port: int
    log_level: str
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables."""
        return cls(
            host=_require_env("VANNA_HOST"),
            port=int(_require_env("VANNA_PORT")),
            log_level=_get_env("VANNA_LOG_LEVEL", "info"),
        )


@dataclass
class LdapConfig:
    """LDAP authentication configuration."""
    host: str
    port: int
    base_dn: str
    user_dn_template: str
    admin_group_dn: str
    bind_dn: str
    bind_password: str
    use_ssl: bool = False
    email_domain: str = "vanna.ai"
    guest_username: str = "guest"
    guest_email: str = "guest@vanna.ai"
    
    @classmethod
    def from_env(cls) -> "LdapConfig":
        """Load LDAP configuration from environment variables."""
        email_domain = _get_env("EMAIL_DOMAIN", "vanna.ai")
        guest_username = _get_env("GUEST_USERNAME", "guest")
        
        return cls(
            host=_require_env("LDAP_HOST"),
            port=int(_require_env("LDAP_PORT")),
            base_dn=_require_env("LDAP_BASE_DN"),
            user_dn_template=_require_env("LDAP_USER_DN_TEMPLATE"),
            admin_group_dn=_require_env("LDAP_ADMIN_GROUP_DN"),
            bind_dn=_require_env("LDAP_BIND_DN"),
            bind_password=_require_env("LDAP_BIND_PASSWORD"),
            use_ssl=_get_env("LDAP_USE_SSL", "false").lower() == "true",
            email_domain=email_domain,
            guest_username=guest_username,
            guest_email=_get_env("GUEST_EMAIL", f"{guest_username}@{email_domain}"),
        )


@dataclass
class UITextConfig:
    """UI text strings configuration - all optional with defaults."""
    page_title: str = "Agents Chat"
    header_title: str = "Agents"
    header_subtitle: str = "DATA-FIRST AGENTS"
    header_description: str = "Interactive AI Assistant powered by Agents Framework"
    login_title: str = "Login to Continue"
    login_description: str = "Enter your credentials to access the chat"
    login_failed_label: str = "Login Failed:"
    username_label: str = "Username"
    username_placeholder: str = "Enter your username"
    password_label: str = "Password"
    password_placeholder: str = "Enter your password"
    login_button: str = "Login"
    authenticating_text: str = "Authenticating..."
    ldap_auth_note: str = "LDAP Authentication: Use your organizational credentials to log in."
    logged_in_prefix: str = "Logged in as"
    logout_button: str = "Logout"
    chat_title: str = "Oracle Database AI Chat"
    chat_welcome_title: str = "Welcome to Oracle Database AI"
    chat_welcome_message: str = "I'm your AI data analyst assistant. Ask me anything about your data in plain English!"
    chat_welcome_help: str = "Type `/help` to see what I can do."
    api_endpoints_title: str = "API Endpoints"
    api_sse_description: str = "Server-Sent Events streaming"
    api_ws_description: str = "WebSocket real-time chat"
    api_poll_description: str = "Request/response polling"
    api_health_description: str = "Health check"
    login_error_missing_fields: str = "Please enter both username and password."
    login_error_invalid_credentials: str = "Authentication failed. Please check your credentials and try again."
    login_error_generic: str = "An unexpected error occurred. Please check the browser console for details."
    login_error_form_elements_not_found: str = "Error: Login form elements not found. Please refresh the page."
    dev_mode_message: str = "Development Mode: Loading components from local assets"
    component_load_error_title: str = "Chat Component"
    component_load_error_message: str = "Web component failed to load. Please check your connection."
    component_load_error_loading_from: str = "Loading from:"
    
    @classmethod
    def from_env(cls) -> "UITextConfig":
        """Load UI text configuration from environment variables."""
        return cls(
            page_title=_get_env("UI_PAGE_TITLE", "Agents Chat"),
            header_title=_get_env("UI_HEADER_TITLE", "Agents"),
            header_subtitle=_get_env("UI_HEADER_SUBTITLE", "DATA-FIRST AGENTS"),
            header_description=_get_env("UI_HEADER_DESCRIPTION", "Interactive AI Assistant powered by Agents Framework"),
            login_title=_get_env("UI_LOGIN_TITLE", "Login to Continue"),
            login_description=_get_env("UI_LOGIN_DESCRIPTION", "Enter your credentials to access the chat"),
            login_failed_label=_get_env("UI_LOGIN_FAILED_LABEL", "Login Failed:"),
            username_label=_get_env("UI_USERNAME_LABEL", "Username"),
            username_placeholder=_get_env("UI_USERNAME_PLACEHOLDER", "Enter your username"),
            password_label=_get_env("UI_PASSWORD_LABEL", "Password"),
            password_placeholder=_get_env("UI_PASSWORD_PLACEHOLDER", "Enter your password"),
            login_button=_get_env("UI_LOGIN_BUTTON", "Login"),
            authenticating_text=_get_env("UI_AUTHENTICATING_TEXT", "Authenticating..."),
            ldap_auth_note=_get_env("UI_LDAP_AUTH_NOTE", "LDAP Authentication: Use your organizational credentials to log in."),
            logged_in_prefix=_get_env("UI_LOGGED_IN_PREFIX", "Logged in as"),
            logout_button=_get_env("UI_LOGOUT_BUTTON", "Logout"),
            chat_title=_get_env("UI_CHAT_TITLE", "Oracle Database AI Chat"),
            chat_welcome_title=_get_env("UI_CHAT_WELCOME_TITLE", "Welcome to Oracle Database AI"),
            chat_welcome_message=_get_env("UI_CHAT_WELCOME_MESSAGE", "I'm your AI data analyst assistant. Ask me anything about your data in plain English!"),
            chat_welcome_help=_get_env("UI_CHAT_WELCOME_HELP", "Type `/help` to see what I can do."),
            api_endpoints_title=_get_env("UI_API_ENDPOINTS_TITLE", "API Endpoints"),
            api_sse_description=_get_env("UI_API_SSE_DESCRIPTION", "Server-Sent Events streaming"),
            api_ws_description=_get_env("UI_API_WS_DESCRIPTION", "WebSocket real-time chat"),
            api_poll_description=_get_env("UI_API_POLL_DESCRIPTION", "Request/response polling"),
            api_health_description=_get_env("UI_API_HEALTH_DESCRIPTION", "Health check"),
            login_error_missing_fields=_get_env("UI_LOGIN_ERROR_MISSING_FIELDS", "Please enter both username and password."),
            login_error_invalid_credentials=_get_env("UI_LOGIN_ERROR_INVALID_CREDENTIALS", "Authentication failed. Please check your credentials and try again."),
            login_error_generic=_get_env("UI_LOGIN_ERROR_GENERIC", "An unexpected error occurred. Please check the browser console for details."),
            login_error_form_elements_not_found=_get_env("UI_LOGIN_ERROR_FORM_ELEMENTS_NOT_FOUND", "Error: Login form elements not found. Please refresh the page."),
            dev_mode_message=_get_env("UI_DEV_MODE_MESSAGE", "Development Mode: Loading components from local assets"),
            component_load_error_title=_get_env("UI_COMPONENT_LOAD_ERROR_TITLE", "Chat Component"),
            component_load_error_message=_get_env("UI_COMPONENT_LOAD_ERROR_MESSAGE", "Web component failed to load. Please check your connection."),
            component_load_error_loading_from=_get_env("UI_COMPONENT_LOAD_ERROR_LOADING_FROM", "Loading from:"),
        )


@dataclass
class UIConfig:
    """UI settings configuration."""
    show_api_endpoints: bool = True
    text: UITextConfig = None
    
    def __post_init__(self):
        """Initialize text config if not provided."""
        if self.text is None:
            self.text = UITextConfig.from_env()
    
    @classmethod
    def from_env(cls) -> "UIConfig":
        """Load UI configuration from environment variables."""
        return cls(
            show_api_endpoints=_get_env("UI_SHOW_API_ENDPOINTS", "true").lower() == "true",
            text=UITextConfig.from_env(),
        )


@dataclass
class AgentConfig:
    """Agent configuration."""
    max_tool_iterations: int = 10
    
    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load agent configuration from environment variables."""
        return cls(
            max_tool_iterations=int(_get_env("VANNA_MAX_TOOL_ITERATIONS", "10")),
        )


@dataclass
class AppConfig:
    """Complete application configuration."""
    oracle: OracleConfig
    ollama: OllamaConfig
    openai: OpenAIConfig
    chroma: ChromaConfig
    server: ServerConfig
    ldap: LdapConfig
    ui: UIConfig
    agent: AgentConfig
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load complete configuration from environment variables."""
        return cls(
            oracle=OracleConfig.from_env(),
            ollama=OllamaConfig.from_env(),
            openai=OpenAIConfig.from_env(),
            chroma=ChromaConfig.from_env(),
            server=ServerConfig.from_env(),
            ldap=LdapConfig.from_env(),
            ui=UIConfig.from_env(),
            agent=AgentConfig.from_env(),
        )
    
    @property
    def oracle_user(self) -> str:
        return self.oracle.user
    
    @property
    def oracle_password(self) -> str:
        return self.oracle.password
    
    @property
    def oracle_dsn(self) -> str:
        return self.oracle.dsn
    
    @property
    def ollama_model(self) -> str:
        return self.ollama.model
    
    @property
    def ollama_host(self) -> str:
        return self.ollama.host
    
    @property
    def inference_provider(self) -> str:
        """Get the inference provider from environment variable."""
        return _get_env("INFERENCE_PROVIDER", "ollama").lower()


def load_dotenv_if_available():
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


# Auto-load .env file when module is imported
load_dotenv_if_available()

# Global configuration instance
config = AppConfig.from_env()
