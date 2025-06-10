import logging
import json
from typing import Dict, List, Any, Tuple, Optional

from .psql_connector import db_connector

logger = logging.getLogger(__name__)

class QueryExecutor:
    """
    Executes SQL queries against the PostgreSQL database
    and formats the results for consumption by LLM or clients.
    """
    
    def __init__(self):
        self.connector = db_connector
    
    def execute_and_format(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """
        Execute a SQL query and format the results for consumption.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Dictionary containing query status and results
        """
        try:
            # Validate query first
            valid, error = self.connector.validate_query(query, params)
            if not valid:
                return {
                    "success": False,
                    "error": f"Query validation failed: {error}",
                    "results": []
                }
            
            # Execute the query
            results = self.connector.execute_query(query, params)
            
            # Format the results
            formatted_results = self._format_results(results)
            
            return {
                "success": True,
                "query": query,
                "row_count": len(results),
                "results": formatted_results
            }
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format the results for consumption.
        
        Args:
            results: List of dictionaries containing query results
            
        Returns:
            Formatted results
        """
        # For large result sets, limit the number of rows returned
        MAX_ROWS = 100
        if len(results) > MAX_ROWS:
            logger.warning(f"Query returned {len(results)} rows, limiting to {MAX_ROWS}")
            results = results[:MAX_ROWS]
        
        # Convert any non-serializable objects to strings
        formatted_results = []
        for row in results:
            formatted_row = {}
            for key, value in row.items():
                if isinstance(value, (int, float, str, bool, type(None))):
                    formatted_row[key] = value
                else:
                    # Try to serialize complex types, fallback to string representation
                    try:
                        formatted_row[key] = json.dumps(value)
                    except:
                        formatted_row[key] = str(value)
            formatted_results.append(formatted_row)
        
        return formatted_results
    
    def execute_sql_safely(self, sql: str) -> Tuple[bool, Any, str]:
        """
        Execute a SQL query with safety checks.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            Tuple of (success, results, error_message)
        """
        # Check for potentially harmful SQL commands
        unsafe_commands = [
            "DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT", 
            "CREATE", "GRANT", "REVOKE", "COMMIT", "ROLLBACK"
        ]
        
        upper_sql = sql.upper()
        for command in unsafe_commands:
            if command in upper_sql:
                error = f"Unsafe SQL command detected: {command}"
                logger.warning(error)
                return False, None, error
        
        try:
            # Execute the query
            result = self.execute_and_format(sql)
            if result["success"]:
                return True, result["results"], ""
            else:
                return False, None, result["error"]
        except Exception as e:
            error = f"Error executing SQL: {str(e)}"
            logger.error(error)
            return False, None, error

# Singleton instance
query_executor = QueryExecutor() 