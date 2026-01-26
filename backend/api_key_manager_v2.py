"""
API Key Manager
Handles API key generation, validation, and management
"""

from typing import Dict, Any, Optional, List
import logging
import secrets
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages API keys for programmatic access"""
    
    def __init__(self):
        self.key_prefix = "sk_live_"
        self.key_length = 32  # characters after prefix
    
    async def create_api_key(
        self,
        email: str,
        name: str,
        description: Optional[str] = None,
        expires_days: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
        rate_limit_per_day: Optional[int] = None,
        monthly_quota: Optional[int] = None,
        scopes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key
        
        Args:
            email: User email
            name: Human-readable key name
            description: Optional description
            expires_days: Days until expiration (None = never)
            rate_limit_per_minute: Custom rate limit per minute
            rate_limit_per_hour: Custom rate limit per hour
            rate_limit_per_day: Custom rate limit per day
            monthly_quota: Custom monthly quota
            scopes: Permission scopes (default: ['all'])
            
        Returns:
            Dict with api_key (plaintext, show once) and key details
        """
        try:
            from database import get_db_pool
            
            # Generate secure random key
            random_part = secrets.token_urlsafe(self.key_length)
            api_key = f"{self.key_prefix}{random_part}"
            
            # Hash the key for storage
            key_hash = self._hash_key(api_key)
            key_prefix = api_key[:20]  # Store prefix for identification
            
            # Get subscription ID
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                subscription = await conn.fetchrow("""
                    SELECT id FROM user_subscriptions WHERE email = $1
                """, email)
                
                subscription_id = subscription['id'] if subscription else None
                
                # Calculate expiration
                expires_at = None
                if expires_days:
                    expires_at = datetime.utcnow() + timedelta(days=expires_days)
                
                # Prepare scopes
                import json
                scopes_json = json.dumps(scopes or ['all'])
                
                # Create API key record
                result = await conn.fetchrow("""
                    INSERT INTO api_keys (
                        key_hash,
                        key_prefix,
                        email,
                        subscription_id,
                        name,
                        description,
                        is_active,
                        is_revoked,
                        rate_limit_per_minute,
                        rate_limit_per_hour,
                        rate_limit_per_day,
                        monthly_quota,
                        scopes,
                        expires_at,
                        created_at,
                        total_requests
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14, NOW(), 0)
                    RETURNING id, created_at
                """, key_hash, key_prefix, email, subscription_id, name, description,
                True, False, rate_limit_per_minute, rate_limit_per_hour, 
                rate_limit_per_day, monthly_quota, scopes_json, expires_at)
                
                logger.info(f"Created API key {result['id']} for {email}: {name}")
                
                return {
                    "id": result['id'],
                    "api_key": api_key,  # Only returned once!
                    "key_prefix": key_prefix,
                    "name": name,
                    "description": description,
                    "email": email,
                    "subscription_id": subscription_id,
                    "is_active": True,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "created_at": result['created_at'].isoformat(),
                    "scopes": scopes or ['all']
                }
                
        except Exception as e:
            logger.error(f"Error creating API key: {e}", exc_info=True)
            raise
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and return key details
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Dict with key details if valid, None if invalid
        """
        try:
            from database import get_db_pool
            
            key_hash = self._hash_key(api_key)
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                key_data = await conn.fetchrow("""
                    SELECT 
                        k.*,
                        s.status as subscription_status,
                        s.tier_id,
                        st.api_calls_limit,
                        st.rate_limit_per_minute as tier_rate_limit_per_minute,
                        st.rate_limit_per_hour as tier_rate_limit_per_hour
                    FROM api_keys k
                    LEFT JOIN user_subscriptions s ON k.subscription_id = s.id
                    LEFT JOIN subscription_tiers st ON s.tier_id = st.id
                    WHERE k.key_hash = $1
                """, key_hash)
                
                if not key_data:
                    logger.warning(f"Invalid API key attempt")
                    return None
                
                # Check if key is active
                if not key_data['is_active'] or key_data['is_revoked']:
                    logger.warning(f"Revoked/inactive API key used: {key_data['id']}")
                    return None
                
                # Check expiration
                if key_data['expires_at'] and key_data['expires_at'] < datetime.utcnow():
                    logger.warning(f"Expired API key used: {key_data['id']}")
                    return None
                
                # Check subscription status
                if key_data['subscription_status'] in ['cancelled', 'past_due', 'expired']:
                    logger.warning(f"API key {key_data['id']} has inactive subscription")
                    return None
                
                # Update last used timestamp
                await conn.execute("""
                    UPDATE api_keys
                    SET last_used_at = NOW(),
                        total_requests = total_requests + 1
                    WHERE id = $1
                """, key_data['id'])
                
                # Determine effective rate limits
                rate_limit_per_minute = key_data['rate_limit_per_minute'] or key_data['tier_rate_limit_per_minute'] or 60
                rate_limit_per_hour = key_data['rate_limit_per_hour'] or key_data['tier_rate_limit_per_hour'] or 1000
                rate_limit_per_day = key_data['rate_limit_per_day'] or 10000
                monthly_quota = key_data['monthly_quota'] or key_data['api_calls_limit']
                
                return {
                    "id": key_data['id'],
                    "key_prefix": key_data['key_prefix'],
                    "email": key_data['email'],
                    "subscription_id": key_data['subscription_id'],
                    "name": key_data['name'],
                    "scopes": key_data['scopes'],
                    "rate_limit_per_minute": rate_limit_per_minute,
                    "rate_limit_per_hour": rate_limit_per_hour,
                    "rate_limit_per_day": rate_limit_per_day,
                    "monthly_quota": monthly_quota,
                    "total_requests": key_data['total_requests']
                }
                
        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            return None
    
    async def list_api_keys(self, email: str) -> List[Dict[str, Any]]:
        """
        List all API keys for a user
        
        Args:
            email: User email
            
        Returns:
            List of API key details (without actual keys)
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                keys = await conn.fetch("""
                    SELECT 
                        id,
                        key_prefix,
                        name,
                        description,
                        is_active,
                        is_revoked,
                        last_used_at,
                        created_at,
                        expires_at,
                        total_requests,
                        scopes
                    FROM api_keys
                    WHERE email = $1
                    ORDER BY created_at DESC
                """, email)
                
                return [dict(key) for key in keys]
                
        except Exception as e:
            logger.error(f"Error listing API keys: {e}", exc_info=True)
            return []
    
    async def revoke_api_key(
        self,
        key_id: int,
        email: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Revoke an API key
        
        Args:
            key_id: API key ID
            email: User email (for authorization)
            reason: Optional revocation reason
            
        Returns:
            True if revoked successfully
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                # Verify ownership and revoke
                result = await conn.execute("""
                    UPDATE api_keys
                    SET is_revoked = true,
                        is_active = false,
                        revoked_at = NOW(),
                        revoked_reason = $1
                    WHERE id = $2 AND email = $3 AND is_revoked = false
                """, reason, key_id, email)
                
                if result == "UPDATE 1":
                    logger.info(f"Revoked API key {key_id} for {email}")
                    return True
                else:
                    logger.warning(f"Failed to revoke API key {key_id} for {email}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error revoking API key: {e}", exc_info=True)
            return False
    
    async def delete_api_key(self, key_id: int, email: str) -> bool:
        """
        Permanently delete an API key
        
        Args:
            key_id: API key ID
            email: User email (for authorization)
            
        Returns:
            True if deleted successfully
        """
        try:
            from database import get_db_pool
            
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM api_keys
                    WHERE id = $1 AND email = $2
                """, key_id, email)
                
                if result == "DELETE 1":
                    logger.info(f"Deleted API key {key_id} for {email}")
                    return True
                else:
                    logger.warning(f"Failed to delete API key {key_id} for {email}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting API key: {e}", exc_info=True)
            return False
    
    def _hash_key(self, api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()


# Global singleton
api_key_manager = APIKeyManager()
