"""
Configuration management for the Vanna Oracle Application.

This module provides centralized configuration with support for:
- Environment variables (recommended for production)
- Default values for development

Environment Variables:
    ORACLE_USER: Oracle database username (default: hr)
    ORACLE_PASSWORD: Oracle database password (default: hr123)
    ORACLE_DSN: Oracle connection string (default: localhost:1521/ORCL)
    
    OLLAMA_MODEL: Ollama model name (default: gpt-oss:20b)
    OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
    
    CHROMA_COLLECTION: ChromaDB collection name (default: vanna_memory)
    CHROMA_PERSIST_DIR: ChromaDB persistence directory (default: ./chroma_db)
    
    VANNA_HOST: Server host (default: 0.0.0.0)
    VANNA_PORT: Server port (default: 8000)

Usage:
    from app.config import config
    
    # Access configuration values
    print(config.oracle_user)
    print(config.ollama_model)
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OracleConfig:
    """Oracle database connection configuration."""
    user: str
    password: str
    dsn: str
    
    @classmethod
    def from_env(cls) -> "OracleConfig":
        """Load Oracle configuration from environment variables."""
        return cls(
            user=os.getenv("ORACLE_USER", "hr"),
            password=os.getenv("ORACLE_PASSWORD", "hr123"),
            dsn=os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1"),
        )


@dataclass
class OllamaConfig:
    """Ollama LLM service configuration."""
    model: str
    host: str
    timeout: float = 240.0
    num_ctx: int = 8192
    temperature: float = 0.7
    
    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Load Ollama configuration from environment variables."""
        return cls(
            model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "240.0")),
            num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "8192")),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
        )


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
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        # For gpt-oss-120b, use lower default temperature due to function calling issues
        default_temp = "0.1" if "gpt-oss-120b" in model.lower() else "0.7"
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE"),
            model=model,
            temperature=float(os.getenv("OPENAI_TEMPERATURE", default_temp)),
            timeout=float(os.getenv("OPENAI_TIMEOUT", "60.0")),
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
            collection_name=os.getenv("CHROMA_COLLECTION", "vanna_memory"),
            persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
        )


@dataclass
class ServerConfig:
    """FastAPI server configuration."""
    host: str
    port: int
    log_level: str
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables."""
        return cls(
            host=os.getenv("VANNA_HOST", "0.0.0.0"),
            port=int(os.getenv("VANNA_PORT", "8000")),
            log_level=os.getenv("VANNA_LOG_LEVEL", "info"),
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
        email_domain = os.getenv("EMAIL_DOMAIN", "vanna.ai")
        guest_username = os.getenv("GUEST_USERNAME", "guest")
        return cls(
            host=os.getenv("LDAP_HOST", "ldap"),
            port=int(os.getenv("LDAP_PORT", "389")),
            base_dn=os.getenv("LDAP_BASE_DN", "dc=vanna,dc=ai"),
            user_dn_template=os.getenv("LDAP_USER_DN_TEMPLATE", "cn={username},ou=users,dc=vanna,dc=ai"),
            admin_group_dn=os.getenv("LDAP_ADMIN_GROUP_DN", "cn=admin,ou=groups,dc=vanna,dc=ai"),
            bind_dn=os.getenv("LDAP_BIND_DN", "cn=admin,dc=vanna,dc=ai"),
            bind_password=os.getenv("LDAP_BIND_PASSWORD", "Vanna123"),
            use_ssl=os.getenv("LDAP_USE_SSL", "false").lower() == "true",
            email_domain=email_domain,
            guest_username=guest_username,
            guest_email=os.getenv("GUEST_EMAIL", f"{guest_username}@{email_domain}"),
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
        )
    
    # Convenience properties for backwards compatibility
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


# Global configuration instance
config = AppConfig.from_env()


def load_dotenv_if_available():
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


# Auto-load .env file when module is imported
load_dotenv_if_available()

