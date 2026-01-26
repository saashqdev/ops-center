"""
Trial Management API
Admin endpoints for managing trials and conversions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging

from trial_manager import trial_manager
from auth_dependencies import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/trials", tags=["admin-trials"])


class TrialAssignmentRequest(BaseModel):
    email: EmailStr
    trial_days: Optional[int] = None


class TrialExtensionRequest(BaseModel):
    email: EmailStr
    additional_days: int
    reason: Optional[str] = None


class TrialResponse(BaseModel):
    subscription_id: Optional[int] = None
    email: str
    tier_code: str
    status: str
    trial_end: Optional[str] = None
    days_remaining: Optional[int] = None


@router.post("/assign", response_model=TrialResponse)
async def assign_trial(
    request: TrialAssignmentRequest,
    admin: dict = Depends(require_admin)
):
    """
    Assign a trial subscription to a user (admin only)
    """
    try:
        result = await trial_manager.assign_trial_subscription(
            email=request.email,
            trial_days=request.trial_days
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning trial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign trial")


@router.post("/extend")
async def extend_trial(
    request: TrialExtensionRequest,
    admin: dict = Depends(require_admin)
):
    """
    Extend a trial subscription (admin only)
    """
    try:
        result = await trial_manager.extend_trial(
            email=request.email,
            additional_days=request.additional_days,
            reason=request.reason
        )
        
        return {
            "message": f"Trial extended by {request.additional_days} days",
            "email": result["email"],
            "new_trial_end": result["new_trial_end"].isoformat(),
            "reason": result["reason"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error extending trial: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to extend trial")


@router.get("/expiring")
async def get_expiring_trials(
    days: int = 7,
    admin: dict = Depends(require_admin)
):
    """
    Get trials expiring within N days (admin only)
    """
    try:
        trials = await trial_manager.get_expiring_trials(days=days)
        
        return {
            "days": days,
            "count": len(trials),
            "trials": trials
        }
        
    except Exception as e:
        logger.error(f"Error getting expiring trials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get expiring trials")


@router.post("/check-expirations")
async def check_expirations(
    admin: dict = Depends(require_admin)
):
    """
    Manually trigger trial expiration check (admin only)
    Normally run by scheduled task
    """
    try:
        downgraded = await trial_manager.check_trial_expiration()
        
        return {
            "message": "Trial expiration check completed",
            "downgraded_count": len(downgraded),
            "downgraded": downgraded
        }
        
    except Exception as e:
        logger.error(f"Error checking expirations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check expirations")


@router.get("/stats")
async def get_trial_stats(
    admin: dict = Depends(require_admin)
):
    """
    Get trial statistics (admin only)
    """
    try:
        stats = await trial_manager.get_trial_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting trial stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get trial stats")
