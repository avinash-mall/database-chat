"""
Cleanup Memory Tool for Database Chat Application.

This module provides a custom tool that allows admin users to clear
all stored memories from Milvus via the /cleanup command.
"""

import logging
from typing import Type
from pydantic import BaseModel, Field
from vanna.core.tool import Tool, ToolContext, ToolResult
from pymilvus import connections, utility

logger = logging.getLogger(__name__)

class CleanupMemoryArgs(BaseModel):
    """Arguments for the cleanup memory tool."""
    confirm: bool = Field(..., description="Confirmation to delete all memories. MUST be True.")

class CleanupMemoryTool(Tool):
    """Tool for clearing Milvus agent memory."""
    
    def __init__(self, milvus_config):
        """Initialize the cleanup tool."""
        super().__init__()
        self.milvus_config = milvus_config

    @property
    def name(self) -> str:
        return "cleanup_memory"

    @property
    def description(self) -> str:
        return "Clear all stored memories from the agent's vector database (Milvus). Use this to start fresh before re-training."

    def get_args_schema(self) -> Type[CleanupMemoryArgs]:
        return CleanupMemoryArgs
    
    async def execute(self, context: ToolContext, args: CleanupMemoryArgs) -> ToolResult:
        """Execute the memory cleanup."""
        user = context.user if context else None
        username = user.username if user else "unknown"
        
        logger.info(f"Memory cleanup triggered by user: {username}")
        
        if not args.confirm:
            return ToolResult(
                success=False,
                result_for_llm="Cleanup cancelled. Confirmation was not provided."
            )
        
        try:
            # Connect to Milvus
            connections.connect(
                alias="default",
                host=self.milvus_config.host,
                port=self.milvus_config.port
            )
            
            # Drop collection if it exists
            if utility.has_collection(self.milvus_config.collection_name):
                utility.drop_collection(self.milvus_config.collection_name)
                msg = f"Successfully cleared all memories by dropping collection '{self.milvus_config.collection_name}'."
                logger.info(msg)
            else:
                msg = f"Collection '{self.milvus_config.collection_name}' does not exist. Nothing to clear."
                logger.warning(msg)
            
            return ToolResult(
                success=True,
                result_for_llm=f"{msg} You can now run /gather to re-train the agent."
            )
            
        except Exception as e:
            logger.error(f"Error during memory cleanup: {e}")
            return ToolResult(
                success=False,
                result_for_llm=f"Error clearing memory: {str(e)}"
            )
