"""
Atlas MCP Tools - Infrastructure Management Tools

Provides 5 core tools for Lt. Colonel Atlas to manage Ops-Center infrastructure:
1. system_status - Check system health and service status
2. manage_user - Create, modify, or delete users
3. check_billing - View billing usage and subscription status
4. restart_service - Restart Docker services
5. query_logs - Search and analyze system logs

These tools are exposed as MCP (Model Context Protocol) tools for AI agents.
"""

import asyncio
import subprocess
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)

# ===================================================================
# Tool 1: System Status
# ===================================================================

async def system_status(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Check system health and service status
    
    Args:
        filters: Optional filters for specific services or components
            - services: List of service names to check (default: all)
            - include_metrics: Include CPU/memory metrics (default: true)
            - include_docker: Include Docker container status (default: true)
    
    Returns:
        Dict containing:
        - overall_status: "healthy" | "degraded" | "critical"
        - services: List of service statuses
        - system_metrics: CPU, memory, disk usage
        - docker_containers: Container status list
        - timestamp: ISO timestamp
    """
    filters = filters or {}
    
    try:
        result = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": [],
            "system_metrics": {},
            "docker_containers": []
        }
        
        # Check key Ops-Center services
        services_to_check = filters.get("services", [
            "backend", "keycloak", "grafana", "prometheus", 
            "umami", "forgejo", "brigade", "litellm"
        ])
        
        service_statuses = []
        for service in services_to_check:
            try:
                # Check if service is reachable via health endpoint
                url = get_service_health_url(service)
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(url)
                    status = "healthy" if response.status_code == 200 else "degraded"
            except Exception as e:
                status = "down"
                logger.warning(f"Service {service} health check failed: {e}")
            
            service_statuses.append({
                "name": service,
                "status": status,
                "checked_at": datetime.utcnow().isoformat()
            })
        
        result["services"] = service_statuses
        
        # Get system metrics if requested
        if filters.get("include_metrics", True):
            result["system_metrics"] = await get_system_metrics()
        
        # Get Docker container status if requested
        if filters.get("include_docker", True):
            result["docker_containers"] = await get_docker_status()
        
        # Determine overall status
        down_services = [s for s in service_statuses if s["status"] == "down"]
        degraded_services = [s for s in service_statuses if s["status"] == "degraded"]
        
        if len(down_services) > 2:
            result["overall_status"] = "critical"
        elif len(down_services) > 0 or len(degraded_services) > 2:
            result["overall_status"] = "degraded"
        
        return result
        
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_service_health_url(service: str) -> str:
    """Map service name to health check URL"""
    health_urls = {
        "backend": "http://localhost:8084/health",
        "keycloak": "http://localhost:8080/health",
        "grafana": "http://taxsquare-grafana:3000/api/health",
        "prometheus": "http://prometheus:9090/-/healthy",
        "umami": "http://umami:3000/api/heartbeat",
        "forgejo": "http://git.unicorncloud.consulting:3000/api/healthz",
        "brigade": "http://unicorn-brigade:8112/health",
        "litellm": "http://localhost:4000/health"
    }
    return health_urls.get(service, f"http://{service}:80/health")


async def get_system_metrics() -> Dict[str, Any]:
    """Get system CPU, memory, and disk metrics"""
    try:
        # Get CPU usage
        cpu_percent = subprocess.check_output(
            "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
            shell=True
        ).decode().strip().replace('%us,', '')
        
        # Get memory usage
        mem_info = subprocess.check_output(
            "free -m | awk 'NR==2{printf \"%s,%s,%.2f\", $3,$2,$3*100/$2 }'",
            shell=True
        ).decode().strip().split(',')
        
        # Get disk usage
        disk_info = subprocess.check_output(
            "df -h / | awk 'NR==2{printf \"%s,%s,%s\", $3,$2,$5}'",
            shell=True
        ).decode().strip().split(',')
        
        return {
            "cpu_percent": float(cpu_percent) if cpu_percent else 0,
            "memory_used_mb": int(mem_info[0]) if len(mem_info) > 0 else 0,
            "memory_total_mb": int(mem_info[1]) if len(mem_info) > 1 else 0,
            "memory_percent": float(mem_info[2]) if len(mem_info) > 2 else 0,
            "disk_used": disk_info[0] if len(disk_info) > 0 else "0",
            "disk_total": disk_info[1] if len(disk_info) > 1 else "0",
            "disk_percent": disk_info[2] if len(disk_info) > 2 else "0%"
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {"error": str(e)}


async def get_docker_status() -> List[Dict[str, Any]]:
    """Get Docker container status"""
    try:
        output = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Image}}"],
            text=True
        )
        
        containers = []
        for line in output.strip().split('\n'):
            if line:
                parts = line.split('\t')
                containers.append({
                    "name": parts[0],
                    "status": parts[1],
                    "image": parts[2] if len(parts) > 2 else "unknown"
                })
        
        return containers
    except Exception as e:
        logger.error(f"Failed to get Docker status: {e}")
        return [{"error": str(e)}]


# ===================================================================
# Tool 2: Manage User
# ===================================================================

async def manage_user(
    action: str,
    user_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create, modify, or delete users in Ops-Center
    
    Args:
        action: "create" | "update" | "delete" | "list"
        user_data: User information
            - username: User's username (required for all actions)
            - email: User's email (required for create)
            - password: User's password (required for create)
            - role: User role (optional, default: "user")
            - organization: Organization ID (optional)
            - enabled: Boolean (optional, default: true)
    
    Returns:
        Dict containing:
        - success: Boolean
        - message: Success or error message
        - user: User object (for create/update)
        - users: List of users (for list action)
    """
    try:
        if action == "create":
            return await create_user(user_data)
        elif action == "update":
            return await update_user(user_data)
        elif action == "delete":
            return await delete_user(user_data.get("username"))
        elif action == "list":
            return await list_users(user_data.get("filters", {}))
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}. Use 'create', 'update', 'delete', or 'list'"
            }
    except Exception as e:
        logger.error(f"User management failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user via Ops-Center API"""
    required_fields = ["username", "email", "password"]
    for field in required_fields:
        if field not in user_data:
            return {
                "success": False,
                "error": f"Missing required field: {field}"
            }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8084/api/v1/admin/users",
                json={
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "role": user_data.get("role", "user"),
                    "organization_id": user_data.get("organization"),
                    "enabled": user_data.get("enabled", True)
                },
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "success": True,
                    "message": f"User '{user_data['username']}' created successfully",
                    "user": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}"
                }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create user: {str(e)}"
        }


async def update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update existing user"""
    if "username" not in user_data:
        return {"success": False, "error": "Username required for update"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://localhost:8084/api/v1/admin/users/{user_data['username']}",
                json=user_data
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"User '{user_data['username']}' updated successfully",
                    "user": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}"
                }
    except Exception as e:
        return {"success": False, "error": f"Failed to update user: {str(e)}"}


async def delete_user(username: str) -> Dict[str, Any]:
    """Delete a user"""
    if not username:
        return {"success": False, "error": "Username required for delete"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://localhost:8084/api/v1/admin/users/{username}"
            )
            
            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": f"User '{username}' deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}"
                }
    except Exception as e:
        return {"success": False, "error": f"Failed to delete user: {str(e)}"}


async def list_users(filters: Dict[str, Any]) -> Dict[str, Any]:
    """List users with optional filters"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8084/api/v1/admin/users",
                params=filters
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "users": data.get("users", []),
                    "total": data.get("total", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}"
                }
    except Exception as e:
        return {"success": False, "error": f"Failed to list users: {str(e)}"}


# ===================================================================
# Tool 3: Check Billing
# ===================================================================

async def check_billing(
    scope: str = "current_user",
    user_id: Optional[str] = None,
    timeframe: str = "month"
) -> Dict[str, Any]:
    """
    View billing usage and subscription status
    
    Args:
        scope: "current_user" | "organization" | "system"
        user_id: Specific user ID to check (admin only)
        timeframe: "day" | "week" | "month" | "year"
    
    Returns:
        Dict containing:
        - subscription: Current subscription tier
        - usage: Resource usage statistics
        - costs: Cost breakdown
        - limits: Subscription limits
        - alerts: Any billing alerts
    """
    try:
        # Calculate date range based on timeframe
        end_date = datetime.utcnow()
        if timeframe == "day":
            start_date = end_date - timedelta(days=1)
        elif timeframe == "week":
            start_date = end_date - timedelta(weeks=1)
        elif timeframe == "month":
            start_date = end_date - timedelta(days=30)
        elif timeframe == "year":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)
        
        # Fetch billing data from API
        async with httpx.AsyncClient() as client:
            params = {
                "scope": scope,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
            if user_id:
                params["user_id"] = user_id
            
            response = await client.get(
                "http://localhost:8084/api/v1/billing/usage",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "subscription": data.get("subscription", {}),
                    "usage": data.get("usage", {}),
                    "costs": data.get("costs", {}),
                    "limits": data.get("limits", {}),
                    "alerts": data.get("alerts", []),
                    "timeframe": timeframe,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Billing API returned {response.status_code}: {response.text}"
                }
    except Exception as e:
        logger.error(f"Billing check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ===================================================================
# Tool 4: Restart Service
# ===================================================================

async def restart_service(
    service_name: str,
    confirmation: bool = False
) -> Dict[str, Any]:
    """
    Restart a Docker service
    
    Args:
        service_name: Name of the service to restart
        confirmation: Must be True to execute (safety check)
    
    Returns:
        Dict containing:
        - success: Boolean
        - message: Success or error message
        - service: Service name
        - status: New service status
    """
    if not confirmation:
        return {
            "success": False,
            "error": "Confirmation required. Set confirmation=True to proceed."
        }
    
    # Whitelist of restartable services
    allowed_services = [
        "ops-center-direct", "taxsquare-grafana", "prometheus",
        "umami", "forgejo", "unicorn-brigade", "litellm"
    ]
    
    if service_name not in allowed_services:
        return {
            "success": False,
            "error": f"Service '{service_name}' is not in the allowed restart list",
            "allowed_services": allowed_services
        }
    
    try:
        # Restart the Docker container
        result = subprocess.run(
            ["docker", "restart", service_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Wait a bit for service to come back up
            await asyncio.sleep(3)
            
            # Check new status
            status_result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", service_name],
                capture_output=True,
                text=True
            )
            new_status = status_result.stdout.strip()
            
            return {
                "success": True,
                "message": f"Service '{service_name}' restarted successfully",
                "service": service_name,
                "status": new_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": f"Failed to restart service: {result.stderr}",
                "service": service_name
            }
    except Exception as e:
        logger.error(f"Service restart failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "service": service_name
        }


# ===================================================================
# Tool 5: Query Logs
# ===================================================================

async def query_logs(
    source: str = "all",
    level: str = "all",
    limit: int = 100,
    search_term: Optional[str] = None,
    timeframe: str = "1h"
) -> Dict[str, Any]:
    """
    Search and analyze system logs
    
    Args:
        source: Log source ("all" | "backend" | "docker" | specific service)
        level: Log level filter ("all" | "error" | "warning" | "info" | "debug")
        limit: Maximum number of log entries to return
        search_term: Optional text to search for in logs
        timeframe: Time range ("1h" | "6h" | "24h" | "7d")
    
    Returns:
        Dict containing:
        - logs: List of log entries
        - total: Total matching entries
        - summary: Log statistics
        - errors_count: Number of errors found
    """
    try:
        # Parse timeframe
        timeframe_map = {
            "1h": 3600,
            "6h": 21600,
            "24h": 86400,
            "7d": 604800
        }
        since_seconds = timeframe_map.get(timeframe, 3600)
        
        logs = []
        
        if source == "all" or source == "docker":
            # Get Docker container logs
            docker_logs = await get_docker_logs(since_seconds, search_term)
            logs.extend(docker_logs)
        
        if source == "all" or source == "backend":
            # Get backend application logs
            backend_logs = await get_backend_logs(since_seconds, search_term)
            logs.extend(backend_logs)
        
        # Filter by log level
        if level != "all":
            logs = [log for log in logs if log.get("level", "").lower() == level.lower()]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit results
        logs = logs[:limit]
        
        # Calculate summary
        error_count = len([log for log in logs if log.get("level", "").lower() in ["error", "critical"]])
        warning_count = len([log for log in logs if log.get("level", "").lower() == "warning"])
        
        return {
            "success": True,
            "logs": logs,
            "total": len(logs),
            "summary": {
                "errors": error_count,
                "warnings": warning_count,
                "total_entries": len(logs),
                "timeframe": timeframe,
                "source": source
            }
        }
    except Exception as e:
        logger.error(f"Log query failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def get_docker_logs(since_seconds: int, search_term: Optional[str]) -> List[Dict[str, Any]]:
    """Get logs from Docker containers"""
    try:
        containers = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}"],
            text=True
        ).strip().split('\n')
        
        logs = []
        for container in containers:
            if not container:
                continue
            
            try:
                cmd = ["docker", "logs", "--since", f"{since_seconds}s", "--tail", "100", container]
                output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=5)
                
                for line in output.split('\n'):
                    if not line.strip():
                        continue
                    
                    if search_term and search_term.lower() not in line.lower():
                        continue
                    
                    logs.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": f"docker:{container}",
                        "level": detect_log_level(line),
                        "message": line.strip()
                    })
            except Exception as e:
                logger.warning(f"Failed to get logs from {container}: {e}")
        
        return logs
    except Exception as e:
        logger.error(f"Failed to get Docker logs: {e}")
        return []


async def get_backend_logs(since_seconds: int, search_term: Optional[str]) -> List[Dict[str, Any]]:
    """Get logs from backend application"""
    # TODO: Implement backend log file reading
    # For now, return empty list
    return []


def detect_log_level(log_line: str) -> str:
    """Detect log level from log line content"""
    line_lower = log_line.lower()
    if any(word in line_lower for word in ["error", "exception", "failed", "critical"]):
        return "error"
    elif any(word in line_lower for word in ["warning", "warn"]):
        return "warning"
    elif any(word in line_lower for word in ["info", "started", "completed"]):
        return "info"
    elif "debug" in line_lower:
        return "debug"
    else:
        return "info"


# ===================================================================
# Tool Registry for MCP
# ===================================================================

ATLAS_TOOLS = {
    "system_status": {
        "name": "system_status",
        "description": "Check system health and service status across all Ops-Center components",
        "function": system_status,
        "input_schema": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "object",
                    "description": "Optional filters",
                    "properties": {
                        "services": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific services to check"
                        },
                        "include_metrics": {
                            "type": "boolean",
                            "description": "Include system metrics",
                            "default": True
                        },
                        "include_docker": {
                            "type": "boolean",
                            "description": "Include Docker status",
                            "default": True
                        }
                    }
                }
            }
        }
    },
    "manage_user": {
        "name": "manage_user",
        "description": "Create, update, delete, or list users in Ops-Center",
        "function": manage_user,
        "input_schema": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "delete", "list"],
                    "description": "Action to perform"
                },
                "user_data": {
                    "type": "object",
                    "description": "User data (username required for all, email/password for create)"
                }
            }
        }
    },
    "check_billing": {
        "name": "check_billing",
        "description": "View billing usage, costs, and subscription status",
        "function": check_billing,
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["current_user", "organization", "system"],
                    "description": "Billing scope",
                    "default": "current_user"
                },
                "user_id": {
                    "type": "string",
                    "description": "Specific user ID (admin only)"
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Time range",
                    "default": "month"
                }
            }
        }
    },
    "restart_service": {
        "name": "restart_service",
        "description": "Restart a Docker service (requires confirmation)",
        "function": restart_service,
        "input_schema": {
            "type": "object",
            "required": ["service_name", "confirmation"],
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to restart"
                },
                "confirmation": {
                    "type": "boolean",
                    "description": "Must be true to execute",
                    "default": False
                }
            }
        }
    },
    "query_logs": {
        "name": "query_logs",
        "description": "Search and analyze system logs",
        "function": query_logs,
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Log source",
                    "default": "all"
                },
                "level": {
                    "type": "string",
                    "enum": ["all", "error", "warning", "info", "debug"],
                    "description": "Log level filter",
                    "default": "all"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max entries to return",
                    "default": 100
                },
                "search_term": {
                    "type": "string",
                    "description": "Text to search for"
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["1h", "6h", "24h", "7d"],
                    "description": "Time range",
                    "default": "1h"
                }
            }
        }
    }
}


async def execute_atlas_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an Atlas tool by name
    
    Args:
        tool_name: Name of the tool to execute
        parameters: Tool parameters
    
    Returns:
        Tool execution result
    """
    if tool_name not in ATLAS_TOOLS:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}",
            "available_tools": list(ATLAS_TOOLS.keys())
        }
    
    tool = ATLAS_TOOLS[tool_name]
    try:
        result = await tool["function"](**parameters)
        return result
    except Exception as e:
        logger.error(f"Tool execution failed for {tool_name}: {e}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }
