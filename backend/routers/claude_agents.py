"""
Claude Agent API Endpoints
RESTful API for managing Claude agent workflows

Endpoints:
- POST   /api/v1/claude-agents/flows - Create flow
- GET    /api/v1/claude-agents/flows - List flows
- GET    /api/v1/claude-agents/flows/{id} - Get flow
- PUT    /api/v1/claude-agents/flows/{id} - Update flow
- DELETE /api/v1/claude-agents/flows/{id} - Delete flow
- POST   /api/v1/claude-agents/flows/{id}/execute - Execute flow
- GET    /api/v1/claude-agents/flows/{id}/executions - Get execution history
- GET    /api/v1/claude-agents/api-keys - List API keys
- POST   /api/v1/claude-agents/api-keys - Add API key
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import asyncpg
import json
import os
from uuid import UUID

from claude_agent_sdk import ClaudeAgentManager, encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/claude-agents", tags=["Claude Agents"])

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ops_center:your_password@ops-center-postgresql:5432/ops_center")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "default-encryption-key-change-in-production")


# Pydantic Models
class AgentFlowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    flow_config: Dict[str, Any]
    org_id: Optional[str] = None


class AgentFlowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    flow_config: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|archived)$")


class AgentFlowExecute(BaseModel):
    input_data: Dict[str, Any]
    stream: bool = False
    context: Optional[Dict[str, Any]] = None


class APIKeyCreate(BaseModel):
    key_name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., pattern="^(anthropic|openai)$")
    api_key: str
    org_id: Optional[str] = None
    is_default: bool = False


# Dependency to get current user from header
async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Extract user from authorization header - simplified for now"""
    # TODO: Implement proper JWT token validation
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    # For now, return a mock user - replace with real auth
    return {
        "user_id": "user_123",  # Extract from JWT
        "email": "user@example.com"
    }


async def get_db_pool():
    """Get database connection pool"""
    return await asyncpg.create_pool(DATABASE_URL)


# ==================== Flow Management ====================

@router.post("/flows", status_code=201)
async def create_agent_flow(
    flow: AgentFlowCreate,
    user: Dict = Depends(get_current_user)
):
    """Create a new agent flow"""
    try:
        # Validate flow config
        manager = ClaudeAgentManager(api_key="dummy")  # Just for validation
        is_valid, error = manager.validate_flow_config(flow.flow_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid flow config: {error}")
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO agent_flows (user_id, org_id, name, description, flow_config)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, name, created_at
            """, user['user_id'], flow.org_id, flow.name, flow.description, json.dumps(flow.flow_config))
            
            return {
                "id": str(result['id']),
                "name": result['name'],
                "created_at": result['created_at'].isoformat(),
                "message": "Flow created successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flows")
async def list_agent_flows(
    org_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(active|paused|archived)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Dict = Depends(get_current_user)
):
    """List all agent flows for user/org"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Build query
            query = """
                SELECT id, name, description, flow_config, status, 
                       created_at, updated_at, last_executed_at
                FROM agent_flows
                WHERE user_id = $1
            """
            params = [user['user_id']]
            param_count = 1
            
            if org_id:
                param_count += 1
                query += f" AND org_id = ${param_count}"
                params.append(org_id)
            
            if status:
                param_count += 1
                query += f" AND status = ${param_count}"
                params.append(status)
            
            query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            
            flows = []
            for row in rows:
                flows.append({
                    "id": str(row['id']),
                    "name": row['name'],
                    "description": row['description'],
                    "flow_config": row['flow_config'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                    "updated_at": row['updated_at'].isoformat(),
                    "last_executed_at": row['last_executed_at'].isoformat() if row['last_executed_at'] else None
                })
            
            return {
                "flows": flows,
                "total": len(flows),
                "limit": limit,
                "offset": offset
            }
    
    except Exception as e:
        logger.error(f"Error listing flows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flows/{flow_id}")
async def get_agent_flow(
    flow_id: str,
    user: Dict = Depends(get_current_user)
):
    """Get specific agent flow"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, description, flow_config, status,
                       created_at, updated_at, last_executed_at, org_id
                FROM agent_flows
                WHERE id = $1 AND user_id = $2
            """, UUID(flow_id), user['user_id'])
            
            if not row:
                raise HTTPException(status_code=404, detail="Flow not found")
            
            return {
                "id": str(row['id']),
                "name": row['name'],
                "description": row['description'],
                "flow_config": row['flow_config'],
                "status": row['status'],
                "org_id": row['org_id'],
                "created_at": row['created_at'].isoformat(),
                "updated_at": row['updated_at'].isoformat(),
                "last_executed_at": row['last_executed_at'].isoformat() if row['last_executed_at'] else None
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/flows/{flow_id}")
async def update_agent_flow(
    flow_id: str,
    flow: AgentFlowUpdate,
    user: Dict = Depends(get_current_user)
):
    """Update agent flow"""
    try:
        # Validate flow config if provided
        if flow.flow_config:
            manager = ClaudeAgentManager(api_key="dummy")
            is_valid, error = manager.validate_flow_config(flow.flow_config)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid flow config: {error}")
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Build update query dynamically
            updates = []
            params = [UUID(flow_id), user['user_id']]
            param_count = 2
            
            if flow.name:
                param_count += 1
                updates.append(f"name = ${param_count}")
                params.append(flow.name)
            
            if flow.description is not None:
                param_count += 1
                updates.append(f"description = ${param_count}")
                params.append(flow.description)
            
            if flow.flow_config:
                param_count += 1
                updates.append(f"flow_config = ${param_count}")
                params.append(json.dumps(flow.flow_config))
            
            if flow.status:
                param_count += 1
                updates.append(f"status = ${param_count}")
                params.append(flow.status)
            
            if not updates:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            updates.append("updated_at = NOW()")
            
            query = f"""
                UPDATE agent_flows
                SET {', '.join(updates)}
                WHERE id = $1 AND user_id = $2
                RETURNING id, name, updated_at
            """
            
            result = await conn.fetchrow(query, *params)
            
            if not result:
                raise HTTPException(status_code=404, detail="Flow not found")
            
            return {
                "id": str(result['id']),
                "name": result['name'],
                "updated_at": result['updated_at'].isoformat(),
                "message": "Flow updated successfully"
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/flows/{flow_id}")
async def delete_agent_flow(
    flow_id: str,
    user: Dict = Depends(get_current_user)
):
    """Delete agent flow"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM agent_flows
                WHERE id = $1 AND user_id = $2
            """, UUID(flow_id), user['user_id'])
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Flow not found")
            
            return {"message": "Flow deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Flow Execution ====================

@router.post("/flows/{flow_id}/execute")
async def execute_agent_flow(
    flow_id: str,
    execution: AgentFlowExecute,
    user: Dict = Depends(get_current_user)
):
    """Execute an agent flow"""
    try:
        pool = await get_db_pool()
        
        # Get flow and API key
        async with pool.acquire() as conn:
            flow = await conn.fetchrow("""
                SELECT flow_config FROM agent_flows
                WHERE id = $1 AND user_id = $2 AND status = 'active'
            """, UUID(flow_id), user['user_id'])
            
            if not flow:
                raise HTTPException(status_code=404, detail="Flow not found or not active")
            
            # Get user's default API key
            api_key_row = await conn.fetchrow("""
                SELECT encrypted_api_key FROM agent_api_keys
                WHERE user_id = $1 AND provider = 'anthropic' AND is_default = true
            """, user['user_id'])
            
            if not api_key_row:
                raise HTTPException(
                    status_code=400,
                    detail="No API key configured. Please add an Anthropic API key first."
                )
            
            api_key = decrypt_api_key(api_key_row['encrypted_api_key'], ENCRYPTION_KEY)
        
        # Create execution record
        async with pool.acquire() as conn:
            exec_id = await conn.fetchval("""
                INSERT INTO agent_flow_executions (flow_id, user_id, input_data, status)
                VALUES ($1, $2, $3, 'running')
                RETURNING id
            """, UUID(flow_id), user['user_id'], json.dumps(execution.input_data))
        
        # Execute flow
        manager = ClaudeAgentManager(api_key=api_key)
        user_input = execution.input_data.get('prompt', execution.input_data.get('message', ''))
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Input must contain 'prompt' or 'message'")
        
        result = await manager.execute_flow(
            flow_config=flow['flow_config'],
            user_input=user_input,
            context=execution.context,
            stream=execution.stream
        )
        
        # Update execution record
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE agent_flow_executions
                SET status = $1, output_data = $2, tokens_used = $3,
                    execution_time_ms = $4, completed_at = NOW(),
                    error_message = $5
                WHERE id = $6
            """,
                result.get('status', 'completed'),
                json.dumps({"output": result.get('output', '')}),
                json.dumps(result.get('tokens_used', {})),
                result.get('execution_time_ms'),
                result.get('error'),
                exec_id
            )
            
            # Update last_executed_at on flow
            await conn.execute("""
                UPDATE agent_flows SET last_executed_at = NOW()
                WHERE id = $1
            """, UUID(flow_id))
        
        return {
            "execution_id": str(exec_id),
            "flow_id": flow_id,
            "status": result.get('status'),
            "output": result.get('output'),
            "tokens_used": result.get('tokens_used'),
            "execution_time_ms": result.get('execution_time_ms')
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing flow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flows/{flow_id}/executions")
async def get_flow_executions(
    flow_id: str,
    limit: int = Query(50, ge=1, le=100),
    user: Dict = Depends(get_current_user)
):
    """Get execution history for a flow"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, status, input_data, output_data, error_message,
                       tokens_used, execution_time_ms, created_at, completed_at
                FROM agent_flow_executions
                WHERE flow_id = $1 AND user_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """, UUID(flow_id), user['user_id'], limit)
            
            executions = []
            for row in rows:
                executions.append({
                    "id": str(row['id']),
                    "status": row['status'],
                    "input_data": row['input_data'],
                    "output_data": row['output_data'],
                    "error_message": row['error_message'],
                    "tokens_used": row['tokens_used'],
                    "execution_time_ms": row['execution_time_ms'],
                    "created_at": row['created_at'].isoformat(),
                    "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None
                })
            
            return {
                "executions": executions,
                "total": len(executions)
            }
    
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== API Key Management ====================

@router.get("/api-keys")
async def list_api_keys(user: Dict = Depends(get_current_user)):
    """List user's API keys (without exposing actual keys)"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, key_name, provider, is_default, created_at, last_used_at
                FROM agent_api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user['user_id'])
            
            keys = []
            for row in rows:
                keys.append({
                    "id": str(row['id']),
                    "key_name": row['key_name'],
                    "provider": row['provider'],
                    "is_default": row['is_default'],
                    "created_at": row['created_at'].isoformat(),
                    "last_used_at": row['last_used_at'].isoformat() if row['last_used_at'] else None
                })
            
            return {"api_keys": keys}
    
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api-keys", status_code=201)
async def add_api_key(
    key: APIKeyCreate,
    user: Dict = Depends(get_current_user)
):
    """Add a new API key"""
    try:
        # Encrypt the API key
        encrypted_key = encrypt_api_key(key.api_key, ENCRYPTION_KEY)
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # If setting as default, unset other defaults
            if key.is_default:
                await conn.execute("""
                    UPDATE agent_api_keys
                    SET is_default = false
                    WHERE user_id = $1 AND provider = $2
                """, user['user_id'], key.provider)
            
            result = await conn.fetchrow("""
                INSERT INTO agent_api_keys (user_id, org_id, key_name, provider, encrypted_api_key, is_default)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, key_name, created_at
            """, user['user_id'], key.org_id, key.key_name, key.provider, encrypted_key, key.is_default)
            
            return {
                "id": str(result['id']),
                "key_name": result['key_name'],
                "created_at": result['created_at'].isoformat(),
                "message": "API key added successfully"
            }
    
    except Exception as e:
        logger.error(f"Error adding API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    user: Dict = Depends(get_current_user)
):
    """Delete an API key"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM agent_api_keys
                WHERE id = $1 AND user_id = $2
            """, UUID(key_id), user['user_id'])
            
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="API key not found")
            
            return {"message": "API key deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "claude-agents-api",
        "version": "1.0.0"
    }
