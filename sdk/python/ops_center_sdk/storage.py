"""
Storage interface for plugins
"""

import json
import aiofiles
from pathlib import Path
from typing import Any, Optional


class Storage:
    """
    Plugin storage interface for persisting data
    
    Example:
        ```python
        storage = plugin.storage
        
        # Store data
        await storage.set("user:123:preferences", {"theme": "dark"})
        
        # Get data
        prefs = await storage.get("user:123:preferences")
        
        # Delete data
        await storage.delete("user:123:preferences")
        
        # List keys
        keys = await storage.list_keys("user:*")
        ```
    """
    
    def __init__(self, plugin_id: str, base_path: Path):
        self.plugin_id = plugin_id
        self.base_path = base_path / plugin_id
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for a key"""
        # Sanitize key for filesystem
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.base_path / f"{safe_key}.json"
    
    async def set(self, key: str, value: Any):
        """
        Store value for key
        
        Args:
            key: Storage key
            value: JSON-serializable value
        """
        file_path = self._get_file_path(key)
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(value, indent=2))
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value for key
        
        Args:
            key: Storage key
            default: Default value if key doesn't exist
        
        Returns:
            Stored value or default
        """
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return default
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception:
            return default
    
    async def delete(self, key: str):
        """
        Delete key
        
        Args:
            key: Storage key
        """
        file_path = self._get_file_path(key)
        
        if file_path.exists():
            file_path.unlink()
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Storage key
        
        Returns:
            True if key exists
        """
        file_path = self._get_file_path(key)
        return file_path.exists()
    
    async def list_keys(self, pattern: str = "*") -> list[str]:
        """
        List keys matching pattern
        
        Args:
            pattern: Glob pattern (e.g., "user:*")
        
        Returns:
            List of matching keys
        """
        # Simple implementation - list all .json files
        keys = []
        
        for file_path in self.base_path.glob("*.json"):
            # Convert filename back to key
            key = file_path.stem.replace("_", ":")
            keys.append(key)
        
        return keys
    
    async def clear(self):
        """Clear all stored data for this plugin"""
        for file_path in self.base_path.glob("*.json"):
            file_path.unlink()
