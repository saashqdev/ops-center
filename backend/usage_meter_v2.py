"""
Usage Metering System
Tracks API usage, enforces limits, and generates analytics
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class UsageMeter:
    """Tracks and meters API usage"""
    
    def __init__(self):
        pass
    
    async def record_usage(
        self,
        api_key_id: int,
        subscription_id: Optional[int],
        email: str,
        event_type: str,
        endpoint: str,
        method: str = "POST",
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        status_code: int = 200,
        response_time_ms: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        model: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a usage event
        
        Args:
            api_key_id: API key ID
            subscription_id: Subscription ID (if applicable)
            email: User email
            event_type: Type of event (api_call, chat_completion, etc.)
            endpoint: API endpoint called
            method: HTTP method
            tokens_used: Number of tokens consumed
            cost_usd: Estimated cost in USD
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            success: Whether request succeeded
            error_message: Error message if failed
            model: AI model used (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            
        Returns:
            Event ID
        """
        try:
            from database import get_db_pool
            import json
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                metadata_json = json.dumps(metadata) if metadata else None
                
                result = await conn.fetchrow("""
                    INSERT INTO usage_events (
                        api_key_id,
                        subscription_id,
                        email,
                        event_type,
                        endpoint,
                        method,
                        tokens_used,
                        cost_usd,
                        status_code,
                        response_time_ms,
                        success,
                        error_message,
                        model,
                        ip_address,
                        user_agent,
                        metadata,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16::jsonb, NOW())
                    RETURNING id
                """, api_key_id, subscription_id, email, event_type, endpoint, method,
                tokens_used, cost_usd, status_code, response_time_ms, success,
                error_message, model, ip_address, user_agent, metadata_json)
                
                return result['id']
                
        except Exception as e:
            logger.error(f"Error recording usage: {e}", exc_info=True)
            raise
    
    async def get_usage_summary(
        self,
        email: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for a user
        
        Args:
            email: User email
            period_start: Start of period (default: current month start)
            period_end: End of period (default: now)
            
        Returns:
            Dict with usage statistics
        """
        try:
            from database import get_db_pool
            
            # Default to current month
            if not period_start:
                now = datetime.utcnow()
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if not period_end:
                period_end = datetime.utcnow()
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Get overall stats
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_requests,
                        COUNT(*) FILTER (WHERE success = true) as successful_requests,
                        COUNT(*) FILTER (WHERE success = false) as failed_requests,
                        COALESCE(SUM(tokens_used), 0) as total_tokens,
                        COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                        COALESCE(AVG(response_time_ms), 0) as avg_response_time_ms
                    FROM usage_events
                    WHERE email = $1
                    AND created_at >= $2
                    AND created_at <= $3
                """, email, period_start, period_end)
                
                # Get breakdown by event type
                event_breakdown = await conn.fetch("""
                    SELECT 
                        event_type,
                        COUNT(*) as count,
                        COALESCE(SUM(tokens_used), 0) as tokens
                    FROM usage_events
                    WHERE email = $1
                    AND created_at >= $2
                    AND created_at <= $3
                    GROUP BY event_type
                    ORDER BY count DESC
                """, email, period_start, period_end)
                
                # Get breakdown by model
                model_breakdown = await conn.fetch("""
                    SELECT 
                        model,
                        COUNT(*) as count,
                        COALESCE(SUM(tokens_used), 0) as tokens,
                        COALESCE(SUM(cost_usd), 0) as cost_usd
                    FROM usage_events
                    WHERE email = $1
                    AND created_at >= $2
                    AND created_at <= $3
                    AND model IS NOT NULL
                    GROUP BY model
                    ORDER BY count DESC
                """, email, period_start, period_end)
                
                return {
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "total_requests": stats['total_requests'],
                    "successful_requests": stats['successful_requests'],
                    "failed_requests": stats['failed_requests'],
                    "total_tokens": stats['total_tokens'],
                    "total_cost_usd": float(stats['total_cost_usd']),
                    "avg_response_time_ms": int(stats['avg_response_time_ms']),
                    "by_event_type": [dict(row) for row in event_breakdown],
                    "by_model": [dict(row) for row in model_breakdown]
                }
                
        except Exception as e:
            logger.error(f"Error getting usage summary: {e}", exc_info=True)
            return {}
    
    async def check_quota(
        self,
        email: str,
        monthly_quota: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded their monthly quota
        
        Args:
            email: User email
            monthly_quota: Monthly quota limit (from subscription)
            
        Returns:
            Dict with quota info and whether limit is exceeded
        """
        try:
            from database import get_db_pool
            
            # Get current month usage
            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                usage = await conn.fetchrow("""
                    SELECT COUNT(*) as requests_this_month
                    FROM usage_events
                    WHERE email = $1
                    AND created_at >= $2
                """, email, month_start)
                
                requests_used = usage['requests_this_month']
                
                # If no quota specified, check subscription tier
                if monthly_quota is None:
                    sub = await conn.fetchrow("""
                        SELECT st.api_calls_limit
                        FROM user_subscriptions us
                        JOIN subscription_tiers st ON us.tier_id = st.id
                        WHERE us.email = $1
                    """, email)
                    monthly_quota = sub['api_calls_limit'] if sub else 1000
                
                exceeded = requests_used >= monthly_quota
                percentage = (requests_used / monthly_quota * 100) if monthly_quota > 0 else 0
                
                return {
                    "monthly_quota": monthly_quota,
                    "requests_used": requests_used,
                    "requests_remaining": max(0, monthly_quota - requests_used),
                    "percentage_used": round(percentage, 2),
                    "quota_exceeded": exceeded,
                    "period_start": month_start.isoformat(),
                    "period_end": (month_start.replace(month=month_start.month + 1) if month_start.month < 12 
                                   else month_start.replace(year=month_start.year + 1, month=1)).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error checking quota: {e}", exc_info=True)
            return {"quota_exceeded": False, "error": str(e)}
    
    async def get_daily_usage(
        self,
        email: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily usage breakdown
        
        Args:
            email: User email
            days: Number of days to look back
            
        Returns:
            List of daily usage stats
        """
        try:
            from database import get_db_pool
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                daily = await conn.fetch("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as requests,
                        COUNT(*) FILTER (WHERE success = true) as successful,
                        COUNT(*) FILTER (WHERE success = false) as failed,
                        COALESCE(SUM(tokens_used), 0) as tokens,
                        COALESCE(SUM(cost_usd), 0) as cost_usd
                    FROM usage_events
                    WHERE email = $1
                    AND created_at >= $2
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, email, start_date)
                
                return [{
                    "date": row['date'].isoformat(),
                    "requests": row['requests'],
                    "successful": row['successful'],
                    "failed": row['failed'],
                    "tokens": row['tokens'],
                    "cost_usd": float(row['cost_usd'])
                } for row in daily]
                
        except Exception as e:
            logger.error(f"Error getting daily usage: {e}", exc_info=True)
            return []


# Global singleton
usage_meter = UsageMeter()
