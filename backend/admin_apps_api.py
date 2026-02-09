"""
Admin Apps API - Temporary stub
"""
from fastapi import APIRouter, Request, Depends
from typing import List, Dict, Any
import logging
from auth_dependencies import require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-apps"])


@router.get("/apps/")
async def get_admin_apps(
    request: Request,
    active_only: bool = False,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """
    Get list of apps for admin management.
    
    TODO: Implement proper app management with database backend
    For now, returns empty list to allow admin dashboard to load.
    """
    logger.info(f"Admin apps requested (active_only={active_only}) by user {user.get('email', 'unknown')}")
    return []


@router.get("/tiers/apps/detailed")
async def get_tier_apps_detailed(
    request: Request,
    user: Dict[str, Any] = Depends(require_authenticated_user)
):
    """
    Get detailed tier-app associations.
    
    TODO: Implement proper tier-app associations
    For now, returns empty list to allow admin dashboard to load.
    """
    logger.info(f"Tier apps detailed requested by user {user.get('email', 'unknown')}")
    return []
