"""
Configuration loading and merging logic.

This module handles the hierarchical loading of configuration files,
environment variable processing, and configuration merging.
"""
import copy
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict,  Optional

import yaml
from pydantic import ValidationError

from doc_crawler.config.exceptions import ConfigurationLoadError, ConfigurationValidationError
from doc_crawler.config.models import BaseConfiguration, Environment, SiteConfiguration

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """
    Handles loading and merging configuration from multiple sources.
    
    Loading hierarchy (highest to lowest priority):
    1. Environment variables
    2. Runtime overrides
    3. Site-specific configurations
    4. Environment-specific files
    5. Base configuration file
    """
    
    def __init__(self, config_dir: Path = Path("config")):
        """Initialize the configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.environments_dir = self.config_dir / "environments"
        self.sites_dir = self.config_dir / "sites"
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.environments_dir.mkdir(exist_ok=True)
        self.sites_dir.mkdir(exist_ok=True)
    
    def load_configuration(
        self,
        environment: Optional[Environment] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> BaseConfiguration:
        """
        Load complete configuration with hierarchy.
        
        Args:
            environment: Target environment (auto-detected if None)
            overrides: Runtime configuration overrides
            
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationLoadError: If configuration files cannot be loaded
            ConfigurationValidationError: If configuration validation fails
        """
        try:
            # Auto-detect environment if not specified
            if environment is None:
                environment = self._detect_environment()
            
            logger.info(f"Loading configuration for environment: {environment.value}")
            
            # Step 1: Load base configuration
            base_config = self._load_base_configuration()
            logger.debug("Loaded base configuration")
            
            # Step 2: Load environment-specific overrides
            env_config = self._load_environment_configuration(environment)
            if env_config:
                base_config = self._deep_merge(base_config, env_config)
                logger.debug(f"Applied {environment.value} environment overrides")
            
            # Step 3: Load site configurations
            site_configs = self._load_site_configurations()
            if site_configs:
                base_config["sites"] = site_configs
                logger.debug(f"Loaded {len(site_configs)} site configurations")

            # *** MISSING STEP: Load environment variables ***
            env_vars = self._load_environment_variables()
            if env_vars:
                base_config = self._deep_merge(base_config, env_vars)
                logger.debug("Applied environment variable overrides")

            # Step 4: Apply runtime overrides
            if overrides:
                base_config = self._deep_merge(base_config, overrides)
                logger.debug("Applied runtime overrides")
            
            # Step 5: Set environment in config
            base_config["environment"] = environment.value
            
            # Step 6: Validate complete configuration
            try:
                config = BaseConfiguration(**base_config)
                logger.info("Configuration loaded and validated successfully")
                return config
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                raise ConfigurationValidationError(f"Configuration validation failed: {e}")
        
        except Exception as e:
            if isinstance(e, (ConfigurationLoadError, ConfigurationValidationError)):
                raise
            logger.error(f"Unexpected error loading configuration: {e}")
            raise ConfigurationLoadError(f"Failed to load configuration: {e}")
        
    def _load_environment_variables(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Returns:
            Dictionary with environment variable overrides
        """
        env_config = {}
        
        # Map environment variables to config structure
        env_mappings = {
            'CRAWLER_DATABASE__URL': ['database', 'url'],
            'CRAWLER_SECURITY__SECRET_KEY': ['security', 'secret_key'],
            'CRAWLER_LOGGING__LEVEL': ['logging', 'level'],
            # Add more mappings as needed
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Build nested dictionary structure
                current = env_config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = value
        
        return env_config    
    
    def _detect_environment(self) -> Environment:
        """Detect environment from various sources."""
        # Check environment variable
        env_var = os.getenv("ENVIRONMENT", os.getenv("ENV", "")).lower()
        if env_var:
            try:
                return Environment(env_var)
            except ValueError:
                logger.warning(f"Invalid environment variable value: {env_var}")
        
        # Check for environment-specific files
        if (self.environments_dir / "prod.yaml").exists():
            return Environment.PRODUCTION
        elif (self.environments_dir / "staging.yaml").exists():
            return Environment.STAGING
        
        # Default to development
        return Environment.DEVELOPMENT
    
    def _load_base_configuration(self) -> Dict[str, Any]:
        """Load base configuration file."""
        base_file = self.environments_dir / "base.yaml"
        if not base_file.exists():
            logger.warning(f"Base configuration file not found: {base_file}")
            return {}
        
        return self._load_yaml_file(base_file)
    
    def _load_environment_configuration(self, environment: Environment) -> Optional[Dict[str, Any]]:
        """Load environment-specific configuration."""
        env_file = self.environments_dir / f"{environment.value}.yaml"
        if not env_file.exists():
            logger.warning(f"Environment configuration file not found: {env_file}")
            return None
        
        return self._load_yaml_file(env_file)
    
    def _load_site_configurations(self) -> Dict[str, SiteConfiguration]:
        """Load all site-specific configurations."""
        site_configs = {}
        
        if not self.sites_dir.exists():
            logger.warning(f"Sites directory not found: {self.sites_dir}")
            return site_configs
        
        for site_file in self.sites_dir.glob("*.yaml"):
            try:
                site_name = site_file.stem
                site_data = self._load_yaml_file(site_file)
                
                # Validate site configuration
                site_config = SiteConfiguration(**site_data)
                site_configs[site_name] = site_config
                
                logger.debug(f"Loaded site configuration: {site_name}")
            
            except Exception as e:
                logger.error(f"Failed to load site configuration {site_file}: {e}")
                # Continue loading other sites
        
        return site_configs
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                return content or {}
        except yaml.YAMLError as e:
            raise ConfigurationLoadError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationLoadError(f"Failed to read {file_path}: {e}")
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationLoadError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationLoadError(f"Failed to read {file_path}: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries with override taking precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Merged dictionary
            
        Note:
            - Nested dictionaries are recursively merged
            - Lists and other types are replaced entirely by override values
            - Uses deep copy to avoid modifying original dictionaries
        """
        # Use deep copy to avoid any potential reference issues
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # For non-dict values, override completely
                # Use deep copy for mutable objects to avoid reference issues
                if isinstance(value, (dict, list)):
                    result[key] = copy.deepcopy(value)
                else:
                    result[key] = value
        
        return result