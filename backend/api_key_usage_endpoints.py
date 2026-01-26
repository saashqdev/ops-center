"""
API Key & Usage Management Endpoints
Epic 7.0: User-facing endpoints for API key and usage management
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from auth_dependencies import require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    expires_days: Optional[int] = None
    scopes: Optional[List[str]] = None


class RevokeAPIKeyRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/")
async def create_api_key(
    request: CreateAPIKeyRequest,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """Create a new API key"""
    try:
        from api_key_manager_v2 import api_key_manager
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        result = await api_key_manager.create_api_key(
            email=user_email,
            name=request.name,
            description=request.description,
            expires_days=request.expires_days,
            scopes=request.scopes
        )
        
        return {
            "success": True,
            "api_key": result['api_key'],  # Only shown once!
            "key_id": result['id'],
            "key_prefix": result['key_prefix'],
            "name": result['name'],
            "created_at": result['created_at'],
            "expires_at": result['expires_at'],
            "message": "IMPORTANT: Save this API key now. You won't be able to see it again!"
        }
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_api_keys(user: Dict[str, Any] = Depends(require_authenticated_user)):
    """List all API keys for current user"""
    try:
        from api_key_manager_v2 import api_key_manager
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        keys = await api_key_manager.list_api_keys(email=user_email)
        
        return {
            "success": True,
            "keys": keys,
            "count": len(keys)
        }
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    request: RevokeAPIKeyRequest,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """Revoke an API key"""
    try:
        from api_key_manager_v2 import api_key_manager
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        success = await api_key_manager.revoke_api_key(
            key_id=key_id,
            email=user_email,
            reason=request.reason
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="API key not found or already revoked")
        
        return {
            "success": True,
            "message": "API key revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """Permanently delete an API key"""
    try:
        from api_key_manager_v2 import api_key_manager
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        success = await api_key_manager.delete_api_key(
            key_id=key_id,
            email=user_email
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {
            "success": True,
            "message": "API key deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Usage Dashboard Endpoints
usage_router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@usage_router.get("/summary")
async def get_usage_summary(user: Dict[str, Any] = Depends(require_authenticated_user)):
    """Get usage summary for current month"""
    try:
        from usage_meter_v2 import usage_meter
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        summary = await usage_meter.get_usage_summary(email=user_email)
        
        return {
            "success": True,
            **summary
        }
        
    except Exception as e:
        logger.error(f"Error getting usage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@usage_router.get("/quota")
async def get_quota_status(user: Dict[str, Any] = Depends(require_authenticated_user)):
    """Get quota status"""
    try:
        from usage_meter_v2 import usage_meter
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        quota = await usage_meter.check_quota(email=user_email)
        
        return {
            "success": True,
            **quota
        }
        
    except Exception as e:
        logger.error(f"Error getting quota status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@usage_router.get("/daily")
async def get_daily_usage(
    days: int = 30,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """Get daily usage breakdown"""
    try:
        from usage_meter_v2 import usage_meter
        
        user_email = user.get("email")
        if not user_email:
            raise HTTPException(status_code=400, detail="User email not found in session")
        
        daily = await usage_meter.get_daily_usage(email=user_email, days=days)
        
        return {
            "success": True,
            "daily_usage": daily,
            "days": days
        }
        
    except Exception as e:
        logger.error(f"Error getting daily usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
