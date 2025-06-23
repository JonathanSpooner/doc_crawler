"""Integration tests for the complete configuration system."""

import os
import yaml
from unittest.mock import patch
import pytest

from doc_crawler.config.manager import ConfigurationManager
from doc_crawler.config.models import Environment
from ..database.models.conftest import session_config_file, mock_env_vars, temp_config_dir

class TestConfigurationSystemIntegration:
    """Integration tests for the complete configuration system."""
    
    def setup_method(self):
        """Reset singleton for each test."""
        ConfigurationManager._instance = None
    
    def test_complete_configuration_flow(self, session_config_file, mock_env_vars):
        """Test complete configuration loading and access flow."""
        manager = ConfigurationManager(config_dir=session_config_file)
        
        # Test configuration access
        config = manager.config
        assert config.environment == Environment.DEVELOPMENT
        
        # Test that environment variables override file values
        assert "env_db" in config.database.url.get_secret_value()
        
        # Test site configuration access
        site_config = manager.get_site_config("iep")
        assert site_config is not None
        assert site_config.name == "Internet Encyclopedia of Philosophy"
        
        # Test masked configuration
        masked = manager.get_masked_config()
        assert masked["database"]["url"] == "***MASKED***"
    
    
    async def test_configuration_reload_integration(self, session_config_file):
        """Test configuration reload with file changes."""
        manager = ConfigurationManager(config_dir=session_config_file)
        
        original_delay = manager.config.crawling.default_delay
        
        # Modify base configuration
        base_file = session_config_file / "environments" / "prod.yaml"
        with open(base_file, "r") as f:
            config_data = yaml.safe_load(f)
        
        config_data["crawling"]["default_delay"] = 5.0
        
        with open(base_file, "w") as f:
            yaml.dump(config_data, f)
        
        # Reload configuration
        success = await manager.reload_configuration()
        assert success is True
        
        # Verify change was applied
        assert manager.config.crawling.default_delay == 5.0
        assert manager.config.crawling.default_delay != original_delay
    
    def test_environment_specific_behavior(self, session_config_file):
        """Test environment-specific configuration behavior."""
        # Create different environment configs
        environments_dir = session_config_file / "environments"
        
        base_config = {
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "base-secret"},
            "crawling": {"default_delay": 1.0},
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
            }
        }
        
        dev_config = {
            "debug": True,
            "hot_reload": True,
            "crawling": {"default_delay": 0.5}
        }
        
        prod_config = {
            "debug": False,
            "hot_reload": False,
            "crawling": {"default_delay": 2.0}
        }
        
        # Write config files
        with open(environments_dir / "base.yaml", "w") as f:
            yaml.dump(base_config, f)
        with open(environments_dir / "dev.yaml", "w") as f:
            yaml.dump(dev_config, f)
        os.remove(environments_dir/"prod.yaml")
        
        # Test development environment
        dev_manager = ConfigurationManager(config_dir=session_config_file)
        dev_config_obj = dev_manager.config
        
        assert dev_config_obj.environment == Environment.DEVELOPMENT
        assert dev_config_obj.debug is True
        assert dev_config_obj.crawling.default_delay == 0.5
        
        dev_manager.shutdown()
        ConfigurationManager._instance = None
        
        with open(environments_dir / "prod.yaml", "w") as f:
            yaml.dump(prod_config, f)

        # Test production environment
        with patch.dict("os.environ", {"ENVIRONMENT": "prod"}):
            prod_manager = ConfigurationManager(config_dir=session_config_file)
            prod_config_obj = prod_manager.config
            
            assert prod_config_obj.environment == Environment.PRODUCTION
            assert prod_config_obj.debug is False
            assert prod_config_obj.crawling.default_delay == 2.0
    
    def test_configuration_change_callbacks(self, session_config_file):
        """Test configuration change callback system."""
        os.remove(session_config_file/"environments"/"prod.yaml")
        manager = ConfigurationManager(config_dir=session_config_file)
        
        callback_calls = []
        
        def change_callback(new_config):
            callback_calls.append(new_config)
        
        manager.register_change_callback(change_callback)
        
        # Test runtime update (development environment)
        success = manager.update_runtime_config({
            "crawling": {"default_delay": 3.0}
        })
        
        assert success is True
        assert len(callback_calls) == 1
        assert callback_calls[0].crawling.default_delay == 3.0
    
    def test_error_handling_integration(self, temp_config_dir):
        """Test error handling throughout the system."""
        # Test with missing required configuration
        with pytest.raises(Exception):  # Should fail due to missing required fields
            ConfigurationManager(config_dir=temp_config_dir)
        
        ConfigurationManager._instance = None
        
        # Test with invalid configuration
        environments_dir = temp_config_dir / "environments"
        invalid_config = {
            "database": {"url": "invalid-url"},  # Invalid URL
            "security": {"secret_key": "test"}
        }
        
        with open(environments_dir / "base.yaml", "w") as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises(Exception):  # Should fail validation
            ConfigurationManager(config_dir=temp_config_dir)
    
    def test_thread_safety_integration(self, session_config_file):
        """Test thread safety of the complete system."""
        try:
            os.remove(session_config_file/"environments"/"prod.yaml")
        except:
            print()
        manager = ConfigurationManager(config_dir=session_config_file)
        
        import threading
        import time
        
        results = []
        errors = []
        
        def worker():
            try:
                for _ in range(50):
                    # Test various operations
                    config = manager.config
                    site_config = manager.get_site_config("iep")
                    masked = manager.get_masked_config()
                    
                    results.append((config, site_config, masked))
                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert len(errors) == 0
        assert len(results) == 250  # 5 threads * 50 operations
        
        # All results should be consistent
        first_config = results[0][0]
        for config, site_config, masked in results:
            assert config.environment == first_config.environment
            assert site_config.name == "Internet Encyclopedia of Philosophy"
            assert masked["database"]["url"] == "***MASKED***"
    
    
    async def test_validation_integration(self, session_config_file):
        """Test validation integration throughout the system."""
        manager = ConfigurationManager(config_dir=session_config_file)
        
        # Test that validation runs during reload
        success = await manager.reload_configuration(validate=True)
        assert success is True
        
        # Test validation failure handling
        with patch('doc_crawler.config.validator.ConfigurationValidator.validate_configuration', 
                  side_effect=Exception("Validation failed")):
            success = await manager.reload_configuration(validate=True)
            assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])