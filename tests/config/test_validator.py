"""Tests for configuration validation utilities."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from aioresponses import aioresponses

from doc_crawler.config.validator import ConfigurationValidator
from doc_crawler.config.models import BaseConfiguration, SiteConfiguration, Environment
from doc_crawler.config.exceptions import ConfigurationValidationError
from ..database.models.conftest import sample_base_config, sample_site_config


class TestConfigurationValidator:
    """Test configuration validator functionality."""
    
    def test_init(self):
        """Test validator initialization."""
        validator = ConfigurationValidator(timeout=15)
        assert validator.timeout == 15
    
    async def test_validate_configuration_success(self, sample_base_config):
        """Test successful configuration validation."""
        validator = ConfigurationValidator()
        config = BaseConfiguration(**sample_base_config)
        
        warnings = await validator.validate_configuration(config)
        assert isinstance(warnings, list)
        # May have warnings but should not raise errors
    
    async def test_validate_configuration_with_errors(self):
        """Test configuration validation with errors."""
        validator = ConfigurationValidator()
        
        # Create config with validation errors
        config_data = {
            "environment": "prod",
            "debug": True,  # Error: debug in production
            "notifications": {"enabled": True},  # Error: no notification methods
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"}
        }
        
        # This should fail at Pydantic level before reaching advanced validation
        with pytest.raises(Exception):  # Could be ValidationError or ConfigurationValidationError
            config = BaseConfiguration(**config_data)
    
    def test_validate_business_rules_production(self):
        """Test business rule validation for production."""
        validator = ConfigurationValidator()
        
        config_data = {
            "environment": "prod",
            "debug": False,  # Correct for production
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
            "crawling": {"default_delay": 0.8},  # Warning: short delay in prod
            "logging": {"level": "DEBUG"},  # Warning: debug logging in prod
            "notifications": {
                "email": {
                    "smtp_server": "smtp.example.com",
                    "username": "username",
                    "password": "password",
                    "from_address": "user@example.com",
                    "recipients": ["receipt@example.com", "receipt2@example.com"]
                }
            }
        }
        
        config = BaseConfiguration(**config_data)
        warnings, errors = validator._validate_business_rules(config)
        
        assert any("less than 1 second in production" in w for w in warnings)
        assert any("Debug logging" in w for w in warnings)
        assert len(errors) == 0  # Should be warnings, not errors
    
    def test_validate_business_rules_development(self):
        """Test business rule validation for development."""
        validator = ConfigurationValidator()
        
        config_data = {
            "environment": "dev",
            "debug": True,
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
            "crawling": {"max_concurrent_requests": 15},  # Warning: high concurrency
            "notifications": {
                "email": {
                    "smtp_server": "smtp.example.com",
                    "username": "username",
                    "password": "password",
                    "from_address": "user@example.com",
                    "recipients": ["receipt@example.com", "receipt2@example.com"]
                }
            }
        }
        
        config = BaseConfiguration(**config_data)
        warnings, errors = validator._validate_business_rules(config)
        
        assert any("High concurrent request count" in w for w in warnings)
        assert len(errors) == 0
    
    def test_validate_business_rules_notifications(self):
        """Test business rule validation for notifications."""
        validator = ConfigurationValidator()
        
        config_data = {
            "environment": "dev",
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
            "notifications": {"enabled": True}  # Error: no methods configured
        }
        
        # This should fail at Pydantic validation level
        with pytest.raises(Exception):
            BaseConfiguration(**config_data)
    
    async def test_validate_site_configurations_empty(self):
        """Test site configuration validation with no sites."""
        validator = ConfigurationValidator()
        
        warnings, errors = await validator._validate_site_configurations({})
        
        assert any("No site configurations found" in w for w in warnings)
        assert len(errors) == 0
    
    async def test_validate_site_configurations_warnings(self, sample_site_config):
        """Test site configuration validation with warnings."""
        validator = ConfigurationValidator()
        
        # Modify config to trigger warnings
        sample_site_config["delay"] = 0.3  # Very short delay
        sample_site_config["max_concurrent"] = 10  # High concurrency
        
        site_config = SiteConfiguration(**sample_site_config)
        sites = {"test_site": site_config}
        
        warnings, errors = await validator._validate_site_configurations(sites)
        
        assert any("very short delay" in w for w in warnings)
        assert any("high concurrent requests" in w for w in warnings)
        assert len(errors) == 0
    
    async def test_validate_site_configurations_invalid_patterns(self, sample_site_config):
        """Test site configuration validation with invalid URL patterns."""
        validator = ConfigurationValidator()
        
        # Add invalid URL pattern
        sample_site_config["allowed_urls"].append({
            "pattern": "[invalid-regex",
            "type": "regex",
            "description": "Invalid pattern"
        })
        
        sites = {}
        with pytest.raises(Exception):
            SiteConfiguration(**sample_site_config)
    
    async def test_validate_site_configurations_conflicting_patterns(self, sample_site_config):
        """Test site configuration validation with conflicting patterns."""
        validator = ConfigurationValidator()
        
        # Add conflicting patterns
        sample_site_config["denied_urls"] = [
            {
                "pattern": "^https://iep.utm\\.edu/[a-zA-Z0-9-]+/?$",  # Same as allowed
                "type": "regex",
                "description": "Conflicting pattern"
            }
        ]
        
        site_config = SiteConfiguration(**sample_site_config)
        sites = {"test_site": site_config}
        
        warnings, errors = await validator._validate_site_configurations(sites)
        
        assert any("conflicting URL patterns" in w for w in warnings)

    async def test_check_site_accessibility_success(self, sample_site_config):
        """Test successful site accessibility check."""
        validator = ConfigurationValidator()
        site_config = SiteConfiguration(**sample_site_config)

        with aioresponses() as m:
            # Mock the actual URL that will be requested
            m.get(str(site_config.base_url), status=200)
            
            result = await validator._check_site_accessibility("test_site", site_config)
            assert result is None    

    async def test_check_site_accessibility_http_error(self, sample_site_config):
        """Test site accessibility check with HTTP error."""
        validator = ConfigurationValidator()
        site_config = SiteConfiguration(**sample_site_config)
        
        with aioresponses() as m:
            # Mock HTTP 404 error response
            m.get(str(site_config.base_url), status=404)
            
            result = await validator._check_site_accessibility("test_site", site_config)
            assert "HTTP 404" in result    

    async def test_check_site_accessibility_timeout(self, sample_site_config):
        """Test site accessibility check with timeout."""
        validator = ConfigurationValidator()
        site_config = SiteConfiguration(**sample_site_config)
        
        with aioresponses() as m:
            # Mock timeout exception
            m.get(str(site_config.base_url), exception=asyncio.TimeoutError())
            
            result = await validator._check_site_accessibility("test_site", site_config)
            assert "timed out" in result    

    async def test_check_site_accessibility_with_health_check(self, sample_site_config):
        """Test site accessibility check with health check URL."""
        validator = ConfigurationValidator()
        
        # Add health check URL
        sample_site_config["health_check_url"] = "https://iep.utm.edu/health"
        site_config = SiteConfiguration(**sample_site_config)
        
        with aioresponses() as m:
            # Mock successful responses for both URLs
            m.get(str(site_config.base_url), status=200)  # Main URL
            m.get(str(site_config.health_check_url), status=200)     # Health check URL
            
            result = await validator._check_site_accessibility("test_site", site_config)
            assert result is None
            
            # Verify both URLs were checked
            assert len(m.requests) == 2
            
    async def test_validate_external_resources_skip_dev(self, sample_base_config):
        """Test that external resource validation is skipped in development."""
        validator = ConfigurationValidator()
        
        sample_base_config["environment"] = "dev"
        config = BaseConfiguration(**sample_base_config)
        
        warnings, errors = await validator._validate_external_resources(config)
        
        assert len(warnings) == 0
        assert len(errors) == 0
    
    async def test_validate_external_resources_with_sites(self, sample_base_config, sample_site_config):
        """Test external resource validation with sites."""
        validator = ConfigurationValidator()
        
        sample_base_config["environment"] = "prod"
        sample_base_config["sites"] = {"test_site": sample_site_config}
        config = BaseConfiguration(**sample_base_config)
        
        # Mock site accessibility check
        with patch.object(validator, '_check_site_accessibility', return_value=None):
            warnings, errors = await validator._validate_external_resources(config)
            
            assert len(errors) == 0  # Should be successful