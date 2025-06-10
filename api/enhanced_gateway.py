"""
Enhanced AI Gateway that uses LangGraph for state management.
Orchestrates the text-to-SQL workflow with improved context handling.
"""

import logging
import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple

from core.ai.text_to_sql import text_to_sql_service
from core.ai.sql_validator import sql_validator
from core.db.query_executor import query_executor
from core.state.state_manager import state_manager, State, Message
from core.ai.contextualizer import query_contextualizer
from utils.tracing import trace

logger = logging.getLogger(__name__)

class EnhancedAIGateway:
    """
    Enhanced AI Gateway that orchestrates the text-to-SQL workflow.
    Uses LangGraph for state management and improved context handling.
    """
    
    def __init__(self):
        """Initialize the Enhanced AI Gateway."""
        self.text_to_sql = text_to_sql_service
        self.sql_validator = sql_validator
        self.query_executor = query_executor
        self.state_manager = state_manager
        self.contextualizer = query_contextualizer
        logger.info("Enhanced AI Gateway initialized")
    
    @trace("process_query")
    async def process_query(self, query: str, thread_id: Optional[str] = None, user_id: str = "anonymous") -> Dict[str, Any]:
        """
        Process a natural language query through the text-to-SQL workflow.
        
        Args:
            query: Natural language query
            thread_id: ID of the conversation thread (optional)
            user_id: ID of the user (optional)
            
        Returns:
            Dictionary containing query results and metadata
        """
        # Get or create state for this conversation
        state = self._get_or_create_state(query, thread_id, user_id)
        thread_id = state["thread_id"]
        
        logger.info(f"Processing query with trace ID: {state['trace_id']} in thread: {thread_id}")
        
        try:
            # Step 1: Contextualize the query (handle follow-up questions)
            state = await self.contextualizer.contextualize(state)
            contextualized_query = state.get("contextualized_query", query)
            
            # Step 2: Convert text to SQL
            state = await self._generate_sql(state, contextualized_query)
            if not state.get("success", False):
                return self._format_error_response(state)
            
            # Step 3: Validate the SQL
            state = await self._validate_sql(state)
            if not state.get("success", False):
                return self._format_error_response(state)
            
            # Step 4: Execute the SQL query
            state = await self._execute_sql(state)
            if not state.get("success", False):
                return self._format_error_response(state)
            
            # Step 5: Format the response
            response = self._format_success_response(state)
            
            # Save the updated state
            self.state_manager.save_state(thread_id, state)
            
            return response
            
        except Exception as e:
            error = f"Error processing query: {str(e)}"
            logger.error(f"{error} (trace_id: {state['trace_id']})")
            
            # Update state with error
            state["success"] = False
            state["error"] = error
            
            # Add assistant message with error
            error_message = Message(
                role="assistant",
                content=f"I encountered an error processing your query: {error}",
                metadata={"trace_id": state["trace_id"], "error": error}
            )
            state["messages"].append(error_message)
            
            # Save the error state
            self.state_manager.save_state(thread_id, state)
            
            return self._format_error_response(state)
    
    def _get_or_create_state(self, query: str, thread_id: Optional[str], user_id: str) -> State:
        """Get existing state or create a new one."""
        if thread_id:
            # Try to get existing state
            existing_state = self.state_manager.get_state(thread_id)
            if existing_state:
                # Add the new query message
                existing_state["messages"].append(
                    Message(
                        role="user",
                        content=query,
                        metadata={"trace_id": existing_state["trace_id"]}
                    )
                )
                existing_state["query"] = query
                return existing_state
        
        # Create new state if thread_id doesn't exist or no state found
        return self.state_manager.create_initial_state(query, thread_id, user_id)
    
    @trace("generate_sql")
    async def _generate_sql(self, state: State, contextualized_query: str) -> State:
        """Generate SQL from natural language query."""
        logger.info(f"Generating SQL for query: {contextualized_query} (trace_id: {state['trace_id']})")
        
        try:
            # Run the non-async text_to_sql method in a thread pool to avoid blocking
            loop = asyncio.get_running_loop()
            success, sql, error = await loop.run_in_executor(
                None, 
                lambda: self.text_to_sql.generate_sql(contextualized_query)
            )
            
            # Update state with result
            state["success"] = success
            if success:
                state["sql"] = sql
                logger.info(f"Generated SQL: {sql} (trace_id: {state['trace_id']})")
            else:
                state["error"] = error
                logger.error(f"SQL generation failed: {error} (trace_id: {state['trace_id']})")
                
                # Add assistant message with error
                error_message = Message(
                    role="assistant",
                    content=f"I couldn't generate SQL for your query: {error}",
                    metadata={"trace_id": state["trace_id"], "error": error}
                )
                state["messages"].append(error_message)
                
                # We no longer save state here, it will be saved at the end of process_query
            
            return state
        except Exception as e:
            error = f"Error generating SQL: {str(e)}"
            logger.error(f"{error} (trace_id: {state['trace_id']})")
            state["success"] = False
            state["error"] = error
            
            # Add assistant message with error
            error_message = Message(
                role="assistant",
                content=f"I encountered an unexpected error generating SQL: {error}",
                metadata={"trace_id": state["trace_id"], "error": error}
            )
            state["messages"].append(error_message)
            
            # We no longer save state here, it will be saved at the end of process_query
                
            return state
    
    @trace("validate_sql")
    async def _validate_sql(self, state: State) -> State:
        """Validate the generated SQL query."""
        sql = state.get("sql", "")
        logger.info(f"Validating SQL: {sql} (trace_id: {state['trace_id']})")
        
        try:
            # Run the non-async validator in a thread pool
            loop = asyncio.get_running_loop()
            valid, error = await loop.run_in_executor(
                None,
                lambda: self.sql_validator.validate(sql)
            )
            
            # Update state with result
            state["success"] = valid
            if valid:
                state["validated_sql"] = sql
                logger.info(f"SQL validation passed (trace_id: {state['trace_id']})")
            else:
                state["error"] = error
                logger.error(f"SQL validation failed: {error} (trace_id: {state['trace_id']})")
                
                # Add assistant message with error
                error_message = Message(
                    role="assistant",
                    content=f"I encountered an error validating the SQL: {error}\n\nGenerated SQL (which failed validation):\n{sql}",
                    metadata={"trace_id": state["trace_id"], "error": error, "sql": sql}
                )
                state["messages"].append(error_message)
                
                # We no longer save state here, it will be saved at the end of process_query
            
            return state
        except Exception as e:
            error = f"Error validating SQL: {str(e)}"
            logger.error(f"{error} (trace_id: {state['trace_id']})")
            state["success"] = False
            state["error"] = error
            
            # Add assistant message with error
            error_message = Message(
                role="assistant",
                content=f"I encountered an unexpected error during SQL validation: {error}\n\nSQL query:\n{sql}",
                metadata={"trace_id": state["trace_id"], "error": error, "sql": sql}
            )
            state["messages"].append(error_message)
            
            # We no longer save state here, it will be saved at the end of process_query
                
            return state
    
    @trace("execute_sql")
    async def _execute_sql(self, state: State) -> State:
        """Execute the SQL query and return results."""
        sql = state.get("validated_sql", "")
        logger.info(f"Executing SQL: {sql} (trace_id: {state['trace_id']})")
        
        try:
            # Run the non-async executor in a thread pool
            loop = asyncio.get_running_loop()
            success, results, error = await loop.run_in_executor(
                None,
                lambda: self.query_executor.execute_sql_safely(sql)
            )
            
            # Update state with result
            state["success"] = success
            if success:
                state["results"] = results
                logger.info(f"SQL execution succeeded with {len(results) if isinstance(results, list) else 0} results (trace_id: {state['trace_id']})")
                
                # Format results for display
                result_summary = json.dumps(results[:5]) if isinstance(results, list) and results else str(results)
                assistant_message = f"I ran the SQL query: {sql}\n\nResults: {result_summary}"
                
                if isinstance(results, list) and len(results) > 5:
                    assistant_message += f"\n\n(Showing 5 of {len(results)} results)"
                
                # Add assistant message with results
                response_message = Message(
                    role="assistant",
                    content=assistant_message,
                    metadata={
                        "trace_id": state["trace_id"],
                        "sql": sql,
                        "result_count": len(results) if isinstance(results, list) else 0
                    }
                )
                state["messages"].append(response_message)
            else:
                state["error"] = error
                logger.error(f"SQL execution failed: {error} (trace_id: {state['trace_id']})")
                
                # Add assistant message with error
                error_message = Message(
                    role="assistant",
                    content=f"I encountered an error executing the SQL: {error}\n\nSQL query:\n{sql}",
                    metadata={"trace_id": state["trace_id"], "error": error, "sql": sql}
                )
                state["messages"].append(error_message)
            
            # We no longer save state here, it will be saved at the end of process_query
            
            return state
        except Exception as e:
            error = f"Error executing SQL: {str(e)}"
            logger.error(f"{error} (trace_id: {state['trace_id']})")
            state["success"] = False
            state["error"] = error
            
            # Add assistant message with error
            error_message = Message(
                role="assistant",
                content=f"I encountered an unexpected error: {error}\n\nSQL query:\n{sql}",
                metadata={"trace_id": state["trace_id"], "error": error, "sql": sql}
            )
            state["messages"].append(error_message)
            
            # We no longer save state here, it will be saved at the end of process_query
                
            return state
            
    def _format_success_response(self, state: State) -> Dict[str, Any]:
        """Format a success response for the client."""
        return {
            "success": True,
            "trace_id": state["trace_id"],
            "thread_id": state["thread_id"],
            "query": state["query"],
            "contextualized_query": state.get("contextualized_query", state["query"]),
            "sql": state.get("sql", ""),
            "results": state.get("results", [])
        }
    
    def _format_error_response(self, state: State) -> Dict[str, Any]:
        """Format an error response for the client."""
        # Ensure there's an error message in the conversation
        if state.get("error") and not any(msg.metadata.get("error") for msg in state["messages"] if msg.role == "assistant"):
            # No error message found, add one
            error_message = Message(
                role="assistant",
                content=f"I encountered an error: {state.get('error')}",
                metadata={
                    "trace_id": state["trace_id"], 
                    "error": state.get("error"),
                    "sql": state.get("sql", "")
                }
            )
            state["messages"].append(error_message)
            
            # We no longer save state here, it will be saved at the end of process_query
                
        return {
            "success": False,
            "trace_id": state["trace_id"],
            "thread_id": state["thread_id"],
            "query": state["query"],
            "contextualized_query": state.get("contextualized_query", state["query"]),
            "sql": state.get("sql", ""),
            "error": state.get("error", "Unknown error")
        }


# Singleton instance
enhanced_ai_gateway = EnhancedAIGateway() 