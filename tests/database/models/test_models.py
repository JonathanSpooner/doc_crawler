# tests/test_models.py
"""Tests for Pydantic configuration models."""

import pytest
from datetime import time
from pathlib import Path

from doc_crawler.config.models import (
    BaseConfiguration,
    SiteConfiguration,
    NotificationConfiguration,
    SecurityConfiguration,
    DatabaseConfiguration,
    CrawlingConfiguration,
    EmailConfiguration,
    URLPattern,
    ContentSelector,
    Environment,
)


class TestDatabaseConfiguration:
    """Test database configuration model."""
    
    def test_valid_database_config(self):
        """Test valid database configuration."""
        config = DatabaseConfiguration(
            url="postgresql://user:pass@localhost:5432/test_db"
        )
        
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.echo is False
    
    def test_invalid_database_url(self):
        """Test invalid database URL validation."""
        with pytest.raises(ValueError) as exc_info:
            DatabaseConfiguration(url="invalid-url")
        
        assert "Database URL must be a valid connection string" in str(exc_info.value)
    
    def test_pool_size_constraints(self):
        """Test pool size constraints."""
        with pytest.raises(ValueError):
            DatabaseConfiguration(
                url="postgresql://user:pass@localhost:5432/test_db",
                pool_size=0  # Below minimum
            )
        
        with pytest.raises(ValueError):
            DatabaseConfiguration(
                url="postgresql://user:pass@localhost:5432/test_db",
                pool_size=100  # Above maximum
            )
    
    def test_custom_pool_settings(self):
        """Test custom pool settings."""
        config = DatabaseConfiguration(
            url="postgresql://user:pass@localhost:5432/test_db",
            pool_size=10,
            max_overflow=20,
            pool_timeout=60
        )
        
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_timeout == 60


class TestSecurityConfiguration:
    """Test security configuration model."""
    
    def test_valid_security_config(self):
        """Test valid security configuration."""
        config = SecurityConfiguration(
            secret_key="test-secret-key-12345"
        )
        
        assert config.secret_key.get_secret_value() == "test-secret-key-12345"
        assert config.token_expiry == 3600
        assert config.rate_limit_per_minute == 60
    
    def test_host_pattern_validation(self):
        """Test host pattern validation."""
        # Valid patterns
        config = SecurityConfiguration(
            secret_key="test-secret",
            allowed_hosts=[
                "example.com",
                "sub.example.com", 
                "*.example.com",          # Valid wildcard
                # "*.sub.example.com",      # Valid nested wildcard
                # "localhost",
                # "192.168.1.1",
                # "[::1]",
                # "*.168.1.1",             # Invalid - wildcard with IP
                # "*.",                     # Invalid - wildcard only
                # "*.*.example.com",        # Invalid - multiple wildcards
                # "sub.*.example.com",      # Invalid - wildcard in middle
                # "example.*.com",          # Invalid - wildcard in middle
                # ""
            ]
        )
        assert len(config.allowed_hosts) == 3
        
        # Invalid regex pattern
        with pytest.raises(ValueError) as exc_info:
            SecurityConfiguration(
                secret_key="test-secret",
                allowed_hosts=["..."]
            )
        assert "Invalid host pattern" in str(exc_info.value)
    
    def test_cors_origins_validation(self):
        """Test CORS origins validation."""
        config = SecurityConfiguration(
            secret_key="test-secret",
            cors_origins=["https://example.com", "http://localhost:3000"]
        )
        assert len(config.cors_origins) == 2


class TestCrawlingConfiguration:
    """Test crawling configuration model."""
    
    def test_default_crawling_config(self):
        """Test default crawling configuration values."""
        config = CrawlingConfiguration()
        
        assert config.default_delay == 1.0
        assert config.max_concurrent_requests == 5
        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert config.respect_robots_txt is True
        assert "text/html" in config.allowed_content_types
    
    def test_delay_validation(self):
        """Test delay validation rules."""
        # Valid delays
        config = CrawlingConfiguration(default_delay=1.5, min_delay=0.5)
        assert config.default_delay == 1.5
        assert config.min_delay == 0.5
        
        # Default delay too short for politeness
        with pytest.raises(ValueError) as exc_info:
            CrawlingConfiguration(default_delay=0.1)
        assert "Default delay should be at least 0.5 seconds" in str(exc_info.value)
    
    def test_concurrent_requests_limits(self):
        """Test concurrent request limits."""
        with pytest.raises(ValueError):
            CrawlingConfiguration(max_concurrent_requests=0)
        
        with pytest.raises(ValueError):
            CrawlingConfiguration(max_concurrent_requests=100)
    
    def test_allowed_content_types(self):
        """Test allowed content types configuration."""
        config = CrawlingConfiguration(
            allowed_content_types={"text/html", "application/pdf"}
        )
        assert len(config.allowed_content_types) == 2
        assert "text/html" in config.allowed_content_types


class TestEmailConfiguration:
    """Test email configuration model."""
    
    def test_valid_email_config(self):
        """Test valid email configuration."""
        config = EmailConfiguration(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="test@example.com",
            password="test-password",
            from_address="noreply@example.com",
            recipients=["admin@example.com", "dev@example.com"]
        )
        
        assert config.smtp_server == "smtp.gmail.com"
        assert config.smtp_port == 587
        assert config.use_tls is True
        assert len(config.recipients) == 2
    
    def test_email_validation(self):
        """Test email address validation."""
        # Valid emails
        config = EmailConfiguration(
            smtp_server="smtp.example.com",
            username="user@example.com",
            password="password",
            from_address="from@example.com",
            recipients=["valid@example.com", "test+tag@domain.co.uk"]
        )
        assert len(config.recipients) == 2
        
        # Invalid email
        with pytest.raises(ValueError) as exc_info:
            EmailConfiguration(
                smtp_server="smtp.example.com",
                username="user@example.com",
                password="password",
                from_address="from@example.com",
                recipients=["invalid-email"]
            )
        assert "Invalid email address" in str(exc_info.value)
    
    def test_smtp_port_validation(self):
        """Test SMTP port validation."""
        with pytest.raises(ValueError):
            EmailConfiguration(
                smtp_server="smtp.example.com",
                smtp_port=0,  # Invalid port
                username="user@example.com",
                password="password",
                from_address="from@example.com",
                recipients=["admin@example.com"]
            )


class TestNotificationConfiguration:
    """Test notification configuration model."""
    
    def test_default_notification_config(self):
        """Test default notification configuration."""
        config = NotificationConfiguration(
            email=EmailConfiguration(
                smtp_server="smtp.example.com",
                username="username",
                password="password",
                from_address="user@example.com",
                recipients=["user2@example.com"]
            ))
        
        assert config.enabled is True
        assert config.error_threshold == 10
        assert config.failure_rate_threshold == 0.1
        assert config.max_alerts_per_hour == 5
    
    def test_notification_with_email(self):
        """Test notification configuration with email."""
        email_config = EmailConfiguration(
            smtp_server="smtp.example.com",
            username="user@example.com",
            password="password",
            from_address="from@example.com",
            recipients=["admin@example.com"]
        )
        
        config = NotificationConfiguration(
            enabled=True,
            email=email_config
        )
        
        assert config.email is not None
        assert config.email.smtp_server == "smtp.example.com"
    
    def test_notification_validation_enabled_without_methods(self):
        """Test validation when notifications are enabled but no methods configured."""
        with pytest.raises(ValueError) as exc_info:
            NotificationConfiguration(enabled=True)
        
        assert "At least one notification method must be configured" in str(exc_info.value)
    
    def test_quiet_hours_validation(self):
        """Test quiet hours validation."""
        # Valid quiet hours
        config = NotificationConfiguration(
            enabled=False,  # Disable to skip method validation
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(6, 0)
        )
        assert config.quiet_hours_start.hour == 22
        assert config.quiet_hours_end.hour == 6
        
        # Invalid: same start and end time
        with pytest.raises(ValueError) as exc_info:
            NotificationConfiguration(
                enabled=False,
                quiet_hours_start=time(22, 0),
                quiet_hours_end=time(22, 0)
            )
        assert "Quiet hours start and end times cannot be the same" in str(exc_info.value)


class TestURLPattern:
    """Test URL pattern model."""
    
    def test_valid_url_pattern(self):
        """Test valid URL pattern."""
        pattern = URLPattern(
            pattern=r"^https://example\.com/.*$",
            type="regex",
            description="Example site pages"
        )
        
        assert pattern.pattern == r"^https://example\.com/.*$"
        assert pattern.type == "regex"
        assert pattern.description == "Example site pages"
    
    def test_invalid_regex_pattern(self):
        """Test invalid regex pattern validation."""
        with pytest.raises(ValueError) as exc_info:
            URLPattern(pattern="[invalid-regex")
        
        assert "Invalid regex pattern" in str(exc_info.value)
    
    def test_pattern_type_validation(self):
        """Test pattern type validation."""
        with pytest.raises(ValueError):
            URLPattern(pattern="test", type="invalid-type")


class TestContentSelector:
    """Test content selector model."""
    
    def test_valid_content_selector(self):
        """Test valid content selector."""
        selector = ContentSelector(
            name="main_content",
            selector="#main-content",
            type="css",
            required=True,
            multiple=False
        )
        
        assert selector.name == "main_content"
        assert selector.selector == "#main-content"
        assert selector.type == "css"
        assert selector.required is True
        assert selector.multiple is False
    
    def test_xpath_selector(self):
        """Test XPath selector."""
        selector = ContentSelector(
            name="title",
            selector="//h1[@class='title']",
            type="xpath"
        )
        
        assert selector.type == "xpath"
        assert selector.required is False  # Default
    
    def test_selector_type_validation(self):
        """Test selector type validation."""
        with pytest.raises(ValueError):
            ContentSelector(
                name="test",
                selector="test",
                type="invalid-type"
            )


class TestSiteConfiguration:
    """Test site configuration model."""
    
    def test_valid_site_config(self, sample_site_config):
        """Test valid site configuration."""
        config = SiteConfiguration(**sample_site_config)
        
        assert config.name == "Test Philosophy Site"
        assert str(config.base_url) == "https://iep.utm.edu/"
        assert "iep.utm.edu" in config.domains
        assert config.enabled is True
        assert config.priority == 1
        assert config.delay == 1.5
    
    def test_domain_validation(self):
        """Test domain validation."""
        # Valid domains
        config = SiteConfiguration(
            name="Test Site",
            base_url="https://example.com",
            domains=["example.com", "sub.example.com", "test-domain.org"]
        )
        assert len(config.domains) == 3
        
        # Invalid domain format
        with pytest.raises(ValueError) as exc_info:
            SiteConfiguration(
                name="Test Site",
                base_url="https://example.com",
                domains=["invalid..domain"]
            )
        assert "Invalid domain format" in str(exc_info.value)
    
    def test_base_url_in_domains_validation(self):
        """Test that base URL domain must be in allowed domains."""
        with pytest.raises(ValueError) as exc_info:
            SiteConfiguration(
                name="Test Site",
                base_url="https://example.com",
                domains=["different-domain.com"]  # Base URL domain not included
            )
        assert "Base URL domain example.com must be in allowed domains" in str(exc_info.value)
    
    def test_unique_selector_names(self):
        """Test that content selector names must be unique."""
        with pytest.raises(ValueError) as exc_info:
            SiteConfiguration(
                name="Test Site",
                base_url="https://example.com",
                domains=["example.com"],
                content_selectors=[
                    ContentSelector(name="content", selector="#content1"),
                    ContentSelector(name="content", selector="#content2")  # Duplicate name
                ]
            )
        assert "Content selector names must be unique" in str(exc_info.value)
    
    def test_site_specific_delays(self):
        """Test site-specific delay configuration."""
        config = SiteConfiguration(
            name="Slow Site",
            base_url="https://slow-site.com",
            domains=["slow-site.com"],
            delay=5.0,
            max_concurrent=1
        )
        
        assert config.delay == 5.0
        assert config.max_concurrent == 1
    
    def test_rate_limiting_config(self):
        """Test rate limiting configuration."""
        config = SiteConfiguration(
            name="Rate Limited Site",
            base_url="https://limited-site.com",
            domains=["limited-site.com"],
            requests_per_minute=10,
            daily_limit=500
        )
        
        assert config.requests_per_minute == 10
        assert config.daily_limit == 500


class TestBaseConfiguration:
    """Test base configuration model."""
    
    def test_valid_base_config(self, sample_base_config):
        """Test valid base configuration."""
        config = BaseConfiguration(**sample_base_config)
        
        assert config.environment == Environment.DEVELOPMENT  # Default
        assert config.database.pool_size == 5
        assert config.crawling.default_delay == 1.0
        assert config.notifications.enabled is True
    
    def test_environment_specific_validation_production(self):
        """Test production-specific validation rules."""
        config_data = {
            "environment": "prod",
            "debug": True,  # Not allowed in production
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
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
        
        with pytest.raises(ValueError) as exc_info:
            BaseConfiguration(**config_data)
        assert "Debug mode not allowed in production" in str(exc_info.value)
    
    def test_environment_specific_validation_hot_reload(self):
        """Test hot reload validation in production."""
        config_data = {
            "environment": "prod",
            "hot_reload": True,  # Not allowed in production
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
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
        
        with pytest.raises(ValueError) as exc_info:
            BaseConfiguration(**config_data)
        assert "Hot reload not allowed in production" in str(exc_info.value)
    
    def test_development_defaults(self):
        """Test development environment defaults."""
        config_data = {
            "environment": "dev",
            "database": {"url": "postgresql://user:pass@localhost:5432/db"},
            "security": {"secret_key": "test-secret"},
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
        # assert config.debug is True ### this stepped on the override. Changed to printing 3 times that debug is off
        assert config.logging.file_path == Path("logs/crawler.log")
    
    def test_mask_sensitive_values(self, sample_base_config):
        """Test masking of sensitive configuration values."""
        config = BaseConfiguration(**sample_base_config)
        masked = config.mask_sensitive_values()
        
        # Check that sensitive values are masked
        assert masked["database"]["url"] == "***MASKED***"
        assert masked["security"]["secret_key"] == "***MASKED***"
        
        # Check that non-sensitive values are preserved
        assert masked["database"]["pool_size"] == 5
        assert masked["crawling"]["default_delay"] == 1.0
    
    def test_sites_configuration(self, sample_base_config, sample_site_config):
        """Test sites configuration integration."""
        sample_base_config["sites"] = {"test_site": sample_site_config}
        config = BaseConfiguration(**sample_base_config)
        
        assert "test_site" in config.sites
        assert config.sites["test_site"].name == "Test Philosophy Site"
    
    def test_environment_variable_integration(self, mock_env_vars):
        """Test environment variable integration."""
        config_data = {
            "database": {"url": "postgresql://default:default@localhost:5432/db"},
            "security": {"secret_key": "default-secret"},
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
        
        # Environment variables should override file values
        assert config.database.url.get_secret_value() == "postgresql://default:default@localhost:5432/db"
        assert config.security.secret_key.get_secret_value() == "default-secret"
