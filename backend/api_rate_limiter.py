"""
Rate Limiting Middleware for API Keys
Enforces per-key and per-user rate limits with Redis/PostgreSQL backend
"""

from typing import Dict, Optional
import logging
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """Rate limiting for API keys with Redis/PostgreSQL backend"""
    
    def __init__(self):
        # Try to use Redis for rate limiting, fall back to PostgreSQL
        self.use_redis = False
        try:
            from redis_session import get_redis
            self.redis = get_redis()
            self.use_redis = True
            logger.info("APIRateLimiter using Redis")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting, using PostgreSQL: {e}")
    
    async def check_rate_limit(
        self,
        api_key_id: int,
        rate_limit_per_minute: int,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> Dict[str, any]:
        """
        Check if request is within rate limits
        
        Args:
            api_key_id: API key ID
            rate_limit_per_minute: Limit per minute
            rate_limit_per_hour: Limit per hour
            rate_limit_per_day: Limit per day
            
        Returns:
            Dict with allowed status and limit info
        """
        if self.use_redis:
            return await self._check_redis(api_key_id, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day)
        else:
            return await self._check_postgres(api_key_id, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day)
    
    async def _check_redis(
        self,
        api_key_id: int,
        rate_limit_per_minute: int,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> Dict[str, any]:
        """Check rate limits using Redis"""
        try:
            now = datetime.utcnow()
            
            # Check minute window
            minute_key = f"rate_limit:{api_key_id}:minute:{now.strftime('%Y%m%d%H%M')}"
            minute_count = self.redis.incr(minute_key)
            if minute_count == 1:
                self.redis.expire(minute_key, 60)
            
            if minute_count > rate_limit_per_minute:
                return {
                    "allowed": False,
                    "limit": rate_limit_per_minute,
                    "used": minute_count,
                    "window": "minute",
                    "reset_in_seconds": 60 - now.second
                }
            
            # Check hour window
            hour_key = f"rate_limit:{api_key_id}:hour:{now.strftime('%Y%m%d%H')}"
            hour_count = self.redis.incr(hour_key)
            if hour_count == 1:
                self.redis.expire(hour_key, 3600)
            
            if hour_count > rate_limit_per_hour:
                return {
                    "allowed": False,
                    "limit": rate_limit_per_hour,
                    "used": hour_count,
                    "window": "hour",
                    "reset_in_seconds": (60 - now.minute) * 60 - now.second
                }
            
            # Check day window
            day_key = f"rate_limit:{api_key_id}:day:{now.strftime('%Y%m%d')}"
            day_count = self.redis.incr(day_key)
            if day_count == 1:
                self.redis.expire(day_key, 86400)
            
            if day_count > rate_limit_per_day:
                return {
                    "allowed": False,
                    "limit": rate_limit_per_day,
                    "used": day_count,
                    "window": "day",
                    "reset_in_seconds": ((24 - now.hour) * 3600) - (now.minute * 60) - now.second
                }
            
            return {
                "allowed": True,
                "limits": {
                    "minute": {"limit": rate_limit_per_minute, "used": minute_count},
                    "hour": {"limit": rate_limit_per_hour, "used": hour_count},
                    "day": {"limit": rate_limit_per_day, "used": day_count}
                }
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit check error: {e}")
            # On error, allow the request (fail open)
            return {"allowed": True, "error": str(e)}
    
    async def _check_postgres(
        self,
        api_key_id: int,
        rate_limit_per_minute: int,
        rate_limit_per_hour: int,
        rate_limit_per_day: int
    ) -> Dict[str, any]:
        """Check rate limits using PostgreSQL (fallback)"""
        try:
            from database import get_db_pool
            
            now = datetime.utcnow()
            pool = await get_db_pool()
            
            async with pool.acquire() as conn:
                # Clean up old records
                await conn.execute("""
                    DELETE FROM rate_limits WHERE expires_at < NOW()
                """)
                
                # Check and update minute window
                minute_start = now.replace(second=0, microsecond=0)
                minute_expires = minute_start + timedelta(minutes=1)
                
                minute_result = await conn.fetchrow("""
                    INSERT INTO rate_limits (api_key_id, window_type, window_start, request_count, expires_at)
                    VALUES ($1, 'minute', $2, 1, $3)
                    ON CONFLICT (api_key_id, window_type, window_start)
                    DO UPDATE SET request_count = rate_limits.request_count + 1
                    RETURNING request_count
                """, api_key_id, minute_start, minute_expires)
                
                if minute_result['request_count'] > rate_limit_per_minute:
                    return {
                        "allowed": False,
                        "limit": rate_limit_per_minute,
                        "used": minute_result['request_count'],
                        "window": "minute",
                        "reset_in_seconds": 60 - now.second
                    }
                
                # Check hour window
                hour_start = now.replace(minute=0, second=0, microsecond=0)
                hour_expires = hour_start + timedelta(hours=1)
                
                hour_result = await conn.fetchrow("""
                    INSERT INTO rate_limits (api_key_id, window_type, window_start, request_count, expires_at)
                    VALUES ($1, 'hour', $2, 1, $3)
                    ON CONFLICT (api_key_id, window_type, window_start)
                    DO UPDATE SET request_count = rate_limits.request_count + 1
                    RETURNING request_count
                """, api_key_id, hour_start, hour_expires)
                
                if hour_result['request_count'] > rate_limit_per_hour:
                    return {
                        "allowed": False,
                        "limit": rate_limit_per_hour,
                        "used": hour_result['request_count'],
                        "window": "hour",
                        "reset_in_seconds": (60 - now.minute) * 60 - now.second
                    }
                
                # Check day window
                day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                day_expires = day_start + timedelta(days=1)
                
                day_result = await conn.fetchrow("""
                    INSERT INTO rate_limits (api_key_id, window_type, window_start, request_count, expires_at)
                    VALUES ($1, 'day', $2, 1, $3)
                    ON CONFLICT (api_key_id, window_type, window_start)
                    DO UPDATE SET request_count = rate_limits.request_count + 1
                    RETURNING request_count
                """, api_key_id, day_start, day_expires)
                
                if day_result['request_count'] > rate_limit_per_day:
                    return {
                        "allowed": False,
                        "limit": rate_limit_per_day,
                        "used": day_result['request_count'],
                        "window": "day",
                        "reset_in_seconds": ((24 - now.hour) * 3600) - (now.minute * 60) - now.second
                    }
                
                return {
                    "allowed": True,
                    "limits": {
                        "minute": {"limit": rate_limit_per_minute, "used": minute_result['request_count']},
                        "hour": {"limit": rate_limit_per_hour, "used": hour_result['request_count']},
                        "day": {"limit": rate_limit_per_day, "used": day_result['request_count']}
                    }
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL rate limit check error: {e}")
            # On error, allow the request (fail open)
            return {"allowed": True, "error": str(e)}


# Global singleton
api_rate_limiter = APIRateLimiter()


async def require_api_key_with_limits(request: Request):
    """
    FastAPI dependency to validate API key and enforce rate limits
    
    Usage:
        @router.get("/protected", dependencies=[Depends(require_api_key_with_limits)])
    """
    from api_key_manager_v2 import api_key_manager
    from usage_meter_v2 import usage_meter
    
    # Extract API key from header
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header or Authorization Bearer token."
        )
    
    # Validate API key
    key_data = await api_key_manager.validate_api_key(api_key)
    
    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    # Check rate limits
    rate_check = await api_rate_limiter.check_rate_limit(
        api_key_id=key_data['id'],
        rate_limit_per_minute=key_data['rate_limit_per_minute'],
        rate_limit_per_hour=key_data['rate_limit_per_hour'],
        rate_limit_per_day=key_data['rate_limit_per_day']
    )
    
    if not rate_check['allowed']:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rate_check['limit']} requests per {rate_check['window']}. Resets in {rate_check['reset_in_seconds']}s.",
            headers={
                "X-RateLimit-Limit": str(rate_check['limit']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_check['reset_in_seconds']),
                "Retry-After": str(rate_check['reset_in_seconds'])
            }
        )
    
    # Check monthly quota
    quota_check = await usage_meter.check_quota(key_data['email'], key_data.get('monthly_quota'))
    
    if quota_check.get('quota_exceeded'):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly quota exceeded: {quota_check['requests_used']}/{quota_check['monthly_quota']} requests used."
        )
    
    # Attach key data to request state for use in endpoint
    request.state.api_key_data = key_data
    request.state.rate_limit_info = rate_check.get('limits', {})
    request.state.quota_info = quota_check
    
    return key_data
