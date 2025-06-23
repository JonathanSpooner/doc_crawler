"""Tests for configuration loading logic."""

import json
import pytest
import yaml
from unittest.mock import patch

from doc_crawler.config.loader import ConfigurationLoader
from doc_crawler.config.models import Environment
from doc_crawler.config.exceptions import ConfigurationLoadError, ConfigurationValidationError
from ..database.repositories.repository_utils import sample_object_ids
from ..database.models.conftest import session_config_file, mock_env_vars, temp_config_dir, sample_dev_config, sample_base_config, sample_site_config


class TestConfigurationLoader:
    """Test configuration loader functionality."""
    
    def test_init_creates_directories(self, temp_config_dir):
        """Test that loader creates necessary directories."""
        loader = ConfigurationLoader(temp_config_dir)
        
        assert loader.config_dir == temp_config_dir
        assert (temp_config_dir / "environments").exists()
        assert (temp_config_dir / "sites").exists()
    
    def test_detect_environment_from_env_var(self):
        """Test environment detection from environment variable."""
        loader = ConfigurationLoader()
        
        with patch.dict("os.environ", {"ENVIRONMENT": "prod"}):
            env = loader._detect_environment()
            assert env == Environment.PRODUCTION
        
        with patch.dict("os.environ", {"ENV": "staging"}):
            env = loader._detect_environment()
            assert env == Environment.STAGING
    
    def test_detect_environment_from_files(self, temp_config_dir):
        """Test environment detection from file existence."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Create prod.yaml file
        (temp_config_dir / "environments" / "prod.yaml").touch()
        env = loader._detect_environment()
        assert env == Environment.PRODUCTION
        
        # Remove prod.yaml, create staging.yaml
        (temp_config_dir / "environments" / "prod.yaml").unlink()
        (temp_config_dir / "environments" / "staging.yaml").touch()
        env = loader._detect_environment()
        assert env == Environment.STAGING
    
    def test_detect_environment_default(self, temp_config_dir):
        """Test default environment detection."""
        loader = ConfigurationLoader(temp_config_dir)
        env = loader._detect_environment()
        assert env == Environment.DEVELOPMENT
    
    def test_load_base_configuration(self, temp_config_dir, sample_base_config):
        """Test loading base configuration."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Write base config
        base_file = temp_config_dir / "environments" / "base.yaml"
        with open(base_file, "w") as f:
            yaml.dump(sample_base_config, f)
        
        config = loader._load_base_configuration()
        assert config["database"]["pool_size"] == 5
        assert config["crawling"]["default_delay"] == 1.0
    
    def test_load_base_configuration_missing_file(self, temp_config_dir):
        """Test loading base configuration when file is missing."""
        loader = ConfigurationLoader(temp_config_dir)
        
        config = loader._load_base_configuration()
        assert config == {}
    
    def test_load_environment_configuration(self, temp_config_dir, sample_dev_config):
        """Test loading environment-specific configuration."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Write dev config
        dev_file = temp_config_dir / "environments" / "dev.yaml"
        with open(dev_file, "w") as f:
            yaml.dump(sample_dev_config, f)
        
        config = loader._load_environment_configuration(Environment.DEVELOPMENT)
        assert config["logging"]["level"] == "DEBUG"
        assert config["debug"] is True
    
    def test_load_environment_configuration_missing(self, temp_config_dir):
        """Test loading environment configuration when file is missing."""
        loader = ConfigurationLoader(temp_config_dir)
        
        config = loader._load_environment_configuration(Environment.PRODUCTION)
        assert config is None
    
    def test_load_site_configurations(self, temp_config_dir, sample_site_config):
        """Test loading site configurations."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Write site config
        site_file = temp_config_dir / "sites" / "test_site.yaml"
        with open(site_file, "w") as f:
            yaml.dump(sample_site_config, f)
        
        sites = loader._load_site_configurations()
        assert "test_site" in sites
        assert sites["test_site"].name == "Test Philosophy Site"
    
    def test_load_site_configurations_invalid_file(self, temp_config_dir):
        """Test loading site configurations with invalid file."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Write invalid site config
        site_file = temp_config_dir / "sites" / "invalid_site.yaml"
        with open(site_file, "w") as f:
            f.write("invalid: yaml: content:")
        
        # Should continue loading other sites despite invalid file
        sites = loader._load_site_configurations()
        assert "invalid_site" not in sites
    
    def test_load_yaml_file_invalid_yaml(self, temp_config_dir):
        """Test loading invalid YAML file."""
        loader = ConfigurationLoader(temp_config_dir)
        
        invalid_file = temp_config_dir / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [unclosed")
        
        with pytest.raises(ConfigurationLoadError) as exc_info:
            loader._load_yaml_file(invalid_file)
        assert "Invalid YAML" in str(exc_info.value)
    
    def test_load_json_file(self, temp_config_dir):
        """Test loading JSON file."""
        loader = ConfigurationLoader(temp_config_dir)
        
        test_data = {"test": "value", "nested": {"key": "value"}}
        json_file = temp_config_dir / "test.json"
        with open(json_file, "w") as f:
            json.dump(test_data, f)
        
        data = loader._load_json_file(json_file)
        assert data == test_data
    
    def test_load_json_file_invalid(self, temp_config_dir):
        """Test loading invalid JSON file."""
        loader = ConfigurationLoader(temp_config_dir)
        
        invalid_file = temp_config_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{invalid json")
        
        with pytest.raises(ConfigurationLoadError) as exc_info:
            loader._load_json_file(invalid_file)
        assert "Invalid JSON" in str(exc_info.value)
    
    def test_deep_merge_dictionaries(self, temp_config_dir):
        """Test deep merging of dictionaries."""
        loader = ConfigurationLoader(temp_config_dir)
        
        base = {
            "database": {"pool_size": 5, "timeout": 30},
            "logging": {"level": "INFO"},
            "simple": "value"
        }
        
        override = {
            "database": {"pool_size": 10, "new_setting": True},
            "security": {"api_key": "test"},
            "simple": "new_value"
        }
        
        result = loader._deep_merge(base, override)
        
        # Check deep merge
        assert result["database"]["pool_size"] == 10  # Overridden
        assert result["database"]["timeout"] == 30    # Preserved
        assert result["database"]["new_setting"] is True  # Added
        
        # Check simple override
        assert result["simple"] == "new_value"
        
        # Check new sections
        assert result["security"]["api_key"] == "test"
        assert result["logging"]["level"] == "INFO"
    
    def test_load_configuration_complete_flow(self, session_config_file, mock_env_vars):
        """Test complete configuration loading flow."""
        loader = ConfigurationLoader(session_config_file)
        
        config = loader.load_configuration(Environment.DEVELOPMENT)
        
        # Check that all levels are merged correctly
        assert config.environment == Environment.DEVELOPMENT
        assert config.database.pool_size == 2  # From dev override
        assert config.logging.level.value == "DEBUG"  # From dev override
        assert config.debug is True  # From dev override
        assert "iep" in config.sites  # Site config loaded
    
    def test_load_configuration_with_overrides(self, session_config_file):
        """Test configuration loading with runtime overrides."""
        loader = ConfigurationLoader(session_config_file)
        
        overrides = {
            "crawling": {"default_delay": 3.0},
            "debug": False
        }
        config = loader.load_configuration(
            Environment.DEVELOPMENT,
            overrides=overrides
        )
        assert config.crawling.default_delay == 3.0  # Runtime override
        assert config.debug is False  # Runtime override
        assert config.logging.level.value == "DEBUG"  # Still from env config
    
    def test_load_configuration_validation_error(self, temp_config_dir):
        """Test configuration loading with validation errors."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Create invalid config
        base_file = temp_config_dir / "environments" / "base.yaml"
        invalid_config = {
            "database": {"url": "invalid-url"},  # Invalid database URL
            "security": {"secret_key": "test"}
        }
        with open(base_file, "w") as f:
            yaml.dump(invalid_config, f)
        
        with pytest.raises(ConfigurationValidationError):
            loader.load_configuration()
    
    def test_load_configuration_file_error(self, temp_config_dir):
        """Test configuration loading with file system errors."""
        loader = ConfigurationLoader(temp_config_dir)
        
        # Create a directory where file should be (causes permission error)
        (temp_config_dir / "environments" / "base.yaml").mkdir()
        
        with pytest.raises(ConfigurationLoadError):
            loader.load_configuration()
