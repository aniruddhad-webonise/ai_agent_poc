import logging
import re
from typing import Dict, Any, Tuple, Optional

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import openai

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS
from config.schema_loader import schema_loader
from .prompt_templates import text_to_sql_prompt, sql_validation_prompt

logger = logging.getLogger(__name__)

class TextToSQLService:
    """
    Service for converting natural language questions to SQL queries
    using LangChain with OpenAI.
    """
    
    def __init__(self):
        """Initialize the TextToSQL service."""
        self.api_key = OPENAI_API_KEY
        self.model_name = OPENAI_MODEL
        self.temperature = OPENAI_TEMPERATURE
        self.max_tokens = OPENAI_MAX_TOKENS
        
        # Create modern LLM instance
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Create modern runnable chains
        self.text_to_sql_chain = text_to_sql_prompt | self.llm
        self.sql_validation_chain = sql_validation_prompt | self.llm
        
        # Get schema for context
        self.schema_text = schema_loader.get_schema_for_llm()
        
        logger.info(f"TextToSQL service initialized with model {self.model_name}")
    
    def generate_sql(self, question: str) -> Tuple[bool, str, Optional[str]]:
        """
        Convert a natural language question to a SQL query.
        
        Args:
            question: Natural language question
            
        Returns:
            Tuple of (success, sql_query, error_message)
        """
        try:
            # Log the incoming question
            logger.info(f"Generating SQL for question: {question}")
            
            # Generate SQL using modern invoke pattern
            response = self.text_to_sql_chain.invoke({
                "schema": self.schema_text,
                "question": question
            })
            
            # Extract content from the response object
            response_text = response.content
            
            # Clean up the response and extract SQL from markdown code blocks if present
            sql_query = self._extract_sql_from_response(response_text)
            
            # Add schema prefixes to tables
            sql_query = self._add_schema_prefixes(sql_query)
            
            # Log the raw generated SQL for debugging
            logger.debug(f"Raw generated SQL with schema prefixes: {sql_query}")
            
            # Validate SQL
            success, validated_query, error = self._validate_sql(question, sql_query)
            
            if not success:
                logger.warning(f"SQL validation failed: {error}")
                # Return the original SQL even though validation failed
                return False, sql_query, error
            
            return True, validated_query, None
            
        except Exception as e:
            error = f"Error generating SQL: {str(e)}"
            logger.error(error)
            return False, "", error
    
    def _extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL query from response, handling markdown code blocks.
        
        Args:
            response: Raw response that might contain markdown
            
        Returns:
            Clean SQL query
        """
        response = response.strip()
        
        # Check if the response is wrapped in markdown code blocks
        sql_code_block_pattern = r"```(?:sql)?\n([\s\S]*?)\n```"
        match = re.search(sql_code_block_pattern, response)
        
        if match:
            # Extract the SQL from inside the code block
            sql = match.group(1).strip()
            logger.debug(f"Extracted SQL from markdown code block: {sql}")
            return sql
        
        # If no code block is found, return the original response
        return response
    
    def _add_schema_prefixes(self, sql: str) -> str:
        """
        Add schema prefixes to table names that should have them.
        This is a direct fix for the known tables in the system.
        
        Args:
            sql: SQL query to modify
            
        Returns:
            SQL query with schema prefixes added
        """
        # Check if the query already has double schema prefixes
        if 'affinity_gaming.affinity_gaming.' in sql:
            # Fix double schema prefixes
            fixed_sql = sql.replace('affinity_gaming.affinity_gaming.', 'affinity_gaming.')
            logger.warning(f"Fixed duplicate schema prefixes: {sql} -> {fixed_sql}")
            return fixed_sql
        
        # Create a modified SQL query
        modified_sql = sql
        
        # List of PostgreSQL functions and keywords that should not have schema prefixes
        pg_functions = [
            'current_date', 'current_time', 'current_timestamp', 'now', 'today', 
            'extract', 'date_part', 'to_char', 'to_date', 'to_timestamp',
            'sum', 'avg', 'min', 'max', 'count', 'coalesce', 'nullif'
        ]
        
        # Extract all potential table names from the query
        # Pattern to find table names after FROM and JOIN
        table_pattern = r'\b(FROM|JOIN)\s+([a-zA-Z0-9_\.]+)'
        matches = re.finditer(table_pattern, sql, re.IGNORECASE)
        
        for match in matches:
            table_ref = match.group(2)
            
            # Skip if table already has the correct schema prefix
            if table_ref.startswith('affinity_gaming.'):
                continue
                
            # Skip if it's a common SQL keyword
            if table_ref.lower() in ['select', 'where', 'group', 'order', 'having', 'limit']:
                continue
                
            # Skip if it's a PostgreSQL function
            if table_ref.lower() in pg_functions:
                continue
                
            # Handle the case where there might be another schema prefix
            if '.' in table_ref:
                schema, table_name = table_ref.split('.', 1)
                # Only replace if not already using affinity_gaming schema
                if schema.lower() != 'affinity_gaming':
                    qualified_name = f"affinity_gaming.{table_name}"
                    replace_pattern = f"{match.group(1)}\\s+{re.escape(table_ref)}\\b"
                    replacement = f"{match.group(1)} {qualified_name}"
                    modified_sql = re.sub(replace_pattern, replacement, modified_sql, flags=re.IGNORECASE)
                    logger.info(f"Replaced schema: {table_ref} -> {qualified_name}")
                continue
                
            # Add schema prefix to the table
            qualified_name = f"affinity_gaming.{table_ref}"
            # Pattern to replace just this specific table reference
            replace_pattern = f"{match.group(1)}\\s+{table_ref}\\b"
            replacement = f"{match.group(1)} {qualified_name}"
            modified_sql = re.sub(replace_pattern, replacement, modified_sql, flags=re.IGNORECASE)
            logger.info(f"Added schema prefix to table: {table_ref} -> {qualified_name}")
        
        # Remove schema prefixes from PostgreSQL functions (like CURRENT_DATE)
        for func in pg_functions:
            # Find instances where a function has been given a schema prefix
            func_pattern = f'affinity_gaming\\.{func}\\b'
            if re.search(func_pattern, modified_sql, re.IGNORECASE):
                # Remove the schema prefix from the function
                modified_sql = re.sub(func_pattern, func, modified_sql, flags=re.IGNORECASE)
                logger.info(f"Removed schema prefix from PostgreSQL function: affinity_gaming.{func} -> {func}")
        
        # Log if changes were made
        if modified_sql != sql:
            logger.info(f"Added schema prefixes to tables. Original: {sql}, Modified: {modified_sql}")
        
        return modified_sql
    
    def _validate_sql(self, question: str, sql_query: str) -> Tuple[bool, str, Optional[str]]:
        """
        Validate and potentially improve the generated SQL.
        
        Args:
            question: Original natural language question
            sql_query: Generated SQL query
            
        Returns:
            Tuple of (success, validated_sql, error_message)
        """
        try:
            # Check if the query is empty
            if not sql_query or sql_query.strip() == "":
                return False, "", "Generated SQL query is empty"
            
            # Log the SQL query for validation
            logger.debug(f"Validating SQL: {sql_query}")
            
            # Check for common SQL injection patterns - allow multiple lines but not multiple statements
            # A single statement can end with a semicolon, but shouldn't have multiple semicolons
            if ";" in sql_query and not sql_query.endswith(";") and sql_query.count(";") > 1:
                return False, sql_query, f"Potential SQL injection detected: multiple statements in query"
            
            # Use modern invoke pattern for validation
            response = self.sql_validation_chain.invoke({
                "question": question,
                "sql_query": sql_query,
                "schema": self.schema_text
            })
            
            # Extract content from the response object
            validated_text = response.content
            
            # Extract SQL from response if it's in a code block
            validated_sql = self._extract_sql_from_response(validated_text)
            
            # Apply schema prefixes again to the validated SQL
            validated_sql = self._add_schema_prefixes(validated_sql)
            
            # Check if the validation returned NULL
            if validated_sql.strip().upper() == "NULL":
                return False, sql_query, f"SQL validation failed: query cannot be fixed"
            
            # Return the validated SQL
            return True, validated_sql, None
            
        except Exception as e:
            error = f"Error validating SQL: {str(e)}"
            logger.error(error)
            return False, sql_query, error


# Singleton instance
text_to_sql_service = TextToSQLService() 