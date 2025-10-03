"""Plugin system for AI service providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, List
import pkg_resources
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PluginInfo:
    """Information about a plugin."""
    name: str
    version: str
    description: str
    author: str
    requirements: List[str]
    config_schema: Dict[str, Any]

class AIPlugin(ABC):
    """Base class for AI service plugins."""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """Get information about the plugin."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the plugin with configuration."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration and return list of errors."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass

class PluginManager:
    """Manages AI service plugins."""
    
    def __init__(self):
        self._plugins: Dict[str, Type[AIPlugin]] = {}
        self._instances: Dict[str, AIPlugin] = {}
        self._discover_plugins()
    
    def _discover_plugins(self):
        """Discover available plugins."""
        for entry_point in pkg_resources.iter_entry_points('videosplitter.plugins'):
            try:
                plugin_class = entry_point.load()
                if issubclass(plugin_class, AIPlugin):
                    self._plugins[entry_point.name] = plugin_class
                    logger.info(f"Discovered plugin: {entry_point.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {entry_point.name}: {e}")
    
    def get_available_plugins(self) -> Dict[str, PluginInfo]:
        """Get information about all available plugins."""
        plugins = {}
        for name, plugin_class in self._plugins.items():
            try:
                instance = plugin_class()
                plugins[name] = instance.get_info()
            except Exception as e:
                logger.error(f"Failed to get info for plugin {name}: {e}")
        return plugins
    
    def initialize_plugin(self, name: str, config: Dict[str, Any]) -> AIPlugin:
        """Initialize a plugin with configuration."""
        if name not in self._plugins:
            raise ValueError(f"Plugin {name} not found")
            
        plugin_class = self._plugins[name]
        instance = plugin_class()
        
        # Validate configuration
        errors = instance.validate_config(config)
        if errors:
            raise ValueError(f"Invalid configuration for plugin {name}: {', '.join(errors)}")
        
        # Initialize plugin
        instance.initialize(config)
        self._instances[name] = instance
        return instance
    
    def get_plugin(self, name: str) -> AIPlugin:
        """Get an initialized plugin instance."""
        if name not in self._instances:
            raise ValueError(f"Plugin {name} not initialized")
        return self._instances[name]
    
    def cleanup(self):
        """Clean up all plugin instances."""
        for name, instance in self._instances.items():
            try:
                instance.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin {name}: {e}")
        self._instances.clear()