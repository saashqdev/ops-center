"""
Testing utilities for Ops-Center plugins

Provides test fixtures and helpers for plugin development
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime
import pytest


class MockAPIClient:
    """Mock API client for testing"""
    
    def __init__(self):
        self.devices = MockDevicesAPI()
        self.users = MockUsersAPI()
        self.organizations = MockOrganizationsAPI()
        self.webhooks = MockWebhooksAPI()
        self.alerts = MockAlertsAPI()
        
        self._requests = []
    
    async def request(self, method: str, endpoint: str, **kwargs):
        """Record all API requests for verification"""
        self._requests.append({
            "method": method,
            "endpoint": endpoint,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })
        return {"status": "ok"}
    
    def get_requests(self, method: Optional[str] = None, endpoint: Optional[str] = None):
        """Get recorded requests, optionally filtered"""
        requests = self._requests
        
        if method:
            requests = [r for r in requests if r["method"] == method]
        if endpoint:
            requests = [r for r in requests if endpoint in r["endpoint"]]
        
        return requests
    
    def reset(self):
        """Clear recorded requests"""
        self._requests = []


class MockDevicesAPI:
    """Mock devices API"""
    
    def __init__(self):
        self._devices = {}
    
    async def list(self, page: int = 1, page_size: int = 50, status: Optional[str] = None):
        devices = list(self._devices.values())
        if status:
            devices = [d for d in devices if d.get("status") == status]
        return devices
    
    async def get(self, device_id: str):
        return self._devices.get(device_id)
    
    async def create(self, data: Dict[str, Any]):
        device_id = data.get("id", f"device-{len(self._devices)}")
        device = {"id": device_id, **data}
        self._devices[device_id] = device
        return device
    
    async def update(self, device_id: str, data: Dict[str, Any]):
        if device_id in self._devices:
            self._devices[device_id].update(data)
            return self._devices[device_id]
        return None
    
    async def delete(self, device_id: str):
        if device_id in self._devices:
            del self._devices[device_id]
            return {"status": "deleted"}
        return None
    
    async def get_status(self, device_id: str):
        device = self._devices.get(device_id)
        if device:
            return {"status": device.get("status", "unknown")}
        return None


class MockUsersAPI:
    """Mock users API"""
    
    def __init__(self):
        self._users = {}
    
    async def list(self):
        return list(self._users.values())
    
    async def get(self, user_id: str):
        return self._users.get(user_id)
    
    async def create(self, data: Dict[str, Any]):
        user_id = data.get("id", f"user-{len(self._users)}")
        user = {"id": user_id, **data}
        self._users[user_id] = user
        return user
    
    async def update(self, user_id: str, data: Dict[str, Any]):
        if user_id in self._users:
            self._users[user_id].update(data)
            return self._users[user_id]
        return None


class MockOrganizationsAPI:
    """Mock organizations API"""
    
    def __init__(self):
        self._orgs = {}
    
    async def list(self):
        return list(self._orgs.values())
    
    async def get(self, org_id: str):
        return self._orgs.get(org_id)
    
    async def create(self, data: Dict[str, Any]):
        org_id = data.get("id", f"org-{len(self._orgs)}")
        org = {"id": org_id, **data}
        self._orgs[org_id] = org
        return org


class MockWebhooksAPI:
    """Mock webhooks API"""
    
    def __init__(self):
        self._webhooks = {}
    
    async def list(self):
        return list(self._webhooks.values())
    
    async def create(self, data: Dict[str, Any]):
        webhook_id = f"webhook-{len(self._webhooks)}"
        webhook = {"id": webhook_id, **data}
        self._webhooks[webhook_id] = webhook
        return webhook
    
    async def delete(self, webhook_id: str):
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return {"status": "deleted"}
        return None


class MockAlertsAPI:
    """Mock alerts API"""
    
    def __init__(self):
        self._alerts = {}
    
    async def list(self, severity: Optional[str] = None, status: Optional[str] = None):
        alerts = list(self._alerts.values())
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        if status:
            alerts = [a for a in alerts if a.get("status") == status]
        return alerts
    
    async def get(self, alert_id: str):
        return self._alerts.get(alert_id)
    
    async def create(self, data: Dict[str, Any]):
        alert_id = f"alert-{len(self._alerts)}"
        alert = {
            "id": alert_id,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            **data
        }
        self._alerts[alert_id] = alert
        return alert
    
    async def acknowledge(self, alert_id: str):
        if alert_id in self._alerts:
            self._alerts[alert_id]["status"] = "acknowledged"
            return self._alerts[alert_id]
        return None


class MockStorage:
    """Mock storage for testing"""
    
    def __init__(self):
        self._data = {}
    
    async def set(self, key: str, value: Any):
        self._data[key] = value
    
    async def get(self, key: str, default: Any = None):
        return self._data.get(key, default)
    
    async def delete(self, key: str):
        if key in self._data:
            del self._data[key]
    
    async def exists(self, key: str):
        return key in self._data
    
    async def list_keys(self, pattern: Optional[str] = None):
        keys = list(self._data.keys())
        if pattern:
            # Simple glob pattern matching
            import fnmatch
            keys = [k for k in keys if fnmatch.fnmatch(k, pattern)]
        return keys
    
    async def clear(self):
        self._data.clear()


class MockScheduler:
    """Mock scheduler for testing"""
    
    def __init__(self):
        self._tasks = {}
        self._task_counter = 0
    
    async def run_at(self, run_time: datetime, handler: Callable, **kwargs):
        task_id = f"task-{self._task_counter}"
        self._task_counter += 1
        
        self._tasks[task_id] = {
            "type": "run_at",
            "run_time": run_time,
            "handler": handler,
            "kwargs": kwargs
        }
        
        return task_id
    
    async def run_in(self, delay: float, handler: Callable, **kwargs):
        task_id = f"task-{self._task_counter}"
        self._task_counter += 1
        
        self._tasks[task_id] = {
            "type": "run_in",
            "delay": delay,
            "handler": handler,
            "kwargs": kwargs
        }
        
        return task_id
    
    async def schedule(self, cron: str, task_name: str, handler: Callable):
        self._tasks[task_name] = {
            "type": "cron",
            "cron": cron,
            "handler": handler
        }
        
        return task_name
    
    async def cancel(self, task_id: str):
        if task_id in self._tasks:
            del self._tasks[task_id]
    
    async def cancel_all(self):
        self._tasks.clear()
    
    def get_tasks(self):
        return list(self._tasks.values())
    
    async def trigger_task(self, task_id: str):
        """Manually trigger a task for testing"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            handler = task["handler"]
            kwargs = task.get("kwargs", {})
            
            if asyncio.iscoroutinefunction(handler):
                await handler(**kwargs)
            else:
                handler(**kwargs)


class MockConfig:
    """Mock config for testing"""
    
    def __init__(self, defaults: Optional[Dict[str, Any]] = None):
        self._config = defaults or {}
    
    def get(self, key: str, default: Any = None):
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        self._config[key] = value
    
    def all(self):
        return self._config.copy()
    
    async def save(self):
        pass  # No-op for testing
    
    async def reload(self):
        pass  # No-op for testing


class MockLogger:
    """Mock logger for testing"""
    
    def __init__(self, plugin_id: str = "test-plugin"):
        self.plugin_id = plugin_id
        self.logs = []
    
    def _log(self, level: str, message: str):
        self.logs.append({
            "level": level,
            "message": message,
            "timestamp": datetime.now()
        })
    
    def debug(self, message: str):
        self._log("DEBUG", message)
    
    def info(self, message: str):
        self._log("INFO", message)
    
    def warning(self, message: str):
        self._log("WARNING", message)
    
    def error(self, message: str):
        self._log("ERROR", message)
    
    def critical(self, message: str):
        self._log("CRITICAL", message)
    
    def get_logs(self, level: Optional[str] = None):
        """Get recorded logs, optionally filtered by level"""
        logs = self.logs
        if level:
            logs = [l for l in logs if l["level"] == level]
        return logs
    
    def clear(self):
        """Clear recorded logs"""
        self.logs.clear()


# ==================== Test Fixtures ====================

def create_test_plugin(plugin_id: str = "test-plugin", **kwargs):
    """
    Create a plugin instance with mock dependencies for testing
    
    Example:
        plugin = create_test_plugin("my-plugin")
        
        # Use mock API
        await plugin.api.devices.create({"name": "Test Device"})
        
        # Verify requests
        requests = plugin.api.get_requests()
    """
    from ops_center_sdk.plugin import Plugin, PluginMetadata
    
    metadata = PluginMetadata(
        id=plugin_id,
        name=kwargs.get("name", "Test Plugin"),
        version=kwargs.get("version", "1.0.0"),
        description=kwargs.get("description", "Test plugin"),
        author=kwargs.get("author", "Test Author"),
        category=kwargs.get("category", "monitoring")
    )
    
    plugin = Plugin.__new__(Plugin)
    plugin._metadata = metadata
    plugin._api = MockAPIClient()
    plugin._storage = MockStorage()
    plugin._scheduler = MockScheduler()
    plugin._config = MockConfig(kwargs.get("config", {}))
    plugin._logger = MockLogger(plugin_id)
    
    # Initialize registries
    plugin._hooks = {}
    plugin._filters = {}
    plugin._routes = []
    plugin._lifecycle_handlers = {}
    
    return plugin


async def trigger_hook(plugin, event: str, **kwargs):
    """
    Trigger a hook event for testing
    
    Example:
        await trigger_hook(plugin, "device.created", device_id="123", device_data={})
    """
    if event in plugin._hooks:
        for handler in sorted(plugin._hooks[event], key=lambda h: h["priority"], reverse=True):
            if asyncio.iscoroutinefunction(handler["handler"]):
                await handler["handler"](**kwargs)
            else:
                handler["handler"](**kwargs)


async def trigger_filter(plugin, filter_name: str, data: Any, **kwargs) -> Any:
    """
    Trigger a filter hook for testing
    
    Example:
        result = await trigger_filter(plugin, "device.data.process", {"id": "123"})
    """
    result = data
    
    if filter_name in plugin._filters:
        for handler in sorted(plugin._filters[filter_name], key=lambda h: h["priority"], reverse=True):
            if asyncio.iscoroutinefunction(handler["handler"]):
                result = await handler["handler"](result, **kwargs)
            else:
                result = handler["handler"](result, **kwargs)
    
    return result


# ==================== Pytest Fixtures ====================

try:
    @pytest.fixture
    def plugin():
        """Pytest fixture for plugin testing"""
        return create_test_plugin()
    
    @pytest.fixture
    def mock_api():
        """Pytest fixture for mock API client"""
        return MockAPIClient()
    
    @pytest.fixture
    def mock_storage():
        """Pytest fixture for mock storage"""
        return MockStorage()
    
    @pytest.fixture
    def mock_scheduler():
        """Pytest fixture for mock scheduler"""
        return MockScheduler()
    
except ImportError:
    # pytest not installed
    pass
