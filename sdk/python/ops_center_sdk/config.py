"""
Plugin configuration management
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """
    Plugin configuration manager
    
    Loads configuration from:
    1. plugin.yaml (defaults)
    2. config.yaml (user overrides)
    3. Environment variables
    
    Example:
        ```python
        config = plugin.config
        
        # Get config value
        api_key = config.get("api_key")
        threshold = config.get("threshold", 0.85)
        
        # Update config
        config.set("threshold", 0.90)
        await config.save()
        
        # Get all config
        all_config = config.all()
        ```
    """
    
    def __init__(self, plugin_id: str, base_path: Path):
        self.plugin_id = plugin_id
        self.base_path = base_path
        
        self._config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from files"""
        # Load defaults from plugin.yaml
        plugin_yaml = self.base_path / "plugin.yaml"
        if plugin_yaml.exists():
            with open(plugin_yaml, 'r') as f:
                manifest = yaml.safe_load(f)
                
                # Extract default config from schema
                config_schema = manifest.get("config_schema", {})
                if "properties" in config_schema:
                    for key, schema in config_schema["properties"].items():
                        if "default" in schema:
                            self._defaults[key] = schema["default"]
        
        # Load user config from config.yaml
        config_yaml = self.base_path / "config.yaml"
        if config_yaml.exists():
            with open(config_yaml, 'r') as f:
                self._config = yaml.safe_load(f) or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
        
        Returns:
            Configuration value
        """
        # Check user config first
        if key in self._config:
            return self._config[key]
        
        # Fall back to defaults
        if key in self._defaults:
            return self._defaults[key]
        
        return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value
    
    def all(self) -> Dict[str, Any]:
        """
        Get all configuration
        
        Returns:
            Dictionary of all config values
        """
        # Merge defaults and user config
        return {**self._defaults, **self._config}
    
    async def save(self):
        """Save configuration to config.yaml"""
        config_yaml = self.base_path / "config.yaml"
        
        with open(config_yaml, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)
    
    def reload(self):
        """Reload configuration from files"""
        self._config.clear()
        self._defaults.clear()
        self._load_config()
