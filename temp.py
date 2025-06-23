import asyncio
import logging
from pathlib import Path

from config import ConfigurationManager
from config.models import Environment

# Setup logging
logging.basicConfig(level=logging.INFO)

async def main():
    """Example usage of the configuration system."""
    
    # Initialize configuration manager
    config_manager = ConfigurationManager(
        config_dir=Path("config"),
        auto_reload=True  # Enable hot reloading in development
    )
    
    # Access configuration
    config = config_manager.config
    print(f"Running in {config.environment} environment")
    print(f"Database URL: {config.database.url}")  # Will be masked in logs
    print(f"Crawling delay: {config.crawling.default_delay}")
    
    # Access site-specific configuration
    iep_config = config_manager.get_site_config("iep")
    if iep_config:
        print(f"IEP site delay: {iep_config.delay}")
        print(f"IEP enabled: {iep_config.enabled}")
    
    # Register for configuration changes
    def on_config_change(new_config):
        print(f"Configuration changed! New delay: {new_config.crawling.default_delay}")
    
    config_manager.register_change_callback(on_config_change)
    
    # Runtime configuration update (development only)
    if config.environment == Environment.DEVELOPMENT:
        success = config_manager.update_runtime_config({
            "crawling": {
                "default_delay": 1.5
            }
        })
        print(f"Runtime update successful: {success}")
    
    print(f"Current environment: {config_manager.config.environment}")
    # Manually reload configuration
    reload_success = await config_manager.reload_configuration()
    print(f"Configuration reload successful: {reload_success}")
    
    # Get masked configuration for logging
    masked_config = config_manager.get_masked_config()
    print("Masked configuration (safe for logging):")
    print(masked_config.get("database", {}).get("url", "Not set"))
    
    # Cleanup
    config_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())