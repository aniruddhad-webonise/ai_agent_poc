import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

from config.settings import MONGODB_URI, MONGODB_DB, MONGODB_CONVERSATION_COLLECTION

logger = logging.getLogger(__name__)

class ConversationStore:
    """
    Manages storage and retrieval of conversation history in MongoDB.
    """
    
    def __init__(self):
        """Initialize the conversation store."""
        try:
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client[MONGODB_DB]
            self.collection = self.db[MONGODB_CONVERSATION_COLLECTION]
            
            # Create indexes for efficient querying
            self.collection.create_index("conversation_id")
            self.collection.create_index("created_at")
            self.collection.create_index("user_id")
            
            logger.info(f"Connected to MongoDB: {MONGODB_URI}, DB: {MONGODB_DB}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    def create_conversation(self, user_id: str) -> str:
        """
        Create a new conversation.
        
        Args:
            user_id: ID of the user creating the conversation
            
        Returns:
            Conversation ID
        """
        try:
            # Create a new conversation document
            conversation = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": []
            }
            
            # Insert into MongoDB
            result = self.collection.insert_one(conversation)
            conversation_id = str(result.inserted_id)
            
            logger.info(f"Created new conversation with ID: {conversation_id} for user: {user_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            role: Role of the message sender (user/assistant)
            content: Message content
            metadata: Additional metadata about the message
            
        Returns:
            Success indicator
        """
        try:
            # Create message document
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            # Update the conversation with the new message
            result = self.collection.update_one(
                {"_id": ObjectId(conversation_id)},
                {
                    "$push": {"messages": message},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            if result.modified_count == 0:
                logger.warning(f"No conversation found with ID: {conversation_id}")
                return False
                
            logger.info(f"Added {role} message to conversation: {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Retrieve a conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation document or None if not found
        """
        try:
            conversation = self.collection.find_one({"_id": ObjectId(conversation_id)})
            
            if conversation:
                # Convert ObjectId to string for JSON serialization
                conversation["_id"] = str(conversation["_id"])
                return conversation
                
            logger.warning(f"No conversation found with ID: {conversation_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {e}")
            return None
    
    def get_messages(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Get the most recent messages from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of message documents
        """
        try:
            conversation = self.collection.find_one(
                {"_id": ObjectId(conversation_id)},
                {"messages": {"$slice": -limit}}
            )
            
            if not conversation or "messages" not in conversation:
                logger.warning(f"No messages found for conversation: {conversation_id}")
                return []
                
            return conversation["messages"]
            
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            return []
    
    def get_conversation_context(self, conversation_id: str, max_messages: int = 5) -> str:
        """
        Get conversation context formatted for LLM context.
        
        Args:
            conversation_id: ID of the conversation
            max_messages: Maximum number of messages to include in context
            
        Returns:
            Formatted conversation context string
        """
        messages = self.get_messages(conversation_id, max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            context_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n\n".join(context_parts)
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")


# Singleton instance
conversation_store = ConversationStore() 