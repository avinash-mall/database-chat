"""
User-Aware System Prompt Builder for Database Chat Application.

This module provides a custom SystemPromptBuilder that injects user context
into the LLM system prompt, including:
- User's identity (username, email, groups)
- User's RLS filter values from AI_USERS table
- Instructions for handling "my data" queries

This allows the LLM to automatically know who the user is when they ask
questions like "give me my details" or "show my orders".
"""

import logging
from typing import List, Dict, Any, Optional

from vanna.core.system_prompt import SystemPromptBuilder, DefaultSystemPromptBuilder
from vanna.core.user import User

from .rls_service import RowLevelSecurityService

logger = logging.getLogger(__name__)


class UserAwareSystemPromptBuilder(SystemPromptBuilder):
    """
    A system prompt builder that includes user context in the LLM prompt.
    
    This builder:
    1. Extends the default system prompt with user identity
    2. Includes user's filter column values from AI_USERS table
    3. Provides instructions for the LLM to use user context appropriately
    """
    
    def __init__(
        self, 
        rls_service: RowLevelSecurityService,
        company_name: str = "Database Chat",
        include_rls_values: bool = True
    ):
        """
        Initialize the user-aware system prompt builder.
        
        Args:
            rls_service: The RLS service for fetching user filter values
            company_name: Company/application name for the prompt
            include_rls_values: Whether to include RLS filter values in prompt
        """
        self.rls_service = rls_service
        self.company_name = company_name
        self.include_rls_values = include_rls_values
        self._default_builder = DefaultSystemPromptBuilder()
        
        # Cache for user filter values
        self._user_filter_cache: Dict[str, Dict[str, Any]] = {}
    
    def _get_user_filter_values(self, username: str) -> Dict[str, Any]:
        """Get user's filter values with caching."""
        if username not in self._user_filter_cache:
            self._user_filter_cache[username] = self.rls_service.get_user_filter_values(username)
        return self._user_filter_cache[username]
    
    def _is_privileged_user(self, user: User) -> bool:
        """Check if user has privileged access (admin or superuser)."""
        if not user or not hasattr(user, 'group_memberships'):
            return False
        
        privileged_groups = {'admin', 'superuser'}
        user_groups = {g.lower() for g in user.group_memberships}
        
        return bool(privileged_groups & user_groups)
    
    async def build_system_prompt(
        self, 
        user: User, 
        tools: List[Any]
    ) -> Optional[str]:
        """
        Build the system prompt with user context included.
        
        Args:
            user: The current user
            tools: List of available tool schemas
            
        Returns:
            The complete system prompt string
        """
        # Start with base prompt (await since it's async)
        base_prompt = await self._default_builder.build_system_prompt(user, tools)
        if base_prompt is None:
            base_prompt = ""
        
        # Build user context section
        user_context = self._build_user_context(user)
        
        # Combine prompts
        full_prompt = f"""{base_prompt}

## Current User Context

{user_context}

## Important Instructions for User Context

When the user asks about "my data", "my details", "my records", "my information", or uses phrases like "give me my...", "show me my...", "what are my...":

1. **You already know who they are** - Use the user information provided above
2. **Do NOT ask for their user ID or email** - You have this information
3. **If you don't know which table to query**, use the `discover_my_tables` tool first to find tables containing the user's identity columns
4. **Use the appropriate identifier columns** when querying their data

### Recommended Workflow for "My Data" Queries:

1. First, call `discover_my_tables` to find tables/views/materialized views with user identity columns
2. Review the discovered tables and select the most relevant one(s) for the user's question
3. Use `run_sql` to query the selected table(s) - row-level security will automatically filter results

### Identity Column Filtering:
- If querying a table that has an EMPLOYEE_ID column, filter by the user's EMPLOYEE_ID
- If querying a table that has an EMAIL column, filter by the user's EMAIL
- If querying a table that has a PERSON_ID column, filter by the user's PERSON_ID
- If querying a table that has a USERNAME column, filter by the user's USERNAME
"""
        
        logger.debug(f"SystemPrompt: Built prompt for user '{user.id}' with context")
        return full_prompt
    
    def _build_user_context(self, user: User) -> str:
        """Build the user context section of the prompt."""
        lines = []
        
        # Basic user info
        lines.append(f"**Username:** {user.id}")
        if hasattr(user, 'email') and user.email:
            lines.append(f"**Email:** {user.email}")
        if hasattr(user, 'group_memberships') and user.group_memberships:
            lines.append(f"**Groups/Roles:** {', '.join(user.group_memberships)}")
        
        # Determine access level
        if self._is_privileged_user(user):
            lines.append(f"**Access Level:** Full access (admin/superuser)")
        else:
            lines.append(f"**Access Level:** Restricted (row-level security applied)")
        
        # Include RLS filter values if enabled
        if self.include_rls_values:
            filter_values = self._get_user_filter_values(user.id)
            if filter_values:
                lines.append("")
                lines.append("**User Identity Columns (use these to filter 'my data' queries):**")
                for col_name, col_value in filter_values.items():
                    lines.append(f"- {col_name}: {col_value}")
            else:
                lines.append("")
                lines.append("**Note:** No additional identity columns configured for this user in AI_USERS table.")
        
        return "\n".join(lines)
    
    def clear_cache(self, username: str = None):
        """Clear the user filter cache."""
        if username:
            self._user_filter_cache.pop(username, None)
        else:
            self._user_filter_cache.clear()
