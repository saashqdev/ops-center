"""
Colonel API - The Colonel AI Agent
==================================

Lightweight chat endpoint for The Colonel AI agent.
Routes through LiteLLM proxy for model access.
"""

import os
import time
import logging
import httpx
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth_dependencies import require_authenticated_user

logger = logging.getLogger(__name__)

# ==================== Configuration ====================

LITELLM_PROXY_URL = os.getenv('LITELLM_PROXY_URL', 'http://unicorn-litellm-wilmer:4000')
# Fix hostname if 'litellm' alias doesn't resolve in this network
if 'http://litellm:' in LITELLM_PROXY_URL:
    import socket
    try:
        socket.gethostbyname('litellm')
    except socket.gaierror:
        LITELLM_PROXY_URL = LITELLM_PROXY_URL.replace('http://litellm:', 'http://unicorn-litellm-wilmer:')
        logger.info(f"Resolved LiteLLM URL to {LITELLM_PROXY_URL}")
LITELLM_MASTER_KEY = os.getenv('LITELLM_MASTER_KEY', '')
COLONEL_MODEL = os.getenv('COLONEL_MODEL', 'llama-3.3-70b-groq')

# Try to get the real LiteLLM master key if default is a placeholder
def _get_litellm_key():
    """Get the actual LiteLLM master key, trying multiple sources."""
    key = LITELLM_MASTER_KEY
    if key and key != 'your-litellm-master-key-here':
        return key
    # Try reading from LiteLLM container's env via docker (fallback)
    try:
        import subprocess
        result = subprocess.run(
            ['docker', 'exec', 'unicorn-litellm-wilmer', 'printenv', 'LITELLM_MASTER_KEY'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return key

_litellm_key = _get_litellm_key()

COLONEL_SYSTEM_PROMPT = """You are The Colonel — a senior AI operations advisor for Ops-Center, a unified infrastructure management platform.

Your expertise includes:
- Infrastructure monitoring and health analysis
- Docker container management and troubleshooting
- LLM provider management (LiteLLM, OpenAI, Anthropic, etc.)
- Cost optimization and resource planning
- Security best practices
- Database management and backup strategies
- Kubernetes deployments
- CI/CD pipelines

When answering:
- Be concise and actionable
- Use technical details when relevant
- Suggest specific commands or configurations when helpful
- Flag potential risks or security concerns
- Reference Ops-Center features when applicable

You have access to the following tools for real-time system analysis:
- System Health: Check container status, resource usage
- Log Analysis: Search and analyze system logs
- Cost Analysis: Review spending and optimization opportunities

Always provide honest assessments. If you don't know something, say so."""


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        default=[], description="Previous messages for context"
    )


class ChatResponse(BaseModel):
    success: bool
    response: str
    tools_used: List[str] = []
    execution_time: float = 0.0


# ==================== Router ====================

router = APIRouter(prefix="/api/v1/colonel", tags=["colonel"])


# ==================== Tool Definitions ====================

AVAILABLE_TOOLS = [
    {
        "name": "system_health",
        "description": "Check overall system health including container status and resource usage",
        "category": "monitoring"
    },
    {
        "name": "log_search",
        "description": "Search through system logs for errors, warnings, or specific patterns",
        "category": "diagnostics"
    },
    {
        "name": "cost_analysis",
        "description": "Analyze LLM spending, token usage, and cost optimization opportunities",
        "category": "finance"
    },
    {
        "name": "container_status",
        "description": "Get detailed status of Docker containers running in the platform",
        "category": "infrastructure"
    },
    {
        "name": "security_audit",
        "description": "Review security configurations and identify potential vulnerabilities",
        "category": "security"
    },
    {
        "name": "performance_metrics",
        "description": "Analyze API response times, throughput, and error rates",
        "category": "monitoring"
    }
]


# ==================== Endpoints ====================

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Send a message to The Colonel and get an AI response.
    Routes through LiteLLM proxy for model access.
    """
    start_time = time.time()
    
    try:
        # Build messages array
        messages = [{"role": "system", "content": COLONEL_SYSTEM_PROMPT}]
        
        # Add conversation history (last 10 messages)
        for msg in (request.conversation_history or [])[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Call LiteLLM proxy
        headers = {
            "Content-Type": "application/json",
        }
        if _litellm_key:
            headers["Authorization"] = f"Bearer {_litellm_key}"
        
        payload = {
            "model": COLONEL_MODEL,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{LITELLM_PROXY_URL}/v1/chat/completions",
                json=payload,
                headers=headers
            )
        
        if resp.status_code != 200:
            error_text = resp.text[:200]
            logger.error(f"LiteLLM error {resp.status_code}: {error_text}")
            
            # Provide a helpful fallback response
            return ChatResponse(
                success=True,
                response=f"⚠️ I'm having trouble connecting to my AI backend (status {resp.status_code}). "
                         f"This usually means the LiteLLM proxy needs configuration. "
                         f"Please check that LITELLM_PROXY_URL and model '{COLONEL_MODEL}' are configured correctly.\n\n"
                         f"In the meantime, I can tell you that your question was: \"{request.message}\"\n\n"
                         f"Try checking:\n"
                         f"- `/admin/llm-management` for LLM provider configuration\n"
                         f"- Docker container status for `litellm` service\n"
                         f"- Environment variable `COLONEL_MODEL` (currently: `{COLONEL_MODEL}`)",
                tools_used=[],
                execution_time=time.time() - start_time
            )
        
        data = resp.json()
        ai_response = data.get("choices", [{}])[0].get("message", {}).get("content", "No response generated.")
        
        execution_time = time.time() - start_time
        user_email = user.get("email", "unknown")
        logger.info(f"Colonel chat: user={user_email}, model={COLONEL_MODEL}, time={execution_time:.2f}s")
        
        return ChatResponse(
            success=True,
            response=ai_response,
            tools_used=[],
            execution_time=execution_time
        )
        
    except httpx.ConnectError as e:
        logger.error(f"Cannot connect to LiteLLM proxy: {e}")
        return ChatResponse(
            success=True,
            response="⚠️ Cannot connect to the LiteLLM proxy service. "
                     "Please ensure the LiteLLM container is running.\n\n"
                     "Quick check: Run `docker ps | grep litellm` to verify the service status.",
            tools_used=[],
            execution_time=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Colonel chat error: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response=f"An error occurred: {str(e)}",
            tools_used=[],
            execution_time=time.time() - start_time
        )


@router.get("/tools")
async def list_tools(user: Dict = Depends(require_authenticated_user)):
    """List available tools for The Colonel."""
    return {
        "success": True,
        "tools": AVAILABLE_TOOLS,
        "count": len(AVAILABLE_TOOLS)
    }


@router.get("/health")
async def health_check():
    """Check if The Colonel service is operational."""
    # Check LiteLLM connectivity
    litellm_status = "unknown"
    try:
        headers = {}
        if _litellm_key:
            headers["Authorization"] = f"Bearer {_litellm_key}"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LITELLM_PROXY_URL}/health", headers=headers)
            litellm_status = "healthy" if resp.status_code == 200 else f"error ({resp.status_code})"
    except Exception:
        litellm_status = "unreachable"
    
    return {
        "status": "healthy" if litellm_status == "healthy" else "degraded",
        "model": COLONEL_MODEL,
        "litellm_proxy": litellm_status,
        "tools_available": len(AVAILABLE_TOOLS),
        "version": "2.0.0"
    }
