"""
Query contextualization module for handling follow-up questions.
Rewrites ambiguous queries using conversation history.
"""

import logging
from typing import Dict, List, Any, Optional

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import openai

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS
from core.state.state_manager import State, Message

logger = logging.getLogger(__name__)

# Prompt template for query contextualization
CONTEXTUALIZATION_PROMPT = PromptTemplate.from_template("""
You are an AI assistant helping with database queries. Your task is to rewrite potentially ambiguous follow-up questions using conversation history.

Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone, specific question that includes all necessary context.

## Conversation History:
{history}

## Follow-up Question:
{question}

## Standalone Rewritten Question:
""")

class QueryContextualizer:
    """
    Service for contextualizing follow-up questions using conversation history.
    """
    
    def __init__(self):
        """Initialize the contextualizer."""
        self.api_key = OPENAI_API_KEY
        self.model_name = OPENAI_MODEL
        self.temperature = 0.0  # Lower temperature for more deterministic results
        self.max_tokens = 256  # Shorter responses for query rewriting
        
        # Create modern LLM instance
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        # Create a runnable pipeline using the | operator
        self.chain = CONTEXTUALIZATION_PROMPT | self.llm
        
        logger.info(f"Query contextualizer initialized with model {self.model_name}")
    
    async def contextualize(self, state: State) -> State:
        """
        Contextualize a query using conversation history.
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state with contextualized query
        """
        # Extract the current query and messages from state
        query = state["query"]
        messages = state["messages"]
        
        # If this is the first message, no need to contextualize
        if len(messages) <= 1:
            logger.debug("First message in conversation, skipping contextualization")
            state["contextualized_query"] = query
            return state
        
        try:
            # Format conversation history
            history = self._format_history(messages[:-1])  # Exclude the current query
            
            # Use the modern LangChain invoke pattern
            response = await self.chain.ainvoke({
                "history": history,
                "question": query
            })
            
            contextualized_query = response.content.strip()
            
            logger.info(f"Contextualized query: '{query}' -> '{contextualized_query}'")
            
            # Update state with contextualized query
            state["contextualized_query"] = contextualized_query
            return state
            
        except Exception as e:
            logger.error(f"Error contextualizing query: {e}")
            # If contextualization fails, use the original query
            state["contextualized_query"] = query
            return state
    
    def _format_history(self, messages: List[Message]) -> str:
        """
        Format conversation history for the prompt.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Formatted history string
        """
        formatted_messages = []
        
        for message in messages:
            role = message.role
            content = message.content
            formatted_messages.append(f"{role.capitalize()}: {content}")
        
        return "\n\n".join(formatted_messages)


# Singleton instance
query_contextualizer = QueryContextualizer() 