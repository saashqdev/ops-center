"""
Atlas API - AI Infrastructure Assistant Endpoints

Provides REST API endpoints for interacting with Lt. Colonel Atlas,
the AI-powered infrastructure assistant for Ops-Center.

Epic: 6.1
Author: AI Agent
Date: January 25, 2026
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from .atlas_tools import ATLAS_TOOLS, execute_atlas_tool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/atlas", tags=["Atlas AI Assistant"])


# ===================================================================
# Request/Response Models
# ===================================================================

class ChatMessage(BaseModel):
    """Chat message from user or assistant"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class AtlasRequest(BaseModel):
    """Request to Atlas AI"""
    message: str = Field(..., description="User message to Atlas")
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[],
        description="Previous conversation history"
    )
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional context (user info, session data, etc.)"
    )


class Tool ExecutionRequest(BaseModel):
    """Direct tool execution request"""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(
        default={},
        description="Tool parameters"
    )


class AtlasResponse(BaseModel):
    """Response from Atlas AI"""
    success: bool
    message: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    conversation_history: Optional[List[ChatMessage]] = None
    timestamp: str


# ===================================================================
# Health & Info Endpoints
# ===================================================================

@router.get("/health")
async def health_check():
    """Health check for Atlas API"""
    return {
        "status": "healthy",
        "service": "atlas-api",
        "version": "1.0.0",
        "tools_available": len(ATLAS_TOOLS),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/tools")
async def list_tools():
    """
    List all available Atlas tools
    
    Returns:
        List of tools with their descriptions and schemas
    """
    tools = []
    for tool_name, tool_config in ATLAS_TOOLS.items():
        tools.append({
            "name": tool_config["name"],
            "description": tool_config["description"],
            "input_schema": tool_config["input_schema"]
        })
    
    return {
        "success": True,
        "tools": tools,
        "total": len(tools)
    }


@router.get("/tools/{tool_name}")
async def get_tool_info(tool_name: str):
    """
    Get detailed information about a specific tool
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Tool configuration and schema
    """
    if tool_name not in ATLAS_TOOLS:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found. Available tools: {list(ATLAS_TOOLS.keys())}"
        )
    
    tool = ATLAS_TOOLS[tool_name]
    return {
        "success": True,
        "tool": {
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"]
        }
    }


# ===================================================================
# Tool Execution Endpoints
# ===================================================================

@router.post("/execute/{tool_name}")
async def execute_tool(
    tool_name: str,
    request: ToolExecutionRequest
):
    """
    Execute a specific Atlas tool directly
    
    Args:
        tool_name: Name of the tool to execute
        request: Tool parameters
    
    Returns:
        Tool execution result
    """
    if tool_name not in ATLAS_TOOLS:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_name}' not found"
        )
    
    try:
        result = await execute_atlas_tool(tool_name, request.parameters)
        return {
            "success": True,
            "tool_name": tool_name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {str(e)}"
        )


@router.post("/execute")
async def execute_tool_generic(request: ToolExecutionRequest):
    """
    Execute any Atlas tool (generic endpoint)
    
    Body:
        {
            "tool_name": "system_status",
            "parameters": {...}
        }
    """
    return await execute_tool(request.tool_name, request)


# ===================================================================
# Chat Endpoints (Brigade Integration)
# ===================================================================

@router.post("/chat")
async def chat_with_atlas(request: AtlasRequest):
    """
    Chat with Atlas AI assistant
    
    This endpoint:
    1. Takes user message + conversation history
    2. Routes to Brigade for AI processing
    3. Brigade uses Atlas tools as needed
    4. Returns AI response + any tool results
    
    Body:
        {
            "message": "What's the system status?",
            "conversation_history": [...],
            "context": {...}
        }
    """
    try:
        import httpx
        
        # Prepare request for Brigade
        brigade_request = {
            "messages": prepare_messages_for_brigade(
                request.message,
                request.conversation_history
            ),
            "model": "claude-3-5-sonnet-20241022",
            "system": get_atlas_system_prompt(),
            "tools": get_atlas_tools_for_brigade(),
            "max_tokens": 4096,
            "temperature": 0.7
        }
        
        # Route to Brigade
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://unicorn-brigade:8112/api/v1/chat/completions",
                json=brigade_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Brigade API error: {response.text}"
                )
            
            brigade_response = response.json()
            
            # Extract assistant message and tool calls
            assistant_message = extract_assistant_message(brigade_response)
            tool_calls = extract_tool_calls(brigade_response)
            tool_results = []
            
            # Execute tool calls if any
            if tool_calls:
                for tool_call in tool_calls:
                    result = await execute_atlas_tool(
                        tool_call["name"],
                        tool_call.get("parameters", {})
                    )
                    tool_results.append({
                        "tool_name": tool_call["name"],
                        "result": result
                    })
            
            # Update conversation history
            updated_history = request.conversation_history or []
            updated_history.append({
                "role": "user",
                "content": request.message,
                "timestamp": datetime.utcnow().isoformat()
            })
            updated_history.append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "success": True,
                "message": assistant_message,
                "tool_calls": tool_calls if tool_calls else None,
                "tool_results": tool_results if tool_results else None,
                "conversation_history": updated_history,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except httpx.HTTPError as e:
        logger.error(f"Brigade communication error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to communicate with Brigade: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}"
        )


# ===================================================================
# Helper Functions
# ===================================================================

def get_atlas_system_prompt() -> str:
    """Get Atlas AI system prompt"""
    return """You are Lt. Colonel "Atlas", the AI infrastructure assistant for Ops-Center.

You are an expert in:
- Infrastructure management and DevOps
- Docker and container orchestration
- User and access management
- Billing and subscription management
- System monitoring and troubleshooting
- Log analysis and debugging

Your personality:
- Professional but friendly
- Direct and efficient
- Proactive in suggesting solutions
- Safety-conscious (always confirm destructive actions)

Available Tools:
1. system_status - Check health of all services
2. manage_user - Create/update/delete users
3. check_billing - View usage and costs
4. restart_service - Restart Docker services (use sparingly)
5. query_logs - Search and analyze logs

Guidelines:
- Always check system status before making changes
- Confirm with user before restarting services or deleting resources
- Provide context and explanations with your recommendations
- If you encounter errors, suggest troubleshooting steps
- Format technical output clearly (use lists, code blocks, etc.)

Remember: You're helping manage production infrastructure. Be thoughtful and careful."""


def get_atlas_tools_for_brigade() -> List[Dict[str, Any]]:
    """Convert Atlas tools to Brigade/Anthropic tool format"""
    tools = []
    for tool_name, tool_config in ATLAS_TOOLS.items():
        tools.append({
            "name": tool_config["name"],
            "description": tool_config["description"],
            "input_schema": tool_config["input_schema"]
        })
    return tools


def prepare_messages_for_brigade(
    message: str,
    history: List[ChatMessage]
) -> List[Dict[str, str]]:
    """Prepare messages in Brigade/Anthropic format"""
    messages = []
    
    # Add conversation history
    for msg in history:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Add current message
    messages.append({
        "role": "user",
        "content": message
    })
    
    return messages


def extract_assistant_message(brigade_response: Dict[str, Any]) -> str:
    """Extract assistant message from Brigade response"""
    # Handle different response formats
    if "choices" in brigade_response:
        # OpenAI-style format
        return brigade_response["choices"][0]["message"]["content"]
    elif "content" in brigade_response:
        # Direct content
        if isinstance(brigade_response["content"], list):
            # Anthropic format with content blocks
            text_blocks = [
                block["text"]
                for block in brigade_response["content"]
                if block.get("type") == "text"
            ]
            return " ".join(text_blocks)
        return brigade_response["content"]
    else:
        return "I'm sorry, I encountered an error processing your request."


def extract_tool_calls(brigade_response: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool calls from Brigade response"""
    tool_calls = []
    
    # Handle different response formats
    if "choices" in brigade_response:
        message = brigade_response["choices"][0]["message"]
        if "tool_calls" in message:
            for tc in message["tool_calls"]:
                tool_calls.append({
                    "name": tc["function"]["name"],
                    "parameters": tc["function"]["arguments"]
                })
    elif "content" in brigade_response and isinstance(brigade_response["content"], list):
        # Anthropic format
        for block in brigade_response["content"]:
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "name": block["name"],
                    "parameters": block["input"]
                })
    
    return tool_calls if tool_calls else None


# ===================================================================
# Quick Action Endpoints (Convenience)
# ===================================================================

@router.get("/status")
async def quick_system_status():
    """Quick system status check (convenience endpoint)"""
    result = await execute_atlas_tool("system_status", {})
    return result


@router.get("/billing")
async def quick_billing_check():
    """Quick billing check (convenience endpoint)"""
    result = await execute_atlas_tool("check_billing", {
        "scope": "current_user",
        "timeframe": "month"
    })
    return result


@router.post("/restart/{service_name}")
async def quick_restart_service(
    service_name: str,
    confirmed: bool = False
):
    """Quick service restart (convenience endpoint)"""
    result = await execute_atlas_tool("restart_service", {
        "service_name": service_name,
        "confirmation": confirmed
    })
    return result
