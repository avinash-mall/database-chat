"""
Agent Factory for Database Chat Application.

This module provides the factory function for creating and configuring
the Vanna Agent with all required services, tools, and integrations.
"""

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.tools import VisualizeDataTool
from vanna.tools.file_system import WriteFileTool
from vanna.integrations.local import LocalFileSystem
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
    SaveTextMemoryTool,
)
from vanna.integrations.ollama import OllamaLlmService
from vanna.integrations.openai import OpenAILlmService
from vanna.integrations.oracle import OracleRunner
from vanna.integrations.milvus import MilvusAgentMemory

from .config import config
from .auth import HybridUserResolver
from .rls_service import RowLevelSecurityService, RLSConfig
from .secure_sql_tool import SecureRunSqlTool
from .system_prompt_builder import UserAwareSystemPromptBuilder
from .schema_trainer import SchemaTrainer
from .gather_schema_tool import GatherSchemaTool
from .cleanup_memory_tool import CleanupMemoryTool
from .discover_tables_tool import ListAllTablesTool


def create_agent() -> Agent:
    """Create and configure the Vanna Agent with Oracle database connection.
    
    This factory function:
    1. Configures LLM service (OpenAI or Ollama based on INFERENCE_PROVIDER)
    2. Sets up Oracle database runner and Milvus agent memory
    3. Configures Row-Level Security (RLS) for query filtering
    4. Registers all tools with appropriate access controls
    5. Creates user-aware system prompt builder
    
    Returns:
        Configured Agent instance ready to handle requests.
        
    Raises:
        ValueError: If LLM provider is not properly configured.
    """
    llm = _create_llm_service()
    oracle_runner = _create_oracle_runner()
    agent_memory = _create_agent_memory()
    rls_service = _create_rls_service()
    user_resolver = HybridUserResolver(
        ldap_config=config.ldap, 
        oracle_config=config.oracle
    )
    
    # Create schema trainer for /gather command
    schema_trainer = SchemaTrainer(
        oracle_config=config.oracle,
        agent_memory=agent_memory,
        llm_service=llm,
        openai_config=config.openai
    )
    
    # Register all tools
    tools = _register_tools(oracle_runner, rls_service, schema_trainer)
    
    # Create system prompt builder with RLS awareness
    system_prompt_builder = UserAwareSystemPromptBuilder(
        rls_service=rls_service,
        company_name="Database Chat",
        include_rls_values=True
    )
    
    # Create agent configuration
    agent_config = AgentConfig(
        max_tool_iterations=config.agent.max_tool_iterations
    )
    
    return Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=agent_config,
        system_prompt_builder=system_prompt_builder
    )


def _create_llm_service():
    """Create and configure the LLM service.
    
    Returns:
        Configured LLM service (OpenAI or Ollama).
        
    Raises:
        ValueError: If the selected provider is not properly configured.
    """
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
        
        return OpenAILlmService(**llm_kwargs)
    else:
        if not config.ollama.is_configured:
            raise ValueError(
                "INFERENCE_PROVIDER is set to 'ollama' but Ollama is not properly configured. "
                "Please set OLLAMA_MODEL and OLLAMA_HOST in your environment variables."
            )
        
        return OllamaLlmService(
            model=config.ollama.model,
            host=config.ollama.host,
            timeout=config.ollama.timeout,
            num_ctx=config.ollama.num_ctx,
            temperature=config.ollama.temperature,
        )


def _create_oracle_runner() -> OracleRunner:
    """Create the Oracle database runner.
    
    Returns:
        Configured OracleRunner instance.
    """
    return OracleRunner(
        user=config.oracle.user,
        password=config.oracle.password,
        dsn=config.oracle.dsn
    )


def _create_agent_memory() -> MilvusAgentMemory:
    """Create the Milvus agent memory.
    
    Returns:
        Configured MilvusAgentMemory instance.
    """
    return MilvusAgentMemory(
        host=config.milvus.host,
        port=config.milvus.port,
        collection_name=config.milvus.collection_name
    )


def _create_rls_service() -> RowLevelSecurityService:
    """Create and configure the Row-Level Security service.
    
    Returns:
        Configured RowLevelSecurityService instance.
    """
    rls_config = RLSConfig(
        enabled=config.rls.enabled,
        cache_ttl=config.rls.cache_ttl,
        excluded_tables=config.rls.excluded_tables_list
    )
    
    rls_service = RowLevelSecurityService(
        oracle_config=config.oracle,
        rls_config=rls_config
    )
    
    print(f"RLS: Enabled={config.rls.enabled}, CacheTTL={config.rls.cache_ttl}s")
    if config.rls.excluded_tables_list:
        print(f"RLS: Excluded tables: {config.rls.excluded_tables_list}")
    
    return rls_service


def _register_tools(
    oracle_runner: OracleRunner,
    rls_service: RowLevelSecurityService,
    schema_trainer: SchemaTrainer
) -> ToolRegistry:
    """Register all tools with the tool registry.
    
    Args:
        oracle_runner: The Oracle database runner.
        rls_service: The Row-Level Security service.
        schema_trainer: The schema trainer instance.
        
    Returns:
        Configured ToolRegistry with all tools registered.
    """
    tools = ToolRegistry()
    
    # Database query tool with RLS
    db_tool = SecureRunSqlTool(
        sql_runner=oracle_runner,
        rls_service=rls_service
    )
    tools.register_local_tool(db_tool, access_groups=['admin', 'superuser', 'user'])
    
    # Memory tools
    tools.register_local_tool(
        SaveQuestionToolArgsTool(), 
        access_groups=['admin', 'superuser']
    )
    tools.register_local_tool(
        SearchSavedCorrectToolUsesTool(), 
        access_groups=['admin', 'superuser', 'user']
    )
    tools.register_local_tool(
        SaveTextMemoryTool(), 
        access_groups=['admin', 'superuser', 'user']
    )
    
    # Schema tools
    tools.register_local_tool(
        GatherSchemaTool(schema_trainer), 
        access_groups=['admin', 'superuser']
    )
    tools.register_local_tool(
        CleanupMemoryTool(config.milvus), 
        access_groups=['admin', 'superuser']
    )
    tools.register_local_tool(
        ListAllTablesTool(config.oracle), 
        access_groups=['admin', 'superuser', 'user']
    )
    
    # File system tools
    file_system = LocalFileSystem()
    tools.register_local_tool(
        VisualizeDataTool(file_system=file_system), 
        access_groups=['admin', 'superuser', 'user']
    )
    tools.register_local_tool(
        WriteFileTool(file_system=file_system), 
        access_groups=['admin', 'superuser', 'user']
    )
    
    return tools
