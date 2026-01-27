"""
Advanced RBAC Manager - Epic 17
Fine-grained permission and role management system

Provides resource-based access control with:
- Custom role creation
- Permission assignment
- Policy enforcement
- Role inheritance
- Audit logging
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import asyncpg

logger = logging.getLogger(__name__)


class RBACManager:
    """Advanced Role-Based Access Control Manager"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        logger.info("RBACManager initialized")
    
    # ==================== PERMISSION CHECKS ====================
    
    async def has_permission(
        self,
        user_email: str,
        permission_name: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user_email: User's email address
            permission_name: Permission to check (e.g., 'users:create')
            organization_id: Optional organization scope
        
        Returns:
            True if user has permission, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT EXISTS(
                        SELECT 1
                        FROM user_effective_permissions
                        WHERE user_email = $1
                          AND permission_name = $2
                          AND ($3 IS NULL OR organization_id = $3 OR organization_id IS NULL)
                    ) AS has_perm
                """
                result = await conn.fetchval(query, user_email, permission_name, organization_id)
                return result
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False
    
    async def has_any_permission(
        self,
        user_email: str,
        permission_names: List[str],
        organization_id: Optional[str] = None
    ) -> bool:
        """Check if user has ANY of the specified permissions"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT EXISTS(
                        SELECT 1
                        FROM user_effective_permissions
                        WHERE user_email = $1
                          AND permission_name = ANY($2::text[])
                          AND ($3 IS NULL OR organization_id = $3 OR organization_id IS NULL)
                    ) AS has_perm
                """
                result = await conn.fetchval(query, user_email, permission_names, organization_id)
                return result
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False
    
    async def has_all_permissions(
        self,
        user_email: str,
        permission_names: List[str],
        organization_id: Optional[str] = None
    ) -> bool:
        """Check if user has ALL of the specified permissions"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT COUNT(DISTINCT permission_name) = $2
                    FROM user_effective_permissions
                    WHERE user_email = $1
                      AND permission_name = ANY($3::text[])
                      AND ($4 IS NULL OR organization_id = $4 OR organization_id IS NULL)
                """
                result = await conn.fetchval(
                    query, user_email, len(permission_names), permission_names, organization_id
                )
                return result
        except Exception as e:
            logger.error(f"Error checking all permissions: {e}")
            return False
    
    async def get_user_permissions(
        self,
        user_email: str,
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all effective permissions for a user"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT DISTINCT
                        permission_name,
                        resource,
                        action,
                        role_name,
                        organization_id
                    FROM user_effective_permissions
                    WHERE user_email = $1
                      AND ($2 IS NULL OR organization_id = $2 OR organization_id IS NULL)
                    ORDER BY resource, action
                """
                rows = await conn.fetch(query, user_email, organization_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return []
    
    # ==================== ROLE MANAGEMENT ====================
    
    async def create_role(
        self,
        name: str,
        description: str,
        organization_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[int]:
        """Create a new custom role"""
        try:
            async with self.db_pool.acquire() as conn:
                role_id = await conn.fetchval("""
                    INSERT INTO custom_roles (name, organization_id, description, created_by)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, name, organization_id, description, created_by)
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='role_created',
                    actor_email=created_by,
                    role_id=role_id,
                    changes={'name': name, 'organization_id': organization_id}
                )
                
                logger.info(f"Created role: {name} (ID: {role_id})")
                return role_id
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            return None
    
    async def get_role(self, role_id: int) -> Optional[Dict[str, Any]]:
        """Get role details"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM role_summary WHERE id = $1
                """, role_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting role: {e}")
            return None
    
    async def list_roles(
        self,
        organization_id: Optional[str] = None,
        include_system: bool = True
    ) -> List[Dict[str, Any]]:
        """List all roles"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM role_summary
                    WHERE ($1 IS NULL OR organization_id = $1 OR organization_id IS NULL)
                      AND ($2 = true OR is_system_role = false)
                    ORDER BY is_system_role DESC, name
                """
                rows = await conn.fetch(query, organization_id, include_system)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing roles: {e}")
            return []
    
    async def delete_role(
        self,
        role_id: int,
        deleted_by: Optional[str] = None
    ) -> bool:
        """Delete a custom role (cannot delete system roles)"""
        try:
            async with self.db_pool.acquire() as conn:
                # Check if system role
                is_system = await conn.fetchval(
                    "SELECT is_system_role FROM custom_roles WHERE id = $1", role_id
                )
                
                if is_system:
                    logger.warning(f"Cannot delete system role: {role_id}")
                    return False
                
                # Delete role (cascade will remove permissions and user assignments)
                result = await conn.execute(
                    "DELETE FROM custom_roles WHERE id = $1", role_id
                )
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='role_deleted',
                    actor_email=deleted_by,
                    role_id=role_id
                )
                
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"Error deleting role: {e}")
            return False
    
    # ==================== PERMISSION ASSIGNMENT ====================
    
    async def assign_permission_to_role(
        self,
        role_id: int,
        permission_name: str,
        granted_by: Optional[str] = None
    ) -> bool:
        """Assign a permission to a role"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get permission ID
                perm_id = await conn.fetchval(
                    "SELECT id FROM permissions WHERE name = $1", permission_name
                )
                
                if not perm_id:
                    logger.warning(f"Permission not found: {permission_name}")
                    return False
                
                # Assign permission
                await conn.execute("""
                    INSERT INTO role_permissions (role_id, permission_id, granted_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                """, role_id, perm_id, granted_by)
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='permission_granted',
                    actor_email=granted_by,
                    role_id=role_id,
                    permission_id=perm_id,
                    changes={'permission': permission_name}
                )
                
                logger.info(f"Assigned permission {permission_name} to role {role_id}")
                return True
        except Exception as e:
            logger.error(f"Error assigning permission: {e}")
            return False
    
    async def revoke_permission_from_role(
        self,
        role_id: int,
        permission_name: str,
        revoked_by: Optional[str] = None
    ) -> bool:
        """Revoke a permission from a role"""
        try:
            async with self.db_pool.acquire() as conn:
                perm_id = await conn.fetchval(
                    "SELECT id FROM permissions WHERE name = $1", permission_name
                )
                
                if not perm_id:
                    return False
                
                result = await conn.execute("""
                    DELETE FROM role_permissions
                    WHERE role_id = $1 AND permission_id = $2
                """, role_id, perm_id)
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='permission_revoked',
                    actor_email=revoked_by,
                    role_id=role_id,
                    permission_id=perm_id,
                    changes={'permission': permission_name}
                )
                
                return result == "DELETE 1"
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            return False
    
    async def get_role_permissions(self, role_id: int) -> List[Dict[str, Any]]:
        """Get all permissions for a role"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT p.id, p.name, p.resource, p.action, p.description
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = $1
                    ORDER BY p.resource, p.action
                """, role_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting role permissions: {e}")
            return []
    
    # ==================== USER ROLE ASSIGNMENT ====================
    
    async def assign_role_to_user(
        self,
        user_email: str,
        role_id: int,
        organization_id: Optional[str] = None,
        assigned_by: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Assign a role to a user"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_roles (user_email, role_id, organization_id, assigned_by, expires_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_email, role_id, organization_id) DO UPDATE
                    SET expires_at = EXCLUDED.expires_at
                """, user_email, role_id, organization_id, assigned_by, expires_at)
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='role_assigned',
                    actor_email=assigned_by,
                    target_user_email=user_email,
                    role_id=role_id,
                    changes={'organization_id': organization_id, 'expires_at': str(expires_at) if expires_at else None}
                )
                
                logger.info(f"Assigned role {role_id} to user {user_email}")
                return True
        except Exception as e:
            logger.error(f"Error assigning role to user: {e}")
            return False
    
    async def revoke_role_from_user(
        self,
        user_email: str,
        role_id: int,
        organization_id: Optional[str] = None,
        revoked_by: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    DELETE FROM user_roles
                    WHERE user_email = $1 AND role_id = $2
                      AND ($3 IS NULL OR organization_id = $3)
                """, user_email, role_id, organization_id)
                
                # Audit log
                await self._log_audit(
                    conn,
                    event_type='role_revoked',
                    actor_email=revoked_by,
                    target_user_email=user_email,
                    role_id=role_id,
                    changes={'organization_id': organization_id}
                )
                
                return "DELETE" in result
        except Exception as e:
            logger.error(f"Error revoking role from user: {e}")
            return False
    
    async def get_user_roles(
        self,
        user_email: str,
        organization_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all roles assigned to a user"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT ur.id, cr.id as role_id, cr.name, cr.description,
                           ur.organization_id, ur.assigned_at, ur.expires_at,
                           ur.expires_at IS NOT NULL AND ur.expires_at < CURRENT_TIMESTAMP AS is_expired
                    FROM user_roles ur
                    JOIN custom_roles cr ON ur.role_id = cr.id
                    WHERE ur.user_email = $1
                      AND ($2 IS NULL OR ur.organization_id = $2)
                    ORDER BY ur.assigned_at DESC
                """, user_email, organization_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []
    
    # ==================== PERMISSIONS CATALOG ====================
    
    async def list_all_permissions(
        self,
        resource: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all available permissions"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT id, name, resource, action, description
                    FROM permissions
                    WHERE ($1 IS NULL OR resource = $1)
                    ORDER BY resource, action
                """
                rows = await conn.fetch(query, resource)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing permissions: {e}")
            return []
    
    # ==================== AUDIT ====================
    
    async def _log_audit(
        self,
        conn: asyncpg.Connection,
        event_type: str,
        actor_email: Optional[str],
        target_user_email: Optional[str] = None,
        role_id: Optional[int] = None,
        permission_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log RBAC audit event"""
        try:
            await conn.execute("""
                INSERT INTO rbac_audit_log (
                    event_type, actor_email, target_user_email, role_id, permission_id,
                    resource_type, resource_id, changes, ip_address, user_agent
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::inet, $10)
            """, event_type, actor_email, target_user_email, role_id, permission_id,
                 resource_type, resource_id, changes, ip_address, user_agent)
        except Exception as e:
            logger.error(f"Error logging audit: {e}")
    
    async def get_audit_log(
        self,
        event_type: Optional[str] = None,
        actor_email: Optional[str] = None,
        target_user_email: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get RBAC audit log"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT *
                    FROM rbac_audit_log
                    WHERE ($1 IS NULL OR event_type = $1)
                      AND ($2 IS NULL OR actor_email = $2)
                      AND ($3 IS NULL OR target_user_email = $3)
                    ORDER BY created_at DESC
                    LIMIT $4
                """
                rows = await conn.fetch(query, event_type, actor_email, target_user_email, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []


# Global instance (will be initialized in server.py)
rbac_manager: Optional[RBACManager] = None


def init_rbac_manager(db_pool: asyncpg.Pool):
    """Initialize global RBAC manager"""
    global rbac_manager
    rbac_manager = RBACManager(db_pool)
    logger.info("Global RBAC manager initialized")


def get_rbac_manager() -> Optional[RBACManager]:
    """Get global RBAC manager instance"""
    return rbac_manager
