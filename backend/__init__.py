"""
Vanna Oracle Database Agent Application

This package contains a complete example application that connects Vanna to an
Oracle database running on localhost, enabling natural language queries against
your Oracle data.

Quick Start:
    1. Ensure Oracle database is running at localhost:1521
    2. Ensure Ollama is running at localhost:11434 with the 'gpt-oss:20b' model
    3. Run: python -m backend.main
    4. Open http://localhost:8000 in your browser

Configuration:
    Set environment variables or create a .env file:
    - ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN
    - OLLAMA_MODEL, OLLAMA_HOST
    - CHROMA_COLLECTION, CHROMA_PERSIST_DIR
    - VANNA_HOST, VANNA_PORT
    - LDAP_HOST, LDAP_PORT, LDAP_BASE_DN, etc.

Components:
    - main.py: Application entry point
    - config.py: Configuration management with env var support
    - create_agent(): Factory function to create configured agent
    - HybridUserResolver: LDAP auth + Database role resolution

For production deployments, consider:
    - Using environment variables for sensitive credentials
    - Setting up proper CORS and security headers
"""

from .config import config, AppConfig, OracleConfig, OllamaConfig, OpenAIConfig, ChromaConfig, ServerConfig, LdapConfig
from .main import create_agent, main, HybridUserResolver

__all__ = [
    # Configuration
    "config",
    "AppConfig",
    "OracleConfig", 
    "OllamaConfig",
    "OpenAIConfig",
    "ChromaConfig",
    "ServerConfig",
    "LdapConfig",
    # Main application
    "create_agent",
    "main", 
    "HybridUserResolver",
]
