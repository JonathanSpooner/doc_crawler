"""
Runtime configuration management.

This module provides thread-safe configuration management with support for
hot reloading, runtime updates, and configuration change notifications.
"""

import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from doc_crawler.config.exceptions import ConfigurationError, ConfigurationUpdateError
from doc_crawler.config.loader import ConfigurationLoader
from doc_crawler.config.models import BaseConfiguration, Environment
from doc_crawler.config.validator import ConfigurationValidator

logger = logging.getLogger(__name__)


class ConfigurationChangeHandler(FileSystemEventHandler):
    """File system event handler for configuration changes."""
    
    def __init__(self, manager: 'ConfigurationManager'):
        """Initialize the change handler.
        
        Args:
            manager: Configuration manager instance
        """
        self.manager = manager
        self.last_reload = {}  # Track last reload time per file
        self.debounce_seconds = 2.0  # Debounce file changes
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only handle YAML files in config directories
        if file_path.suffix not in ['.yaml', '.yml']:
            return
        
        # Debounce rapid file changes
        now = time.time()
        last_time = self.last_reload.get(event.src_path, 0)
        if now - last_time < self.debounce_seconds:
            return
        
        self.last_reload[event.src_path] = now
        
        logger.info(f"Configuration file changed: {file_path}")
        
        # Trigger async reload
        try:
            asyncio.create_task(self.manager._handle_config_change(file_path))
        except RuntimeError:
            # No event loop running, schedule for next loop
            self.manager._schedule_reload()


class ConfigurationManager:
    """
    Thread-safe configuration manager with hot reloading support.
    
    This class provides a singleton interface for accessing configuration
    throughout the application, with support for runtime updates and
    change notifications.
    """
    
    _instance: Optional['ConfigurationManager'] = None
    _lock = threading.RLock()
    
    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        config_dir: Path = Path("config"),
        auto_reload: bool = False,
        validator_timeout: int = 10
    ):
        """Initialize the configuration manager.
        
        Args:
            config_dir: Configuration directory path
            auto_reload: Enable automatic configuration reloading
            validator_timeout: Validation timeout in seconds
        """
        # Prevent re-initialization
        if hasattr(self, '_initialized'):
            return
        
        self.config_dir = config_dir
        self.auto_reload = auto_reload
        self._initialized = True
        
        # Components
        self.loader = ConfigurationLoader(config_dir)
        self.validator = ConfigurationValidator(validator_timeout)
        
        # State management
        self._config: Optional[BaseConfiguration] = None
        self._config_lock = threading.RLock()
        self._change_callbacks: List[Callable[[BaseConfiguration], None]] = []
        self._observer: Optional[Observer] = None
        self._reload_scheduled = False
        
        # Load initial configuration
        self._load_initial_configuration()
        
        # Setup hot reloading if enabled
        if auto_reload:
            self._setup_hot_reloading()
    
    @property
    def config(self) -> BaseConfiguration:
        """Get current configuration (thread-safe)."""
        with self._config_lock:
            if self._config is None:
                raise ConfigurationError("Configuration not loaded")
            return self._config
    
    def get_site_config(self, site_name: str) -> Optional[Any]:
        """Get configuration for a specific site."""
        with self._config_lock:
            return self._config.sites.get(site_name) if self._config else None
    
    def register_change_callback(self, callback: Callable[[BaseConfiguration], None]):
        """Register a callback for configuration changes.
        
        Args:
            callback: Function to call when configuration changes
        """
        self._change_callbacks.append(callback)
        name = getattr(callback, "__name__", repr(callback))
        logger.debug(f"Registered configuration change callback: {name}")
    
    def unregister_change_callback(self, callback: Callable[[BaseConfiguration], None]):
        """Unregister a configuration change callback.
        
        Args:
            callback: Function to unregister
        """
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
            logger.debug(f"Unregistered configuration change callback: {callback.__name__}")
    
    async def reload_configuration(
        self, 
        environment: Optional[Environment] = None,
        validate: bool = True
    ) -> bool:
        """
        Reload configuration from files.
        
        Args:
            environment: Target environment (use current if None)
            validate: Whether to validate the new configuration
            
        Returns:
            True if reload was successful, False otherwise
        """
        try:
            logger.info("Reloading configuration...")
            
            try:
                # Use current environment if not specified
                if environment is None and self._config:
                    environment = Environment(self._config.environment.lower())
            except ValueError:
                logger.error(f"{environment} is not a valid Status")

            # Load new configuration
            new_config = self.loader.load_configuration(environment=environment)
            
            # Validate if requested
            if validate:
                warnings = await self.validator.validate_configuration(new_config)
                if warnings:
                    logger.warning(f"Configuration reloaded with {len(warnings)} warnings")
            
            # Update configuration atomically
            old_config = None
            try:
                with self._config_lock:
                    old_config = self._config
                    self._config = new_config
                
                # Notify callbacks
                self._notify_change_callbacks(new_config)
                
                logger.info("Configuration reloaded successfully")
                return True
            except Exception as e:
                # Rollback to old configuration
                self._config = old_config
                logger.error(f"Configuration reload failed: {e}")
                raise ConfigurationUpdateError(f"Reload failed: {e}")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def update_runtime_config(
        self, 
        updates: Dict[str, Any], 
        validate: bool = True
    ) -> bool:
        """
        Update configuration at runtime.
        
        Args:
            updates: Dictionary of configuration updates
            validate: Whether to validate the updated configuration
            
        Returns:
            True if update was successful, False otherwise
            
        Raises:
            ConfigurationUpdateError: If update fails
        """
        if not self._config:
            raise ConfigurationUpdateError("No configuration loaded")
        
        # Production safety check
        if self._config.environment == Environment.PRODUCTION:
            raise ConfigurationUpdateError("Runtime updates not allowed in production")
        
        try:
            logger.info(f"Updating runtime configuration: {list(updates.keys())}")
            
            # Create updated configuration
            current_data = self._config.model_dump()
            updated_data = self._deep_merge(current_data, updates)
            
            # Validate new configuration
            new_config = BaseConfiguration(**updated_data)
            
            if validate:
                # Note: Async validation in sync context - consider making this async
                logger.warning("Skipping async validation in runtime update")
            
            # Update configuration atomically
            with self._config_lock:
                old_config = self._config
                self._config = new_config
            
            # Notify callbacks
            self._notify_change_callbacks(new_config)
            
            logger.info("Runtime configuration updated successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update runtime configuration: {e}")
            raise ConfigurationUpdateError(f"Runtime update failed: {e}")
    
    def get_masked_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values masked."""
        with self._config_lock:
            if self._config is None:
                return {}
            return self._config.mask_sensitive_values()
    
    def shutdown(self):
        """Shutdown the configuration manager."""
        logger.info("Shutting down configuration manager")
        
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)  # Add timeout
            except Exception as e:
                logger.error(f"Error stopping file observer: {e}")
            finally:
                self._observer = None
        
        self._change_callbacks.clear()
        
        with self._config_lock:
            self._config = None
    
    def _load_initial_configuration(self):
        """Load initial configuration synchronously."""
        try:
            config = self.loader.load_configuration()
            
            with self._config_lock:
                self._config = config
            
            logger.info(f"Initial configuration loaded for environment: {config.environment}")
        
        except Exception as e:
            logger.error(f"Failed to load initial configuration: {e}")
            raise ConfigurationError(f"Initial configuration load failed: {e}")
    
    def _setup_hot_reloading(self):
        """Setup file system monitoring for hot reloading."""
        if not self._config or self._config.environment == Environment.PRODUCTION:
            logger.info("Hot reloading disabled (only enabled in development)")
            return
        
        try:
            self._observer = Observer()
            handler = ConfigurationChangeHandler(self)
            
            # Watch config directories
            for watch_dir in [self.config_dir / "environments", self.config_dir / "sites"]:
                if watch_dir.exists():
                    self._observer.schedule(handler, str(watch_dir), recursive=False)
                    logger.debug(f"Watching directory for changes: {watch_dir}")
            
            self._observer.start()
            logger.info("Hot reloading enabled")
        
        except Exception as e:
            logger.error(f"Failed to setup hot reloading: {e}")
    
    async def _handle_config_change(self, file_path: Path):
        """Handle configuration file changes."""
        try:
            # Small delay to ensure file write is complete
            await asyncio.sleep(0.5)
            
            # Determine if this affects current environment
            if file_path.parent.name == "environments":
                # Environment file changed - reload if it's current environment
                env_name = file_path.stem
                if (env_name == "base" or 
                    (self._config and env_name == self._config.environment)):
                    await self.reload_configuration()
            
            elif file_path.parent.name == "sites":
                # Site file changed - reload all configuration
                await self.reload_configuration()
        
        except Exception as e:
            logger.error(f"Error handling configuration change for {file_path}: {e}")
    
    def _schedule_reload(self):
        """Schedule a configuration reload."""
        if self._reload_scheduled:
            return
        
        self._reload_scheduled = True
        
        def delayed_reload():
            time.sleep(1.0)  # Small delay
            try:
                # Create new event loop for this thread if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(self.reload_configuration())
            except Exception as e:
                logger.error(f"Scheduled reload failed: {e}")
            finally:
                self._reload_scheduled = False
        
        # Run in separate thread to avoid blocking
        threading.Thread(target=delayed_reload, daemon=True).start()
    
    def _notify_change_callbacks(self, new_config: BaseConfiguration):
        """Notify all registered change callbacks."""
        for callback in self._change_callbacks:
            try:
                callback(new_config)
            except Exception as e:
                logger.error(f"Configuration change callback failed: {callback.__name__}: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result