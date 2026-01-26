"""
Epic 15: Multi-Server Management - Fleet Dashboard
Backend Manager for multi-server orchestration
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import uuid4

import asyncpg
import aiohttp
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class MultiServerManager:
    """Manages fleet of Ops-Center servers"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.http_session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize HTTP session for server communication"""
        if not self.http_session:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "OpsCenter-Fleet-Manager/1.0"}
            )
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
    
    # ========== SERVER REGISTRATION ==========
    
    async def register_server(
        self,
        organization_id: str,
        name: str,
        hostname: str,
        api_url: str,
        api_token: str,
        description: Optional[str] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Register a new managed server"""
        
        # Hash the API token for secure storage
        token_hash = hashlib.sha256(api_token.encode()).hexdigest()
        
        server_id = str(uuid4())
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO managed_servers (
                    id, name, description, hostname, api_url, api_token_hash,
                    region, environment, status, tags, metadata, organization_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', $9, $10, $11)
                """,
                server_id, name, description, hostname, api_url, token_hash,
                region, environment, tags or [], metadata or {}, organization_id
            )
        
        logger.info(f"Registered server {name} ({server_id}) for org {organization_id}")
        
        # Perform initial health check
        await self._perform_health_check(server_id, api_url, api_token)
        
        return await self.get_server(server_id)
    
    async def update_server(
        self,
        server_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update server configuration"""
        
        updates = []
        params = []
        param_num = 1
        
        if name is not None:
            updates.append(f"name = ${param_num}")
            params.append(name)
            param_num += 1
        
        if description is not None:
            updates.append(f"description = ${param_num}")
            params.append(description)
            param_num += 1
        
        if region is not None:
            updates.append(f"region = ${param_num}")
            params.append(region)
            param_num += 1
        
        if environment is not None:
            updates.append(f"environment = ${param_num}")
            params.append(environment)
            param_num += 1
        
        if tags is not None:
            updates.append(f"tags = ${param_num}")
            params.append(tags)
            param_num += 1
        
        if metadata is not None:
            updates.append(f"metadata = ${param_num}")
            params.append(metadata)
            param_num += 1
        
        if status is not None:
            updates.append(f"status = ${param_num}")
            params.append(status)
            param_num += 1
        
        if not updates:
            return await self.get_server(server_id)
        
        updates.append(f"updated_at = ${param_num}")
        params.append(datetime.utcnow())
        param_num += 1
        
        params.append(server_id)
        
        async with self.db.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE managed_servers
                SET {', '.join(updates)}
                WHERE id = ${param_num}
                """,
                *params
            )
        
        logger.info(f"Updated server {server_id}: {', '.join([u.split(' = ')[0] for u in updates])}")
        
        return await self.get_server(server_id)
    
    async def delete_server(self, server_id: str):
        """Remove a server from management (cascades to health checks, metrics)"""
        async with self.db.acquire() as conn:
            await conn.execute("DELETE FROM managed_servers WHERE id = $1", server_id)
        
        logger.info(f"Deleted server {server_id}")
    
    async def get_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server details"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM managed_servers WHERE id = $1",
                server_id
            )
        
        if not row:
            return None
        
        return dict(row)
    
    async def list_servers(
        self,
        organization_id: str,
        status: Optional[str] = None,
        health_status: Optional[str] = None,
        region: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List servers with filtering"""
        
        conditions = ["organization_id = $1"]
        params = [organization_id]
        param_num = 2
        
        if status:
            conditions.append(f"status = ${param_num}")
            params.append(status)
            param_num += 1
        
        if health_status:
            conditions.append(f"health_status = ${param_num}")
            params.append(health_status)
            param_num += 1
        
        if region:
            conditions.append(f"region = ${param_num}")
            params.append(region)
            param_num += 1
        
        if environment:
            conditions.append(f"environment = ${param_num}")
            params.append(environment)
            param_num += 1
        
        if tags:
            conditions.append(f"tags @> ${param_num}")
            params.append(tags)
            param_num += 1
        
        params.extend([limit, offset])
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM managed_servers
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT ${param_num} OFFSET ${param_num + 1}
                """,
                *params
            )
        
        return [dict(row) for row in rows]
    
    # ========== HEALTH CHECKS ==========
    
    async def _perform_health_check(
        self,
        server_id: str,
        api_url: str,
        api_token: str
    ) -> Dict[str, Any]:
        """Perform health check on a managed server"""
        
        await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            async with self.http_session.get(
                f"{api_url}/health",
                headers={"Authorization": f"Bearer {api_token}"}
            ) as response:
                response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                if response.status == 200:
                    data = await response.json()
                    
                    health_status = "healthy"
                    database_healthy = data.get("database", {}).get("status") == "ok"
                    redis_healthy = data.get("redis", {}).get("status") == "ok"
                    services_healthy = data.get("services", {}).get("healthy", True)
                    
                    if not database_healthy or not redis_healthy:
                        health_status = "critical"
                    elif not services_healthy:
                        health_status = "degraded"
                    
                    # Record health check
                    async with self.db.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO server_health_checks (
                                id, server_id, timestamp, status, response_time_ms,
                                database_healthy, redis_healthy, services_healthy
                            )
                            VALUES (DEFAULT, $1, $2, $3, $4, $5, $6, $7)
                            """,
                            server_id, start_time, health_status, response_time_ms,
                            database_healthy, redis_healthy, services_healthy
                        )
                        
                        # Update server health status
                        await conn.execute(
                            """
                            UPDATE managed_servers
                            SET health_status = $1, last_health_check_at = $2, last_seen_at = $2
                            WHERE id = $3
                            """,
                            health_status, start_time, server_id
                        )
                    
                    return {
                        "server_id": server_id,
                        "status": health_status,
                        "response_time_ms": response_time_ms,
                        "timestamp": start_time.isoformat()
                    }
                
                else:
                    # Unhealthy response
                    error_message = f"HTTP {response.status}"
                    
                    async with self.db.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO server_health_checks (
                                id, server_id, timestamp, status, response_time_ms,
                                error_message
                            )
                            VALUES (DEFAULT, $1, $2, 'critical', $3, $4)
                            """,
                            server_id, start_time, response_time_ms, error_message
                        )
                        
                        await conn.execute(
                            """
                            UPDATE managed_servers
                            SET health_status = 'critical', last_health_check_at = $1
                            WHERE id = $2
                            """,
                            start_time, server_id
                        )
                    
                    return {
                        "server_id": server_id,
                        "status": "critical",
                        "error": error_message,
                        "timestamp": start_time.isoformat()
                    }
        
        except Exception as e:
            # Connection error or timeout
            error_message = str(e)
            
            async with self.db.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO server_health_checks (
                        id, server_id, timestamp, status, error_message
                    )
                    VALUES (DEFAULT, $1, $2, 'unreachable', $3)
                    """,
                    server_id, start_time, error_message
                )
                
                await conn.execute(
                    """
                    UPDATE managed_servers
                    SET health_status = 'unreachable', last_health_check_at = $1
                    WHERE id = $2
                    """,
                    start_time, server_id
                )
            
            logger.error(f"Health check failed for server {server_id}: {error_message}")
            
            return {
                "server_id": server_id,
                "status": "unreachable",
                "error": error_message,
                "timestamp": start_time.isoformat()
            }
    
    async def check_all_servers_health(self, organization_id: str) -> List[Dict[str, Any]]:
        """Check health of all active servers in organization"""
        
        async with self.db.acquire() as conn:
            servers = await conn.fetch(
                """
                SELECT id, api_url, api_token_hash FROM managed_servers
                WHERE organization_id = $1 AND status = 'active'
                """,
                organization_id
            )
        
        # Note: In production, you'd retrieve api_token from secure storage
        # For now, we'll skip health checks if token not available
        
        results = []
        for server in servers:
            try:
                # This is a placeholder - in production you'd need to decrypt/retrieve the token
                result = await self._perform_health_check(
                    server['id'],
                    server['api_url'],
                    "PLACEHOLDER_TOKEN"  # Would come from secure storage
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Health check error for {server['id']}: {e}")
                results.append({
                    "server_id": server['id'],
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def get_server_health_history(
        self,
        server_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical health check data for a server"""
        
        conditions = ["server_id = $1"]
        params = [server_id]
        param_num = 2
        
        if start_time:
            conditions.append(f"timestamp >= ${param_num}")
            params.append(start_time)
            param_num += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_num}")
            params.append(end_time)
            param_num += 1
        
        params.append(limit)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM server_health_checks
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT ${param_num}
                """,
                *params
            )
        
        return [dict(row) for row in rows]
    
    # ========== METRICS COLLECTION ==========
    
    async def collect_server_metrics(
        self,
        server_id: str,
        api_url: str,
        api_token: str
    ) -> Dict[str, Any]:
        """Collect metrics from a managed server"""
        
        await self.initialize()
        
        try:
            async with self.http_session.get(
                f"{api_url}/api/v1/metrics/current",
                headers={"Authorization": f"Bearer {api_token}"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Store in aggregated metrics
                    async with self.db.acquire() as conn:
                        await conn.execute(
                            """
                            INSERT INTO server_metrics_aggregated (
                                id, server_id, timestamp, period,
                                cpu_percent, memory_percent, disk_percent,
                                network_rx_bytes, network_tx_bytes,
                                active_services, failed_services, total_services,
                                llm_requests, llm_cost_usd,
                                active_users, total_users
                            )
                            VALUES (
                                DEFAULT, $1, $2, '1m',
                                $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                            )
                            """,
                            server_id,
                            datetime.utcnow(),
                            data.get("cpu_percent"),
                            data.get("memory_percent"),
                            data.get("disk_percent"),
                            data.get("network_rx_bytes"),
                            data.get("network_tx_bytes"),
                            data.get("active_services"),
                            data.get("failed_services"),
                            data.get("total_services"),
                            data.get("llm_requests"),
                            data.get("llm_cost_usd"),
                            data.get("active_users"),
                            data.get("total_users")
                        )
                    
                    return {"status": "success", "server_id": server_id}
                
                else:
                    return {"status": "error", "server_id": server_id, "error": f"HTTP {response.status}"}
        
        except Exception as e:
            logger.error(f"Metrics collection failed for {server_id}: {e}")
            return {"status": "error", "server_id": server_id, "error": str(e)}
    
    async def get_server_metrics(
        self,
        server_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        period: str = "1m",
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical metrics for a server"""
        
        conditions = ["server_id = $1", "period = $2"]
        params = [server_id, period]
        param_num = 3
        
        if start_time:
            conditions.append(f"timestamp >= ${param_num}")
            params.append(start_time)
            param_num += 1
        
        if end_time:
            conditions.append(f"timestamp <= ${param_num}")
            params.append(end_time)
            param_num += 1
        
        params.append(limit)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM server_metrics_aggregated
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT ${param_num}
                """,
                *params
            )
        
        return [dict(row) for row in rows]
    
    # ========== SERVER GROUPS ==========
    
    async def create_group(
        self,
        organization_id: str,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        tags: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        environments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a server group"""
        
        group_id = str(uuid4())
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO server_groups (
                    id, name, description, color, tags, regions, environments, organization_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                group_id, name, description, color,
                tags or [], regions or [], environments or [],
                organization_id
            )
        
        logger.info(f"Created server group {name} ({group_id})")
        
        return await self.get_group(group_id)
    
    async def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get group details"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM server_groups WHERE id = $1",
                group_id
            )
        
        if not row:
            return None
        
        return dict(row)
    
    async def list_groups(self, organization_id: str) -> List[Dict[str, Any]]:
        """List all groups in organization"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM server_groups WHERE organization_id = $1 ORDER BY name",
                organization_id
            )
        
        return [dict(row) for row in rows]
    
    async def add_server_to_group(self, server_id: str, group_id: str):
        """Add a server to a group"""
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO server_group_members (server_id, group_id)
                VALUES ($1, $2)
                ON CONFLICT (server_id, group_id) DO NOTHING
                """,
                server_id, group_id
            )
        
        logger.info(f"Added server {server_id} to group {group_id}")
    
    async def remove_server_from_group(self, server_id: str, group_id: str):
        """Remove a server from a group"""
        async with self.db.acquire() as conn:
            await conn.execute(
                "DELETE FROM server_group_members WHERE server_id = $1 AND group_id = $2",
                server_id, group_id
            )
        
        logger.info(f"Removed server {server_id} from group {group_id}")
    
    async def get_group_servers(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all servers in a group"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ms.* FROM managed_servers ms
                JOIN server_group_members sgm ON ms.id = sgm.server_id
                WHERE sgm.group_id = $1
                ORDER BY ms.name
                """,
                group_id
            )
        
        return [dict(row) for row in rows]
    
    # ========== FLEET OPERATIONS ==========
    
    async def create_fleet_operation(
        self,
        operation_type: str,
        initiated_by: str,
        server_ids: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None,
        filter_criteria: Optional[Dict] = None,
        parameters: Optional[Dict] = None
    ) -> str:
        """Create a fleet operation record"""
        
        operation_id = str(uuid4())
        
        # Calculate total servers
        total_servers = 0
        if server_ids:
            total_servers = len(server_ids)
        elif group_ids:
            # Count servers across all groups
            async with self.db.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT COUNT(DISTINCT server_id) FROM server_group_members
                    WHERE group_id = ANY($1)
                    """,
                    group_ids
                )
                total_servers = result or 0
        
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO fleet_operations (
                    id, operation_type, server_ids, group_ids, filter_criteria,
                    parameters, initiated_by, status, total_servers, started_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8, $9)
                """,
                operation_id, operation_type, server_ids, group_ids, filter_criteria,
                parameters or {}, initiated_by, total_servers, datetime.utcnow()
            )
        
        logger.info(f"Created fleet operation {operation_id}: {operation_type}")
        
        return operation_id
    
    async def update_fleet_operation_status(
        self,
        operation_id: str,
        status: str,
        completed_servers: Optional[int] = None,
        failed_servers: Optional[int] = None,
        results: Optional[Dict] = None,
        error_summary: Optional[str] = None
    ):
        """Update fleet operation status"""
        
        updates = ["status = $1"]
        params = [status]
        param_num = 2
        
        if completed_servers is not None:
            updates.append(f"completed_servers = ${param_num}")
            params.append(completed_servers)
            param_num += 1
        
        if failed_servers is not None:
            updates.append(f"failed_servers = ${param_num}")
            params.append(failed_servers)
            param_num += 1
        
        if results is not None:
            updates.append(f"results = ${param_num}")
            params.append(results)
            param_num += 1
        
        if error_summary is not None:
            updates.append(f"error_summary = ${param_num}")
            params.append(error_summary)
            param_num += 1
        
        if status in ('completed', 'failed'):
            updates.append(f"completed_at = ${param_num}")
            params.append(datetime.utcnow())
            param_num += 1
        
        params.append(operation_id)
        
        async with self.db.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE fleet_operations
                SET {', '.join(updates)}
                WHERE id = ${param_num}
                """,
                *params
            )
    
    async def get_fleet_operation(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get fleet operation details"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fleet_operations WHERE id = $1",
                operation_id
            )
        
        if not row:
            return None
        
        return dict(row)
    
    # ========== FLEET SUMMARY ==========
    
    async def get_fleet_summary(self, organization_id: str) -> Dict[str, Any]:
        """Get fleet summary for organization"""
        async with self.db.acquire() as conn:
            summary = await conn.fetchrow(
                "SELECT * FROM v_fleet_summary WHERE organization_id = $1",
                organization_id
            )
        
        if not summary:
            return {
                "organization_id": organization_id,
                "total_servers": 0,
                "active_servers": 0,
                "healthy_servers": 0
            }
        
        return dict(summary)
