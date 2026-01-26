"""
Colonel API Endpoints

REST API for The Colonel AI agent.
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio

from backend.colonel_service import colonel_service
from backend.colonel_tool_executor import tool_executor
from backend.auth_dependencies import get_current_user
from backend.database import User


# ==================== Request/Response Models ====================

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    model_provider: str = Field(default="anthropic", description="AI provider (anthropic or openai)")
    model_name: str = Field(default="claude-3-5-sonnet-20241022", description="Model name")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")


class CreateConversationResponse(BaseModel):
    """Response for created conversation"""
    id: UUID
    user_id: UUID
    organization_id: Optional[UUID]
    model_provider: str
    model_name: str
    title: str
    status: str
    created_at: str


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    message: str = Field(..., description="User's message")


class UpdateConversationRequest(BaseModel):
    """Request to update conversation"""
    title: Optional[str] = Field(None, description="New title")
    status: Optional[str] = Field(None, description="New status (active, archived)")


class ConversationListResponse(BaseModel):
    """Response with list of conversations"""
    conversations: List[Dict[str, Any]]
    total: int


class MessageListResponse(BaseModel):
    """Response with list of messages"""
    messages: List[Dict[str, Any]]
    total: int


class ToolListResponse(BaseModel):
    """Response with list of available tools"""
    tools: List[Dict[str, Any]]
    total: int


class SystemPromptRequest(BaseModel):
    """Request to create system prompt"""
    name: str
    description: Optional[str]
    prompt_template: str
    is_public: bool = False


# ==================== Router Setup ====================

router = APIRouter(prefix="/api/colonel", tags=["colonel"])


# ==================== Conversation Endpoints ====================

@router.post("/conversations", response_model=CreateConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new conversation with The Colonel.
    
    **Permissions**: Any authenticated user
    
    **Request Body**:
    - model_provider: "anthropic" or "openai" (default: "anthropic")
    - model_name: Specific model (default: "claude-3-5-sonnet-20241022")
    - system_prompt: Custom system prompt (optional, uses default if not provided)
    
    **Returns**: Created conversation object
    """
    conversation = await colonel_service.create_conversation(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        model_provider=request.model_provider,
        model_name=request.model_name,
        system_prompt=request.system_prompt
    )
    
    return CreateConversationResponse(
        id=conversation["id"],
        user_id=conversation["user_id"],
        organization_id=conversation["organization_id"],
        model_provider=conversation["model_provider"],
        model_name=conversation["model_name"],
        title=conversation["title"],
        status=conversation["status"],
        created_at=conversation["created_at"].isoformat()
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    status: str = "active",
    current_user: User = Depends(get_current_user)
):
    """
    List user's conversations.
    
    **Permissions**: Any authenticated user (sees only their own conversations)
    
    **Query Parameters**:
    - limit: Maximum conversations to return (default: 50)
    - offset: Pagination offset (default: 0)
    - status: Filter by status - "active", "archived", "deleted" (default: "active")
    
    **Returns**: List of conversations
    """
    conversations = await colonel_service.list_conversations(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        status=status
    )
    
    return ConversationListResponse(
        conversations=conversations,
        total=len(conversations)
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific conversation.
    
    **Permissions**: User must own the conversation
    
    **Path Parameters**:
    - conversation_id: UUID of the conversation
    
    **Returns**: Conversation details
    """
    conversation = await colonel_service.get_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    return conversation


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    request: UpdateConversationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update conversation (title or status).
    
    **Permissions**: User must own the conversation
    
    **Path Parameters**:
    - conversation_id: UUID of the conversation
    
    **Request Body**:
    - title: New title (optional)
    - status: New status - "active" or "archived" (optional)
    
    **Returns**: Success message
    """
    if request.title:
        await colonel_service.update_conversation_title(
            conversation_id=conversation_id,
            user_id=current_user.id,
            title=request.title
        )
    
    if request.status == "archived":
        await colonel_service.archive_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )
    
    return {"success": True, "message": "Conversation updated"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a conversation (soft delete).
    
    **Permissions**: User must own the conversation
    
    **Path Parameters**:
    - conversation_id: UUID of the conversation
    
    **Returns**: Success message
    """
    await colonel_service.delete_conversation(
        conversation_id=conversation_id,
        user_id=current_user.id
    )
    
    return {"success": True, "message": "Conversation deleted"}


# ==================== Message Endpoints ====================

@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    conversation_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get messages for a conversation.
    
    **Permissions**: User must own the conversation
    
    **Path Parameters**:
    - conversation_id: UUID of the conversation
    
    **Query Parameters**:
    - limit: Maximum messages to return (default: 100)
    
    **Returns**: List of messages in chronological order
    """
    # Verify ownership
    await colonel_service.get_conversation(conversation_id, current_user.id)
    
    messages = await colonel_service.get_conversation_messages(
        conversation_id=conversation_id,
        limit=limit
    )
    
    return MessageListResponse(
        messages=messages,
        total=len(messages)
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send a message to The Colonel (streaming response).
    
    **Permissions**: User must own the conversation
    
    **Path Parameters**:
    - conversation_id: UUID of the conversation
    
    **Request Body**:
    - message: User's message text
    
    **Returns**: Server-Sent Events (SSE) stream with:
    - text_start: AI begins responding
    - text_delta: Chunks of AI response
    - tool_call_start: AI calls a tool
    - tool_execution: Tool is executing
    - tool_result: Tool execution complete
    - done: Response complete
    - error: An error occurred
    """
    # Verify ownership
    await colonel_service.get_conversation(conversation_id, current_user.id)
    
    async def event_stream():
        """Generate Server-Sent Events"""
        try:
            async for event in colonel_service.process_message_stream(
                conversation_id=conversation_id,
                user_id=current_user.id,
                user_message=request.message,
                tool_executor=tool_executor
            ):
                # Format as SSE
                import json
                yield f"data: {json.dumps(event)}\n\n"
                
        except Exception as e:
            import json
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ==================== Tool Endpoints ====================

@router.get("/tools", response_model=ToolListResponse)
async def list_tools(current_user: User = Depends(get_current_user)):
    """
    List all available tools The Colonel can use.
    
    **Permissions**: Any authenticated user
    
    **Returns**: List of tool definitions with descriptions and schemas
    """
    tools = tool_executor.get_tool_definitions()
    
    return ToolListResponse(
        tools=tools,
        total=len(tools)
    )


@router.get("/tools/{tool_name}")
async def get_tool_definition(
    tool_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific tool.
    
    **Permissions**: Any authenticated user
    
    **Path Parameters**:
    - tool_name: Name of the tool
    
    **Returns**: Tool definition
    """
    tool = tool_executor.get_tool(tool_name)
    
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
        "requires_approval": tool.requires_approval,
        "allowed_roles": tool.allowed_roles
    }


# ==================== System Prompt Endpoints ====================

@router.get("/system-prompts")
async def list_system_prompts(
    current_user: User = Depends(get_current_user)
):
    """
    List available system prompts.
    
    **Permissions**: Any authenticated user
    
    **Returns**: List of system prompts (public + user's own)
    """
    from backend.database import get_db_session
    
    async with get_db_session() as db:
        result = await db.execute(
            """
            SELECT id, name, description, is_default, usage_count, created_at
            FROM colonel_system_prompts
            WHERE is_public = true 
               OR created_by = $1 
               OR organization_id = $2
            ORDER BY is_default DESC, usage_count DESC
            """,
            current_user.id,
            current_user.organization_id
        )
        rows = result.fetchall()
        
        return {
            "prompts": [
                {
                    "id": str(row[0]),
                    "name": row[1],
                    "description": row[2],
                    "is_default": row[3],
                    "usage_count": row[4],
                    "created_at": row[5].isoformat()
                }
                for row in rows
            ],
            "total": len(rows)
        }


@router.get("/system-prompts/{prompt_id}")
async def get_system_prompt(
    prompt_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific system prompt.
    
    **Permissions**: Any authenticated user (for public prompts or own prompts)
    
    **Path Parameters**:
    - prompt_id: UUID of the system prompt
    
    **Returns**: System prompt details
    """
    from backend.database import get_db_session
    
    async with get_db_session() as db:
        result = await db.execute(
            """
            SELECT id, name, description, prompt_template, is_default, 
                   variables, is_public, usage_count
            FROM colonel_system_prompts
            WHERE id = $1 AND (is_public = true OR created_by = $2)
            """,
            prompt_id,
            current_user.id
        )
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="System prompt not found")
        
        return {
            "id": str(row[0]),
            "name": row[1],
            "description": row[2],
            "prompt_template": row[3],
            "is_default": row[4],
            "variables": row[5],
            "is_public": row[6],
            "usage_count": row[7]
        }


@router.post("/system-prompts")
async def create_system_prompt(
    request: SystemPromptRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a custom system prompt.
    
    **Permissions**: Any authenticated user
    
    **Request Body**:
    - name: Unique name for the prompt
    - description: Optional description
    - prompt_template: The prompt template text
    - is_public: Whether to share with organization (default: false)
    
    **Returns**: Created system prompt
    """
    from backend.database import get_db_session
    
    async with get_db_session() as db:
        # Check if name already exists
        result = await db.execute(
            "SELECT id FROM colonel_system_prompts WHERE name = $1",
            request.name
        )
        if result.fetchone():
            raise HTTPException(status_code=400, detail="Prompt name already exists")
        
        # Create prompt
        result = await db.execute(
            """
            INSERT INTO colonel_system_prompts
            (name, description, prompt_template, created_by, organization_id, is_public)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
            """,
            request.name,
            request.description,
            request.prompt_template,
            current_user.id,
            current_user.organization_id,
            request.is_public
        )
        row = result.fetchone()
        
        await db.commit()
        
        return {
            "id": str(row[0]),
            "name": request.name,
            "description": request.description,
            "prompt_template": request.prompt_template,
            "is_public": request.is_public,
            "created_at": row[1].isoformat()
        }


# ==================== Statistics Endpoints ====================

@router.get("/statistics")
async def get_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Get usage statistics for The Colonel.
    
    **Permissions**: Any authenticated user (sees only their own stats)
    
    **Returns**: Statistics including:
    - total_conversations: Total conversations created
    - total_messages: Total messages sent
    - total_tokens: Total tokens used (input + output)
    - total_tool_calls: Total tool executions
    - most_used_tools: List of most frequently used tools
    """
    from backend.database import get_db_session
    
    async with get_db_session() as db:
        # Get conversation stats
        result = await db.execute(
            """
            SELECT 
                COUNT(*) as total_conversations,
                SUM(total_input_tokens) as total_input_tokens,
                SUM(total_output_tokens) as total_output_tokens,
                SUM(total_tool_calls) as total_tool_calls
            FROM colonel_conversations
            WHERE user_id = $1 AND status != 'deleted'
            """,
            current_user.id
        )
        conv_row = result.fetchone()
        
        # Get message count
        result = await db.execute(
            """
            SELECT COUNT(*)
            FROM colonel_messages m
            JOIN colonel_conversations c ON m.conversation_id = c.id
            WHERE c.user_id = $1 AND m.role = 'user'
            """,
            current_user.id
        )
        message_count = result.fetchone()[0]
        
        # Get most used tools
        result = await db.execute(
            """
            SELECT te.tool_name, COUNT(*) as count
            FROM colonel_tool_executions te
            JOIN colonel_conversations c ON te.conversation_id = c.id
            WHERE c.user_id = $1 AND te.status = 'success'
            GROUP BY te.tool_name
            ORDER BY count DESC
            LIMIT 10
            """,
            current_user.id
        )
        tool_rows = result.fetchall()
        
        return {
            "total_conversations": conv_row[0] or 0,
            "total_messages": message_count or 0,
            "total_input_tokens": conv_row[1] or 0,
            "total_output_tokens": conv_row[2] or 0,
            "total_tokens": (conv_row[1] or 0) + (conv_row[2] or 0),
            "total_tool_calls": conv_row[3] or 0,
            "most_used_tools": [
                {"tool_name": row[0], "count": row[1]}
                for row in tool_rows
            ]
        }


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """
    Check if The Colonel service is operational.
    
    **Permissions**: Public endpoint
    
    **Returns**: Health status
    """
    # Check if AI providers are configured
    anthropic_configured = colonel_service.anthropic_client is not None
    openai_configured = colonel_service.openai_client is not None
    
    # Check tool count
    tool_count = len(tool_executor.list_tools())
    
    return {
        "status": "healthy" if (anthropic_configured or openai_configured) else "degraded",
        "providers": {
            "anthropic": "configured" if anthropic_configured else "not_configured",
            "openai": "configured" if openai_configured else "not_configured"
        },
        "tools_available": tool_count,
        "version": "1.0.0"
    }
