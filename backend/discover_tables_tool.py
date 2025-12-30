"""
Schema Discovery Tool for Database Chat Application.

This tool provides full database schema visibility to the LLM, listing all
accessible tables, views, and their columns. Unlike discover_my_tables which
only finds tables with identity columns, this tool shows the entire schema
to enable proper JOINs and comprehensive queries.
"""

import logging
from typing import Type, List, Dict, Any, Optional
from pydantic import BaseModel, Field

from vanna.core.tool import Tool, ToolContext, ToolResult

import oracledb

logger = logging.getLogger(__name__)

# Tables to exclude from schema listing (system/internal tables)
EXCLUDED_TABLES = {
    'AI_USERS',  # The identity table itself - PRIVACY PROTECTED
    'CHAINED_ROWS',
    'PLAN_TABLE',
    'MVIEW$_ADV_WORKLOAD',
    'MVIEW$_ADV_LOG',
}


class ListTablesArgs(BaseModel):
    """Arguments for the list all tables tool."""
    include_columns: bool = Field(
        default=True, 
        description="If true, include column names for each table. If false, only list table names."
    )
    table_filter: Optional[str] = Field(
        default=None,
        description="Optional filter to search for specific tables (e.g., 'EMP' to find employee-related tables)"
    )


class ListAllTablesTool(Tool[ListTablesArgs]):
    """
    A tool to list all accessible database tables, views, and materialized views.
    
    This tool:
    1. Queries Oracle metadata to list all tables/views in the schema
    2. Optionally includes column information for each table
    3. Helps the LLM understand table relationships for JOINs
    
    Use this when you need to understand the full database schema,
    especially to find related tables for comprehensive queries.
    """
    
    def __init__(self, oracle_config):
        """
        Initialize the schema listing tool.
        
        Args:
            oracle_config: Oracle database configuration
        """
        self.oracle_config = oracle_config
    
    @property
    def name(self) -> str:
        return "list_all_tables"
    
    @property
    def description(self) -> str:
        return (
            "List all database tables, views, and materialized views accessible in the schema. "
            "Use this to understand the full database structure, find related tables, "
            "and identify columns for JOINs. For example, to compare salaries with job ranges, "
            "you might need to JOIN EMPLOYEES with JOBS table."
        )
    
    def get_args_schema(self) -> Type[ListTablesArgs]:
        return ListTablesArgs
    
    def _get_connection(self) -> oracledb.Connection:
        """Create a database connection."""
        return oracledb.connect(
            user=self.oracle_config.user,
            password=self.oracle_config.password,
            dsn=self.oracle_config.dsn
        )
    
    def _list_tables(
        self, 
        include_columns: bool,
        table_filter: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        List all tables with their metadata.
        
        Args:
            include_columns: Whether to include column information
            table_filter: Optional filter for table names
            
        Returns:
            Dictionary mapping table names to their info
        """
        tables_info = {}
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Build query for tables, views, and MVs
            filter_clause = ""
            bind_params = {}
            if table_filter:
                filter_clause = "AND UPPER(object_name) LIKE UPPER(:filter)"
                bind_params["filter"] = f"%{table_filter}%"
            
            query = f"""
                SELECT object_name, object_type
                FROM (
                    SELECT TABLE_NAME as object_name, 'TABLE' as object_type FROM USER_TABLES
                    UNION ALL
                    SELECT VIEW_NAME as object_name, 'VIEW' as object_type FROM USER_VIEWS
                    UNION ALL
                    SELECT MVIEW_NAME as object_name, 'MATERIALIZED VIEW' as object_type FROM USER_MVIEWS
                )
                WHERE 1=1 {filter_clause}
                ORDER BY object_type, object_name
            """
            
            cursor.execute(query, bind_params)
            
            for row in cursor.fetchall():
                table_name, object_type = row
                
                # Skip excluded tables
                if table_name.upper() in EXCLUDED_TABLES:
                    continue
                
                tables_info[table_name] = {
                    "object_type": object_type,
                    "columns": []
                }
            
            # Get columns if requested
            if include_columns and tables_info:
                for table_name in tables_info.keys():
                    cursor.execute(
                        """
                        SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
                        FROM USER_TAB_COLUMNS 
                        WHERE TABLE_NAME = :table_name
                        ORDER BY COLUMN_ID
                        """,
                        {"table_name": table_name}
                    )
                    columns = []
                    for col_row in cursor.fetchall():
                        col_name, data_type, nullable = col_row
                        col_info = f"{col_name} ({data_type})"
                        if nullable == 'N':
                            col_info += " NOT NULL"
                        columns.append(col_info)
                    tables_info[table_name]["columns"] = columns
            
            # Get primary and foreign keys for relationships
            for table_name in tables_info.keys():
                # Get primary key
                cursor.execute(
                    """
                    SELECT cols.column_name
                    FROM user_constraints cons
                    JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
                    WHERE cons.table_name = :table_name
                    AND cons.constraint_type = 'P'
                    ORDER BY cols.position
                    """,
                    {"table_name": table_name}
                )
                pk_cols = [row[0] for row in cursor.fetchall()]
                if pk_cols:
                    tables_info[table_name]["primary_key"] = pk_cols
                
                # Get foreign keys
                cursor.execute(
                    """
                    SELECT 
                        cols.column_name,
                        r_cons.table_name as ref_table,
                        r_cols.column_name as ref_column
                    FROM user_constraints cons
                    JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
                    JOIN user_constraints r_cons ON cons.r_constraint_name = r_cons.constraint_name
                    JOIN user_cons_columns r_cols ON r_cons.constraint_name = r_cols.constraint_name
                        AND cols.position = r_cols.position
                    WHERE cons.table_name = :table_name
                    AND cons.constraint_type = 'R'
                    ORDER BY cols.position
                    """,
                    {"table_name": table_name}
                )
                fk_info = []
                for row in cursor.fetchall():
                    col_name, ref_table, ref_col = row
                    fk_info.append(f"{col_name} -> {ref_table}.{ref_col}")
                if fk_info:
                    tables_info[table_name]["foreign_keys"] = fk_info
            
            cursor.close()
            connection.close()
            
        except oracledb.Error as e:
            logger.error(f"ListAllTablesTool: Database error: {e}")
            raise RuntimeError(f"Database error during schema listing: {e}")
        
        return tables_info
    
    async def execute(self, context: ToolContext, args: ListTablesArgs) -> ToolResult:
        """
        Execute the schema listing.
        
        Args:
            context: Tool execution context with user info
            args: Tool arguments
            
        Returns:
            ToolResult with schema information
        """
        user = context.user
        logger.info(f"ListAllTablesTool: Executing for user '{user.id}'")
        
        try:
            # List all tables
            tables_info = self._list_tables(
                include_columns=args.include_columns,
                table_filter=args.table_filter
            )
            
            if not tables_info:
                return ToolResult(
                    success=True,
                    result_for_llm="No tables, views, or materialized views found in the schema.",
                    metadata={"tables_found": 0}
                )
            
            # Build result for LLM
            result_lines = []
            result_lines.append("## Database Schema")
            result_lines.append("")
            result_lines.append(f"**Found {len(tables_info)} database objects:**")
            result_lines.append("")
            
            # Group by object type
            tables = {k: v for k, v in tables_info.items() if v["object_type"] == "TABLE"}
            views = {k: v for k, v in tables_info.items() if v["object_type"] == "VIEW"}
            mvs = {k: v for k, v in tables_info.items() if v["object_type"] == "MATERIALIZED VIEW"}
            
            for group_name, group in [("Tables", tables), ("Views", views), ("Materialized Views", mvs)]:
                if group:
                    result_lines.append(f"### {group_name} ({len(group)})")
                    result_lines.append("")
                    
                    for table_name, info in sorted(group.items()):
                        result_lines.append(f"**{table_name}**")
                        
                        if info.get("primary_key"):
                            result_lines.append(f"  - Primary Key: {', '.join(info['primary_key'])}")
                        
                        if info.get("foreign_keys"):
                            result_lines.append(f"  - Foreign Keys: {'; '.join(info['foreign_keys'])}")
                        
                        if args.include_columns and info.get("columns"):
                            cols_display = info["columns"][:10]
                            result_lines.append(f"  - Columns: {', '.join(cols_display)}")
                            if len(info["columns"]) > 10:
                                result_lines.append(f"    ... and {len(info['columns']) - 10} more columns")
                        
                        result_lines.append("")
            
            result_lines.append("---")
            result_lines.append("Use foreign key relationships to JOIN tables when needed.")
            
            result_text = "\n".join(result_lines)
            
            logger.info(f"ListAllTablesTool: Found {len(tables_info)} objects for user '{user.id}'")
            
            return ToolResult(
                success=True,
                result_for_llm=result_text,
                metadata={
                    "tables_found": len(tables_info),
                    "tables": list(tables_info.keys())
                }
            )
            
        except Exception as e:
            logger.error(f"ListAllTablesTool: Error: {e}")
            import traceback
            traceback.print_exc()
            
            return ToolResult(
                success=False,
                result_for_llm=f"Error listing schema: {str(e)}",
                error=str(e),
                metadata={"user_id": user.id}
            )
