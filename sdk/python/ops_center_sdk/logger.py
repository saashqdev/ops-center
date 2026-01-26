"""
Logging utilities for plugins
"""

import logging
import sys
from typing import Optional


def get_logger(plugin_id: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get logger for plugin
    
    Args:
        plugin_id: Plugin ID
        level: Log level (defaults to INFO)
    
    Returns:
        Logger instance
    
    Example:
        ```python
        logger = get_logger("my-plugin")
        
        logger.info("Plugin started")
        logger.warning("Low disk space")
        logger.error("Failed to process data")
        ```
    """
    logger = logging.getLogger(f"ops_center.plugin.{plugin_id}")
    
    if level is not None:
        logger.setLevel(level)
    elif not logger.handlers:
        logger.setLevel(logging.INFO)
    
    # Add console handler if not already added
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
