from fastapi import APIRouter, HTTPException, Path, Query, Body
from typing import List, Optional, Dict
from bson import ObjectId
from datetime import datetime
from app.models.chat import *
from app.services.database import *
from app.services.llm_service import * 


router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/")
async def store_chat_messages(
    messages: List[ChatMessage] = Body(...),
    conversation_id: Optional[str] = None
):
    """
    Store Chat Messages with Heavy INSERT Operations
    
    Supports:
    - Inserting multiple messages
    - Optional conversation ID
    - Bulk message storage
    """
    try:
        # If no conversation ID, create a new conversation
        if not conversation_id:
            conversation = ConversationModel(
                participants=[messages[0].sender, messages[0].receiver],
                messages=messages
            )
            conversation_id = await database_service.start_conversation(conversation)
        else:
            # Add messages to existing conversation
            for message in messages:
                await database_service.add_message_to_conversation(conversation_id, message)
        
        return {
            "status": "success",
            "conversation_id": str(conversation_id),
            "messages_stored": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}")
async def retrieve_chats(
    conversation_id: str = Path(..., description="Unique Conversation ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Retrieve Chats with Heavy SELECT Operations
    
    Features:
    - Pagination
    - Efficient message retrieval
    - Supports large message volumes
    """
    try:
        # Use efficient database query with pagination
        query = {'_id': ObjectId(conversation_id)}
        
        # Aggregation pipeline for efficient retrieval
        pipeline = [
            {'$match': query},
            {'$project': {
                'messages': {
                    '$slice': [
                        '$messages', 
                        (page - 1) * limit, 
                        limit
                    ]
                },
                'total_messages': {'$size': '$messages'},
                'conversation_type': 1,
                'participants': 1
            }}
        ]
        
        result = await database_service.conversations_collection.aggregate(pipeline).to_list(length=1)
        
        if not result:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = result[0]
        
        return {
            "conversation_id": str(conversation['_id']),
            "messages": conversation.get('messages', []),
            "total_messages": conversation.get('total_messages', 0),
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize")
async def summarize_chat(
    conversation_id: str = Body(..., embed=True),
    num_messages: Optional[int] = Query(100, le=500)
):
    """
    LLM-based Chat Summarization
    
    Features:
    - Generate summary using Gemini
    - Configurable message count
    - Comprehensive insights
    """
    try:
        summary = await llm_service.generate_conversation_summary(
            conversation_id, 
            database_service, 
            num_messages
        )
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/history")
async def get_user_chat_history(
    user_id: str = Path(..., description="User's Unique ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Get User's Chat History with Pagination
    
    Features:
    - Efficient pagination
    - Load handling
    - Comprehensive user chat retrieval
    """
    try:
        # Advanced search with user participation
        history = await database_service.advanced_conversation_search(
            filters={'user_id': user_id},
            page=page,
            page_size=limit
        )
        
        return {
            "user_id": user_id,
            "conversations": history['conversations'],
            "total_conversations": history['total_count'],
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{conversation_id}")
async def delete_chat(
    conversation_id: str = Path(..., description="Conversation ID to delete")
):
    """
    Delete Chat with Heavy DELETE Operations
    
    Features:
    - Permanent conversation removal
    - Soft delete option (configurable)
    - Efficient deletion
    """
    try:
        # Option 1: Hard Delete
        result = await database_service.conversations_collection.delete_one(
            {'_id': ObjectId(conversation_id)}
        )
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "status": "success",
            "message": "Conversation deleted successfully",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))