"""
Gather Schema Tool for Database Chat Application.

This module provides a custom tool that allows admin users to manually
trigger schema training via the /gather command.
"""

import logging
from typing import Type
from pydantic import BaseModel, Field
from vanna.core.tool import Tool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

class GatherSchemaArgs(BaseModel):
    """Arguments for the gather schema tool."""
    pass

class GatherSchemaTool(Tool):
    """Tool for triggering manual schema training."""
    
    def __init__(self, schema_trainer):
        """Initialize the gather schema tool."""
        super().__init__()
        self.schema_trainer = schema_trainer

    @property
    def name(self) -> str:
        return "gather_schema"

    @property
    def description(self) -> str:
        return "Manually trigger database schema training. This will scan the database metadata and update the agent's memory. Use after database changes."

    def get_args_schema(self) -> Type[GatherSchemaArgs]:
        return GatherSchemaArgs
    
    async def execute(self, context: ToolContext, args: GatherSchemaArgs) -> ToolResult:
        """Execute the schema gathering process."""
        user = context.user
        
        # Check permissions
        if not user:
             return ToolResult(
                success=False,
                result_for_llm="Error: No user found in context."
            )
            
        user_groups = {g.lower() for g in user.group_memberships or []}
        if 'admin' not in user_groups and 'superuser' not in user_groups:
            return ToolResult(
                success=False,
                result_for_llm="Error: Only admin or superuser users can gather schema information."
            )
            
        logger.info(f"Schema training triggered by user: {user.id}")
        
        try:
            items_trained = self.schema_trainer.train_schema()
            
            return ToolResult(
                success=True,
                result_for_llm=f"Schema training completed successfully. Trained {items_trained} database objects. The schema information is now available in agent memory and will be retrieved via semantic search when needed."
            )
        except Exception as e:
            logger.error(f"Error in GatherSchemaTool: {e}")
            return ToolResult(
                success=False,
                result_for_llm=f"Error gathering schema: {str(e)}"
            )