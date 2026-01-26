"""
Tool Executor Framework

Manages tool discovery, validation, execution, and result formatting for The Colonel.
"""

from typing import Dict, Any, List, Optional, Callable
from uuid import UUID
from datetime import datetime
import asyncio
import inspect
from fastapi import HTTPException

from backend.database import get_db_session


class Tool:
    """
    Represents a single tool available to The Colonel.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
        requires_approval: bool = False,
        allowed_roles: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.requires_approval = requires_approval
        self.allowed_roles = allowed_roles or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Claude/OpenAI tool format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }
    
    async def execute(self, input_params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Execute the tool handler.
        
        Args:
            input_params: Tool input parameters
            context: Execution context (user, organization, etc.)
        
        Returns:
            Tool execution result
        """
        # Check if handler is async
        if inspect.iscoroutinefunction(self.handler):
            return await self.handler(input_params, context)
        else:
            return self.handler(input_params, context)
    
    def validate_input(self, input_params: Dict[str, Any]) -> Optional[str]:
        """
        Validate input parameters against schema.
        
        Returns:
            Error message if validation fails, None if valid
        """
        required = self.input_schema.get("required", [])
        properties = self.input_schema.get("properties", {})
        
        # Check required fields
        for field in required:
            if field not in input_params:
                return f"Missing required field: {field}"
        
        # Check field types
        for field, value in input_params.items():
            if field not in properties:
                return f"Unknown field: {field}"
            
            expected_type = properties[field].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return f"Field {field} must be a string"
            elif expected_type == "integer" and not isinstance(value, int):
                return f"Field {field} must be an integer"
            elif expected_type == "boolean" and not isinstance(value, bool):
                return f"Field {field} must be a boolean"
            elif expected_type == "array" and not isinstance(value, list):
                return f"Field {field} must be an array"
            elif expected_type == "object" and not isinstance(value, dict):
                return f"Field {field} must be an object"
        
        return None


class ToolExecutor:
    """
    Manages tool registration, discovery, and execution.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_core_tools()
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions in Claude/OpenAI format"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self.tools.keys())
    
    async def execute_tool(
        self,
        conversation_id: UUID,
        tool_name: str,
        tool_input: Dict[str, Any],
        user_id: UUID,
        message_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool and log the execution.
        
        Args:
            conversation_id: Conversation UUID
            tool_name: Name of tool to execute
            tool_input: Input parameters for tool
            user_id: User executing tool
            message_id: Optional message ID
        
        Returns:
            Execution result with status, output, and metadata
        """
        start_time = datetime.now()
        
        # Get tool
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "status": "error",
                "error": f"Tool not found: {tool_name}",
                "execution_time_ms": 0
            }
        
        # Validate input
        validation_error = tool.validate_input(tool_input)
        if validation_error:
            return {
                "status": "error",
                "error": f"Invalid input: {validation_error}",
                "execution_time_ms": 0
            }
        
        # Build execution context
        context = await self._build_execution_context(user_id)
        
        # Check permissions
        if not self._check_permission(tool, context):
            return {
                "status": "error",
                "error": "Permission denied",
                "execution_time_ms": 0
            }
        
        # Execute tool
        try:
            output = await tool.execute(tool_input, context)
            status = "success"
            error = None
        except Exception as e:
            output = None
            status = "error"
            error = str(e)
        
        # Calculate execution time
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log execution to database
        await self._log_tool_execution(
            message_id=message_id,
            conversation_id=conversation_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=output,
            status=status,
            error_message=error,
            execution_time_ms=execution_time_ms,
            requires_approval=tool.requires_approval
        )
        
        return {
            "status": status,
            "output": output,
            "error": error,
            "execution_time_ms": execution_time_ms
        }
    
    async def _build_execution_context(self, user_id: UUID) -> Dict[str, Any]:
        """Build execution context with user info"""
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT u.id, u.email, u.name, u.role, u.organization_id,
                       o.name as organization_name
                FROM users u
                LEFT JOIN organizations o ON u.organization_id = o.id
                WHERE u.id = $1
                """,
                user_id
            )
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "user_id": row[0],
                "user_email": row[1],
                "user_name": row[2],
                "user_role": row[3],
                "organization_id": row[4],
                "organization_name": row[5]
            }
    
    def _check_permission(self, tool: Tool, context: Dict[str, Any]) -> bool:
        """Check if user has permission to execute tool"""
        # If tool has no role restrictions, allow all
        if not tool.allowed_roles:
            return True
        
        # Check if user's role is in allowed list
        user_role = context.get("user_role")
        return user_role in tool.allowed_roles
    
    async def _log_tool_execution(
        self,
        message_id: Optional[UUID],
        conversation_id: UUID,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        status: str,
        error_message: Optional[str],
        execution_time_ms: int,
        requires_approval: bool
    ):
        """Log tool execution to database"""
        import json
        
        async with get_db_session() as db:
            await db.execute(
                """
                INSERT INTO colonel_tool_executions
                (message_id, conversation_id, tool_name, tool_input, tool_output,
                 execution_time_ms, status, error_message, requires_approval)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                message_id, conversation_id, tool_name,
                json.dumps(tool_input),
                json.dumps(tool_output) if tool_output is not None else None,
                execution_time_ms, status, error_message, requires_approval
            )
            await db.commit()
    
    # ==================== Core Tool Registration ====================
    
    def _register_core_tools(self):
        """Register all core tools"""
        
        # Device tools
        self.register_tool(Tool(
            name="get_devices",
            description="List devices with optional filtering by status, type, or organization",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["online", "offline", "warning", "error"],
                        "description": "Filter by device status"
                    },
                    "type": {
                        "type": "string",
                        "description": "Filter by device type"
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "Filter by organization UUID"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum devices to return (default 50, max 1000)"
                    }
                }
            },
            handler=self._handle_get_devices
        ))
        
        self.register_tool(Tool(
            name="get_device_details",
            description="Get detailed information about a specific device",
            input_schema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device UUID"
                    }
                },
                "required": ["device_id"]
            },
            handler=self._handle_get_device_details
        ))
        
        self.register_tool(Tool(
            name="get_device_metrics",
            description="Get current or historical metrics for a device",
            input_schema={
                "type": "object",
                "properties": {
                    "device_id": {
                        "type": "string",
                        "description": "Device UUID"
                    },
                    "metric_type": {
                        "type": "string",
                        "enum": ["cpu", "memory", "network", "disk", "all"],
                        "description": "Type of metrics to retrieve"
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["1h", "6h", "24h", "7d", "30d"],
                        "description": "Time range for historical metrics"
                    }
                },
                "required": ["device_id"]
            },
            handler=self._handle_get_device_metrics
        ))
        
        # Alert tools
        self.register_tool(Tool(
            name="get_alerts",
            description="List alerts with optional filtering by severity, status, or device",
            input_schema={
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["info", "warning", "error", "critical"],
                        "description": "Filter by alert severity"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "acknowledged", "resolved"],
                        "description": "Filter by alert status"
                    },
                    "device_id": {
                        "type": "string",
                        "description": "Filter by device UUID"
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["1h", "6h", "24h", "7d", "30d"],
                        "description": "Time range filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum alerts to return"
                    }
                }
            },
            handler=self._handle_get_alerts
        ))
        
        self.register_tool(Tool(
            name="get_alert_details",
            description="Get detailed information about a specific alert",
            input_schema={
                "type": "object",
                "properties": {
                    "alert_id": {
                        "type": "string",
                        "description": "Alert UUID"
                    }
                },
                "required": ["alert_id"]
            },
            handler=self._handle_get_alert_details
        ))
        
        # User & Organization tools
        self.register_tool(Tool(
            name="get_users",
            description="List users (respects RBAC permissions)",
            input_schema={
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "Filter by organization UUID"
                    },
                    "role": {
                        "type": "string",
                        "description": "Filter by role"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "suspended"],
                        "description": "Filter by status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum users to return"
                    }
                }
            },
            handler=self._handle_get_users,
            allowed_roles=["admin", "org_admin"]
        ))
        
        self.register_tool(Tool(
            name="get_organizations",
            description="List organizations (admin only)",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum organizations to return"
                    }
                }
            },
            handler=self._handle_get_organizations,
            allowed_roles=["admin"]
        ))
        
        # Analytics tools
        self.register_tool(Tool(
            name="get_usage_statistics",
            description="Get usage statistics for API calls, tokens, and costs",
            input_schema={
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "Filter by organization UUID"
                    },
                    "time_range": {
                        "type": "string",
                        "enum": ["1h", "24h", "7d", "30d"],
                        "description": "Time range for statistics"
                    },
                    "group_by": {
                        "type": "string",
                        "enum": ["hour", "day", "model", "user"],
                        "description": "Group results by time or dimension"
                    }
                }
            },
            handler=self._handle_get_usage_statistics
        ))
        
        self.register_tool(Tool(
            name="search",
            description="Search across devices, alerts, and system logs",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "scope": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["devices", "alerts", "users", "logs"]
                        },
                        "description": "Search scope"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search
        ))
    
    # ==================== Tool Handlers ====================
    
    async def _handle_get_devices(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_devices tool"""
        status = params.get("status")
        device_type = params.get("type")
        org_id = params.get("organization_id") or context.get("organization_id")
        limit = min(params.get("limit", 50), 1000)
        
        async with get_db_session() as db:
            # Build query
            conditions = []
            query_params = []
            param_count = 1
            
            if status:
                conditions.append(f"status = ${param_count}")
                query_params.append(status)
                param_count += 1
            
            if device_type:
                conditions.append(f"type = ${param_count}")
                query_params.append(device_type)
                param_count += 1
            
            if org_id:
                conditions.append(f"organization_id = ${param_count}")
                query_params.append(org_id)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query_params.append(limit)
            
            result = await db.execute(
                f"""
                SELECT id, name, type, status, last_seen, metadata
                FROM devices
                WHERE {where_clause}
                ORDER BY last_seen DESC NULLS LAST
                LIMIT ${param_count}
                """,
                *query_params
            )
            rows = result.fetchall()
            
            return {
                "devices": [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "type": row[2],
                        "status": row[3],
                        "last_seen": row[4].isoformat() if row[4] else None,
                        "metadata": row[5]
                    }
                    for row in rows
                ],
                "total": len(rows)
            }
    
    async def _handle_get_device_details(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_device_details tool"""
        device_id = params["device_id"]
        
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, name, type, status, ip_address, last_seen,
                       configuration, metadata, created_at
                FROM devices
                WHERE id = $1
                """,
                UUID(device_id)
            )
            row = result.fetchone()
            
            if not row:
                return {"error": "Device not found"}
            
            return {
                "id": str(row[0]),
                "name": row[1],
                "type": row[2],
                "status": row[3],
                "ip_address": row[4],
                "last_seen": row[5].isoformat() if row[5] else None,
                "configuration": row[6],
                "metadata": row[7],
                "created_at": row[8].isoformat()
            }
    
    async def _handle_get_device_metrics(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_device_metrics tool"""
        # Placeholder - would query metrics table
        return {
            "device_id": params["device_id"],
            "metric_type": params.get("metric_type", "all"),
            "time_range": params.get("time_range", "1h"),
            "metrics": {
                "cpu_usage": 45.2,
                "memory_usage": 68.5,
                "network_bytes_in": 1024000,
                "network_bytes_out": 512000
            }
        }
    
    async def _handle_get_alerts(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_alerts tool"""
        from datetime import datetime, timedelta
        
        severity = params.get("severity")
        status = params.get("status")
        device_id = params.get("device_id")
        time_range = params.get("time_range", "24h")
        limit = min(params.get("limit", 50), 1000)
        
        # Parse time range
        time_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168, "30d": 720}
        hours = time_map.get(time_range, 24)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        async with get_db_session() as db:
            conditions = ["created_at >= $1"]
            query_params = [cutoff_time]
            param_count = 2
            
            if severity:
                conditions.append(f"severity = ${param_count}")
                query_params.append(severity)
                param_count += 1
            
            if status:
                conditions.append(f"status = ${param_count}")
                query_params.append(status)
                param_count += 1
            
            if device_id:
                conditions.append(f"device_id = ${param_count}")
                query_params.append(UUID(device_id))
                param_count += 1
            
            # Filter by user's organization
            if context.get("organization_id"):
                conditions.append(f"organization_id = ${param_count}")
                query_params.append(context["organization_id"])
                param_count += 1
            
            where_clause = " AND ".join(conditions)
            query_params.append(limit)
            
            result = await db.execute(
                f"""
                SELECT id, title, message, severity, status, device_id, 
                       created_at, acknowledged_at, resolved_at
                FROM alerts
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count}
                """,
                *query_params
            )
            rows = result.fetchall()
            
            return {
                "alerts": [
                    {
                        "id": str(row[0]),
                        "title": row[1],
                        "message": row[2],
                        "severity": row[3],
                        "status": row[4],
                        "device_id": str(row[5]) if row[5] else None,
                        "created_at": row[6].isoformat(),
                        "acknowledged_at": row[7].isoformat() if row[7] else None,
                        "resolved_at": row[8].isoformat() if row[8] else None
                    }
                    for row in rows
                ],
                "total": len(rows),
                "time_range": time_range
            }
    
    async def _handle_get_alert_details(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_alert_details tool"""
        alert_id = params["alert_id"]
        
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, title, message, severity, status, device_id,
                       created_by, organization_id, metadata,
                       created_at, acknowledged_at, acknowledged_by,
                       resolved_at, resolved_by
                FROM alerts
                WHERE id = $1
                """,
                UUID(alert_id)
            )
            row = result.fetchone()
            
            if not row:
                return {"error": "Alert not found"}
            
            # Check organization access
            if row[7] and row[7] != context.get("organization_id"):
                return {"error": "Access denied"}
            
            return {
                "id": str(row[0]),
                "title": row[1],
                "message": row[2],
                "severity": row[3],
                "status": row[4],
                "device_id": str(row[5]) if row[5] else None,
                "created_by": str(row[6]) if row[6] else None,
                "organization_id": str(row[7]) if row[7] else None,
                "metadata": row[8],
                "created_at": row[9].isoformat(),
                "acknowledged_at": row[10].isoformat() if row[10] else None,
                "acknowledged_by": str(row[11]) if row[11] else None,
                "resolved_at": row[12].isoformat() if row[12] else None,
                "resolved_by": str(row[13]) if row[13] else None
            }
    
    async def _handle_get_users(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_users tool"""
        org_id = params.get("organization_id") or context.get("organization_id")
        role = params.get("role")
        status = params.get("status")
        limit = min(params.get("limit", 50), 500)
        
        async with get_db_session() as db:
            conditions = []
            query_params = []
            param_count = 1
            
            if org_id:
                conditions.append(f"organization_id = ${param_count}")
                query_params.append(UUID(org_id))
                param_count += 1
            
            if role:
                conditions.append(f"role = ${param_count}")
                query_params.append(role)
                param_count += 1
            
            if status:
                conditions.append(f"status = ${param_count}")
                query_params.append(status)
                param_count += 1
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query_params.append(limit)
            
            result = await db.execute(
                f"""
                SELECT id, email, name, role, status, organization_id, 
                       created_at, last_login
                FROM users
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count}
                """,
                *query_params
            )
            rows = result.fetchall()
            
            return {
                "users": [
                    {
                        "id": str(row[0]),
                        "email": row[1],
                        "name": row[2],
                        "role": row[3],
                        "status": row[4],
                        "organization_id": str(row[5]) if row[5] else None,
                        "created_at": row[6].isoformat(),
                        "last_login": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ],
                "total": len(rows)
            }
    
    async def _handle_get_organizations(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_organizations tool"""
        limit = min(params.get("limit", 50), 500)
        
        async with get_db_session() as db:
            result = await db.execute(
                """
                SELECT id, name, plan_tier, status, created_at,
                       (SELECT COUNT(*) FROM users WHERE organization_id = organizations.id) as user_count,
                       (SELECT COUNT(*) FROM devices WHERE organization_id = organizations.id) as device_count
                FROM organizations
                ORDER BY created_at DESC
                LIMIT $1
                """,
                limit
            )
            rows = result.fetchall()
            
            return {
                "organizations": [
                    {
                        "id": str(row[0]),
                        "name": row[1],
                        "plan_tier": row[2],
                        "status": row[3],
                        "created_at": row[4].isoformat(),
                        "user_count": row[5],
                        "device_count": row[6]
                    }
                    for row in rows
                ],
                "total": len(rows)
            }
    
    async def _handle_get_usage_statistics(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for get_usage_statistics tool"""
        from datetime import datetime, timedelta
        
        org_id = params.get("organization_id") or context.get("organization_id")
        time_range = params.get("time_range", "24h")
        group_by = params.get("group_by", "day")
        
        # Parse time range
        time_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
        hours = time_map.get(time_range, 24)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        async with get_db_session() as db:
            # Get API usage stats
            conditions = ["created_at >= $1"]
            query_params = [cutoff_time]
            param_count = 2
            
            if org_id:
                conditions.append(f"organization_id = ${param_count}")
                query_params.append(UUID(org_id))
                param_count += 1
            
            where_clause = " AND ".join(conditions)
            
            # Total stats
            result = await db.execute(
                f"""
                SELECT 
                    COUNT(*) as total_calls,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost), 0) as total_cost
                FROM api_usage_logs
                WHERE {where_clause}
                """,
                *query_params
            )
            stats_row = result.fetchone()
            
            # Group by stats
            if group_by == "model":
                result = await db.execute(
                    f"""
                    SELECT model_name, COUNT(*) as calls, 
                           SUM(input_tokens) + SUM(output_tokens) as tokens,
                           SUM(cost) as cost
                    FROM api_usage_logs
                    WHERE {where_clause}
                    GROUP BY model_name
                    ORDER BY calls DESC
                    LIMIT 10
                    """,
                    *query_params
                )
                grouped_rows = result.fetchall()
                grouped_data = [
                    {
                        "model": row[0],
                        "calls": row[1],
                        "tokens": row[2],
                        "cost": float(row[3]) if row[3] else 0
                    }
                    for row in grouped_rows
                ]
            elif group_by == "user":
                result = await db.execute(
                    f"""
                    SELECT u.email, COUNT(*) as calls,
                           SUM(l.input_tokens) + SUM(l.output_tokens) as tokens,
                           SUM(l.cost) as cost
                    FROM api_usage_logs l
                    JOIN users u ON l.user_id = u.id
                    WHERE {where_clause}
                    GROUP BY u.email
                    ORDER BY calls DESC
                    LIMIT 10
                    """,
                    *query_params
                )
                grouped_rows = result.fetchall()
                grouped_data = [
                    {
                        "user": row[0],
                        "calls": row[1],
                        "tokens": row[2],
                        "cost": float(row[3]) if row[3] else 0
                    }
                    for row in grouped_rows
                ]
            else:
                grouped_data = []
            
            return {
                "time_range": time_range,
                "total_api_calls": stats_row[0],
                "total_input_tokens": stats_row[1],
                "total_output_tokens": stats_row[2],
                "total_tokens": stats_row[1] + stats_row[2],
                "estimated_cost": float(stats_row[3]) if stats_row[3] else 0,
                "group_by": group_by,
                "grouped_data": grouped_data
            }
    
    async def _handle_search(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler for search tool"""
        query = params["query"]
        scope = params.get("scope", ["devices", "alerts"])
        limit = min(params.get("limit", 20), 100)
        
        results = []
        
        async with get_db_session() as db:
            # Search devices
            if "devices" in scope:
                result = await db.execute(
                    """
                    SELECT id, name, type, status, 'device' as result_type
                    FROM devices
                    WHERE name ILIKE $1 OR type ILIKE $1 OR CAST(metadata AS TEXT) ILIKE $1
                    LIMIT $2
                    """,
                    f"%{query}%",
                    limit
                )
                rows = result.fetchall()
                results.extend([
                    {
                        "type": "device",
                        "id": str(row[0]),
                        "name": row[1],
                        "device_type": row[2],
                        "status": row[3]
                    }
                    for row in rows
                ])
            
            # Search alerts
            if "alerts" in scope:
                result = await db.execute(
                    """
                    SELECT id, title, severity, status, 'alert' as result_type
                    FROM alerts
                    WHERE title ILIKE $1 OR message ILIKE $1
                    LIMIT $2
                    """,
                    f"%{query}%",
                    limit
                )
                rows = result.fetchall()
                results.extend([
                    {
                        "type": "alert",
                        "id": str(row[0]),
                        "title": row[1],
                        "severity": row[2],
                        "status": row[3]
                    }
                    for row in rows
                ])
            
            # Search users
            if "users" in scope and context.get("user_role") in ["admin", "org_admin"]:
                result = await db.execute(
                    """
                    SELECT id, email, name, role, 'user' as result_type
                    FROM users
                    WHERE email ILIKE $1 OR name ILIKE $1
                    LIMIT $2
                    """,
                    f"%{query}%",
                    limit
                )
                rows = result.fetchall()
                results.extend([
                    {
                        "type": "user",
                        "id": str(row[0]),
                        "email": row[1],
                        "name": row[2],
                        "role": row[3]
                    }
                    for row in rows
                ])
        
        return {
            "query": query,
            "scope": scope,
            "results": results[:limit],
            "total": len(results)
        }


# Global tool executor instance
tool_executor = ToolExecutor()
