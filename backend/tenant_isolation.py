"""
Tenant Isolation Middleware and Utilities

Provides row-level security, tenant context management, and isolation utilities
for multi-tenant operations in Ops-Center.
"""

import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import Request, HTTPException, status
from functools import wraps
import asyncpg

logger = logging.getLogger(__name__)


class TenantContext:
    """Thread-safe tenant context manager"""
    
    def __init__(self):
        self._tenant_id: Optional[str] = None
        self._tenant_metadata: Optional[Dict[str, Any]] = None
    
    def set_tenant(self, tenant_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Set current tenant context"""
        self._tenant_id = tenant_id
        self._tenant_metadata = metadata or {}
        logger.debug(f"Tenant context set to: {tenant_id}")
    
    def get_tenant_id(self) -> Optional[str]:
        """Get current tenant ID"""
        return self._tenant_id
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get current tenant metadata"""
        return self._tenant_metadata or {}
    
    def clear(self):
        """Clear tenant context"""
        self._tenant_id = None
        self._tenant_metadata = None
        logger.debug("Tenant context cleared")
    
    def is_set(self) -> bool:
        """Check if tenant context is set"""
        return self._tenant_id is not None


# Global tenant context
tenant_context = TenantContext()


class TenantIsolationMiddleware:
    """
    Middleware to enforce tenant isolation across all requests
    
    Extracts tenant information from request and sets context
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        request = Request(scope, receive)
        
        # Extract tenant from various sources
        tenant_id = await self._extract_tenant_id(request)
        
        if tenant_id:
            tenant_context.set_tenant(tenant_id)
        
        try:
            await self.app(scope, receive, send)
        finally:
            tenant_context.clear()
    
    async def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """
        Extract tenant ID from request
        
        Checks in order:
        1. X-Tenant-ID header
        2. Subdomain (e.g., acme.ops-center.com)
        3. User's organization from auth token
        4. Query parameter
        """
        # 1. Check header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id
        
        # 2. Check subdomain
        host = request.headers.get("host", "")
        if "." in host and not host.startswith("localhost"):
            subdomain = host.split(".")[0]
            if subdomain not in ["www", "api", "admin"]:
                return subdomain
        
        # 3. Check user's organization (from auth)
        # This would be set by auth middleware
        if hasattr(request.state, "organization_id"):
            return request.state.organization_id
        
        # 4. Check query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id
        
        return None


class TenantIsolation:
    """Utilities for tenant-isolated database operations"""
    
    @staticmethod
    def add_tenant_filter(query: str, tenant_id: Optional[str] = None) -> str:
        """
        Add tenant filter to SQL query
        
        Args:
            query: Base SQL query
            tenant_id: Tenant ID to filter by (uses context if None)
            
        Returns:
            Modified query with tenant filter
        """
        tid = tenant_id or tenant_context.get_tenant_id()
        if not tid:
            logger.warning("No tenant context set for query filtering")
            return query
        
        # Add WHERE or AND clause based on existing query
        if "WHERE" in query.upper():
            return f"{query} AND organization_id = '{tid}'"
        else:
            return f"{query} WHERE organization_id = '{tid}'"
    
    @staticmethod
    async def validate_tenant_access(
        pool: asyncpg.Pool,
        tenant_id: str,
        resource_id: str,
        resource_type: str
    ) -> bool:
        """
        Validate that a resource belongs to the tenant
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID to check
            resource_id: Resource identifier
            resource_type: Type of resource (user, device, webhook, etc.)
            
        Returns:
            True if resource belongs to tenant
        """
        table_map = {
            'user': 'users',
            'device': 'edge_devices',
            'webhook': 'webhooks',
            'api_key': 'api_keys',
            'alert': 'alerts'
        }
        
        table = table_map.get(resource_type)
        if not table:
            logger.error(f"Unknown resource type: {resource_type}")
            return False
        
        try:
            async with pool.acquire() as conn:
                # Determine ID column name
                id_column = f"{resource_type}_id" if resource_type != 'user' else 'user_id'
                
                query = f"""
                    SELECT organization_id 
                    FROM {table} 
                    WHERE {id_column} = $1
                """
                
                result = await conn.fetchval(query, resource_id)
                
                if result is None:
                    logger.warning(f"Resource not found: {resource_type}/{resource_id}")
                    return False
                
                return result == tenant_id
                
        except Exception as e:
            logger.error(f"Error validating tenant access: {e}")
            return False
    
    @staticmethod
    async def get_tenant_resource_count(
        pool: asyncpg.Pool,
        tenant_id: str,
        resource_type: str
    ) -> int:
        """
        Get count of resources for a tenant
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            resource_type: Type of resource
            
        Returns:
            Count of resources
        """
        table_map = {
            'users': 'organization_members',
            'devices': 'edge_devices',
            'webhooks': 'webhooks',
            'api_keys': 'api_keys',
            'alerts': 'alerts'
        }
        
        table = table_map.get(resource_type)
        if not table:
            return 0
        
        try:
            async with pool.acquire() as conn:
                query = f"""
                    SELECT COUNT(*) 
                    FROM {table} 
                    WHERE organization_id = $1
                """
                count = await conn.fetchval(query, tenant_id)
                return count or 0
                
        except Exception as e:
            logger.error(f"Error getting resource count: {e}")
            return 0
    
    @staticmethod
    async def enforce_tenant_quota(
        pool: asyncpg.Pool,
        tenant_id: str,
        resource_type: str,
        max_allowed: int
    ) -> bool:
        """
        Check if tenant is within quota for resource type
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            resource_type: Type of resource
            max_allowed: Maximum allowed resources
            
        Returns:
            True if within quota, False if exceeded
        """
        current_count = await TenantIsolation.get_tenant_resource_count(
            pool, tenant_id, resource_type
        )
        
        if current_count >= max_allowed:
            logger.warning(
                f"Tenant {tenant_id} exceeded quota for {resource_type}: "
                f"{current_count}/{max_allowed}"
            )
            return False
        
        return True
    
    @staticmethod
    async def list_tenant_resources(
        pool: asyncpg.Pool,
        tenant_id: str,
        resource_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all resources for a tenant with pagination
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID
            resource_type: Type of resource
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of resource records
        """
        table_map = {
            'users': 'organization_members',
            'devices': 'edge_devices',
            'webhooks': 'webhooks',
            'api_keys': 'api_keys',
            'alerts': 'alerts'
        }
        
        table = table_map.get(resource_type)
        if not table:
            return []
        
        try:
            async with pool.acquire() as conn:
                query = f"""
                    SELECT * 
                    FROM {table} 
                    WHERE organization_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                """
                
                rows = await conn.fetch(query, tenant_id, limit, offset)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing tenant resources: {e}")
            return []
    
    @staticmethod
    async def delete_tenant_data(pool: asyncpg.Pool, tenant_id: str) -> Dict[str, int]:
        """
        Delete all data for a tenant (hard delete)
        
        WARNING: This is irreversible!
        
        Args:
            pool: Database connection pool
            tenant_id: Tenant ID to delete
            
        Returns:
            Dictionary with count of deleted records per table
        """
        tables = [
            'webhook_deliveries',  # Delete child records first
            'webhooks',
            'edge_device_logs',
            'edge_devices',
            'api_keys',
            'alerts',
            'analytics_events',
            'audit_logs',
            'users'
        ]
        
        deleted_counts = {}
        
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for table in tables:
                        query = f"""
                            DELETE FROM {table}
                            WHERE organization_id = $1
                        """
                        
                        result = await conn.execute(query, tenant_id)
                        # Extract count from result like "DELETE 5"
                        count = int(result.split()[-1]) if result else 0
                        deleted_counts[table] = count
                        
                        logger.info(f"Deleted {count} records from {table} for tenant {tenant_id}")
            
            logger.warning(f"Completed hard delete for tenant {tenant_id}: {deleted_counts}")
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Error deleting tenant data: {e}")
            raise


def require_tenant_context(func):
    """
    Decorator to ensure tenant context is set before executing function
    
    Raises HTTPException if no tenant context
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not tenant_context.is_set():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not set. Multi-tenant operation requires tenant identification."
            )
        return await func(*args, **kwargs)
    
    return wrapper


def require_tenant_access(resource_type: str):
    """
    Decorator to validate tenant has access to a resource
    
    Args:
        resource_type: Type of resource to validate
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract resource_id from kwargs or args
            resource_id = kwargs.get('resource_id') or kwargs.get('id')
            
            if not resource_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Resource ID not provided"
                )
            
            tenant_id = tenant_context.get_tenant_id()
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant context not set"
                )
            
            # Get database pool from kwargs or dependency injection
            pool = kwargs.get('pool')
            if not pool:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database pool not available"
                )
            
            # Validate access
            has_access = await TenantIsolation.validate_tenant_access(
                pool, tenant_id, resource_id, resource_type
            )
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to {resource_type} {resource_id}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class TenantQuotaManager:
    """Manage resource quotas per tenant tier"""
    
    # Default quotas by tier
    TIER_QUOTAS = {
        'trial': {
            'users': 5,
            'devices': 10,
            'webhooks': 5,
            'api_keys': 3,
            'alerts': 10
        },
        'starter': {
            'users': 25,
            'devices': 50,
            'webhooks': 20,
            'api_keys': 10,
            'alerts': 50
        },
        'professional': {
            'users': 100,
            'devices': 500,
            'webhooks': 100,
            'api_keys': 50,
            'alerts': 500
        },
        'enterprise': {
            'users': -1,  # unlimited
            'devices': -1,
            'webhooks': -1,
            'api_keys': -1,
            'alerts': -1
        }
    }
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def get_tenant_tier(self, tenant_id: str) -> str:
        """Get tenant's subscription tier"""
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT plan_tier 
                    FROM organizations 
                    WHERE organization_id = $1
                """
                tier = await conn.fetchval(query, tenant_id)
                return tier or 'trial'
        except Exception as e:
            logger.error(f"Error getting tenant tier: {e}")
            return 'trial'
    
    async def get_quota(self, tenant_id: str, resource_type: str) -> int:
        """
        Get quota for resource type
        
        Returns:
            Maximum allowed resources (-1 for unlimited)
        """
        tier = await self.get_tenant_tier(tenant_id)
        quotas = self.TIER_QUOTAS.get(tier, self.TIER_QUOTAS['trial'])
        return quotas.get(resource_type, 0)
    
    async def check_quota(self, tenant_id: str, resource_type: str) -> bool:
        """
        Check if tenant is within quota
        
        Returns:
            True if can add more resources, False if quota exceeded
        """
        max_quota = await self.get_quota(tenant_id, resource_type)
        
        # -1 means unlimited
        if max_quota == -1:
            return True
        
        return await TenantIsolation.enforce_tenant_quota(
            self.pool, tenant_id, resource_type, max_quota
        )
    
    async def get_quota_status(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Get quota status for all resource types
        
        Returns:
            Dictionary with current/max for each resource type
        """
        tier = await self.get_tenant_tier(tenant_id)
        quotas = self.TIER_QUOTAS.get(tier, self.TIER_QUOTAS['trial'])
        
        status = {}
        for resource_type, max_quota in quotas.items():
            current = await TenantIsolation.get_tenant_resource_count(
                self.pool, tenant_id, resource_type
            )
            
            status[resource_type] = {
                'current': current,
                'max': max_quota,
                'unlimited': max_quota == -1,
                'usage_percent': (current / max_quota * 100) if max_quota > 0 else 0,
                'available': max_quota - current if max_quota > 0 else -1
            }
        
        return status
