"""
Decorator utilities for plugin development
"""

import functools
from typing import Callable, List

# Global registries for decorators used outside Plugin class
HookRegistry = {}
RouteRegistry = []
LifecycleRegistry = {
    "on_install": [],
    "on_enable": [],
    "on_disable": [],
    "on_uninstall": [],
}


def hook(event_name: str, priority: int = 10):
    """
    Standalone hook decorator
    
    Example:
        ```python
        from ops_center_sdk import hook
        
        @hook("device.created")
        async def on_device_created(device_id: str):
            print(f"Device: {device_id}")
        ```
    """
    def decorator(func: Callable):
        if event_name not in HookRegistry:
            HookRegistry[event_name] = []
        
        HookRegistry[event_name].append({
            "handler": func,
            "priority": priority,
            "name": func.__name__
        })
        
        return func
    return decorator


def filter_hook(filter_name: str, priority: int = 10):
    """
    Standalone filter hook decorator
    """
    def decorator(func: Callable):
        # Similar to hook but for filters
        return func
    return decorator


def route(path: str, methods: List[str] = ["GET"], **kwargs):
    """
    Standalone route decorator
    
    Example:
        ```python
        from ops_center_sdk import route
        
        @route("/predict", methods=["POST"])
        async def predict(data: dict):
            return {"result": "value"}
        ```
    """
    def decorator(func: Callable):
        RouteRegistry.append({
            "path": path,
            "methods": methods,
            "handler": func,
            "name": func.__name__,
            **kwargs
        })
        return func
    return decorator


def on_install(func: Callable):
    """Lifecycle: on install"""
    LifecycleRegistry["on_install"].append(func)
    return func


def on_enable(func: Callable):
    """Lifecycle: on enable"""
    LifecycleRegistry["on_enable"].append(func)
    return func


def on_disable(func: Callable):
    """Lifecycle: on disable"""
    LifecycleRegistry["on_disable"].append(func)
    return func


def on_uninstall(func: Callable):
    """Lifecycle: on uninstall"""
    LifecycleRegistry["on_uninstall"].append(func)
    return func
