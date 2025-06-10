#!/usr/bin/env python
"""
Example script demonstrating how to use the text-to-SQL AI bot directly.
This bypasses the API and uses the components directly.
"""

import logging
import sys
import json
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Load environment variables
load_dotenv()

# Import the AI Gateway
from api.gateway import ai_gateway
from core.mongodb.conversation_store import conversation_store

def main():
    """Run the example."""
    # Create a conversation
    user_id = "example_user"
    conversation_id = conversation_store.create_conversation(user_id)
    print(f"Created conversation with ID: {conversation_id}")
    
    # Process a query
    query = "What was the total revenue in Q1 2023 for all entities?"
    print(f"\nQuery: {query}")
    
    # Process the query
    result = ai_gateway.process_query(
        query=query,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    # Check if the query was successful
    if result["success"]:
        print("\nSQL Query:")
        print(result["sql"])
        
        print("\nResults:")
        print(json.dumps(result["results"][:5], indent=2))
        
        if len(result["results"]) > 5:
            print(f"\n(Showing 5 of {len(result['results'])} results)")
    else:
        print(f"\nError: {result['error']}")
    
    # Ask a follow-up question
    follow_up_query = "Can you break that down by entity?"
    print(f"\nFollow-up Query: {follow_up_query}")
    
    # Process the follow-up query
    follow_up_result = ai_gateway.process_query(
        query=follow_up_query,
        conversation_id=conversation_id,
        user_id=user_id
    )
    
    # Check if the follow-up query was successful
    if follow_up_result["success"]:
        print("\nSQL Query:")
        print(follow_up_result["sql"])
        
        print("\nResults:")
        print(json.dumps(follow_up_result["results"][:5], indent=2))
        
        if len(follow_up_result["results"]) > 5:
            print(f"\n(Showing 5 of {len(follow_up_result['results'])} results)")
    else:
        print(f"\nError: {follow_up_result['error']}")
    
    print(f"\nConversation ID for reference: {conversation_id}")

if __name__ == "__main__":
    main() 