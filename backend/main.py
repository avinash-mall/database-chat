"""
Vanna Oracle Database Agent Application.

This application connects to an Oracle database and provides a natural language
interface for querying data using the Vanna AI framework.

Usage:
    python -m backend.main
    
    Then access the web interface at http://localhost:8000
    
Environment Variables:
    See backend/config.py for all available configuration options.
    You can also create a .env file in the project root.
"""

from .config import config
from .server import VannaFlaskServer
from .agent_factory import create_agent


def main():
    """Main entry point for the application."""
    _print_startup_banner()
    
    agent = create_agent()
    
    server = VannaFlaskServer(agent)
    server.run(
        host=config.server.host,
        port=config.server.port,
        debug=(config.server.log_level == 'debug'),
    )


def _print_startup_banner():
    """Print the startup configuration banner."""
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


if __name__ == "__main__":
    main()
