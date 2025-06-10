"""
State management for the AI Database Query Bot using LangGraph.
Provides thread-based conversation state management and workflow orchestration.
"""

import logging
import uuid
from typing import Dict, List, Any, TypedDict, Optional
from datetime import datetime

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from typing_extensions import Annotated, NotRequired

from core.mongodb.conversation_store import conversation_store

logger = logging.getLogger(__name__)

# State schema defining the structure of our workflow state
class Message(BaseModel):
    """Message in a conversation."""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Function to add messages to the state
def add_messages(state_messages: List[Message], new_messages: List[Message]) -> List[Message]:
    """Add new messages to the state, preserving history."""
    return state_messages + new_messages

# State class for the workflow
class State(TypedDict):
    """State schema for the conversation workflow."""
    messages: Annotated[List[Message], add_messages]  # Automatically accumulates messages
    thread_id: str  # Conversation thread ID
    user_id: str  # User identifier
    query: str  # Original query
    contextualized_query: NotRequired[str]  # Query with context
    sql: NotRequired[str]  # Generated SQL
    validated_sql: NotRequired[str]  # Validated SQL
    results: NotRequired[List[Dict[str, Any]]]  # Query results
    error: NotRequired[str]  # Error message if any
    trace_id: str  # For observability
    success: NotRequired[bool]  # Operation success flag

class StateManager:
    """
    Manages conversation state using LangGraph's state management.
    Provides thread-based persistence and workflow orchestration.
    """
    
    def __init__(self):
        """Initialize the state manager."""
        # Initialize the in-memory saver for state persistence
        self.checkpointer = MemorySaver()
        # Initialize the graph (will be defined in build_workflow_graph)
        self.graph = None
        # Link to the MongoDB conversation store for persistence
        self.conversation_store = conversation_store
        # Internal state storage since MemorySaver doesn't provide direct access
        self.states = {}
        
        logger.info("State manager initialized")
    
    def build_workflow_graph(self):
        """Build the workflow graph for the conversation."""
        # This is a placeholder for the actual graph definition
        # We'll implement this in Phase 2
        return None
    
    def get_state(self, thread_id: str) -> Optional[State]:
        """
        Get the current state for a thread.
        
        Args:
            thread_id: Conversation thread ID
            
        Returns:
            Current state or None if not found
        """
        try:
            # Get state from our internal storage
            return self.states.get(thread_id)
        except Exception as e:
            logger.error(f"Error retrieving state for thread {thread_id}: {e}")
            return None
    
    def save_state(self, thread_id: str, state: State):
        """
        Save the state for a thread.
        
        Args:
            thread_id: Conversation thread ID
            state: State to save
        """
        try:
            # Save to our internal storage
            self.states[thread_id] = state
            
            # Also save to MongoDB for persistence
            self._sync_with_mongodb(thread_id, state)
            
            logger.debug(f"Saved state for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error saving state for thread {thread_id}: {e}")
    
    def create_initial_state(self, query: str, thread_id: Optional[str] = None, user_id: str = "anonymous") -> State:
        """
        Create initial state for a new conversation.
        
        Args:
            query: User query
            thread_id: Optional thread ID (generated if not provided)
            user_id: User identifier
            
        Returns:
            Initial state
        """
        # Generate thread ID if not provided
        thread_id = thread_id or str(uuid.uuid4())
        
        # Generate trace ID for this request
        trace_id = str(uuid.uuid4())
        
        # Create user message
        user_message = Message(
            role="user",
            content=query,
            metadata={"trace_id": trace_id}
        )
        
        # Initialize state
        state: State = {
            "messages": [user_message],
            "thread_id": thread_id,
            "user_id": user_id,
            "query": query,
            "trace_id": trace_id
        }
        
        # Save initial state
        self.save_state(thread_id, state)
        
        return state
    
    def _sync_with_mongodb(self, thread_id: str, state: State):
        """
        Synchronize state with MongoDB for persistence.
        
        Args:
            thread_id: Conversation thread ID
            state: Current state
        """
        try:
            # Check if conversation exists in MongoDB
            conversation = self.conversation_store.get_conversation(thread_id)
            
            if not conversation:
                # If the conversation doesn't exist in MongoDB, create it first
                actual_thread_id = self.conversation_store.create_conversation(state["user_id"])
                logger.info(f"Created new conversation in MongoDB with ID: {actual_thread_id}")
                # If MongoDB generated a different ID, use that one
                if actual_thread_id != thread_id:
                    logger.warning(f"MongoDB thread ID {actual_thread_id} differs from requested {thread_id}")
                    thread_id = actual_thread_id
                    # Update thread_id in state
                    state["thread_id"] = thread_id
                    # Update our internal state
                    self.states[thread_id] = state
            
            # Get the most recent message to sync
            if state["messages"]:
                # Get messages that need to be synced
                synced_messages = []
                if conversation and "messages" in conversation:
                    synced_messages = [msg["content"] for msg in conversation["messages"]]
                
                # Get the messages that haven't been synced yet
                for message in state["messages"]:
                    # Check if message already exists in MongoDB to avoid duplicates
                    # We identify duplicates by matching content and role together
                    message_signature = f"{message.role}:{message.content}"
                    message_exists = False
                    
                    if conversation and "messages" in conversation:
                        for msg in conversation["messages"]:
                            if msg["role"] == message.role and msg["content"] == message.content:
                                message_exists = True
                                break
                    
                    if not message_exists:
                        # Add message to MongoDB
                        success = self.conversation_store.add_message(
                            conversation_id=thread_id,
                            role=message.role,
                            content=message.content,
                            metadata=message.metadata
                        )
                        
                        if success:
                            logger.debug(f"Synced message to MongoDB for thread {thread_id}")
                        else:
                            logger.warning(f"Failed to sync message to MongoDB for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error syncing with MongoDB: {e}")

# Singleton instance
state_manager = StateManager() 