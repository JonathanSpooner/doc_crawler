"""
Pydantic configuration models for the philosophy text crawler.

This module defines comprehensive configuration models with validation,
type safety, and environment-aware loading capabilities.
"""

import re
from datetime import datetime, time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse
import warnings

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    validator,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class LogLevel(str, Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DatabaseConfiguration(BaseModel):
    """Database connection and configuration settings."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    url: SecretStr = Field(
        description="Database connection URL",
        examples=["postgresql://user:pass@localhost:5432/crawler_db"]
    )
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, le=300, description="Pool timeout in seconds")
    pool_recycle: int = Field(default=3600, ge=300, description="Pool recycle time in seconds")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    
    @field_validator('url')
    @classmethod
    def validate_database_url(cls, v: SecretStr) -> SecretStr:
        """Validate database URL format."""
        url_str = v.get_secret_value()
        parsed = urlparse(url_str)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Database URL must be a valid connection string")
        return v


class LoggingConfiguration(BaseModel):
    """Logging configuration settings."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    level: LogLevel = Field(default=LogLevel.INFO, description="Global logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_path: Optional[Path] = Field(default=None, description="Log file path")
    max_bytes: int = Field(default=10485760, ge=1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, ge=1, le=100, description="Number of backup log files")
    structured: bool = Field(default=False, description="Enable structured JSON logging")
    
    # Component-specific log levels
    crawler_level: LogLevel = Field(default=LogLevel.INFO, description="Crawler component log level")
    config_level: LogLevel = Field(default=LogLevel.WARNING, description="Configuration log level")
    database_level: LogLevel = Field(default=LogLevel.WARNING, description="Database log level")


class SecurityConfiguration(BaseModel):
    """Security and authentication settings."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    api_key: Optional[SecretStr] = Field(default=None, description="API authentication key")
    secret_key: SecretStr = Field(description="Application secret key for signing")
    token_expiry: int = Field(default=3600, ge=300, le=86400, description="Token expiry in seconds")
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000, description="API rate limit per minute")
    allowed_hosts: List[str] = Field(default_factory=list, description="Allowed host patterns")
    cors_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")
    
    @field_validator('allowed_hosts')
    @classmethod
    def validate_host_patterns(cls, v: List[str]) -> List[str]:
        """Validate host patterns."""
        HOST_PATTERN_WITH_WILDCARDS = r'^(?:\*\.)?(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$|^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^\[(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\]$|^\[::1\]$|^\[::\]$'
        for pattern in v:
            if not re.match(HOST_PATTERN_WITH_WILDCARDS, pattern, re.IGNORECASE):
                raise ValueError(f"Invalid host pattern: {pattern}")
        return v
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins_patterns(cls, v: List[str]) -> List[str]:
        """Validate host patterns."""
        CORS_ORIGIN_REGEX = re.compile(
            r'^https?://'                    # http:// or https://
            r'(?:'                           # Start non-capturing group for domain
                r'(?:[a-zA-Z0-9-]+\.)*'      # Subdomains (optional, repeating)
                r'[a-zA-Z0-9-]+'             # Domain name
                r'\.[a-zA-Z]{2,}'            # TLD (at least 2 chars)
            r'|'                             # OR
                r'localhost'                 # localhost
            r'|'                             # OR
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'  # IPv4
            r')'                             # End domain group
            r'(?::\d{1,5})?'                 # Optional port
            r'$'                             # End of string
        )
        for pattern in v:
            if not CORS_ORIGIN_REGEX.match(pattern):
                raise ValueError(f"Invalid cors_origin pattern: {pattern}")
        return v


class CrawlingConfiguration(BaseModel):
    """Default crawling behavior and limits."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    # Request settings
    default_delay: float = Field(default=1.0, ge=0.1, le=60.0, description="Default delay between requests")
    max_concurrent_requests: int = Field(default=5, ge=1, le=50, description="Max concurrent requests")
    request_timeout: int = Field(default=30, ge=5, le=300, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: float = Field(default=2.0, ge=0.5, le=30.0, description="Delay between retries")
    
    # User agent settings
    user_agent: str = Field(
        default="PhilosophyCrawler/1.0 (+https://example.com/crawler-info)",
        description="Default user agent string"
    )
    respect_robots_txt: bool = Field(default=True, description="Respect robots.txt files")
    
    # Content settings
    max_page_size: int = Field(default=10485760, ge=1024, description="Max page size in bytes")
    allowed_content_types: Set[str] = Field(
        default_factory=lambda: {"text/html", "application/xhtml+xml"},
        description="Allowed content types"
    )
    
    # Politeness settings
    min_delay: float = Field(default=0.5, ge=0.1, description="Minimum delay between requests")
    burst_delay: float = Field(default=5.0, ge=1.0, description="Delay after burst detection")
    max_pages_per_domain: int = Field(default=1000, ge=1, description="Max pages per domain per session")
    
    @field_validator('default_delay', 'min_delay', 'retry_delay', 'burst_delay')
    @classmethod
    def validate_delays(cls, v: float, info) -> float:
        """Ensure delays are reasonable for polite crawling."""
        if info.field_name == 'default_delay' and v < 0.5:
            raise ValueError("Default delay should be at least 0.5 seconds for politeness")
        return v


class EmailConfiguration(BaseModel):
    """Email notification settings."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    smtp_server: str = Field(description="SMTP server hostname")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP server port")
    username: str = Field(description="SMTP username")
    password: SecretStr = Field(description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    from_address: str = Field(description="From email address")
    recipients: List[str] = Field(description="List of recipient email addresses")
    
    @field_validator('recipients')
    @classmethod
    def validate_email_addresses(cls, v: List[str]) -> List[str]:
        """Validate email address format."""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for email in v:
            if not email_pattern.match(email):
                raise ValueError(f"Invalid email address: {email}")
        return v


class SlackConfiguration(BaseModel):
    """Slack notification settings."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    webhook_url: SecretStr = Field(description="Slack webhook URL")
    channel: str = Field(default="#alerts", description="Default Slack channel")
    username: str = Field(default="PhilosophyCrawler", description="Bot username")
    icon_emoji: str = Field(default=":robot_face:", description="Bot icon emoji")
    mention_users: List[str] = Field(default_factory=list, description="Users to mention for critical alerts")


class NotificationConfiguration(BaseModel):
    """Notification and alerting configuration."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    enabled: bool = Field(default=True, description="Enable notifications")
    email: Optional[EmailConfiguration] = Field(default=None, description="Email settings")
    slack: Optional[SlackConfiguration] = Field(default=None, description="Slack settings")
    
    # Alert thresholds
    error_threshold: int = Field(default=10, ge=1, description="Error count threshold")
    failure_rate_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Failure rate threshold")
    queue_size_threshold: int = Field(default=1000, ge=1, description="Queue size threshold")
    
    # Notification schedules
    quiet_hours_start: Optional[time] = Field(default=None, description="Quiet hours start time")
    quiet_hours_end: Optional[time] = Field(default=None, description="Quiet hours end time")
    max_alerts_per_hour: int = Field(default=5, ge=1, le=100, description="Max alerts per hour")
    
    @model_validator(mode='after')
    def validate_notification_settings(self) -> 'NotificationConfiguration':
        """Validate notification configuration consistency."""
        if self.enabled and not self.email and not self.slack:
            raise ValueError("At least one notification method must be configured when notifications are enabled")
        
        if self.quiet_hours_start and self.quiet_hours_end:
            if self.quiet_hours_start == self.quiet_hours_end:
                raise ValueError("Quiet hours start and end times cannot be the same")
        
        return self


class URLPattern(BaseModel):
    """URL pattern configuration for crawling rules."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    pattern: str = Field(description="URL pattern (regex or glob)")
    type: str = Field(default="regex", pattern="^(regex|glob)$", description="Pattern type")
    description: Optional[str] = Field(default=None, description="Pattern description")
    
    @field_validator('pattern')
    @classmethod
    def validate_pattern(cls, v: str, info) -> str:
        """Validate pattern syntax."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v


class ContentSelector(BaseModel):
    """CSS/XPath selector for content extraction."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    name: str = Field(description="Selector name/identifier")
    selector: str = Field(description="CSS or XPath selector")
    type: str = Field(default="css", pattern="^(css|xpath)$", description="Selector type")
    required: bool = Field(default=False, description="Whether this selector is required")
    multiple: bool = Field(default=False, description="Whether to select multiple elements")


class SiteConfiguration(BaseModel):
    """Site-specific crawling configuration."""
    model_config = ConfigDict(
        extra="forbid",
        # frozen=True,  # For immutable configs in production
        validate_default=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    # Site identification
    name: str = Field(description="Site display name")
    base_url: HttpUrl = Field(description="Base URL of the site")
    domains: List[str] = Field(description="Allowed domains for this site")
    
    # Crawling behavior
    enabled: bool = Field(default=True, description="Whether crawling is enabled for this site")
    priority: int = Field(default=1, ge=1, le=10, description="Crawling priority (1=highest)")
    
    # URL patterns
    allowed_urls: List[URLPattern] = Field(default_factory=list, description="Allowed URL patterns")
    denied_urls: List[URLPattern] = Field(default_factory=list, description="Denied URL patterns")
    
    # Content extraction
    content_selectors: List[ContentSelector] = Field(default_factory=list, description="Content selectors")
    title_selector: Optional[str] = Field(default="title", description="Title selector")
    author_selector: Optional[str] = Field(default=None, description="Author selector")
    date_selector: Optional[str] = Field(default=None, description="Publication date selector")
    
    # Site-specific politeness
    delay: Optional[float] = Field(default=None, ge=0.1, le=60.0, description="Site-specific delay")
    max_concurrent: Optional[int] = Field(default=None, ge=1, le=10, description="Max concurrent requests")
    user_agent: Optional[str] = Field(default=None, description="Site-specific user agent")
    
    # Rate limiting
    requests_per_minute: Optional[int] = Field(default=None, ge=1, le=60, description="Requests per minute limit")
    daily_limit: Optional[int] = Field(default=None, ge=1, description="Daily request limit")
    
    # Content processing
    clean_html: bool = Field(default=True, description="Clean HTML content")
    extract_links: bool = Field(default=True, description="Extract links from pages")
    follow_links: bool = Field(default=True, description="Follow extracted links")
    max_depth: int = Field(default=5, ge=1, le=20, description="Maximum crawling depth")
    
    # Monitoring
    health_check_url: Optional[HttpUrl] = Field(default=None, description="Health check URL")
    monitor_changes: bool = Field(default=True, description="Monitor content changes")
    notification_level: NotificationLevel = Field(
        default=NotificationLevel.MEDIUM,
        description="Notification level for this site"
    )
    
    @field_validator('domains')
    @classmethod
    def validate_domains(cls, v: List[str]) -> List[str]:
        """Validate domain formats."""
        domain_pattern = re.compile(r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$')
        for domain in v:
            if not domain_pattern.match(domain):
                raise ValueError(f"Invalid domain format: {domain}")
        return v
    
    @model_validator(mode='after')
    def validate_site_configuration(self) -> 'SiteConfiguration':
        """Validate site configuration consistency."""
        # Check that base_url domain is in allowed domains
        base_domain = urlparse(str(self.base_url)).netloc
        if base_domain not in self.domains:
            raise ValueError(f"Base URL domain {base_domain} must be in allowed domains")
        
        # Validate content selectors
        selector_names = [sel.name for sel in self.content_selectors]
        if len(selector_names) != len(set(selector_names)):
            raise ValueError("Content selector names must be unique")
        
        return self


class BaseConfiguration(BaseSettings):
    """
    Main configuration class that combines all configuration sections.
    
    This class supports hierarchical configuration loading with the following precedence:
    1. Environment variables (highest priority)
    2. Runtime overrides
    3. Site-specific configurations
    4. Environment-specific configuration files
    5. Base configuration file (lowest priority)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="forbid",
        validate_assignment=True,
        # frozen=True,  # Ensure immutability in production
        use_enum_values=True,  # Convert enums to their values
        populate_by_name=True  # Allow population by field name and alias
    )
    
    # Environment and metadata
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Deployment environment")
    version: str = Field(default="1.0.0", description="Configuration version")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    # Configuration sections
    database: DatabaseConfiguration = Field(description="Database configuration")
    logging: LoggingConfiguration = Field(default_factory=LoggingConfiguration, description="Logging configuration")
    security: SecurityConfiguration = Field(description="Security configuration")
    crawling: CrawlingConfiguration = Field(default_factory=CrawlingConfiguration, description="Default crawling configuration")
    notifications: NotificationConfiguration = Field(default_factory=NotificationConfiguration, description="Notification configuration")
    
    # Site configurations (loaded separately)
    sites: Dict[str, SiteConfiguration] = Field(default_factory=dict, description="Site-specific configurations")
    
    # Runtime settings
    debug: bool = Field(default=False, description="Enable debug mode")
    hot_reload: bool = Field(default=False, description="Enable hot reloading (dev only)")
    config_dir: Path = Field(default=Path("config"), description="Configuration directory path")
    
    @field_validator('hot_reload')
    @classmethod
    def validate_hot_reload(cls, v: bool, info) -> bool:
        """Hot reload only allowed in development."""
        # Note: This validation runs before environment is set, so we need to check differently
        # This will be enforced in the configuration manager
        return v
    
    @model_validator(mode="before")
    @classmethod
    def apply_defaults_and_validate(cls, values: Any) -> Any:
        env = values.get("environment")
        debug = values.get("debug")
        logging = values.get("logging", {})
        log_level = logging.get("level") if isinstance(logging, dict) else getattr(logging, "level", None)
        log_file_path = logging.get("file_path") if isinstance(logging, dict) else getattr(logging, "file_path", None)


        if env == Environment.PRODUCTION:
            if debug:
                raise ValueError("Debug mode not allowed in production")
            if values.get("hot_reload"):
                raise ValueError("Hot reload not allowed in production")
            if log_level == LogLevel.DEBUG:
                warnings.warn("Debug logging not recommended in production")

        if env == Environment.DEVELOPMENT:
            if not debug:
                print("!!!!!!DEBUG HAS BEEN TURNED OFF!!!!!")
                print("!!!!!!DEBUG HAS BEEN TURNED OFF!!!!!")
                print("!!!!!!DEBUG HAS BEEN TURNED OFF!!!!!")
            if not log_file_path:
                logging.setdefault("file_path", Path("logs/crawler.log"))
                values["logging"] = logging

        return values
    
    def mask_sensitive_values(self) -> Dict[str, Any]:
        """Return configuration with sensitive values masked for logging."""
        config_dict = self.model_dump()
        
        # Mask sensitive fields
        sensitive_paths = [
            ["database", "url"],
            ["security", "api_key"],
            ["security", "secret_key"],
            ["notifications", "email", "password"],
            ["notifications", "slack", "webhook_url"],
        ]
        
        for path in sensitive_paths:
            current = config_dict
            for key in path[:-1]:
                if key in current and isinstance(current[key], dict):
                    current = current[key]
                else:
                    break
            else:
                if path[-1] in current:
                    current[path[-1]] = "***MASKED***"
        
        return config_dict