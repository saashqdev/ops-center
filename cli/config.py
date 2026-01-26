"""Configuration management for Ops-Center CLI"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages CLI configuration files"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager
        
        Args:
            config_path: Custom path to config file. If None, uses default location
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default: ~/.ops-center/config.yaml
            self.config_path = Path.home() / '.ops-center' / 'config.yaml'
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Returns:
            Configuration dictionary
        """
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise Exception(f"Failed to load config: {e}")
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
        """
        # Create directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            # Set restrictive permissions (owner read/write only)
            os.chmod(self.config_path, 0o600)
        except Exception as e:
            raise Exception(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        config = self.load_config()
        return config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Value to set
        """
        config = self.load_config()
        config[key] = value
        self.save_config(config)
    
    def delete(self, key: str) -> None:
        """
        Delete configuration key
        
        Args:
            key: Configuration key to delete
        """
        config = self.load_config()
        if key in config:
            del config[key]
            self.save_config(config)
