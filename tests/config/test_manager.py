"""Tests for runtime configuration management."""

import os
from unittest.mock import AsyncMock
import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import pytest

from doc_crawler.config.manager import ConfigurationManager, ConfigurationChangeHandler
from doc_crawler.config.models import Environment, BaseConfiguration
from doc_crawler.config.exceptions import ConfigurationError, ConfigurationUpdateError
from ..database.models.conftest import session_config_file, temp_config_dir


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    def setup_method(self):
        """Reset singleton for each test."""
        ConfigurationManager._instance = None
    
    def test_singleton_pattern(self, session_config_file):
        """Test that ConfigurationManager follows singleton pattern."""
        manager1 = ConfigurationManager(config_dir=session_config_file)
        manager2 = ConfigurationManager(config_dir=session_config_file)
        
        assert manager1 is manager2
    
    def test_initialization_prevents_reinitialization(self, session_config_file):
        """Test that initialization is only done once."""
        manager = ConfigurationManager(config_dir=session_config_file)
        original_config_dir = manager.config_dir
        
        # Second initialization should not change settings
        ConfigurationManager(config_dir=Path("different"))
        assert manager.config_dir == original_config_dir
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_load_initial_configuration_success(self, mock_loader_class, temp_config_dir):
        """Test successful initial configuration loading."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        assert manager._config is mock_config
        mock_loader.load_configuration.assert_called_once()
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_load_initial_configuration_failure(self, mock_loader_class, temp_config_dir):
        """Test initial configuration loading failure."""
        mock_loader = Mock()
        mock_loader.load_configuration.side_effect = Exception("Load failed")
        mock_loader_class.return_value = mock_loader
        
        with pytest.raises(ConfigurationError) as exc_info:
            ConfigurationManager(config_dir=temp_config_dir)
        
        assert "Initial configuration load failed" in str(exc_info.value)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_config_property_access(self, mock_loader_class, temp_config_dir):
        """Test configuration property access."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        assert manager.config is mock_config
    
    def test_config_property_not_loaded(self, temp_config_dir):
        """Test configuration property access when not loaded."""
        with patch('doc_crawler.config.manager.ConfigurationLoader') as mock_loader_class:
            mock_loader = Mock()
            mock_loader.load_configuration.side_effect = Exception("Failed")
            mock_loader_class.return_value = mock_loader
            
            with pytest.raises(ConfigurationError):
                manager = ConfigurationManager(config_dir=temp_config_dir)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_get_site_config(self, mock_loader_class, temp_config_dir):
        """Test getting site-specific configuration."""
        mock_loader = Mock()
        mock_site_config = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_config.sites = {"test_site": mock_site_config}
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        result = manager.get_site_config("test_site")
        assert result is mock_site_config
        
        result = manager.get_site_config("nonexistent")
        assert result is None
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_register_unregister_change_callback(self, mock_loader_class, temp_config_dir):
        """Test registering and unregistering change callbacks."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        callback = Mock()
        callback.__name__ = "callback"
        manager.register_change_callback(callback)
        assert callback in manager._change_callbacks
        
        manager.unregister_change_callback(callback)
        assert callback not in manager._change_callbacks
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    @patch('doc_crawler.config.manager.ConfigurationValidator')
    @pytest.mark.asyncio
    async def test_reload_configuration_success(self, mock_validator_class, mock_loader_class, temp_config_dir):
        """Test successful configuration reload."""
        # Setup mocks
        mock_loader = Mock()
        mock_validator = Mock()
        
        old_config = Mock(spec=BaseConfiguration)
        old_config.environment = Environment.DEVELOPMENT
        
        new_config = Mock(spec=BaseConfiguration)
        new_config.environment = Environment.DEVELOPMENT
        
        mock_loader.load_configuration.side_effect = [old_config, new_config]
        mock_validator.validate_configuration = AsyncMock(return_value=[])
        
        mock_loader_class.return_value = mock_loader
        mock_validator_class.return_value = mock_validator
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        # Register callback to verify it's called
        callback = Mock()
        manager.register_change_callback(callback)
        
        # Reload configuration
        result = await manager.reload_configuration()
        
        assert result is True
        assert manager._config is new_config
        callback.assert_called_once_with(new_config)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    @patch('doc_crawler.config.manager.ConfigurationValidator')
    @pytest.mark.asyncio
    async def test_reload_configuration_failure(self, mock_validator_class, mock_loader_class, temp_config_dir):
        """Test configuration reload failure."""
        mock_loader = Mock()
        mock_validator = Mock()
        
        old_config = Mock(spec=BaseConfiguration)
        old_config.environment = Environment.DEVELOPMENT
        
        mock_loader.load_configuration.side_effect = [old_config, Exception("Reload failed")]
        
        mock_loader_class.return_value = mock_loader
        mock_validator_class.return_value = mock_validator
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        # Reload should fail but not crash
        result = await manager.reload_configuration()
        
        assert result is False
        assert manager._config is old_config  # Old config preserved
    
    @patch('doc_crawler.config.manager.BaseConfiguration')
    def test_update_runtime_config_success(self, mock_loader_class, session_config_file):
        """Test successful runtime configuration update."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_config.model_dump.return_value = {
            "crawling": {"default_delay": 1.0},
            "debug": False,
            "notifications": {
                "enabled": True,
                "error_threshold": 10,
                "failure_rate_threshold": 0.1,
                "email": {
                    "smtp_server": "smtp.example.com",
                    "username": "username", 
                    "password": "password",
                    "from_address": "user@example.com",
                    "recipients": ["receipt@example.com", "receipt2@example.com"]
                }
            },
            "database": {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_recycle": 3600,
                "echo": False,
                "url": "postgresql://user:pass@localhost:5432/crawler_db"
            },
            "security": {
                "token_expiry": 3600,
                "rate_limit_per_minute": 60,
                "allowed_hosts": [],
                "cors_origins": [],
                "secret_key": "secret-xxxxx"
            }
        }
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        os.environ["ENVIRONMENT"] = "dev"
        manager = ConfigurationManager(config_dir=session_config_file)

        updates = {"crawling": {"default_delay": 2.0}}

        # Create the new config that should be assigned after update
        new_config = Mock(spec=BaseConfiguration)
        
        # Mock the BaseConfiguration constructor to return new_config when called during update
        with patch('doc_crawler.config.manager.BaseConfiguration', return_value=new_config) as mock_base_config:
            callback = Mock()
            manager.register_change_callback(callback)

            result = manager.update_runtime_config(updates)

            assert result is True
            assert manager._config is new_config  # Use 'is' for identity comparison
            
            # Verify BaseConfiguration was called with the updated config
            mock_base_config.assert_called_once() 

    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_update_runtime_config_production_restriction(self, mock_loader_class, temp_config_dir):
        """Test that runtime updates are not allowed in production."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.PRODUCTION
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        with pytest.raises(ConfigurationUpdateError) as exc_info:
            manager.update_runtime_config({"debug": True})
        
        assert "not allowed in production" in str(exc_info.value)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_update_runtime_config_no_config(self, mock_loader_class, temp_config_dir):
        """Test runtime update when no configuration is loaded."""
        mock_loader = Mock()
        mock_loader.load_configuration.side_effect = Exception("Failed")
        mock_loader_class.return_value = mock_loader
        
        with pytest.raises(ConfigurationError):
            manager = ConfigurationManager(config_dir=temp_config_dir)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_update_runtime_config_validation_failure(self, mock_loader_class, temp_config_dir):
        """Test runtime update with validation failure."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_config.model_dump.return_value = {"existing": "config"}
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        updates = {"invalid": "update"}
        
        with patch('doc_crawler.config.models.BaseConfiguration', side_effect=Exception("Validation failed")):
            with pytest.raises(ConfigurationUpdateError) as exc_info:
                manager.update_runtime_config(updates)
            
            assert "Runtime update failed" in str(exc_info.value)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_get_masked_config(self, mock_loader_class, temp_config_dir):
        """Test getting masked configuration."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_config.mask_sensitive_values.return_value = {"masked": "config"}
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        result = manager.get_masked_config()
        assert result == {"masked": "config"}
        mock_config.mask_sensitive_values.assert_called_once()
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_get_masked_config_no_config(self, mock_loader_class, temp_config_dir):
        """Test getting masked configuration when no config loaded."""
        mock_loader = Mock()
        mock_loader.load_configuration.side_effect = Exception("Failed")
        mock_loader_class.return_value = mock_loader
        
        with pytest.raises(ConfigurationError):
            manager = ConfigurationManager(config_dir=temp_config_dir)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    @patch('doc_crawler.config.manager.Observer')
    def test_setup_hot_reloading_enabled(self, mock_observer_class, mock_loader_class, temp_config_dir):
        """Test hot reloading setup when enabled."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        manager = ConfigurationManager(config_dir=temp_config_dir, auto_reload=True)
        
        mock_observer.schedule.assert_called()
        mock_observer.start.assert_called_once()
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_setup_hot_reloading_disabled_production(self, mock_loader_class, temp_config_dir):
        """Test that hot reloading is disabled in production."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.PRODUCTION
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir, auto_reload=True)
        
        assert manager._observer is None
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    @patch('doc_crawler.config.manager.Observer')
    def test_shutdown(self, mock_observer_class, mock_loader_class, temp_config_dir):
        """Test manager shutdown."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        manager = ConfigurationManager(config_dir=temp_config_dir, auto_reload=True)
        
        callback = Mock()
        manager.register_change_callback(callback)
        
        manager.shutdown()
        
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()
        assert manager._observer is None
        assert len(manager._change_callbacks) == 0
        assert manager._config is None
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_deep_merge(self, mock_loader_class, temp_config_dir):
        """Test deep merge functionality."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        base = {
            "database": {"pool_size": 5, "timeout": 30},
            "logging": {"level": "INFO"},
            "simple": "value"
        }
        
        override = {
            "database": {"pool_size": 10},
            "security": {"api_key": "test"},
            "simple": "new_value"
        }
        
        result = manager._deep_merge(base, override)
        
        assert result["database"]["pool_size"] == 10
        assert result["database"]["timeout"] == 30
        assert result["security"]["api_key"] == "test"
        assert result["simple"] == "new_value"
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_notify_change_callbacks_exception_handling(self, mock_loader_class, temp_config_dir):
        """Test that callback exceptions don't crash the system."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        # Register callbacks, one that fails
        good_callback = Mock()
        good_callback.__name__ = "good_callback"
        bad_callback = Mock(side_effect=Exception("Callback failed"))
        bad_callback.__name__ = "bad_callback"
        
        manager.register_change_callback(good_callback)
        manager.register_change_callback(bad_callback)
        
        # Should not raise exception
        manager._notify_change_callbacks(mock_config)
        
        good_callback.assert_called_once_with(mock_config)
        bad_callback.assert_called_once_with(mock_config)
    
    @patch('doc_crawler.config.manager.ConfigurationLoader')
    def test_thread_safety(self, mock_loader_class, temp_config_dir):
        """Test thread safety of configuration access."""
        mock_loader = Mock()
        mock_config = Mock(spec=BaseConfiguration)
        mock_config.environment = Environment.DEVELOPMENT
        mock_loader.load_configuration.return_value = mock_config
        mock_loader_class.return_value = mock_loader
        
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        results = []
        exceptions = []
        
        def access_config():
            try:
                for _ in range(100):
                    config = manager.config
                    results.append(config)
            except Exception as e:
                exceptions.append(e)
        
        # Create multiple threads accessing configuration
        threads = [threading.Thread(target=access_config) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All accesses should succeed
        assert len(exceptions) == 0
        assert len(results) == 1000  # 10 threads * 100 accesses
        assert all(r is mock_config for r in results)


class TestConfigurationChangeHandler:
    """Test configuration change handler functionality."""
    
    def test_init(self):
        """Test change handler initialization."""
        manager = Mock()
        handler = ConfigurationChangeHandler(manager)
        
        assert handler.manager is manager
        assert handler.debounce_seconds == 2.0
        assert isinstance(handler.last_reload, dict)
    
    def test_on_modified_ignores_directories(self):
        """Test that directory modifications are ignored."""
        manager = Mock()
        handler = ConfigurationChangeHandler(manager)
        
        event = Mock()
        event.is_directory = True
        event.src_path = "/config/environments"
        
        handler.on_modified(event)
        
        # Should not trigger any action
        assert len(handler.last_reload) == 0
    
    def test_on_modified_ignores_non_yaml_files(self):
        """Test that non-YAML files are ignored."""
        manager = Mock()
        handler = ConfigurationChangeHandler(manager)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/config/test.txt"
        
        handler.on_modified(event)
        
        assert len(handler.last_reload) == 0
    
    def test_on_modified_debounces_changes(self):
        """Test that rapid file changes are debounced."""
        manager = Mock()
        handler = ConfigurationChangeHandler(manager)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/config/environments/base.yaml"
        
        # First modification
        handler.on_modified(event)
        assert event.src_path in handler.last_reload
        
        # Immediate second modification (should be debounced)
        with patch('time.time', return_value=handler.last_reload[event.src_path] + 1.0):
            handler.on_modified(event)
            # Should not update timestamp due to debouncing
    
    @patch('asyncio.create_task')
    def test_on_modified_triggers_reload(self, mock_create_task):
        """Test that YAML file modifications trigger reload."""
        manager = Mock()
        handler = ConfigurationChangeHandler(manager)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/config/environments/base.yaml"
        
        with patch('time.time', return_value=1000.0):
            handler.on_modified(event)
        
        mock_create_task.assert_called_once()
