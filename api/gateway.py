import logging
import uuid
import json
from typing import Dict, Any, Optional, Tuple

from core.ai.text_to_sql import text_to_sql_service
from core.ai.sql_validator import sql_validator
from core.db.query_executor import query_executor
from core.mongodb.conversation_store import conversation_store
from utils.tracing import trace

logger = logging.getLogger(__name__)

class AIGateway:
    """
    AI Gateway that orchestrates the text-to-SQL workflow.
    Handles routing, tracing, and coordination between services.
    """
    
    def __init__(self):
        """Initialize the AI Gateway."""
        self.text_to_sql = text_to_sql_service
        self.sql_validator = sql_validator
        self.query_executor = query_executor
        self.conversation_store = conversation_store
        logger.info("AI Gateway initialized")
    
    @trace("process_query")
    def process_query(self, query: str, conversation_id: Optional[str] = None, user_id: str = "anonymous") -> Dict[str, Any]:
        """
        Process a natural language query through the text-to-SQL workflow.
        
        Args:
            query: Natural language query
            conversation_id: ID of the conversation (optional)
            user_id: ID of the user (optional)
            
        Returns:
            Dictionary containing query results and metadata
        """
        # Generate a trace ID for this request
        trace_id = str(uuid.uuid4())
        logger.info(f"Processing query with trace ID: {trace_id}")
        
        # Store the query in the conversation history
        if not conversation_id:
            conversation_id = self.conversation_store.create_conversation(user_id)
            logger.info(f"Created new conversation: {conversation_id}")
        
        self.conversation_store.add_message(
            conversation_id=conversation_id,
            role="user",
            content=query,
            metadata={"trace_id": trace_id}
        )
        
        # Process the query
        try:
            # Step 1: Convert text to SQL
            success, sql, error = self._generate_sql(query, trace_id, conversation_id)
            if not success:
                return self._error_response(query, error, trace_id, conversation_id)
            
            # Log the generated SQL for debugging
            logger.debug(f"Generated SQL before validation: {sql}")
            
            # Step 2: Validate the SQL
            success, error = self._validate_sql(sql, trace_id)
            if not success:
                # Log validation failure with the SQL that failed
                logger.warning(f"SQL validation failed. SQL: {sql}, Error: {error}")
                return self._error_response(query, error, trace_id, conversation_id, sql)
            
            # Step 3: Execute the SQL query
            success, results, error = self._execute_sql(sql, trace_id)
            if not success:
                return self._error_response(query, error, trace_id, conversation_id, sql)
            
            # Step 4: Format the response
            response = self._format_response(query, sql, results, trace_id, conversation_id)
            return response
            
        except Exception as e:
            error = f"Error processing query: {str(e)}"
            logger.error(f"{error} (trace_id: {trace_id})")
            # Try to include SQL if it was generated before the exception
            sql_value = locals().get('sql') if 'sql' in locals() else None
            return self._error_response(query, error, trace_id, conversation_id, sql_value)
    
    @trace("generate_sql")
    def _generate_sql(self, query: str, trace_id: str, conversation_id: str) -> Tuple[bool, str, str]:
        """Generate SQL from natural language query."""
        logger.info(f"Generating SQL for query: {query} (trace_id: {trace_id})")
        
        # Get conversation context if available
        context = self.conversation_store.get_conversation_context(conversation_id)
        
        # Add context to the query if available
        if context:
            enhanced_query = f"Context from previous conversation:\n{context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query
        
        # Generate SQL
        success, sql, error = self.text_to_sql.generate_sql(enhanced_query)
        
        if success:
            logger.info(f"Generated SQL: {sql} (trace_id: {trace_id})")
        else:
            logger.error(f"SQL generation failed: {error} (trace_id: {trace_id})")
        
        return success, sql, error
    
    @trace("validate_sql")
    def _validate_sql(self, sql: str, trace_id: str) -> Tuple[bool, str]:
        """Validate the generated SQL query."""
        logger.info(f"Validating SQL: {sql} (trace_id: {trace_id})")
        
        # Validate the SQL
        valid, error = self.sql_validator.validate(sql)
        
        if valid:
            logger.info(f"SQL validation passed (trace_id: {trace_id})")
        else:
            logger.error(f"SQL validation failed: {error} (trace_id: {trace_id})")
        
        return valid, error
    
    @trace("execute_sql")
    def _execute_sql(self, sql: str, trace_id: str) -> Tuple[bool, Any, str]:
        """Execute the SQL query and return results."""
        logger.info(f"Executing SQL: {sql} (trace_id: {trace_id})")
        
        # Execute the query
        success, results, error = self.query_executor.execute_sql_safely(sql)
        
        if success:
            logger.info(f"SQL execution succeeded with {len(results)} results (trace_id: {trace_id})")
        else:
            logger.error(f"SQL execution failed: {error} (trace_id: {trace_id})")
        
        return success, results, error
    
    @trace("format_response")
    def _format_response(self, query: str, sql: str, results: Any, trace_id: str, conversation_id: str) -> Dict[str, Any]:
        """Format the response to be returned to the client."""
        # Format the results
        response = {
            "success": True,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "query": query,
            "sql": sql,
            "results": results
        }
        
        # Store the response in the conversation history
        result_summary = json.dumps(results[:5]) if isinstance(results, list) and results else str(results)
        assistant_message = f"I ran the SQL query: {sql}\n\nResults: {result_summary}"
        
        if len(results) > 5:
            assistant_message += f"\n\n(Showing 5 of {len(results)} results)"
        
        self.conversation_store.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message,
            metadata={
                "trace_id": trace_id,
                "sql": sql,
                "result_count": len(results) if isinstance(results, list) else 0
            }
        )
        
        return response
    
    def _error_response(self, query: str, error: str, trace_id: str, conversation_id: str, sql: Optional[str] = None) -> Dict[str, Any]:
        """Generate an error response."""
        # Store the error in the conversation history
        error_message = f"I encountered an error: {error}"
        
        # Include the SQL in the error message if available
        if sql:
            error_message += f"\n\nGenerated SQL (which failed validation):\n{sql}"
        
        self.conversation_store.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=error_message,
            metadata={
                "trace_id": trace_id, 
                "error": error,
                "sql": sql if sql else None
            }
        )
        
        response = {
            "success": False,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "query": query,
            "error": error
        }
        
        # Include SQL in the response if available
        if sql:
            response["sql"] = sql
            
        return response


# Singleton instance
ai_gateway = AIGateway() 