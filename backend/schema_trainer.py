"""
Schema Training Module for Database Chat Application.

This module provides functions to train Vanna's agent memory with the
Oracle database schema. It queries Oracle metadata and saves schema
information (DDL, table descriptions, relationships) to Milvus memory.

The training is triggered manually via the /gather command.
"""

import logging
from typing import List, Dict, Any, Optional
import oracledb
import asyncio

logger = logging.getLogger(__name__)

# Tables to exclude from training (system/internal tables)
EXCLUDED_TABLES = {
    'AI_USERS',
    'CHAINED_ROWS', 
    'PLAN_TABLE',
    'MVIEW$_ADV_WORKLOAD',
    'MVIEW$_ADV_LOG',
}


class SchemaTrainer:
    """
    Trainer for loading Oracle database schema into Vanna's agent memory.
    
    This class:
    1. Queries Oracle metadata to get table/view definitions
    2. Generates DDL-like descriptions for each table
    3. Saves the schema info to MilvusAgentMemory as text memories
    
    The LLM can then search these memories when it needs schema context.
    """
    
    def __init__(self, oracle_config, agent_memory, llm_service=None, openai_config=None):
        """
        Initialize the schema trainer.
        
        Args:
            oracle_config: Oracle database configuration
            agent_memory: MilvusAgentMemory instance for storing training data
            llm_service: Optional LLM service (kept for compatibility, not used for docs)
            openai_config: Optional OpenAI config for direct API calls
        """
        self.oracle_config = oracle_config
        self.agent_memory = agent_memory
        self.llm_service = llm_service
        self.openai_config = openai_config
    
    def _get_connection(self) -> oracledb.Connection:
        """Create a database connection."""
        return oracledb.connect(
            user=self.oracle_config.user,
            password=self.oracle_config.password,
            dsn=self.oracle_config.dsn
        )
    
    def get_schema_info(self) -> List[Dict[str, Any]]:
        """
        Get schema information from Oracle metadata.
        
        Returns:
            List of table/view information dictionaries
        """
        schema_info = []
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Get all tables and views from specified schema
            schema_name = self.oracle_config.schema_name
            cursor.execute("""
                SELECT owner, object_name, object_type
                FROM (
                    SELECT owner, table_name AS object_name, 'TABLE' AS object_type
                    FROM   all_tables
                    UNION ALL
                    SELECT owner, view_name  AS object_name, 'VIEW' AS object_type
                    FROM   all_views
                    UNION ALL
                    SELECT owner, mview_name AS object_name, 'MATERIALIZED VIEW' AS object_type
                    FROM   all_mviews
                )
                WHERE owner = :schema_name
                ORDER BY object_type, owner, object_name
            """, {"schema_name": schema_name})
            
            objects = []
            for row in cursor.fetchall():
                owner, name, obj_type = row
                if name.upper() not in EXCLUDED_TABLES:
                    objects.append((owner, name, obj_type))
            
            # Get detailed info for each object
            for owner, obj_name, obj_type in objects:
                info = {
                    'name': obj_name,
                    'type': obj_type,
                    'columns': [],
                    'primary_key': [],
                    'foreign_keys': [],
                    'comments': None
                }
                
                # Get columns
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, 
                           DATA_SCALE, NULLABLE, DATA_DEFAULT
                    FROM ALL_TAB_COLUMNS 
                    WHERE OWNER = :owner AND TABLE_NAME = :table_name
                    ORDER BY COLUMN_ID
                """, {"owner": owner, "table_name": obj_name})
                
                for col_row in cursor.fetchall():
                    col_name, data_type, length, precision, scale, nullable, default = col_row
                    
                    # Build data type string
                    type_str = data_type
                    if precision:
                        if scale:
                            type_str = f"{data_type}({precision},{scale})"
                        else:
                            type_str = f"{data_type}({precision})"
                    elif length and data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
                        type_str = f"{data_type}({length})"
                    
                    info['columns'].append({
                        'name': col_name,
                        'type': type_str,
                        'nullable': nullable == 'Y',
                        'default': default
                    })
                
                # Get primary key
                cursor.execute("""
                    SELECT cols.column_name
                    FROM all_constraints cons
                    JOIN all_cons_columns cols ON cons.owner = cols.owner 
                         AND cons.constraint_name = cols.constraint_name
                    WHERE cons.owner = :owner AND cons.table_name = :table_name
                    AND cons.constraint_type = 'P'
                    ORDER BY cols.position
                """, {"owner": owner, "table_name": obj_name})
                
                info['primary_key'] = [row[0] for row in cursor.fetchall()]
                
                # Get foreign keys with referenced table info
                cursor.execute("""
                    SELECT 
                        cols.column_name,
                        r_cons.owner as ref_owner,
                        r_cons.table_name as ref_table,
                        r_cols.column_name as ref_column
                    FROM all_constraints cons
                    JOIN all_cons_columns cols ON cons.owner = cols.owner 
                         AND cons.constraint_name = cols.constraint_name
                    JOIN all_constraints r_cons ON cons.r_owner = r_cons.owner 
                         AND cons.r_constraint_name = r_cons.constraint_name
                    JOIN all_cons_columns r_cols ON r_cons.owner = r_cols.owner 
                         AND r_cons.constraint_name = r_cols.constraint_name
                        AND cols.position = r_cols.position
                    WHERE cons.owner = :owner AND cons.table_name = :table_name
                    AND cons.constraint_type = 'R'
                    ORDER BY cols.position
                """, {"owner": owner, "table_name": obj_name})
                
                for fk_row in cursor.fetchall():
                    col_name, ref_owner, ref_table, ref_col = fk_row
                    info['foreign_keys'].append({
                        'column': col_name,
                        'references_table': ref_table,
                        'references_column': ref_col
                    })
                
                # Get table comment
                cursor.execute("""
                    SELECT COMMENTS FROM ALL_TAB_COMMENTS
                    WHERE OWNER = :owner AND TABLE_NAME = :table_name
                """, {"owner": owner, "table_name": obj_name})
                
                comment_row = cursor.fetchone()
                if comment_row and comment_row[0]:
                    info['comments'] = comment_row[0]
                
                schema_info.append(info)
            
            cursor.close()
            connection.close()
            
        except oracledb.Error as e:
            logger.error(f"SchemaTrainer: Error getting schema info: {e}")
            raise
        
        return schema_info
    
    def generate_ddl(self, table_info: Dict[str, Any]) -> str:
        """
        Generate DDL-like documentation for a table.
        
        Args:
            table_info: Dictionary with table information
            
        Returns:
            DDL string describing the table
        """
        lines = []
        
        # Header comment
        if table_info['comments']:
            lines.append(f"-- {table_info['comments']}")
        
        # CREATE statement
        obj_type = table_info['type']
        if obj_type == 'VIEW':
            lines.append(f"-- VIEW: {table_info['name']}")
        elif obj_type == 'MATERIALIZED VIEW':
            lines.append(f"-- MATERIALIZED VIEW: {table_info['name']}")
        else:
            lines.append(f"CREATE TABLE {table_info['name']} (")
        
        # Columns
        column_lines = []
        for col in table_info['columns']:
            col_def = f"    {col['name']} {col['type']}"
            if not col['nullable']:
                col_def += " NOT NULL"
            if col['default']:
                col_def += f" DEFAULT {col['default']}"
            column_lines.append(col_def)
        
        # Primary key
        if table_info['primary_key']:
            pk_cols = ', '.join(table_info['primary_key'])
            column_lines.append(f"    PRIMARY KEY ({pk_cols})")
        
        # Foreign keys
        for fk in table_info['foreign_keys']:
            fk_line = f"    FOREIGN KEY ({fk['column']}) REFERENCES {fk['references_table']}({fk['references_column']})"
            column_lines.append(fk_line)
        
        if obj_type == 'TABLE':
            lines.append(',\n'.join(column_lines))
            lines.append(");")
        else:
            # For views, just list columns
            lines.append("Columns:")
            for col in table_info['columns']:
                lines.append(f"  - {col['name']}: {col['type']}")
        
        return '\n'.join(lines)
    
    def generate_relationship_summary(self, schema_info: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of table relationships.
        
        Args:
            schema_info: List of table info dictionaries
            
        Returns:
            String describing relationships between tables
        """
        lines = ["## Database Table Relationships", ""]
        
        # Build relationship map
        relationships = []
        for table in schema_info:
            for fk in table['foreign_keys']:
                relationships.append({
                    'from_table': table['name'],
                    'from_column': fk['column'],
                    'to_table': fk['references_table'],
                    'to_column': fk['references_column']
                })
        
        if relationships:
            lines.append("Foreign Key Relationships:")
            for rel in relationships:
                lines.append(f"- {rel['from_table']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
        else:
            lines.append("No foreign key relationships defined.")
        
        lines.append("")
        lines.append("Use these relationships for JOIN queries.")
        
        return '\n'.join(lines)

    def _save_text_memory(self, text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Save text to agent memory using SaveTextMemoryTool.
        
        Args:
            text: Text content to save
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not text:
            return False
            
        try:
            from vanna.tools.agent_memory import SaveTextMemoryTool
            from vanna.core.tool import ToolContext
            from vanna.core.user import User
            import uuid
            
            tool = SaveTextMemoryTool()
            system_user = User(
                id="system",
                email="system@database-chat",
                username="system",
                group_memberships=['admin']
            )
            context = ToolContext(
                user=system_user,
                agent_memory=self.agent_memory,
                conversation_id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4())
            )
            
            args_schema_class = tool.get_args_schema()
            
            # Determine the correct field name (text or content)
            fields = []
            if hasattr(args_schema_class, 'model_fields'):
                fields = list(args_schema_class.model_fields.keys())
            
            # Truncate text to avoid Milvus limits (max 2000-3000 chars usually safe)
            MAX_TEXT_LENGTH = 2000
            truncated_text = text[:MAX_TEXT_LENGTH] if text and len(text) > MAX_TEXT_LENGTH else text
            
            if 'text' in fields:
                args = args_schema_class(text=truncated_text, metadata=metadata or {})
            elif 'content' in fields:
                args = args_schema_class(content=truncated_text, metadata=metadata or {})
            else:
                first_field = fields[0] if fields else 'content'
                args = args_schema_class(**{first_field: truncated_text, "metadata": metadata or {}})
            
            # Handle async execution
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(tool.execute(context, args))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result(timeout=30)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(tool.execute(context, args))
            
            success = result.success if hasattr(result, 'success') else True
            if not success:
                logger.error(f"SaveTextMemoryTool failed: {getattr(result, 'result_for_llm', 'Unknown error')}")
            return success
        except Exception as e:
            logger.error(f"Error saving text memory: {e}")
            return False

    def generate_table_documentation(self, table_info: Dict[str, Any], sample_rows: int = 20) -> str:
        """
        Generate documentation for a table using LLM analysis of sample data.
        
        Args:
            table_info: Dictionary with table information
            sample_rows: Number of sample rows to analyze
            
        Returns:
            Documentation string explaining the table
        """
        # Use OpenAI Python package directly if config is available
        if not self.openai_config or not self.openai_config.is_configured:
            logger.warning("No OpenAI configuration available for documentation generation")
            return ""
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            table_name = table_info['name']
            
            # Get sample data
            try:
                # Use parameterized query for safety
                cursor.execute(f"""
                    SELECT * FROM (
                        SELECT * FROM {table_name}
                        WHERE ROWNUM <= :sample_rows
                    )
                """, {"sample_rows": sample_rows})
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                # Build sample data representation
                sample_data_str = f"Columns: {', '.join(columns)}\n"
                sample_data_str += f"Sample rows ({len(rows)}):\n"
                for i, row in enumerate(rows[:10], 1):  # Limit to 10 rows for prompt
                    row_dict = dict(zip(columns, row))
                    sample_data_str += f"Row {i}: {row_dict}\n"
                
                # Get distinct values for key columns (potential coded values)
                distinct_values_info = []
                for col in table_info['columns'][:5]:  # Check first 5 columns
                    col_name = col['name']
                    try:
                        # Use quoted identifier for column name to handle special characters
                        # Note: This is safe because col_name comes from metadata, not user input
                        cursor.execute(f"""
                            SELECT DISTINCT "{col_name}", COUNT(*) as cnt
                            FROM "{table_name}"
                            WHERE "{col_name}" IS NOT NULL
                            GROUP BY "{col_name}"
                            ORDER BY cnt DESC
                            FETCH FIRST 10 ROWS ONLY
                        """)
                        distinct_vals = cursor.fetchall()
                        if distinct_vals and len(distinct_vals) <= 10:
                            distinct_values_info.append(
                                f"{col_name}: {[str(v[0]) for v in distinct_vals]}"
                            )
                    except Exception as e:
                        logger.debug(f"Could not get distinct values for {col_name}: {e}")
                        pass  # Skip if query fails
                
                cursor.close()
                connection.close()
                
                # Build LLM prompt
                prompt = f"""Analyze the following database table structure and sample data, then generate concise documentation:

Table: {table_name}
Type: {table_info['type']}
Columns: {', '.join([c['name'] + ' (' + c['type'] + ')' for c in table_info['columns']])}

Sample Data:
{sample_data_str}

Distinct Values:
{chr(10).join(distinct_values_info) if distinct_values_info else 'N/A'}

Primary Key: {', '.join(table_info['primary_key']) if table_info['primary_key'] else 'None'}
Foreign Keys: {len(table_info['foreign_keys'])} relationships

Generate documentation that explains:
1. What the table represents (business purpose)
2. Meaning of coded values (e.g., if you see 1, 2, decode what they mean)
3. Important columns and their purpose
4. Relationships to other tables (if any)
5. Any business context or patterns observed

Keep the documentation concise and practical. Focus on helping users understand what data is stored and how to query it effectively."""

                # Use OpenAI Python package directly
                try:
                    from openai import OpenAI
                    
                    # Create OpenAI client with configuration
                    client_kwargs = {
                        "api_key": self.openai_config.api_key,
                    }
                    if self.openai_config.base_url:
                        client_kwargs["base_url"] = self.openai_config.base_url
                    
                    client = OpenAI(**client_kwargs)
                    
                    # Call OpenAI API
                    response = client.chat.completions.create(
                        model=self.openai_config.model,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        temperature=self.openai_config.temperature,
                        timeout=self.openai_config.timeout,
                    )
                    
                    # Extract response text
                    if response.choices and len(response.choices) > 0:
                        return response.choices[0].message.content
                    else:
                        logger.warning("OpenAI API returned empty response")
                        return ""
                        
                except ImportError:
                    logger.error("openai package not installed. Install with: pip install openai")
                    return ""
                except Exception as e:
                    logger.warning(f"Error calling OpenAI API: {e}. Skipping documentation generation.")
                    return ""
            
            except Exception as e:
                logger.warning(f"Error querying sample data for {table_name}: {e}")
                cursor.close()
                connection.close()
                return ""
                
        except Exception as e:
            logger.error(f"Error generating documentation for {table_name}: {e}")
            return ""

    def train_schema(self, context=None) -> int:
        """
        Train the agent memory with database schema.
        
        This method:
        1. Gets schema info from Oracle
        2. Generates DDL for each table
        3. Generates LLM-based documentation for each table
        4. Saves schema info to agent memory
        
        Args:
            context: Optional ToolContext (not used, kept for compatibility)
            
        Returns:
            Number of schema items trained
        """
        logger.info("SchemaTrainer: Starting schema training...")
        
        # Get schema info
        schema_info = self.get_schema_info()
        logger.info(f"SchemaTrainer: Found {len(schema_info)} database objects")
        
        items_trained = 0
        
        # Store DDL for each table/view separately
        for table_info in schema_info:
            ddl = self.generate_ddl(table_info)
            
            # Store DDL in agent memory
            success = self._save_text_memory(
                text=ddl,
                metadata={
                    "type": "ddl",
                    "table": table_info['name'],
                    "object_type": table_info['type']
                }
            )
            
            if success:
                items_trained += 1
                logger.debug(f"Stored DDL for {table_info['name']}")
            
            # Generate and store documentation if LLM service is available
            if self.llm_service and table_info['type'] == 'TABLE':
                documentation = self.generate_table_documentation(table_info)
                if documentation:
                    doc_success = self._save_text_memory(
                        text=f"Documentation for table {table_info['name']}:\n\n{documentation}",
                        metadata={
                            "type": "documentation",
                            "table": table_info['name'],
                            "object_type": "TABLE"
                        }
                    )
                    if doc_success:
                        logger.debug(f"Generated and stored documentation for {table_info['name']}")
        
        # Generate and store relationship summary
        relationship_summary = self.generate_relationship_summary(schema_info)
        self._save_text_memory(
            text=relationship_summary,
            metadata={"type": "documentation", "category": "relationships"}
        )
        
        # Store for backward compatibility (if needed)
        self._schema_ddl = '\n\n'.join([self.generate_ddl(t) for t in schema_info])
        self._relationship_summary = relationship_summary
        self._schema_info = schema_info
        
        logger.info(f"SchemaTrainer: Trained {items_trained} schema items")
        
        return items_trained
    
    def get_schema_summary(self) -> str:
        """
        Get a concise summary of the database schema for LLM context.
        
        Returns:
            String with schema summary
        """
        if not hasattr(self, '_schema_info'):
            self.train_schema()
        
        lines = ["## Database Schema Summary", ""]
        
        # Group by type
        tables = [t for t in self._schema_info if t['type'] == 'TABLE']
        views = [t for t in self._schema_info if t['type'] == 'VIEW']
        mvs = [t for t in self._schema_info if t['type'] == 'MATERIALIZED VIEW']
        
        if tables:
            lines.append(f"### Tables ({len(tables)})")
            for t in tables:
                pk = f" [PK: {', '.join(t['primary_key'])}]" if t['primary_key'] else ""
                cols = ', '.join([c['name'] for c in t['columns'][:8]])
                if len(t['columns']) > 8:
                    cols += f"... (+{len(t['columns'])-8} more)"
                lines.append(f"- **{t['name']}**{pk}: {cols}")
            lines.append("")
        
        if views:
            lines.append(f"### Views ({len(views)})")
            for v in views:
                cols = ', '.join([c['name'] for c in v['columns'][:5]])
                lines.append(f"- **{v['name']}**: {cols}")
            lines.append("")
        
        # Add relationships
        lines.append(self._relationship_summary)
        
        return '\n'.join(lines)
    
    def get_full_ddl(self) -> str:
        """Get full DDL for all tables."""
        if not hasattr(self, '_schema_ddl'):
            self.train_schema()
        return self._schema_ddl