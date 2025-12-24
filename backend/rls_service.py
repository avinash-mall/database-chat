"""
Row-Level Security Service for Database Chat Application.

This service manages row-level security (RLS) by:
1. Dynamically discovering filter columns from the AI_USERS table
2. Caching table schema metadata
3. Modifying SQL queries to inject WHERE clause filters for NORMALUSER

Filter columns are any columns in AI_USERS beyond the standard columns:
- USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER

Example filter columns: EMPLOYEE_ID, EMAIL, PERSON_ID, DEPARTMENT_ID, etc.
"""

import re
import time
import logging
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass
import oracledb
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Parenthesis, Token
from sqlparse import tokens as T

logger = logging.getLogger(__name__)

# Standard columns in AI_USERS that are NOT filter columns
STANDARD_COLUMNS = {'USERNAME', 'IS_ADMIN', 'IS_SUPERUSER', 'IS_NORMALUSER'}


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    data: Any
    timestamp: float
    
    def is_expired(self, ttl_seconds: float) -> bool:
        return time.time() - self.timestamp > ttl_seconds


@dataclass
class RLSConfig:
    """Configuration for Row-Level Security."""
    enabled: bool = True
    cache_ttl: float = 300.0  # 5 minutes
    excluded_tables: List[str] = None  # Tables exempt from RLS
    
    def __post_init__(self):
        if self.excluded_tables is None:
            self.excluded_tables = []
        # Normalize to uppercase for Oracle
        self.excluded_tables = [t.upper() for t in self.excluded_tables]


class RowLevelSecurityService:
    """
    Service for applying row-level security to SQL queries.
    
    This service:
    1. Discovers filter columns from AI_USERS table dynamically
    2. Gets user's filter values from AI_USERS
    3. Identifies tables in SQL queries and checks for matching filter columns
    4. Injects WHERE clause conditions to filter results
    
    Filter columns are automatically discovered - any column in AI_USERS
    that is not a standard column (USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER)
    is considered a filter column.
    """
    
    def __init__(self, oracle_config, rls_config: RLSConfig = None):
        """
        Initialize the RLS service.
        
        Args:
            oracle_config: Oracle database configuration with user, password, dsn
            rls_config: Optional RLS configuration settings
        """
        self.oracle_config = oracle_config
        self.config = rls_config or RLSConfig()
        
        # Caches
        self._filter_columns_cache: Optional[CacheEntry] = None
        self._table_columns_cache: Dict[str, CacheEntry] = {}
        self._user_filter_values_cache: Dict[str, CacheEntry] = {}
    
    def _get_connection(self) -> oracledb.Connection:
        """Create a new database connection."""
        return oracledb.connect(
            user=self.oracle_config.user,
            password=self.oracle_config.password,
            dsn=self.oracle_config.dsn
        )
    
    def get_filter_columns(self) -> List[str]:
        """
        Get the list of filter columns from AI_USERS table.
        
        Filter columns are dynamically discovered - any column that is not
        a standard column (USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER).
        
        Returns:
            List of filter column names (uppercase)
        """
        # Check cache
        if self._filter_columns_cache and not self._filter_columns_cache.is_expired(self.config.cache_ttl):
            return self._filter_columns_cache.data
        
        filter_columns = []
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Query table metadata to get all columns
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM USER_TAB_COLUMNS 
                WHERE TABLE_NAME = 'AI_USERS'
                ORDER BY COLUMN_ID
            """)
            
            for row in cursor.fetchall():
                column_name = row[0].upper()
                if column_name not in STANDARD_COLUMNS:
                    filter_columns.append(column_name)
            
            cursor.close()
            connection.close()
            
            # Cache the result
            self._filter_columns_cache = CacheEntry(
                data=filter_columns,
                timestamp=time.time()
            )
            
            logger.info(f"RLS: Discovered filter columns: {filter_columns}")
            
        except oracledb.Error as e:
            logger.error(f"RLS: Error getting filter columns: {e}")
            # Return empty list on error - this means no filtering
            return []
        
        return filter_columns
    
    def get_user_filter_values(self, username: str) -> Dict[str, Any]:
        """
        Get the filter column values for a specific user.
        
        Args:
            username: The username to look up in AI_USERS
            
        Returns:
            Dictionary mapping filter column names to their values for this user
        """
        cache_key = username.upper()
        
        # Check cache
        if cache_key in self._user_filter_values_cache:
            cache_entry = self._user_filter_values_cache[cache_key]
            if not cache_entry.is_expired(self.config.cache_ttl):
                return cache_entry.data
        
        filter_columns = self.get_filter_columns()
        if not filter_columns:
            return {}
        
        filter_values = {}
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Build query for filter columns
            columns_sql = ", ".join(filter_columns)
            cursor.execute(
                f"SELECT {columns_sql} FROM AI_USERS WHERE UPPER(USERNAME) = UPPER(:username)",
                {"username": username}
            )
            
            row = cursor.fetchone()
            if row:
                for i, column_name in enumerate(filter_columns):
                    value = row[i]
                    if value is not None:  # Only include non-NULL values
                        filter_values[column_name] = value
            
            cursor.close()
            connection.close()
            
            # Cache the result
            self._user_filter_values_cache[cache_key] = CacheEntry(
                data=filter_values,
                timestamp=time.time()
            )
            
            logger.info(f"RLS: User '{username}' filter values: {filter_values}")
            
        except oracledb.Error as e:
            logger.error(f"RLS: Error getting filter values for '{username}': {e}")
            return {}
        
        return filter_values
    
    def get_table_columns(self, table_name: str) -> Set[str]:
        """
        Get the column names for a table.
        
        Args:
            table_name: The table name to look up
            
        Returns:
            Set of column names (uppercase)
        """
        table_key = table_name.upper()
        
        # Check cache
        if table_key in self._table_columns_cache:
            cache_entry = self._table_columns_cache[table_key]
            if not cache_entry.is_expired(self.config.cache_ttl):
                return cache_entry.data
        
        columns = set()
        
        try:
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Query table metadata
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM USER_TAB_COLUMNS 
                WHERE TABLE_NAME = :table_name
            """, {"table_name": table_key})
            
            for row in cursor.fetchall():
                columns.add(row[0].upper())
            
            cursor.close()
            connection.close()
            
            # Cache the result
            self._table_columns_cache[table_key] = CacheEntry(
                data=columns,
                timestamp=time.time()
            )
            
        except oracledb.Error as e:
            logger.error(f"RLS: Error getting columns for table '{table_name}': {e}")
            return set()
        
        return columns
    
    def _extract_table_names(self, parsed_sql) -> List[Tuple[str, Optional[str]]]:
        """
        Extract table names and their aliases from a parsed SQL statement.
        
        Returns:
            List of tuples (table_name, alias) where alias may be None
        """
        tables = []
        
        def extract_table_identifier(token) -> Optional[Tuple[str, Optional[str]]]:
            """Extract table name and alias from an identifier token."""
            if isinstance(token, Identifier):
                # Get the real name (might be schema.table)
                real_name = token.get_real_name()
                alias = token.get_alias()
                if real_name:
                    # Handle schema.table format
                    if '.' in real_name:
                        real_name = real_name.split('.')[-1]
                    return (real_name.upper(), alias.upper() if alias else None)
            return None
        
        def process_token(token):
            """Recursively process tokens to find table references."""
            if token.ttype is T.Keyword and token.value.upper() in ('FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN', 'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN'):
                return True
            return False
        
        # Find FROM and JOIN clauses
        from_seen = False
        for token in parsed_sql.tokens:
            # Skip whitespace and comments
            if token.is_whitespace or token.ttype in T.Comment:
                continue
            
            # Check for FROM/JOIN keywords
            if token.ttype is T.Keyword:
                keyword = token.value.upper()
                if keyword in ('FROM', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'OUTER', 'NATURAL'):
                    from_seen = True
                    continue
                elif keyword in ('WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'UNION', 'INTERSECT', 'EXCEPT', 'MINUS'):
                    from_seen = False
                    continue
            
            if from_seen:
                if isinstance(token, IdentifierList):
                    # Multiple tables: FROM t1, t2, t3
                    for identifier in token.get_identifiers():
                        result = extract_table_identifier(identifier)
                        if result:
                            tables.append(result)
                    from_seen = False
                elif isinstance(token, Identifier):
                    result = extract_table_identifier(token)
                    if result:
                        tables.append(result)
                    from_seen = False
                elif token.ttype is T.Name or (token.ttype is T.Keyword and token.value.upper() not in ('JOIN', 'ON', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'OUTER', 'NATURAL')):
                    # Simple table name without alias
                    if token.ttype is T.Name:
                        tables.append((token.value.upper(), None))
                        from_seen = False
            
            # Recursively process subqueries
            if isinstance(token, Parenthesis):
                inner_sql = token.value[1:-1].strip()
                if inner_sql.upper().startswith('SELECT'):
                    inner_parsed = sqlparse.parse(inner_sql)
                    if inner_parsed:
                        tables.extend(self._extract_table_names(inner_parsed[0]))
        
        return tables
    
    def _find_matching_filter_columns(self, table_name: str, filter_columns: List[str]) -> List[str]:
        """
        Find which filter columns exist in a given table.
        
        Args:
            table_name: The table to check
            filter_columns: List of filter column names to look for
            
        Returns:
            List of filter column names that exist in the table
        """
        table_columns = self.get_table_columns(table_name)
        return [col for col in filter_columns if col in table_columns]
    
    def apply_rls_filters(self, sql: str, user_filter_values: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Apply RLS filters to a SQL query.
        
        Args:
            sql: The original SQL query
            user_filter_values: Dictionary of filter column values for the user
            
        Returns:
            Tuple of (modified_sql, bind_params) where bind_params contains
            the parameterized values for the filter conditions
        """
        if not self.config.enabled:
            return sql, {}
        
        if not user_filter_values:
            logger.debug("RLS: No filter values for user, returning original query")
            return sql, {}
        
        # Strip trailing semicolons (Oracle doesn't want them in programmatic execution)
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1].strip()
        
        # Parse the SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql, {}
        
        statement = parsed[0]
        
        # Get statement type
        stmt_type = statement.get_type()
        if stmt_type not in ('SELECT', 'UPDATE', 'DELETE'):
            # Don't filter INSERT or other statement types
            logger.debug(f"RLS: Skipping filter for statement type: {stmt_type}")
            return sql, {}
        
        # Extract tables from the query
        tables = self._extract_table_names(statement)
        logger.debug(f"RLS: Extracted tables: {tables}")
        
        if not tables:
            return sql, {}
        
        # Build filter conditions
        filter_conditions = []
        bind_params = {}
        param_counter = 0
        
        filter_columns = list(user_filter_values.keys())
        
        for table_name, alias in tables:
            # Check if table is excluded
            if table_name in self.config.excluded_tables:
                logger.debug(f"RLS: Table '{table_name}' is excluded from RLS")
                continue
            
            # Find matching filter columns for this table
            matching_columns = self._find_matching_filter_columns(table_name, filter_columns)
            
            if not matching_columns:
                logger.debug(f"RLS: Table '{table_name}' has no matching filter columns")
                continue
            
            # Build conditions for this table
            table_prefix = alias if alias else table_name
            for column in matching_columns:
                param_name = f"rls_param_{param_counter}"
                param_counter += 1
                
                condition = f"{table_prefix}.{column} = :{param_name}"
                filter_conditions.append(condition)
                bind_params[param_name] = user_filter_values[column]
        
        if not filter_conditions:
            logger.debug("RLS: No filter conditions to apply")
            return sql, {}
        
        # Inject WHERE clause
        combined_condition = " AND ".join(filter_conditions)
        modified_sql = self._inject_where_clause(sql, combined_condition)
        
        logger.info(f"RLS: Applied filters. Original: {sql[:100]}...")
        logger.info(f"RLS: Modified: {modified_sql[:100]}...")
        logger.debug(f"RLS: Bind params: {bind_params}")
        
        return modified_sql, bind_params
    
    def _inject_where_clause(self, sql: str, condition: str) -> str:
        """
        Inject a WHERE clause condition into a SQL query.
        
        Handles:
        - Queries without existing WHERE clause
        - Queries with existing WHERE clause (adds AND)
        - Queries with GROUP BY, ORDER BY, etc.
        
        Args:
            sql: The original SQL query
            condition: The condition to add (without WHERE/AND prefix)
            
        Returns:
            Modified SQL with the condition injected
        """
        # Parse the SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql
        
        statement = parsed[0]
        
        # Find if there's an existing WHERE clause
        has_where = False
        where_end_pos = -1
        
        tokens = list(statement.flatten())
        
        for i, token in enumerate(tokens):
            if token.ttype is T.Keyword and token.value.upper() == 'WHERE':
                has_where = True
                break
        
        if has_where:
            # Add condition with AND after existing WHERE conditions
            # Find the position just before GROUP BY, ORDER BY, HAVING, LIMIT, UNION, etc.
            
            # Use regex to find where to insert
            # Look for existing WHERE and insert before GROUP BY, ORDER BY, HAVING, etc.
            pattern = r'(\bWHERE\b\s+.+?)(\s+(?:GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|UNION|INTERSECT|EXCEPT|MINUS|FETCH|OFFSET|FOR\s+UPDATE)\b|\s*$)'
            
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            if match:
                where_clause = match.group(1)
                remainder = match.group(2)
                before_where = sql[:match.start(1)]
                
                # Insert the AND condition
                modified_sql = f"{before_where}{where_clause} AND ({condition}){remainder}"
                return modified_sql
            else:
                # Fallback: just append AND at the end
                return f"{sql} AND ({condition})"
        else:
            # No existing WHERE clause - need to insert one
            # Find the position just before GROUP BY, ORDER BY, HAVING, etc.
            
            pattern = r'(\bFROM\b\s+.+?)(\s+(?:GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT|UNION|INTERSECT|EXCEPT|MINUS|FETCH|OFFSET|FOR\s+UPDATE)\b|\s*$)'
            
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            if match:
                from_clause = match.group(1)
                remainder = match.group(2)
                before_from = sql[:match.start(1)]
                
                # Insert WHERE clause
                modified_sql = f"{before_from}{from_clause} WHERE ({condition}){remainder}"
                return modified_sql
            else:
                # Fallback: just append WHERE at the end
                return f"{sql} WHERE ({condition})"
    
    def clear_cache(self):
        """Clear all caches."""
        self._filter_columns_cache = None
        self._table_columns_cache.clear()
        self._user_filter_values_cache.clear()
        logger.info("RLS: Caches cleared")
    
    def clear_user_cache(self, username: str):
        """Clear cache for a specific user."""
        cache_key = username.upper()
        if cache_key in self._user_filter_values_cache:
            del self._user_filter_values_cache[cache_key]
            logger.info(f"RLS: Cache cleared for user '{username}'")
