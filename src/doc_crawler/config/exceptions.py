"""Configuration-related exceptions."""

class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigurationLoadError(ConfigurationError):
    """Error loading configuration files."""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Error validating configuration values."""
    pass


class ConfigurationUpdateError(ConfigurationError):
    """Error updating runtime configuration."""
    pass