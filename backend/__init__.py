"""
Vanna Oracle Database Agent Application.

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
    - MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION
    - VANNA_HOST, VANNA_PORT
    - LDAP_HOST, LDAP_PORT, LDAP_BASE_DN, etc.

Modules:
    - main.py: Application entry point
    - config.py: Configuration management with env var support
    - server.py: Custom Flask server with LDAP authentication
    - auth.py: Hybrid LDAP + database role authentication
    - agent_factory.py: Agent creation and configuration
"""

from .config import (
    config,
    AppConfig,
    OracleConfig,
    OllamaConfig,
    OpenAIConfig,
    MilvusConfig,
    ServerConfig,
    LdapConfig,
)
from .main import main
from .server import VannaFlaskServer
from .auth import HybridUserResolver
from .agent_factory import create_agent

__all__ = [
    # Configuration
    "config",
    "AppConfig",
    "OracleConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "MilvusConfig",
    "ServerConfig",
    "LdapConfig",
    # Main application
    "main",
    "VannaFlaskServer",
    "HybridUserResolver",
    "create_agent",
]

