"""
Ops-Center Plugin SDK

Official Python SDK for building Ops-Center plugins.
"""

__version__ = "0.1.0"

from .plugin import Plugin
from .decorators import hook, route, filter_hook, on_install, on_enable, on_disable, on_uninstall
from .api_client import APIClient
from .storage import Storage
from .scheduler import Scheduler
from .config import Config
from .logger import get_logger

# Testing utilities
from .testing import (
    MockAPIClient,
    MockStorage,
    MockScheduler,
    MockConfig,
    MockLogger,
    create_test_plugin,
    trigger_hook,
    trigger_filter,
)

__all__ = [
    "Plugin",
    "hook",
    "route",
    "filter_hook",
    "on_install",
    "on_enable",
    "on_disable",
    "on_uninstall",
    "APIClient",
    "Storage",
    "Scheduler",
    "Config",
    "get_logger",
    # Testing
    "MockAPIClient",
    "MockStorage",
    "MockScheduler",
    "MockConfig",
    "MockLogger",
    "create_test_plugin",
    "trigger_hook",
    "trigger_filter",
]
