"""
Public Signup API with Trial Assignment
Allows new users to sign up and automatically receive trial subscription
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from trial_manager import trial_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public/signup", tags=["public-signup"])


class SignupRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class SignupResponse(BaseModel):
    email: str
    trial_assigned: bool
    trial_days: Optional[int] = None
    trial_end: Optional[str] = None
    message: str


@router.post("/", response_model=SignupResponse)
async def signup_with_trial(request: SignupRequest):
    """
    Public endpoint for new user signup with automatic trial assignment
    
    - Creates a trial subscription for the user
    - Returns trial details
    - User can then complete onboarding
    """
    try:
        # Check if email already exists
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("""
                SELECT id FROM user_subscriptions WHERE email = $1
            """, request.email)
            
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Email already registered. Please sign in instead."
                )
        
        # Assign trial subscription
        result = await trial_manager.assign_trial_subscription(email=request.email)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info(f"New signup: {request.email} - trial assigned")
        
        return SignupResponse(
            email=request.email,
            trial_assigned=True,
            trial_days=result.get("days_remaining"),
            trial_end=result.get("trial_end").isoformat() if result.get("trial_end") else None,
            message=f"Welcome! You have {result.get('days_remaining', 14)} days of free trial."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Signup failed. Please try again.")


@router.get("/check-email/{email}")
async def check_email_availability(email: str):
    """
    Check if email is available for signup
    """
    try:
        from database import get_db_pool
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("""
                SELECT id FROM user_subscriptions WHERE email = $1
            """, email)
            
            return {
                "email": email,
                "available": existing is None,
                "message": "Email is available" if not existing else "Email already registered"
            }
            
    except Exception as e:
        logger.error(f"Error checking email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check email availability")
