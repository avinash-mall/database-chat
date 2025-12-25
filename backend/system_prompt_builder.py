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
        include_rls_values: bool = True,
        schema_summary: str = None
    ):
        """
        Initialize the user-aware system prompt builder.
        
        Args:
            rls_service: The RLS service for fetching user filter values
            company_name: Company/application name for the prompt
            include_rls_values: Whether to include RLS filter values in prompt
            schema_summary: Pre-generated schema summary to include in prompts
        """
        self.rls_service = rls_service
        self.company_name = company_name
        self.include_rls_values = include_rls_values
        self.schema_summary = schema_summary
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
    
    def _is_normaluser(self, user: User) -> bool:
        """Check if user is specifically a NORMALUSER (not admin or superuser)."""
        if not user or not hasattr(user, 'group_memberships'):
            return False
        
        user_groups = {g.lower() for g in user.group_memberships}
        privileged_groups = {'admin', 'superuser'}
        
        # User is NORMALUSER if they have 'user' group but no privileged groups
        return 'user' in user_groups and not bool(privileged_groups & user_groups)
    
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
        
        # Build schema context if available
        schema_context = ""
        if self.schema_summary:
            schema_context = f"""
## Database Schema

The following database tables and relationships are available:

{self.schema_summary}
"""
        
        # Build RLS authorization instructions if user is NORMALUSER
        rls_instructions = ""
        if self._is_normaluser(user):
            rls_instructions = """
## Row-Level Security (RLS) Authorization Rules for NORMALUSER

**CRITICAL: This user is a NORMALUSER and has restricted data access.**

### Authorization Restrictions:
1. **Data Access Limit**: This user can ONLY access data belonging to them. They are UNAUTHORIZED to access any data belonging to other users.
2. **Automatic Filtering**: Row-Level Security (RLS) is automatically applied at the database level. All SQL queries are automatically modified to include WHERE clause filters that restrict results to only this user's data.
3. **No Bypass Possible**: Even if the user explicitly requests data for other users (e.g., "show me John's salary"), the RLS system will automatically filter the results to only show data matching this user's identity columns.
4. **Query Behavior**: When executing queries:
   - The system automatically injects WHERE conditions based on the user's identity columns (shown in User Context above)
   - Results will only contain rows where the identity columns match the user's values
   - If a query would return no results due to RLS filtering, inform the user that they don't have access to that data

### How to Handle Unauthorized Data Requests:
- If the user asks for data belonging to another person (e.g., "show me employee X's details"):
  - Politely inform them: "I can only access data that belongs to you due to row-level security restrictions. I'm unable to retrieve information for other users."
  - Explain that RLS automatically filters all queries to show only their own data
  - Offer to help them with queries about their own data instead

- If the user asks for aggregate data across all users (e.g., "show me all employees"):
  - Inform them: "Due to row-level security, I can only show you data that belongs to you. I cannot provide information about other users."
  - The query will automatically be filtered to only show their own records
  - If they need aggregate statistics, explain that they would need admin privileges

- If a query returns no results:
  - Check if it's because RLS filtered out all rows
  - Inform the user that the query was executed but no matching records were found in their accessible data
  - Suggest they may need to refine their query or that the data they're looking for may not be accessible to them

### Important Notes:
- **You do NOT need to manually add WHERE clauses** - RLS handles this automatically
- **You CAN execute queries normally** - The system will automatically apply filters
- **Always be helpful and clear** when explaining RLS restrictions to users
- **Never attempt to bypass RLS** - It's enforced at the database level and cannot be circumvented

"""
        
        # Combine prompts
        full_prompt = f"""{base_prompt}

## Current User Context

{user_context}
{schema_context}
## Important Instructions for User Queries

When the user asks about "my data", "my details", "my records", "my information", or uses phrases like "give me my...", "show me my...", "what are my...":

1. **You already know who they are** - Use the user information provided above
2. **Do NOT ask for their user ID or email** - You have this information
3. **Use the schema information above** to understand available tables and relationships
4. **Use JOINs** when you need related data (e.g., JOIN EMPLOYEES with JOBS for salary ranges)
{rls_instructions}
### Query Guidelines:

- **Row-Level Security (RLS)**: For NORMALUSER users, RLS automatically filters all query results at the database level based on their identity columns. Queries are automatically modified to include WHERE clause conditions that restrict access to only the user's own data.
- **Automatic Filtering**: You don't need to manually add WHERE clauses for user filtering - RLS handles this automatically. However, you should still inform users when they request data they're not authorized to access.
- **Unauthorized Data Access**: If a user requests data belonging to other users or aggregate data across all users, inform them that RLS restrictions prevent access to that information. The query will automatically be filtered, but you should explain the restriction clearly.
- **Query Execution**: Execute queries normally - the system will automatically apply RLS filters. If results are empty, it may be due to RLS filtering, so inform the user accordingly.
- Use the foreign key relationships shown above to JOIN tables correctly
- For salary comparisons, the JOBS table has MIN_SALARY and MAX_SALARY columns
- Always use the user's identity columns (EMPLOYEE_ID, EMAIL) when querying user-specific data

### Example: "Is my salary good for my job?"
Query approach:
```sql
SELECT e.SALARY, j.MIN_SALARY, j.MAX_SALARY, j.JOB_TITLE
FROM EMPLOYEES e
JOIN JOBS j ON e.JOB_ID = j.JOB_ID
WHERE e.EMPLOYEE_ID = <user's employee_id>
```
Note: For NORMALUSER, the WHERE clause will be automatically added by RLS even if you don't include it, but including it makes the query intent clearer.

## Visualization Guidelines

**IMPORTANT: You have access to the `visualize_data` tool. Use it proactively to create visualizations when they add value to the user's understanding of the data.**

### When to Create Visualizations Automatically:

After executing a SQL query, **automatically create a visualization** if the results contain:

1. **Numeric/Aggregate Data:**
   - Queries with aggregate functions (SUM, COUNT, AVG, MIN, MAX)
   - Queries with GROUP BY clauses showing comparisons
   - Statistical summaries or aggregations

2. **Time Series Data:**
   - Queries with date/time columns
   - Data showing trends over time
   - Historical comparisons (e.g., "sales by month", "employee count over time")

3. **Comparison Data:**
   - Queries comparing multiple categories (e.g., departments, products, regions)
   - Rankings or top N lists (e.g., "top 10 products", "highest salaries")
   - Distribution data (e.g., "employees by department", "sales by region")

4. **Relationship Data:**
   - Data showing correlations between variables
   - Multi-dimensional comparisons

### When NOT to Create Visualizations:

Do NOT create visualizations for:
- Simple lookups (single record retrieval)
- Text-only results without numeric data
- Very small result sets (1-2 rows) where a table is clearer
- When the user explicitly asks for text-only results or a table format
- When the data doesn't lend itself to meaningful visualization

### Tool Usage Instructions:

- **Use the `visualize_data` tool proactively** - Don't wait for the user to ask for a chart
- **Create visualizations automatically** when the query results are suitable for visualization
- **Choose appropriate chart types** based on the data:
  - **Bar charts**: For categorical comparisons, rankings, top N lists
  - **Line charts**: For time series, trends over time
  - **Pie charts**: For part-to-whole relationships, distributions
  - **Scatter plots**: For relationships between two numeric variables
  - **Histograms**: For distribution of numeric data

### Examples of Queries That Should Automatically Trigger Visualizations:

1. **"Show me sales by month"** → Create a line or bar chart showing sales trends
2. **"What are the top 10 products?"** → Create a bar chart showing the top products
3. **"Compare departments by revenue"** → Create a bar or pie chart comparing departments
4. **"Show employee count over time"** → Create a line chart showing the trend
5. **"What's the distribution of salaries?"** → Create a histogram or bar chart
6. **"Show me sales by region"** → Create a bar chart or pie chart comparing regions
7. **"Compare this year vs last year"** → Create a bar chart with grouped bars

### Visualization Best Practices:

- **Always provide the data table first**, then add the visualization as an enhancement
- **Explain what the visualization shows** in your response
- **Use clear, descriptive titles** for charts
- **Choose chart types that best represent the data** - don't force inappropriate visualizations
- **Respect user preferences** - if they explicitly ask for "just the table" or "no chart", don't create one

Remember: The goal is to enhance understanding through visual representation when it adds value. Use your judgment to determine when a visualization would be helpful versus when a table is sufficient.
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
        
        # Determine access level and add explicit RLS warnings for NORMALUSER
        if self._is_privileged_user(user):
            lines.append(f"**Access Level:** Full access (admin/superuser)")
        else:
            is_normaluser = self._is_normaluser(user)
            if is_normaluser:
                lines.append(f"**Access Level:** NORMALUSER - Row-Level Security (RLS) Applied")
                lines.append("")
                lines.append("**⚠️ IMPORTANT: RLS Authorization Restrictions**")
                lines.append("")
                lines.append("This user belongs to the NORMALUSER group and has the following restrictions:")
                lines.append("- **Can ONLY access data belonging to them** - Queries are automatically filtered to show only their own records")
                lines.append("- **Unauthorized to access other users' data** - Any attempt to query data not belonging to this user will be automatically filtered by RLS")
                lines.append("- **RLS is enforced at the database level** - The system automatically injects WHERE clause filters based on the user's identity columns")
                lines.append("- **No manual filtering needed** - The user's queries are automatically restricted, but you should inform them if they request data they're not authorized to see")
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
