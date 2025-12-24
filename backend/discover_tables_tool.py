"""
User Data Discovery Tool for Database Chat Application.

This tool discovers database tables, views, and materialized views that contain
the user's identity columns (EMPLOYEE_ID, EMAIL, PERSON_ID, etc.).

It queries Oracle metadata to find matching objects and returns structured
information to help the LLM decide which tables are relevant for user queries.
"""

import logging
from typing import Type, List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

from vanna.core.tool import Tool, ToolContext, ToolResult
from vanna.components import SimpleTextComponent

import oracledb

from .rls_service import RowLevelSecurityService

logger = logging.getLogger(__name__)

# Tables to exclude from discovery (system/internal tables)
EXCLUDED_TABLES = {
    'AI_USERS',  # The identity table itself
    'CHAINED_ROWS',
    'PLAN_TABLE',
    'MVIEW$_ADV_WORKLOAD',
    'MVIEW$_ADV_LOG',
}


class DiscoverTablesArgs(BaseModel):
    """Arguments for the discover tables tool."""
    include_all_columns: bool = Field(
        default=False, 
        description="If true, include all column names for each table. If false, only show matching identity columns."
    )


class DiscoverUserTablesTool(Tool[DiscoverTablesArgs]):
    """
    A tool to discover database tables containing the user's identity columns.
    
    This tool:
    1. Gets the user's identity columns from AI_USERS (EMPLOYEE_ID, EMAIL, etc.)
    2. Queries Oracle metadata to find tables/views/MVs with matching columns
    3. Returns structured information to help the LLM query relevant tables
    
    Access: Available to all authenticated users.
    """
    
    def __init__(self, rls_service: RowLevelSecurityService, oracle_config):
        """
        Initialize the discovery tool.
        
        Args:
            rls_service: RLS service for getting filter columns
            oracle_config: Oracle database configuration
        """
        self.rls_service = rls_service
        self.oracle_config = oracle_config
        
        # Cache for discovered tables (refreshed on each call but cached within call)
        self._schema_cache: Optional[Dict[str, Any]] = None
    
    @property
    def name(self) -> str:
        return "discover_my_tables"
    
    @property
    def description(self) -> str:
        return (
            "Discover which database tables, views, and materialized views contain "
            "your identity columns (like EMPLOYEE_ID, EMAIL, PERSON_ID). "
            "Use this tool when you need to find where the user's data is stored "
            "before running SQL queries."
        )
    
    def get_args_schema(self) -> Type[DiscoverTablesArgs]:
        return DiscoverTablesArgs
    
    def _get_connection(self) -> oracledb.Connection:
        """Create a database connection."""
        return oracledb.connect(
            user=self.oracle_config.user,
            password=self.oracle_config.password,
            dsn=self.oracle_config.dsn
        )
    
    def _discover_tables_with_columns(
        self, 
        filter_columns: List[str],
        include_all_columns: bool
    ) -> Dict[str, Dict[str, Any]]:
        """
        Discover tables that contain any of the filter columns.
        
        Args:
            filter_columns: List of column names to search for
            include_all_columns: Whether to include all columns or just matching ones
            
        Returns:
            Dictionary mapping table names to their info
        """
        if not filter_columns:
            return {}
        
        tables_info = {}
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Build query to find matching tables/views/MVs
            # Include TABLE, VIEW, and MATERIALIZED VIEW
            placeholders = ", ".join([f":col{i}" for i in range(len(filter_columns))])
            bind_params = {f"col{i}": col for i, col in enumerate(filter_columns)}
            
            query = f"""
                SELECT DISTINCT 
                    utc.TABLE_NAME,
                    utc.COLUMN_NAME,
                    CASE 
                        WHEN ut.TABLE_NAME IS NOT NULL THEN 'TABLE'
                        WHEN uv.VIEW_NAME IS NOT NULL THEN 'VIEW'
                        WHEN um.MVIEW_NAME IS NOT NULL THEN 'MATERIALIZED VIEW'
                        ELSE 'UNKNOWN'
                    END AS OBJECT_TYPE
                FROM USER_TAB_COLUMNS utc
                LEFT JOIN USER_TABLES ut ON utc.TABLE_NAME = ut.TABLE_NAME
                LEFT JOIN USER_VIEWS uv ON utc.TABLE_NAME = uv.VIEW_NAME
                LEFT JOIN USER_MVIEWS um ON utc.TABLE_NAME = um.MVIEW_NAME
                WHERE utc.COLUMN_NAME IN ({placeholders})
                ORDER BY utc.TABLE_NAME, utc.COLUMN_NAME
            """
            
            cursor.execute(query, bind_params)
            
            for row in cursor.fetchall():
                table_name, column_name, object_type = row
                
                # Skip excluded tables
                if table_name.upper() in EXCLUDED_TABLES:
                    continue
                
                if table_name not in tables_info:
                    tables_info[table_name] = {
                        "object_type": object_type,
                        "matching_columns": [],
                        "all_columns": []
                    }
                
                tables_info[table_name]["matching_columns"].append(column_name)
            
            # If requested, get all columns for each discovered table
            if include_all_columns and tables_info:
                for table_name in tables_info.keys():
                    cursor.execute(
                        """
                        SELECT COLUMN_NAME, DATA_TYPE 
                        FROM USER_TAB_COLUMNS 
                        WHERE TABLE_NAME = :table_name
                        ORDER BY COLUMN_ID
                        """,
                        {"table_name": table_name}
                    )
                    columns = []
                    for col_row in cursor.fetchall():
                        col_name, data_type = col_row
                        columns.append(f"{col_name} ({data_type})")
                    tables_info[table_name]["all_columns"] = columns
            
            cursor.close()
            connection.close()
            
        except oracledb.Error as e:
            logger.error(f"DiscoverUserTablesTool: Database error: {e}")
            raise RuntimeError(f"Database error during table discovery: {e}")
        
        return tables_info
    
    async def execute(self, context: ToolContext, args: DiscoverTablesArgs) -> ToolResult:
        """
        Execute the table discovery.
        
        Args:
            context: Tool execution context with user info
            args: Tool arguments
            
        Returns:
            ToolResult with discovered tables information
        """
        user = context.user
        logger.info(f"DiscoverUserTablesTool: Executing for user '{user.id}'")
        
        try:
            # Get the filter columns (identity columns)
            filter_columns = self.rls_service.get_filter_columns()
            
            if not filter_columns:
                return ToolResult(
                    success=True,
                    result_for_llm=(
                        "No identity columns are configured in the system. "
                        "The AI_USERS table only has standard columns (USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER). "
                        "Please ask the database administrator to add identity columns like EMPLOYEE_ID, EMAIL, etc."
                    ),
                    metadata={"filter_columns": [], "tables_found": 0}
                )
            
            # Get the user's filter values for context
            user_filter_values = self.rls_service.get_user_filter_values(user.id)
            
            # Discover tables with matching columns
            tables_info = self._discover_tables_with_columns(
                filter_columns=filter_columns,
                include_all_columns=args.include_all_columns
            )
            
            if not tables_info:
                return ToolResult(
                    success=True,
                    result_for_llm=(
                        f"No tables, views, or materialized views were found containing the identity columns: {filter_columns}. "
                        "This means the database schema does not have tables with these column names."
                    ),
                    metadata={
                        "filter_columns": filter_columns,
                        "tables_found": 0
                    }
                )
            
            # Build result for LLM
            result_lines = []
            result_lines.append(f"## Discovered Tables/Views with Your Identity Columns")
            result_lines.append("")
            result_lines.append(f"**Your Identity Columns:** {', '.join(filter_columns)}")
            result_lines.append(f"**Your Values:** {user_filter_values}")
            result_lines.append("")
            result_lines.append(f"**Found {len(tables_info)} database objects:**")
            result_lines.append("")
            
            for table_name, info in sorted(tables_info.items()):
                result_lines.append(f"### {table_name} ({info['object_type']})")
                result_lines.append(f"- **Matching identity columns:** {', '.join(info['matching_columns'])}")
                
                if args.include_all_columns and info['all_columns']:
                    result_lines.append(f"- **All columns:** {', '.join(info['all_columns'][:15])}")
                    if len(info['all_columns']) > 15:
                        result_lines.append(f"  ... and {len(info['all_columns']) - 15} more columns")
                
                result_lines.append("")
            
            result_lines.append("---")
            result_lines.append("Use the `run_sql` tool to query these tables. ")
            result_lines.append("Row-level security will automatically filter results to show only the user's data.")
            
            result_text = "\n".join(result_lines)
            
            logger.info(f"DiscoverUserTablesTool: Found {len(tables_info)} tables for user '{user.id}'")
            
            return ToolResult(
                success=True,
                result_for_llm=result_text,
                metadata={
                    "filter_columns": filter_columns,
                    "user_values": user_filter_values,
                    "tables_found": len(tables_info),
                    "tables": list(tables_info.keys())
                }
            )
            
        except Exception as e:
            logger.error(f"DiscoverUserTablesTool: Error: {e}")
            import traceback
            traceback.print_exc()
            
            return ToolResult(
                success=False,
                result_for_llm=f"Error discovering tables: {str(e)}",
                error=str(e),
                metadata={"user_id": user.id}
            )
