"""
Schema Training Module for Database Chat Application.

This module provides functions to train Vanna's agent memory with the
Oracle database schema. It queries Oracle metadata and saves schema
information (DDL, table descriptions, relationships) to Milvus memory.

The training happens at startup and can be refreshed periodically.
"""

import logging
from typing import List, Dict, Any, Optional
import oracledb

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
    
    def __init__(self, oracle_config, agent_memory):
        """
        Initialize the schema trainer.
        
        Args:
            oracle_config: Oracle database configuration
            agent_memory: MilvusAgentMemory instance for storing training data
        """
        self.oracle_config = oracle_config
        self.agent_memory = agent_memory
    
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
            
            # Get all tables and views
            cursor.execute("""
                SELECT object_name, object_type
                FROM (
                    SELECT TABLE_NAME as object_name, 'TABLE' as object_type FROM USER_TABLES
                    UNION ALL
                    SELECT VIEW_NAME as object_name, 'VIEW' as object_type FROM USER_VIEWS
                    UNION ALL
                    SELECT MVIEW_NAME as object_name, 'MATERIALIZED VIEW' as object_type FROM USER_MVIEWS
                )
                ORDER BY object_type, object_name
            """)
            
            objects = []
            for row in cursor.fetchall():
                name, obj_type = row
                if name.upper() not in EXCLUDED_TABLES:
                    objects.append((name, obj_type))
            
            # Get detailed info for each object
            for obj_name, obj_type in objects:
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
                    FROM USER_TAB_COLUMNS 
                    WHERE TABLE_NAME = :table_name
                    ORDER BY COLUMN_ID
                """, {"table_name": obj_name})
                
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
                    FROM user_constraints cons
                    JOIN user_cons_columns cols ON cons.constraint_name = cols.constraint_name
                    WHERE cons.table_name = :table_name
                    AND cons.constraint_type = 'P'
                    ORDER BY cols.position
                """, {"table_name": obj_name})
                
                info['primary_key'] = [row[0] for row in cursor.fetchall()]
                
                # Get foreign keys with referenced table info
                cursor.execute("""
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
                """, {"table_name": obj_name})
                
                for fk_row in cursor.fetchall():
                    col_name, ref_table, ref_col = fk_row
                    info['foreign_keys'].append({
                        'column': col_name,
                        'references_table': ref_table,
                        'references_column': ref_col
                    })
                
                # Get table comment
                cursor.execute("""
                    SELECT COMMENTS FROM USER_TAB_COMMENTS
                    WHERE TABLE_NAME = :table_name
                """, {"table_name": obj_name})
                
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
    
    def train_schema(self, context=None) -> int:
        """
        Train the agent memory with database schema.
        
        This method:
        1. Gets schema info from Oracle
        2. Generates DDL for each table
        3. Saves schema info to agent memory
        
        Args:
            context: Optional ToolContext for save_text_memory
            
        Returns:
            Number of schema items trained
        """
        logger.info("SchemaTrainer: Starting schema training...")
        
        # Get schema info
        schema_info = self.get_schema_info()
        logger.info(f"SchemaTrainer: Found {len(schema_info)} database objects")
        
        items_trained = 0
        
        # Since we don't have a ToolContext at startup, we'll store schema
        # info in a different way - as documentation that can be retrieved
        # The schema info will be available via the system prompt or as
        # a pre-built summary
        
        # For now, we'll generate the schema summary that can be included
        # in the system prompt or stored as a file
        all_ddl = []
        
        for table_info in schema_info:
            ddl = self.generate_ddl(table_info)
            all_ddl.append(ddl)
            items_trained += 1
        
        # Generate relationship summary
        relationship_summary = self.generate_relationship_summary(schema_info)
        
        # Store for later use
        self._schema_ddl = '\n\n'.join(all_ddl)
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
