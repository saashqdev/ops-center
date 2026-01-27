"""
Terraform/IaC Manager - Epic 19
Infrastructure as Code management with Terraform state tracking

Provides:
- Terraform workspace management
- State file versioning and locking
- Infrastructure resource tracking
- Plan/apply/destroy execution
- Drift detection
- Template library
"""

import logging
import asyncpg
import json
import subprocess
import os
import tempfile
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TerraformManager:
    """Terraform Infrastructure as Code Manager"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.terraform_dir = Path("/var/lib/terraform")
        self.terraform_dir.mkdir(parents=True, exist_ok=True)
        logger.info("TerraformManager initialized")
    
    # ==================== WORKSPACE MANAGEMENT ====================
    
    async def create_workspace(
        self,
        name: str,
        cloud_provider: str,
        environment: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        terraform_version: str = "1.6.0",
        auto_apply: bool = False
    ) -> Optional[str]:
        """Create a new Terraform workspace"""
        try:
            async with self.db_pool.acquire() as conn:
                workspace_id = await conn.fetchval("""
                    INSERT INTO terraform_workspaces (
                        name, description, cloud_provider, environment,
                        created_by, terraform_version, auto_apply
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING workspace_id::text
                """, name, description, cloud_provider, environment, created_by, terraform_version, auto_apply)
                
                # Create workspace directory
                workspace_path = self.terraform_dir / workspace_id
                workspace_path.mkdir(parents=True, exist_ok=True)
                
                logger.info(f"Created Terraform workspace: {workspace_id} ({name})")
                return workspace_id
        except Exception as e:
            logger.error(f"Error creating workspace: {e}")
            return None
    
    async def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace details"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM terraform_workspace_summary
                    WHERE workspace_id = $1::uuid
                """, workspace_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting workspace: {e}")
            return None
    
    async def list_workspaces(
        self,
        cloud_provider: Optional[str] = None,
        environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all workspaces"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM terraform_workspace_summary
                    WHERE ($1 IS NULL OR cloud_provider = $1)
                      AND ($2 IS NULL OR environment = $2)
                    ORDER BY name
                """
                rows = await conn.fetch(query, cloud_provider, environment)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing workspaces: {e}")
            return []
    
    async def lock_workspace(
        self,
        workspace_id: str,
        locked_by: str
    ) -> bool:
        """Lock workspace to prevent concurrent modifications"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE terraform_workspaces
                    SET locked = true,
                        locked_by = $2,
                        locked_at = CURRENT_TIMESTAMP
                    WHERE workspace_id = $1::uuid
                      AND locked = false
                """, workspace_id, locked_by)
                return "UPDATE 1" in result
        except Exception as e:
            logger.error(f"Error locking workspace: {e}")
            return False
    
    async def unlock_workspace(self, workspace_id: str) -> bool:
        """Unlock workspace"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE terraform_workspaces
                    SET locked = false,
                        locked_by = NULL,
                        locked_at = NULL
                    WHERE workspace_id = $1::uuid
                """, workspace_id)
                return "UPDATE" in result
        except Exception as e:
            logger.error(f"Error unlocking workspace: {e}")
            return False
    
    # ==================== STATE MANAGEMENT ====================
    
    async def save_state(
        self,
        workspace_id: str,
        state_data: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """Save Terraform state"""
        try:
            version = state_data.get('version', 4)
            serial = state_data.get('serial', 0)
            lineage = state_data.get('lineage', '')
            terraform_version = state_data.get('terraform_version', '1.6.0')
            
            # Count resources
            resources_count = len(state_data.get('resources', []))
            outputs = state_data.get('outputs', {})
            
            async with self.db_pool.acquire() as conn:
                # Mark previous state as not current
                await conn.execute("""
                    UPDATE terraform_states
                    SET is_current = false
                    WHERE workspace_id = $1::uuid
                """, workspace_id)
                
                # Insert new state
                state_id = await conn.fetchval("""
                    INSERT INTO terraform_states (
                        workspace_id, version, serial, lineage,
                        state_data, resources_count, outputs,
                        created_by, terraform_version
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5::jsonb, $6, $7::jsonb, $8, $9)
                    RETURNING state_id::text
                """, workspace_id, version, serial, lineage, json.dumps(state_data),
                    resources_count, json.dumps(outputs), created_by, terraform_version)
                
                # Update workspace state version
                await conn.execute("""
                    UPDATE terraform_workspaces
                    SET state_version = $2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE workspace_id = $1::uuid
                """, workspace_id, version)
                
                logger.info(f"Saved state for workspace {workspace_id}: {resources_count} resources")
                return state_id
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            return None
    
    async def get_current_state(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get current Terraform state"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT state_data, version, serial
                    FROM terraform_states
                    WHERE workspace_id = $1::uuid
                      AND is_current = true
                """, workspace_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting current state: {e}")
            return None
    
    # ==================== RESOURCE TRACKING ====================
    
    async def sync_resources(
        self,
        workspace_id: str,
        state_id: str,
        resources: List[Dict[str, Any]]
    ) -> int:
        """Sync resources from Terraform state"""
        try:
            async with self.db_pool.acquire() as conn:
                # Mark all existing resources as potentially destroyed
                await conn.execute("""
                    UPDATE terraform_resources
                    SET status = 'destroyed',
                        destroyed_at = CURRENT_TIMESTAMP
                    WHERE workspace_id = $1::uuid
                """, workspace_id)
                
                synced = 0
                for resource in resources:
                    resource_type = resource.get('type', '')
                    resource_name = resource.get('name', '')
                    provider = resource.get('provider', '').split('/')[-1]
                    address = resource.get('address', '')
                    attributes = resource.get('values', {})
                    dependencies = resource.get('depends_on', [])
                    
                    await conn.execute("""
                        INSERT INTO terraform_resources (
                            workspace_id, state_id, resource_type, resource_name,
                            provider, address, attributes, dependencies, status
                        )
                        VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7::jsonb, $8, 'active')
                        ON CONFLICT (workspace_id, address)
                        DO UPDATE SET
                            state_id = EXCLUDED.state_id,
                            attributes = EXCLUDED.attributes,
                            status = 'active',
                            destroyed_at = NULL,
                            updated_at = CURRENT_TIMESTAMP
                    """, workspace_id, state_id, resource_type, resource_name,
                        provider, address, json.dumps(attributes), dependencies)
                    synced += 1
                
                logger.info(f"Synced {synced} resources for workspace {workspace_id}")
                return synced
        except Exception as e:
            logger.error(f"Error syncing resources: {e}")
            return 0
    
    async def get_resources(
        self,
        workspace_id: str,
        resource_type: Optional[str] = None,
        status: str = 'active'
    ) -> List[Dict[str, Any]]:
        """Get workspace resources"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM terraform_resources
                    WHERE workspace_id = $1::uuid
                      AND ($2 IS NULL OR resource_type = $2)
                      AND status = $3
                    ORDER BY resource_type, resource_name
                """
                rows = await conn.fetch(query, workspace_id, resource_type, status)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting resources: {e}")
            return []
    
    # ==================== EXECUTION MANAGEMENT ====================
    
    async def create_execution(
        self,
        workspace_id: str,
        execution_type: str,
        triggered_by: Optional[str] = None
    ) -> Optional[str]:
        """Create execution record"""
        try:
            async with self.db_pool.acquire() as conn:
                execution_id = await conn.fetchval("""
                    INSERT INTO terraform_executions (
                        workspace_id, execution_type, triggered_by
                    )
                    VALUES ($1::uuid, $2, $3)
                    RETURNING execution_id::text
                """, workspace_id, execution_type, triggered_by)
                return execution_id
        except Exception as e:
            logger.error(f"Error creating execution: {e}")
            return None
    
    async def update_execution(
        self,
        execution_id: str,
        status: str,
        plan_output: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> bool:
        """Update execution status"""
        try:
            async with self.db_pool.acquire() as conn:
                # Calculate duration
                duration_query = """
                    SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - triggered_at))::int
                    FROM terraform_executions
                    WHERE execution_id = $1::uuid
                """
                duration = await conn.fetchval(duration_query, execution_id)
                
                # Update execution
                result = await conn.execute("""
                    UPDATE terraform_executions
                    SET status = $2,
                        completed_at = CURRENT_TIMESTAMP,
                        duration_seconds = $3,
                        plan_output = $4::jsonb,
                        error_message = $5,
                        exit_code = $6,
                        resources_to_add = $7,
                        resources_to_change = $8,
                        resources_to_destroy = $9
                    WHERE execution_id = $1::uuid
                """, execution_id, status, duration,
                    json.dumps(plan_output) if plan_output else None,
                    error_message, exit_code,
                    plan_output.get('to_add', 0) if plan_output else 0,
                    plan_output.get('to_change', 0) if plan_output else 0,
                    plan_output.get('to_destroy', 0) if plan_output else 0)
                
                return "UPDATE" in result
        except Exception as e:
            logger.error(f"Error updating execution: {e}")
            return False
    
    async def get_executions(
        self,
        workspace_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution history"""
        try:
            async with self.db_pool.acquire() as conn:
                if workspace_id:
                    query = """
                        SELECT * FROM terraform_executions
                        WHERE workspace_id = $1::uuid
                        ORDER BY triggered_at DESC
                        LIMIT $2
                    """
                    rows = await conn.fetch(query, workspace_id, limit)
                else:
                    query = """
                        SELECT * FROM recent_terraform_executions
                        LIMIT $1
                    """
                    rows = await conn.fetch(query, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting executions: {e}")
            return []
    
    # ==================== TEMPLATE LIBRARY ====================
    
    async def get_templates(
        self,
        cloud_provider: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get IaC templates"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT * FROM iac_templates
                    WHERE ($1 IS NULL OR cloud_provider = $1)
                      AND ($2 IS NULL OR category = $2)
                    ORDER BY downloads_count DESC, name
                """
                rows = await conn.fetch(query, cloud_provider, category)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM iac_templates
                    WHERE template_id = $1::uuid
                """, template_id)
                
                if row:
                    # Increment download count
                    await conn.execute("""
                        UPDATE iac_templates
                        SET downloads_count = downloads_count + 1
                        WHERE template_id = $1::uuid
                    """, template_id)
                
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting template: {e}")
            return None
    
    # ==================== VARIABLES MANAGEMENT ====================
    
    async def set_variable(
        self,
        workspace_id: str,
        key: str,
        value: str,
        is_sensitive: bool = False,
        description: Optional[str] = None
    ) -> bool:
        """Set workspace variable"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO terraform_variables (
                        workspace_id, key, value, is_sensitive, description
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5)
                    ON CONFLICT (workspace_id, key, category)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        is_sensitive = EXCLUDED.is_sensitive,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                """, workspace_id, key, value, is_sensitive, description)
                return True
        except Exception as e:
            logger.error(f"Error setting variable: {e}")
            return False
    
    async def get_variables(
        self,
        workspace_id: str,
        include_sensitive: bool = False
    ) -> List[Dict[str, Any]]:
        """Get workspace variables"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT variable_id, key, 
                           CASE WHEN is_sensitive AND $2 = false THEN '***' ELSE value END as value,
                           is_sensitive, description
                    FROM terraform_variables
                    WHERE workspace_id = $1::uuid
                    ORDER BY key
                """, workspace_id, include_sensitive)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting variables: {e}")
            return []
    
    # ==================== DRIFT DETECTION ====================
    
    async def record_drift(
        self,
        workspace_id: str,
        resource_id: str,
        drift_type: str,
        expected_state: Dict[str, Any],
        actual_state: Dict[str, Any],
        differences: Dict[str, Any]
    ) -> Optional[str]:
        """Record infrastructure drift"""
        try:
            async with self.db_pool.acquire() as conn:
                drift_id = await conn.fetchval("""
                    INSERT INTO terraform_drift_detections (
                        workspace_id, resource_id, drift_type,
                        expected_state, actual_state, differences
                    )
                    VALUES ($1::uuid, $2::uuid, $3, $4::jsonb, $5::jsonb, $6::jsonb)
                    RETURNING drift_id::text
                """, workspace_id, resource_id, drift_type,
                    json.dumps(expected_state), json.dumps(actual_state),
                    json.dumps(differences))
                
                logger.warning(f"Drift detected in workspace {workspace_id}: {drift_type}")
                return drift_id
        except Exception as e:
            logger.error(f"Error recording drift: {e}")
            return None
    
    async def get_drifts(
        self,
        workspace_id: str,
        resolved: bool = False
    ) -> List[Dict[str, Any]]:
        """Get drift detections"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT d.*, r.resource_name, r.resource_type
                    FROM terraform_drift_detections d
                    JOIN terraform_resources r ON d.resource_id = r.resource_id
                    WHERE d.workspace_id = $1::uuid
                      AND d.resolved = $2
                    ORDER BY d.detected_at DESC
                """, workspace_id, resolved)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting drifts: {e}")
            return []
    
    # ==================== STATISTICS ====================
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get overall Terraform statistics"""
        try:
            async with self.db_pool.acquire() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(DISTINCT w.workspace_id) as total_workspaces,
                        COUNT(DISTINCT r.resource_id) as total_resources,
                        COUNT(DISTINCT CASE WHEN r.status = 'active' THEN r.resource_id END) as active_resources,
                        COUNT(DISTINCT e.execution_id) as total_executions,
                        COUNT(DISTINCT CASE WHEN d.resolved = false THEN d.drift_id END) as active_drifts,
                        COUNT(DISTINCT t.template_id) as available_templates
                    FROM terraform_workspaces w
                    LEFT JOIN terraform_resources r ON w.workspace_id = r.workspace_id
                    LEFT JOIN terraform_executions e ON w.workspace_id = e.workspace_id
                    LEFT JOIN terraform_drift_detections d ON w.workspace_id = d.workspace_id
                    CROSS JOIN iac_templates t
                """)
                
                return dict(stats) if stats else {}
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


# Global instance
terraform_manager: Optional[TerraformManager] = None


def init_terraform_manager(db_pool: asyncpg.Pool):
    """Initialize global Terraform manager"""
    global terraform_manager
    terraform_manager = TerraformManager(db_pool)
    logger.info("Global Terraform manager initialized")


def get_terraform_manager() -> Optional[TerraformManager]:
    """Get global Terraform manager instance"""
    return terraform_manager
