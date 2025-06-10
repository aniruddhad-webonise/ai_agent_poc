import logging
import re
from typing import Tuple, List, Set, Dict

from config.schema_loader import schema_loader

logger = logging.getLogger(__name__)

class SQLValidator:
    """
    Validator for SQL queries to ensure they are safe to execute.
    Performs additional security checks beyond LLM validation.
    """
    
    def __init__(self):
        """Initialize the SQL validator."""
        # Load schema information
        schema = schema_loader.load_and_process()
        self.schema = schema
        
        # Extract table and column names for validation
        self.tables = set(schema["tables"].keys())
        self.views = set(schema["views"].keys())
        
        # Store schema information for tables and views
        self.table_schemas: Dict[str, str] = {}
        for table_name, table_info in schema["tables"].items():
            # Use "affinity_gaming" as the default schema for all tables
            schema_name = "affinity_gaming"
            self.table_schemas[table_name.lower()] = schema_name
        
        for view_name, view_info in schema["views"].items():
            # Use "affinity_gaming" as the default schema for all views
            schema_name = "affinity_gaming"
            self.table_schemas[view_name.lower()] = schema_name
        
        self.columns = set()
        for table_info in schema["tables"].values():
            self.columns.update(table_info["columns"].keys())
        
        for view_info in schema["views"].values():
            self.columns.update(view_info["columns"].keys())
        
        # Define patterns for potentially unsafe operations
        self.unsafe_patterns = [
            (r'\bDROP\b', "DROP statement detected"),
            (r'\bDELETE\b', "DELETE statement detected"),
            (r'\bTRUNCATE\b', "TRUNCATE statement detected"),
            (r'\bALTER\b', "ALTER statement detected"),
            (r'\bUPDATE\b', "UPDATE statement detected"),
            (r'\bINSERT\b', "INSERT statement detected"),
            (r'\bCREATE\b', "CREATE statement detected"),
            (r'\bGRANT\b', "GRANT statement detected"),
            (r'\bREVOKE\b', "REVOKE statement detected"),
            (r'\bINTO\s+OUTFILE\b', "File output operation detected"),
            (r'\bINTO\s+DUMPFILE\b', "File dump operation detected"),
            (r'\bLOAD_FILE\b', "File loading operation detected"),
            (r'\bUNION.*?SELECT\b', "UNION attack detected"),
            (r'\/\*.*?\*\/', "Comment block detected")
        ]
    
    def validate(self, sql: str) -> Tuple[bool, str]:
        """
        Validate a SQL query for safety and correctness.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sql or not sql.strip():
            return False, "SQL query is empty"
        
        # Log the query for debugging
        logger.debug(f"Validating SQL query: {sql}")
        
        # Normalize whitespace for better pattern matching
        normalized_sql = re.sub(r'\s+', ' ', sql.strip())
        
        # Convert to uppercase for case-insensitive matching but keep original for error messages
        sql_upper = normalized_sql.upper()
        
        # Check for multiple statements
        # We need to be careful about semicolons in strings or comments
        # This is a simplified approach - a proper SQL parser would be better
        semicolons = sql.count(';')
        if semicolons > 1:
            # Check if all but the last semicolon are within quotes
            parts = sql.split(';')
            # If we have multiple statements that aren't within quotes, reject
            if len(parts) - 1 > sql.count("';") + sql.count('";'):
                error_msg = f"Multiple statements detected: found {semicolons} semicolons in query"
                logger.warning(f"Validation failed: {error_msg}")
                return False, error_msg
        
        # Check for unsafe patterns
        for pattern, error_description in self.unsafe_patterns:
            match = re.search(pattern, sql_upper, re.IGNORECASE)
            if match:
                # Extract the matched text for better error reporting
                matched_text = match.group(0)
                error_msg = f"Unsafe SQL pattern detected: {error_description} at '{matched_text}'"
                logger.warning(f"Validation failed: {error_msg}")
                return False, error_msg
        
        # Ensure query is read-only (starts with SELECT)
        first_word = sql_upper.strip().split()[0] if sql_upper.strip().split() else ""
        if first_word != "SELECT":
            error_msg = f"Query must start with SELECT, found: {first_word}"
            logger.warning(f"Validation failed: {error_msg}")
            return False, error_msg
        
        # Check for referenced tables/views
        referenced_tables = self._extract_referenced_tables(sql)
        
        if not referenced_tables:
            logger.warning("No tables or views found in query")
            return False, "No tables or views referenced in the query"
        
        # Validate tables and add schema prefixes if needed
        corrected_sql = self._add_schema_prefixes(sql, referenced_tables)
        if corrected_sql != sql:
            logger.info(f"Added schema prefixes to query: {corrected_sql}")
            return True, corrected_sql
        
        logger.info(f"SQL validation passed for query: {sql[:50]}...")
        return True, sql
    
    def _extract_referenced_tables(self, sql: str) -> Set[str]:
        """
        Extract table/view names referenced in the SQL query.
        
        Args:
            sql: SQL query
            
        Returns:
            Set of table/view names
        """
        # Handle multi-line SQL by normalizing whitespace
        normalized_sql = re.sub(r'\s+', ' ', sql)
        
        # Simple regex to extract table names from FROM and JOIN clauses
        # This is a simplified approach and may not catch all edge cases
        from_regex = r'\bFROM\s+([a-zA-Z0-9_\.]+)'
        join_regex = r'\bJOIN\s+([a-zA-Z0-9_\.]+)'
        
        tables = set()
        
        # Extract from FROM clause
        from_matches = re.finditer(from_regex, normalized_sql, re.IGNORECASE)
        for match in from_matches:
            tables.add(match.group(1).strip())
        
        # Extract from JOIN clauses
        join_matches = re.finditer(join_regex, normalized_sql, re.IGNORECASE)
        for match in join_matches:
            tables.add(match.group(1).strip())
        
        return tables
    
    def _add_schema_prefixes(self, sql: str, referenced_tables: Set[str]) -> str:
        """
        Add schema prefixes to table names if they don't already have them.
        
        Args:
            sql: SQL query
            referenced_tables: Set of table names referenced in the query
            
        Returns:
            SQL with schema prefixes added
        """
        corrected_sql = sql
        
        for table in referenced_tables:
            # Skip if table already has a schema prefix
            if '.' in table:
                continue
                
            # Always add affinity_gaming schema prefix for tables without schema
            schema_name = "affinity_gaming"
            qualified_name = f"{schema_name}.{table}"
            
            # Replace table name with schema-qualified name
            # We need to be careful to replace only exact matches
            pattern = r'\b' + re.escape(table) + r'\b'
            corrected_sql = re.sub(pattern, qualified_name, corrected_sql)
            logger.debug(f"Added schema prefix to table: {table} -> {qualified_name}")
        
        return corrected_sql


# Singleton instance
sql_validator = SQLValidator() 