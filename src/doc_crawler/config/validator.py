"""
Configuration validation utilities.

This module provides additional validation logic beyond what's handled
by Pydantic models, including business rule validation and external
resource checks.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from pydantic import ValidationError

from .exceptions import ConfigurationValidationError
from .models import BaseConfiguration, SiteConfiguration

logger = logging.getLogger(__name__)


class ConfigurationValidator:
    """Advanced configuration validation and health checks."""
    
    def __init__(self, timeout: int = 10):
        """Initialize validator.
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
    
    async def validate_configuration(self, config: BaseConfiguration) -> List[str]:
        """
        Perform comprehensive configuration validation.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation warnings (empty if all valid)
            
        Raises:
            ConfigurationValidationError: If critical validation errors found
        """
        warnings = []
        errors = []
        
        try:
            # Basic Pydantic validation is already done
            logger.debug("Starting advanced configuration validation")
            
            # Validate business rules
            business_warnings, business_errors = self._validate_business_rules(config)
            warnings.extend(business_warnings)
            errors.extend(business_errors)
            
            # Validate site configurations
            site_warnings, site_errors = await self._validate_site_configurations(config.sites)
            warnings.extend(site_warnings)
            errors.extend(site_errors)
            
            # Validate external resources
            if config.environment != "dev":  # Skip in development
                resource_warnings, resource_errors = await self._validate_external_resources(config)
                warnings.extend(resource_warnings)
                errors.extend(resource_errors)
            
            # Log warnings
            for warning in warnings:
                logger.warning(f"Configuration validation warning: {warning}")
            
            # Raise errors if any
            if errors:
                error_msg = f"Configuration validation failed with {len(errors)} errors: {'; '.join(errors)}"
                logger.error(error_msg)
                raise ConfigurationValidationError(error_msg)
            
            logger.info(f"Configuration validation completed with {len(warnings)} warnings")
            return warnings
        
        except Exception as e:
            if isinstance(e, ConfigurationValidationError):
                raise
            logger.error(f"Unexpected error during validation: {e}")
            raise ConfigurationValidationError(f"Validation failed: {e}")
    
    def _validate_business_rules(self, config: BaseConfiguration) -> tuple[List[str], List[str]]:
        """Validate business logic rules."""
        warnings = []
        errors = []
        
        # Crawling politeness rules
        if config.crawling.default_delay < 1.0 and config.environment == "prod":
            warnings.append("Default crawling delay is less than 1 second in production")
        
        if config.crawling.max_concurrent_requests > 10:
            warnings.append("High concurrent request count may overwhelm target sites")
        
        # Database configuration
        if config.database.pool_size > 20 and config.environment == "dev":
            warnings.append("Large database pool size for development environment")
        
        # Security validation
        if config.environment == "prod":
            if config.debug:
                errors.append("Debug mode enabled in production")
            if config.logging.level == "DEBUG":
                warnings.append("Debug logging enabled in production")
            if not config.security.api_key:
                warnings.append("No API key configured for production")
        
        # Notification validation
        if config.notifications.enabled:
            if not config.notifications.email and not config.notifications.slack:
                errors.append("Notifications enabled but no notification methods configured")
        
        return warnings, errors
    
    async def _validate_site_configurations(
        self, 
        sites: Dict[str, SiteConfiguration]
    ) -> tuple[List[str], List[str]]:
        """Validate site-specific configurations."""
        warnings = []
        errors = []
        
        if not sites:
            warnings.append("No site configurations found")
            return warnings, errors
        
        for site_name, site_config in sites.items():
            # Check for reasonable delays
            delay = site_config.delay or 1.0
            if delay < 0.5:
                warnings.append(f"Site {site_name} has very short delay: {delay}s")
            
            # Check concurrent request limits
            max_concurrent = site_config.max_concurrent or 5
            if max_concurrent > 5:
                warnings.append(f"Site {site_name} allows high concurrent requests: {max_concurrent}")
            
            # Validate URL patterns
            for pattern in site_config.allowed_urls + site_config.denied_urls:
                try:
                    re.compile(pattern.pattern)
                except re.error as e:
                    errors.append(f"Invalid URL pattern in site {site_name}: {pattern.pattern} - {e}")
            
            # Check for conflicting patterns
            allowed_patterns = [p.pattern for p in site_config.allowed_urls]
            denied_patterns = [p.pattern for p in site_config.denied_urls]
            
            for allowed in allowed_patterns:
                for denied in denied_patterns:
                    if allowed == denied:
                        warnings.append(f"Site {site_name} has conflicting URL patterns: {allowed}")
        
        return warnings, errors
    
    async def _validate_external_resources(
        self, 
        config: BaseConfiguration
    ) -> tuple[List[str], List[str]]:
        """Validate external resource accessibility."""
        warnings = []
        errors = []
        
        # Validate site URLs
        site_checks = []
        for site_name, site_config in config.sites.items():
            site_checks.append(self._check_site_accessibility(site_name, site_config))
        
        if site_checks:
            results = await asyncio.gather(*site_checks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    warnings.append(f"Site accessibility check failed: {result}")
                elif isinstance(result, str):  # Warning message
                    warnings.append(result)
        
        return warnings, errors
    
    async def _check_site_accessibility(
        self, 
        site_name: str, 
        site_config: SiteConfiguration
    ) -> Optional[str]:
        """Check if a site is accessible."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Check base URL
                async with session.get(str(site_config.base_url)) as response:
                    if response.status >= 400:
                        return f"Site {site_name} returned HTTP {response.status}"
                
                # Check health check URL if configured
                if site_config.health_check_url:
                    async with session.get(str(site_config.health_check_url)) as response:
                        if response.status >= 400:
                            return f"Site {site_name} health check failed with HTTP {response.status}"
        
        except asyncio.TimeoutError:
            return f"Site {site_name} accessibility check timed out"
        except Exception as e:
            return f"Site {site_name} accessibility check failed: {e}"
        
        return None
