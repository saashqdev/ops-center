"""
Plugin Base Class

Core plugin class that handles lifecycle, hooks, routes, and integrations.
"""

import asyncio
import inspect
from typing import Dict, List, Any, Optional, Callable, Type
from pathlib import Path
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, Field

from .api_client import APIClient
from .storage import Storage
from .scheduler import Scheduler
from .config import Config
from .logger import get_logger
from .decorators import HookRegistry, RouteRegistry, LifecycleRegistry


class PluginMetadata(BaseModel):
    """Plugin metadata"""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    type: str = "backend"
    category: str = "other"


class Plugin:
    """
    Base Plugin class for Ops-Center plugins
    
    Example:
        ```python
        from ops_center_sdk import Plugin, hook, route
        
        plugin = Plugin(
            id="my-plugin",
            name="My Plugin",
            version="1.0.0"
        )
        
        @plugin.hook("device.created")
        async def on_device_created(device_id: str, device_data: dict):
            print(f"New device: {device_id}")
            return {"processed": True}
        
        @plugin.route("/predict", methods=["POST"])
        async def predict(request: dict):
            return {"prediction": "value"}
        
        # Export FastAPI app
        app = plugin.create_app()
        ```
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        description: str = "",
        author: str = "",
        type: str = "backend",
        category: str = "other",
        base_path: Optional[Path] = None
    ):
        self.metadata = PluginMetadata(
            id=id,
            name=name,
            version=version,
            description=description,
            author=author,
            type=type,
            category=category
        )
        
        self.base_path = base_path or Path.cwd()
        
        # Core components
        self._api_client: Optional[APIClient] = None
        self._storage: Optional[Storage] = None
        self._scheduler: Optional[Scheduler] = None
        self._config: Optional[Config] = None
        self._logger = get_logger(id)
        
        # Registries
        self._hooks: Dict[str, List[Callable]] = {}
        self._filters: Dict[str, List[Callable]] = {}
        self._routes: List[Dict[str, Any]] = []
        self._lifecycle_handlers: Dict[str, List[Callable]] = {
            "on_install": [],
            "on_enable": [],
            "on_disable": [],
            "on_uninstall": [],
            "on_config_change": [],
        }
        
        # FastAPI app
        self._app: Optional[FastAPI] = None
        self._router: Optional[APIRouter] = None
        
        # State
        self._initialized = False
        self._enabled = False
    
    @property
    def api(self) -> APIClient:
        """Access Ops-Center API"""
        if not self._api_client:
            self._api_client = APIClient(
                base_url=self.config.get("ops_center_api_url", "http://localhost:8000"),
                api_key=self.config.get("ops_center_api_key", "")
            )
        return self._api_client
    
    @property
    def storage(self) -> Storage:
        """Plugin storage interface"""
        if not self._storage:
            self._storage = Storage(
                plugin_id=self.metadata.id,
                base_path=self.base_path / "data"
            )
        return self._storage
    
    @property
    def scheduler(self) -> Scheduler:
        """Task scheduler"""
        if not self._scheduler:
            self._scheduler = Scheduler(plugin_id=self.metadata.id)
        return self._scheduler
    
    @property
    def config(self) -> Config:
        """Plugin configuration"""
        if not self._config:
            self._config = Config(
                plugin_id=self.metadata.id,
                base_path=self.base_path
            )
        return self._config
    
    @property
    def logger(self):
        """Plugin logger"""
        return self._logger
    
    # ==================== Decorators ====================
    
    def hook(self, event_name: str, priority: int = 10):
        """
        Register a hook handler for an event
        
        Args:
            event_name: Event to listen for (e.g., "device.created")
            priority: Lower priority runs first (default: 10)
        
        Example:
            ```python
            @plugin.hook("device.created")
            async def on_device_created(device_id: str, device_data: dict):
                print(f"Device created: {device_id}")
            ```
        """
        def decorator(func: Callable):
            if event_name not in self._hooks:
                self._hooks[event_name] = []
            
            # Store with priority for sorting
            self._hooks[event_name].append({
                "handler": func,
                "priority": priority,
                "name": func.__name__
            })
            
            # Sort by priority
            self._hooks[event_name].sort(key=lambda x: x["priority"])
            
            return func
        return decorator
    
    def filter_hook(self, filter_name: str, priority: int = 10):
        """
        Register a filter hook that can modify data
        
        Args:
            filter_name: Filter to apply (e.g., "device.data.process")
            priority: Lower priority runs first
        
        Example:
            ```python
            @plugin.filter_hook("device.data.process")
            async def process_device_data(data: dict) -> dict:
                data["enhanced"] = True
                return data
            ```
        """
        def decorator(func: Callable):
            if filter_name not in self._filters:
                self._filters[filter_name] = []
            
            self._filters[filter_name].append({
                "handler": func,
                "priority": priority,
                "name": func.__name__
            })
            
            self._filters[filter_name].sort(key=lambda x: x["priority"])
            
            return func
        return decorator
    
    def route(self, path: str, methods: List[str] = ["GET"], **kwargs):
        """
        Register a custom API route
        
        Args:
            path: Route path (will be prefixed with /plugins/{plugin_id})
            methods: HTTP methods (default: ["GET"])
            **kwargs: Additional route configuration
        
        Example:
            ```python
            @plugin.route("/predict", methods=["POST"])
            async def predict_endpoint(request: dict):
                return {"prediction": "value"}
            ```
        """
        def decorator(func: Callable):
            self._routes.append({
                "path": path,
                "methods": methods,
                "handler": func,
                "name": func.__name__,
                **kwargs
            })
            return func
        return decorator
    
    def on_install(self, func: Callable):
        """Run when plugin is first installed"""
        self._lifecycle_handlers["on_install"].append(func)
        return func
    
    def on_enable(self, func: Callable):
        """Run when plugin is enabled"""
        self._lifecycle_handlers["on_enable"].append(func)
        return func
    
    def on_disable(self, func: Callable):
        """Run when plugin is disabled"""
        self._lifecycle_handlers["on_disable"].append(func)
        return func
    
    def on_uninstall(self, func: Callable):
        """Run before plugin is uninstalled"""
        self._lifecycle_handlers["on_uninstall"].append(func)
        return func
    
    def on_config_change(self, func: Callable):
        """Run when configuration changes"""
        self._lifecycle_handlers["on_config_change"].append(func)
        return func
    
    # ==================== Event Handling ====================
    
    async def emit(self, event_name: str, **event_data):
        """
        Emit an event to trigger hooks
        
        Args:
            event_name: Event name
            **event_data: Event data as kwargs
        """
        if event_name not in self._hooks:
            return
        
        for hook_def in self._hooks[event_name]:
            handler = hook_def["handler"]
            
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(**event_data)
                else:
                    handler(**event_data)
            except Exception as e:
                self.logger.error(f"Error in hook {hook_def['name']}: {e}")
    
    async def apply_filter(self, filter_name: str, data: Any) -> Any:
        """
        Apply filter hooks to transform data
        
        Args:
            filter_name: Filter name
            data: Data to transform
        
        Returns:
            Transformed data
        """
        if filter_name not in self._filters:
            return data
        
        result = data
        
        for filter_def in self._filters[filter_name]:
            handler = filter_def["handler"]
            
            try:
                if inspect.iscoroutinefunction(handler):
                    result = await handler(result)
                else:
                    result = handler(result)
            except Exception as e:
                self.logger.error(f"Error in filter {filter_def['name']}: {e}")
        
        return result
    
    # ==================== Lifecycle Methods ====================
    
    async def _run_lifecycle_hook(self, hook_name: str, **kwargs):
        """Run lifecycle hook handlers"""
        if hook_name not in self._lifecycle_handlers:
            return
        
        for handler in self._lifecycle_handlers[hook_name]:
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception as e:
                self.logger.error(f"Error in lifecycle hook {hook_name}: {e}")
    
    async def install(self):
        """Called when plugin is installed"""
        await self._run_lifecycle_hook("on_install")
        self.logger.info(f"Plugin {self.metadata.name} installed")
    
    async def enable(self):
        """Called when plugin is enabled"""
        await self._run_lifecycle_hook("on_enable")
        self._enabled = True
        self.logger.info(f"Plugin {self.metadata.name} enabled")
    
    async def disable(self):
        """Called when plugin is disabled"""
        await self._run_lifecycle_hook("on_disable")
        self._enabled = False
        self.logger.info(f"Plugin {self.metadata.name} disabled")
    
    async def uninstall(self):
        """Called before plugin is uninstalled"""
        await self._run_lifecycle_hook("on_uninstall")
        self.logger.info(f"Plugin {self.metadata.name} uninstalled")
    
    async def config_changed(self, old_config: dict, new_config: dict):
        """Called when configuration changes"""
        await self._run_lifecycle_hook(
            "on_config_change",
            old_config=old_config,
            new_config=new_config
        )
        self.logger.info("Plugin configuration updated")
    
    # ==================== FastAPI Integration ====================
    
    def create_app(self) -> FastAPI:
        """
        Create FastAPI application for the plugin
        
        Returns:
            FastAPI app instance
        """
        if self._app:
            return self._app
        
        app = FastAPI(
            title=self.metadata.name,
            description=self.metadata.description,
            version=self.metadata.version,
        )
        
        # Create router with plugin prefix
        router = APIRouter(prefix=f"/plugins/{self.metadata.id}")
        
        # Register routes
        for route_def in self._routes:
            for method in route_def["methods"]:
                router.add_api_route(
                    path=route_def["path"],
                    endpoint=route_def["handler"],
                    methods=[method],
                    name=route_def.get("name"),
                    **{k: v for k, v in route_def.items() 
                       if k not in ["path", "methods", "handler", "name"]}
                )
        
        app.include_router(router)
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "plugin": self.metadata.id,
                "version": self.metadata.version,
                "enabled": self._enabled
            }
        
        self._app = app
        self._router = router
        
        return app
    
    def get_manifest(self) -> dict:
        """
        Generate plugin manifest
        
        Returns:
            Plugin manifest dictionary
        """
        return {
            "id": self.metadata.id,
            "name": self.metadata.name,
            "version": self.metadata.version,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "type": self.metadata.type,
            "category": self.metadata.category,
            "hooks": [
                {
                    "name": hook_name,
                    "handlers": [h["name"] for h in handlers]
                }
                for hook_name, handlers in self._hooks.items()
            ],
            "routes": [
                {
                    "path": f"/plugins/{self.metadata.id}{r['path']}",
                    "methods": r["methods"]
                }
                for r in self._routes
            ],
            "filters": list(self._filters.keys()),
        }
