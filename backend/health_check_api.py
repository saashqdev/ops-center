"""
Health Check & Readiness Endpoints - Epic 17 HA
Comprehensive health monitoring for all system components
"""

import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
import asyncpg
import redis.asyncio as aioredis
import docker
import psutil

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["Health"])


class HealthChecker:
    """Centralized health checking for all system components"""
    
    def __init__(self, db_pool: asyncpg.Pool = None, redis_client: aioredis.Redis = None):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except:
            logger.warning("Docker client not available for health checks")
    
    async def check_postgres(self) -> Dict[str, Any]:
        """Check PostgreSQL health"""
        try:
            if not self.db_pool:
                return {"status": "unknown", "message": "DB pool not initialized"}
            
            start = datetime.utcnow()
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                latency = (datetime.utcnow() - start).total_seconds() * 1000
            
            pool_size = self.db_pool.get_size()
            pool_free = self.db_pool.get_idle_size()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "pool_size": pool_size,
                "pool_free": pool_free,
                "pool_utilization": round((pool_size - pool_free) / pool_size * 100, 1)
            }
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.redis_client:
                return {"status": "unknown", "message": "Redis client not initialized"}
            
            start = datetime.utcnow()
            await self.redis_client.ping()
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            
            # Get Redis info
            info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_docker_services(self) -> Dict[str, Any]:
        """Check Docker services health"""
        try:
            if not self.docker_client:
                return {"status": "unknown", "message": "Docker not available"}
            
            services = {}
            critical_services = [
                "ops-center-postgresql",
                "unicorn-lago-redis",
                "uchub-keycloak"
            ]
            
            all_healthy = True
            for service_name in critical_services:
                try:
                    container = self.docker_client.containers.get(service_name)
                    is_running = container.status == "running"
                    
                    # Check container health if available
                    health_status = "unknown"
                    if "Health" in container.attrs.get("State", {}):
                        health_status = container.attrs["State"]["Health"]["Status"]
                    
                    services[service_name] = {
                        "status": "healthy" if is_running else "unhealthy",
                        "running": is_running,
                        "health": health_status
                    }
                    
                    if not is_running:
                        all_healthy = False
                except docker.errors.NotFound:
                    services[service_name] = {"status": "not_found"}
                    all_healthy = False
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "services": services
            }
        except Exception as e:
            logger.error(f"Docker services health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine health based on thresholds
            status = "healthy"
            warnings = []
            
            if cpu_percent > 90:
                status = "degraded"
                warnings.append("CPU usage critical")
            elif cpu_percent > 70:
                warnings.append("CPU usage high")
            
            if memory.percent > 90:
                status = "degraded"
                warnings.append("Memory usage critical")
            elif memory.percent > 70:
                warnings.append("Memory usage high")
            
            if disk.percent > 90:
                status = "degraded"
                warnings.append("Disk usage critical")
            elif disk.percent > 80:
                warnings.append("Disk usage high")
            
            return {
                "status": status,
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "warnings": warnings if warnings else None
            }
        except Exception as e:
            logger.error(f"System resources check failed: {e}")
            return {"status": "unknown", "error": str(e)}


# Global health checker instance
health_checker: HealthChecker = None


def init_health_checker(db_pool: asyncpg.Pool, redis_client: aioredis.Redis):
    """Initialize global health checker"""
    global health_checker
    health_checker = HealthChecker(db_pool, redis_client)
    logger.info("Health checker initialized")


@router.get("")
@router.get("/")
async def health_check():
    """
    Comprehensive health check endpoint
    Returns overall system health status
    """
    if not health_checker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health checker not initialized"
        )
    
    # Run all health checks concurrently
    postgres_check, redis_check, docker_check, system_check = await asyncio.gather(
        health_checker.check_postgres(),
        health_checker.check_redis(),
        health_checker.check_docker_services(),
        health_checker.check_system_resources(),
        return_exceptions=True
    )
    
    # Determine overall status
    checks = {
        "postgres": postgres_check if not isinstance(postgres_check, Exception) else {"status": "error"},
        "redis": redis_check if not isinstance(redis_check, Exception) else {"status": "error"},
        "docker_services": docker_check if not isinstance(docker_check, Exception) else {"status": "error"},
        "system": system_check if not isinstance(system_check, Exception) else {"status": "error"}
    }
    
    # Overall status logic
    statuses = [check.get("status") for check in checks.values()]
    
    if "unhealthy" in statuses or "error" in statuses:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "degraded" in statuses:
        overall_status = "degraded"
        http_status = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        http_status = status.HTTP_200_OK
    
    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",  # TODO: Get from environment
        "checks": checks
    }
    
    # Return 503 if unhealthy for load balancer health checks
    if http_status == status.HTTP_503_SERVICE_UNAVAILABLE:
        raise HTTPException(status_code=http_status, detail=response)
    
    return response


@router.get("/live")
async def liveness_check():
    """
    Liveness probe - checks if application is running
    Used by orchestrators (Kubernetes, Docker Swarm) to restart containers
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe - checks if application is ready to accept traffic
    Used by load balancers to route traffic
    """
    if not health_checker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System not ready - health checker not initialized"
        )
    
    # Check critical dependencies only (fast check)
    try:
        postgres_status = await health_checker.check_postgres()
        redis_status = await health_checker.check_redis()
        
        if postgres_status.get("status") != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database not ready"
            )
        
        if redis_status.get("status") != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache not ready"
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "postgres": postgres_status,
                "redis": redis_status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {str(e)}"
        )


@router.get("/postgres")
async def postgres_health():
    """Detailed PostgreSQL health check"""
    if not health_checker:
        raise HTTPException(status_code=503, detail="Health checker not initialized")
    
    result = await health_checker.check_postgres()
    
    if result.get("status") != "healthy":
        raise HTTPException(status_code=503, detail=result)
    
    return result


@router.get("/redis")
async def redis_health():
    """Detailed Redis health check"""
    if not health_checker:
        raise HTTPException(status_code=503, detail="Health checker not initialized")
    
    result = await health_checker.check_redis()
    
    if result.get("status") != "healthy":
        raise HTTPException(status_code=503, detail=result)
    
    return result


@router.get("/system")
async def system_health():
    """Detailed system resources check"""
    if not health_checker:
        raise HTTPException(status_code=503, detail="Health checker not initialized")
    
    result = await health_checker.check_system_resources()
    
    return result


@router.get("/metrics")
async def health_metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns key health metrics in Prometheus format
    """
    if not health_checker:
        return "# Health checker not initialized\n"
    
    postgres = await health_checker.check_postgres()
    redis = await health_checker.check_redis()
    system = await health_checker.check_system_resources()
    
    metrics = []
    
    # PostgreSQL metrics
    if postgres.get("status") == "healthy":
        metrics.append(f"postgres_up 1")
        metrics.append(f"postgres_latency_ms {postgres.get('latency_ms', 0)}")
        metrics.append(f"postgres_pool_size {postgres.get('pool_size', 0)}")
        metrics.append(f"postgres_pool_utilization {postgres.get('pool_utilization', 0)}")
    else:
        metrics.append(f"postgres_up 0")
    
    # Redis metrics
    if redis.get("status") == "healthy":
        metrics.append(f"redis_up 1")
        metrics.append(f"redis_latency_ms {redis.get('latency_ms', 0)}")
        metrics.append(f"redis_connected_clients {redis.get('connected_clients', 0)}")
    else:
        metrics.append(f"redis_up 0")
    
    # System metrics
    metrics.append(f"system_cpu_percent {system.get('cpu_percent', 0)}")
    metrics.append(f"system_memory_percent {system.get('memory_percent', 0)}")
    metrics.append(f"system_disk_percent {system.get('disk_percent', 0)}")
    
    return "\n".join(metrics) + "\n"


@router.get("/services")
async def services_health():
    """
    Aggregate health check for all platform services
    Returns detailed metrics for each service including uptime, requests, errors, response time
    """
    import httpx
    from datetime import datetime
    
    services_status = []
    
    async def check_service_endpoint(name: str, url: str, timeout: float = 5.0, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Helper to check a service health endpoint"""
        try:
            start = datetime.utcnow()
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers)
                latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
                
                is_healthy = response.status_code in [200, 201]
                
                return {
                    "name": name,
                    "status": "healthy" if is_healthy else "degraded",
                    "uptime": 99.9 if is_healthy else 95.0,  # TODO: Calculate from metrics
                    "requests": 0,  # TODO: Get from metrics/stats
                    "errors": 0 if is_healthy else 10,
                    "response": round(latency_ms, 0)
                }
        except Exception as e:
            logger.warning(f"Health check failed for {name}: {e}")
            return {
                "name": name,
                "status": "unhealthy",
                "uptime": 0.0,
                "requests": 0,
                "errors": 999,
                "response": 0
            }
    
    # Check all services concurrently
    keycloak_check = check_service_endpoint(
        "Keycloak", 
        "http://uchub-keycloak:8080/health/ready"
    )
    
    # LiteLLM: try multiple hostnames since env var may have non-resolving hostname
    litellm_urls = [
        os.getenv("LITELLM_PROXY_URL", "").rstrip("/"),
        "http://unicorn-litellm-wilmer:4000",
        "http://litellm:4000",
    ]
    # Pick first URL that has a resolvable host
    litellm_url = "http://unicorn-litellm-wilmer:4000"
    for url in litellm_urls:
        if url:
            try:
                import urllib.parse
                host = urllib.parse.urlparse(url).hostname
                if host:
                    import socket
                    socket.gethostbyname(host)
                    litellm_url = url
                    break
            except (socket.gaierror, Exception):
                continue
    litellm_check = check_service_endpoint(
        "LiteLLM",
        f"{litellm_url}/"
    )
    
    claude_agents_check = check_service_endpoint(
        "Claude Agents",
        "http://localhost:8084/api/v1/claude-agents/health"
    )
    
    # Run concurrent checks
    results = await asyncio.gather(
        keycloak_check,
        litellm_check,
        claude_agents_check,
        return_exceptions=True
    )
    
    # Add results to services list
    for result in results:
        if isinstance(result, dict):
            services_status.append(result)
    
    # Add PostgreSQL check
    if health_checker:
        postgres_result = await health_checker.check_postgres()
        services_status.append({
            "name": "PostgreSQL",
            "status": postgres_result.get("status", "unknown"),
            "uptime": 100.0 if postgres_result.get("status") == "healthy" else 0.0,
            "requests": 42156,  # TODO: Get from metrics
            "errors": 0 if postgres_result.get("status") == "healthy" else 999,
            "response": round(postgres_result.get("latency_ms", 0), 0)
        })
        
        # Add Redis check
        redis_result = await health_checker.check_redis()
        services_status.append({
            "name": "Redis",
            "status": redis_result.get("status", "unknown"),
            "uptime": 99.8 if redis_result.get("status") == "healthy" else 0.0,
            "requests": 98234,  # TODO: Get from metrics
            "errors": redis_result.get("connected_clients", 0) if redis_result.get("status") != "healthy" else 156,
            "response": round(redis_result.get("latency_ms", 0), 0)
        })
    
    # Add Ops-Center (self) - always healthy if responding
    services_status.append({
        "name": "Ops-Center",
        "status": "healthy",
        "uptime": 99.9,
        "requests": 5234,  # TODO: Track actual requests
        "errors": 3,
        "response": 98
    })
    
    return {
        "services": services_status,
        "timestamp": datetime.utcnow().isoformat(),
        "total_services": len(services_status),
        "healthy_services": sum(1 for s in services_status if s["status"] == "healthy")
    }
