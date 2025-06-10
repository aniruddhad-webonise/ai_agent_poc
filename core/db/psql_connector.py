import logging
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from urllib.parse import urlparse, unquote

from config.settings import DB_URL

logger = logging.getLogger(__name__)

class PostgreSQLConnector:
    """
    Manages connections to the PostgreSQL database and provides methods
    for executing queries and fetching results.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgreSQLConnector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Initializing PostgreSQL connector")
        self._pool = None
        self._init_connection_pool()
        self._initialized = True
    
    def _init_connection_pool(self) -> None:
        """Initialize the connection pool using the DB_URL."""
        try:
            # Log the DB_URL (with password masked)
            masked_url = self._mask_password(DB_URL)
            logger.info(f"Connecting to database: {masked_url}")
            
            # Parse the DB_URL to extract connection parameters
            url = urlparse(DB_URL)
            dbname = url.path[1:]  # Remove leading slash
            user = url.username
            password = unquote(url.password) if url.password else ""  # Handle URL-encoded password
            host = url.hostname
            port = url.port or 5432
            
            # Create a connection pool
            self._pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                user=user,
                password=password,
                host=host,
                port=port,
                dbname=dbname
            )
            logger.info(f"Connection pool established to {host}:{port}/{dbname}")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _mask_password(self, url: str) -> str:
        """Mask the password in a URL for logging purposes."""
        if "://" not in url:
            return url
        
        parts = url.split("://", 1)
        if "@" not in parts[1]:
            return url
        
        auth, rest = parts[1].split("@", 1)
        if ":" not in auth:
            return url
        
        user = auth.split(":", 1)[0]
        return f"{parts[0]}://{user}:****@{rest}"
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool and return it when done."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Error with database connection: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """Get a cursor for executing queries."""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Database error: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of dictionaries containing the query results
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    return cursor.fetchall()
                return []
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
            raise
    
    def execute_explain(self, query: str, params: Optional[tuple] = None) -> str:
        """
        Execute an EXPLAIN on the query for validation.
        
        Args:
            query: SQL query to explain
            params: Query parameters
            
        Returns:
            Explanation string
        """
        explain_query = f"EXPLAIN {query}"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(explain_query, params)
                return "\n".join([row["QUERY PLAN"] for row in cursor.fetchall()])
        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            raise
    
    def validate_query(self, query: str, params: Optional[tuple] = None) -> Tuple[bool, str]:
        """
        Validate a SQL query by executing EXPLAIN.
        
        Args:
            query: SQL query to validate
            params: Query parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.execute_explain(query, params)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Closed all database connections")

# Singleton instance
db_connector = PostgreSQLConnector() 