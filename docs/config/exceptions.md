### ConfigurationError(Exception)
- Inherits from `Exception`. Base exception for configuration errors.

### ConfigurationLoadError(ConfigurationError)
- Inherits from `ConfigurationError`. Raised when there is an error loading configuration files.

### ConfigurationValidationError(ConfigurationError)
- Inherits from `ConfigurationError`. Raised when there is an error validating configuration values.

### ConfigurationUpdateError(ConfigurationError)
- Inherits from `ConfigurationError`. Raised when updating runtime configuration fails.