"""
Secure SQL Tool with Row-Level Security.

This module provides a custom SQL execution tool that applies row-level
security (RLS) filtering for NORMALUSER role. It wraps the standard
RunSqlTool and injects WHERE clause filters based on user's AI_USERS data.

For ADMIN and SUPERUSER roles, queries are executed without filtering.
"""

import logging
from typing import Type, List, Optional, Dict, Any
from pydantic import BaseModel, Field

from vanna.core.tool import Tool, ToolContext, ToolResult
from vanna.components import DataFrameComponent
from vanna.capabilities.sql_runner.models import RunSqlToolArgs

from .rls_service import RowLevelSecurityService

logger = logging.getLogger(__name__)


class SecureSqlArgs(BaseModel):
    """Arguments for the secure SQL tool."""
    sql: str = Field(description="The SQL query to execute")


class SecureRunSqlTool(Tool[SecureSqlArgs]):
    """
    A secure SQL execution tool that applies row-level security.
    
    This tool:
    1. Checks the user's role (admin, superuser, or user/normaluser)
    2. For NORMALUSER, applies RLS filtering by injecting WHERE clauses
    3. Executes the (potentially modified) query
    4. Returns results with appropriate filtering applied
    
    Security model:
    - ADMIN: Full access to all data
    - SUPERUSER: Full access to all data
    - USER/NORMALUSER: Filtered access based on AI_USERS filter columns
    """
    
    def __init__(self, sql_runner, rls_service: RowLevelSecurityService):
        """
        Initialize the secure SQL tool.
        
        Args:
            sql_runner: The database runner (e.g., OracleRunner) for executing queries
            rls_service: The RLS service for applying security filters
        """
        self.sql_runner = sql_runner
        self.rls_service = rls_service
        # Cache for user filter values to avoid repeated DB queries in same session
        self._user_filter_cache: Dict[str, Any] = {}
    
    @property
    def name(self) -> str:
        return "run_sql"
    
    @property
    def description(self) -> str:
        return (
            "Execute a SQL query against the database. "
            "Results may be filtered based on your access level. "
            "Use this to retrieve, analyze, or modify data."
        )
    
    def get_args_schema(self) -> Type[SecureSqlArgs]:
        return SecureSqlArgs
    
    def _is_privileged_user(self, user) -> bool:
        """
        Check if user has privileged access (admin or superuser).
        
        Args:
            user: The User object from context
            
        Returns:
            True if user is admin or superuser, False otherwise
        """
        if not user or not hasattr(user, 'group_memberships'):
            return False
        
        privileged_groups = {'admin', 'superuser'}
        user_groups = {g.lower() for g in user.group_memberships}
        
        return bool(privileged_groups & user_groups)
    
    def _get_user_filter_values(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's filter values with caching.
        
        Args:
            user_id: The user's ID/username
            
        Returns:
            Dictionary of filter column values
        """
        if user_id not in self._user_filter_cache:
            self._user_filter_cache[user_id] = self.rls_service.get_user_filter_values(user_id)
        return self._user_filter_cache[user_id]
    
    async def _execute_query(self, sql: str, bind_params: dict = None, context = None):
        """
        Execute a SQL query using the sql_runner.
        
        Args:
            sql: The SQL query to execute
            bind_params: Optional bind parameters for the query
            context: Optional ToolContext to pass to run_sql
            
        Returns:
            Query results (typically a pandas DataFrame)
        """
        # The sql_runner.run() method may not support bind_params directly
        # We need to handle this based on the runner's capabilities
        
        if bind_params:
            # If we have bind params, we need to execute with them
            # The OracleRunner typically uses oracledb which supports bind params
            import oracledb
            
            try:
                connection = oracledb.connect(
                    user=self.sql_runner.user,
                    password=self.sql_runner.password,
                    dsn=self.sql_runner.dsn
                )
                cursor = connection.cursor()
                cursor.execute(sql, bind_params)
                
                # Fetch results
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                
                cursor.close()
                connection.close()
                
                # Convert to pandas DataFrame
                import pandas as pd
                if columns and rows:
                    return pd.DataFrame(rows, columns=columns)
                elif columns:
                    return pd.DataFrame(columns=columns)
                else:
                    return pd.DataFrame()
                    
            except oracledb.Error as e:
                logger.error(f"Database error executing secure query: {e}")
                raise RuntimeError(f"Database error: {e}")
        else:
            # No bind params, use the standard runner
            # run_sql requires RunSqlToolArgs and ToolContext, and is async
            if context is None:
                raise ValueError("context is required for OracleRunner.run_sql()")
            
            sql_args = RunSqlToolArgs(sql=sql)
            result = await self.sql_runner.run_sql(sql_args, context)
            return result
    
    async def execute(self, context: ToolContext, args: SecureSqlArgs) -> ToolResult:
        """
        Execute a SQL query with row-level security applied.
        
        Args:
            context: The tool execution context containing user info
            args: The SQL query arguments
            
        Returns:
            ToolResult with query results or error
        """
        user = context.user
        original_sql = args.sql.strip()
        
        logger.info(f"SecureRunSqlTool: Executing query for user '{user.id}'")
        logger.debug(f"SecureRunSqlTool: Original SQL: {original_sql}")
        
        try:
            # Check if user is privileged
            if self._is_privileged_user(user):
                logger.info(f"SecureRunSqlTool: User '{user.id}' is privileged, no RLS applied")
                result_df = await self._execute_query(original_sql, None, context)
            else:
                # User is NORMALUSER - apply RLS filtering
                logger.info(f"SecureRunSqlTool: User '{user.id}' requires RLS filtering")
                
                # Get user's filter values
                filter_values = self._get_user_filter_values(user.id)
                
                if filter_values:
                    # Apply RLS filters to the query
                    modified_sql, bind_params = self.rls_service.apply_rls_filters(
                        original_sql, 
                        filter_values
                    )
                    
                    logger.info(f"SecureRunSqlTool: RLS applied, modified query: {modified_sql[:200]}...")
                    result_df = await self._execute_query(modified_sql, bind_params, context)
                else:
                    # No filter values - execute original query
                    # This could mean the user has NULL values in filter columns
                    logger.warning(f"SecureRunSqlTool: No filter values for user '{user.id}', executing original query")
                    result_df = await self._execute_query(original_sql, None, context)
            
            # Build result
            row_count = len(result_df) if hasattr(result_df, '__len__') else 0
            
            # Create result summary for LLM
            if row_count == 0:
                result_text = "Query executed successfully. No rows returned."
            else:
                result_text = f"Query executed successfully. Returned {row_count} row(s)."
                if row_count <= 10:
                    result_text += f"\n\nData:\n{result_df.to_string()}"
                else:
                    result_text += f"\n\nFirst 10 rows:\n{result_df.head(10).to_string()}"
            
            return ToolResult(
                success=True,
                result_for_llm=result_text,
                metadata={
                    "row_count": row_count,
                    "rls_applied": not self._is_privileged_user(user),
                    "user_id": user.id
                }
            )
            
        except Exception as e:
            logger.error(f"SecureRunSqlTool: Error executing query: {e}")
            import traceback
            traceback.print_exc()
            
            return ToolResult(
                success=False,
                result_for_llm=f"Error executing SQL query: {str(e)}",
                error=str(e),
                metadata={"user_id": user.id}
            )
    
    def clear_user_cache(self, user_id: str = None):
        """
        Clear the user filter cache.
        
        Args:
            user_id: Optional specific user to clear. If None, clears all.
        """
        if user_id:
            self._user_filter_cache.pop(user_id, None)
        else:
            self._user_filter_cache.clear()
