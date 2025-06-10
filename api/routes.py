from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

from api.gateway import ai_gateway
from core.mongodb.conversation_store import conversation_store
from utils.errors import format_error_response

# Create router
router = APIRouter(
    prefix="/v1",
    tags=["AI Database Query"]
)

# Models
class QueryRequest(BaseModel):
    """Model for query request."""
    query: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"

    class Config:
        schema_extra = {
            "example": {
                "query": "What was our revenue in Q1 2023?",
                "conversation_id": None,
                "user_id": "user123"
            }
        }

class QueryResponse(BaseModel):
    """Model for query response."""
    success: bool
    trace_id: str
    conversation_id: str
    query: str
    sql: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "trace_id": "abc123",
                "conversation_id": "def456",
                "query": "What was our revenue in Q1 2023?",
                "sql": "SELECT SUM(revenue) FROM ...",
                "results": [{"revenue": 1000000}],
                "error": None
            }
        }

class ConversationResponse(BaseModel):
    """Model for conversation response."""
    conversation_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str

    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "abc123",
                "user_id": "user123",
                "messages": [
                    {"role": "user", "content": "What was our revenue in Q1 2023?"},
                    {"role": "assistant", "content": "Revenue in Q1 2023 was $1,000,000"}
                ],
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:01:00Z"
            }
        }

# Routes
@router.post("/ai/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Process a natural language query and return SQL results.
    """
    try:
        result = ai_gateway.process_query(
            query=request.query,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        error_dict, status_code = format_error_response(e)
        raise HTTPException(status_code=status_code, detail=error_dict)

@router.get("/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """
    Get conversation history by ID.
    """
    try:
        conversation = conversation_store.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        return conversation
    except Exception as e:
        error_dict, status_code = format_error_response(e)
        raise HTTPException(status_code=status_code, detail=error_dict)

@router.post("/conversation/create", response_model=Dict[str, str])
async def create_conversation(user_id: str = Body(..., embed=True)):
    """
    Create a new conversation.
    """
    try:
        conversation_id = conversation_store.create_conversation(user_id)
        return {"conversation_id": conversation_id}
    except Exception as e:
        error_dict, status_code = format_error_response(e)
        raise HTTPException(status_code=status_code, detail=error_dict) 