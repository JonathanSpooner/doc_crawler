"""Pytest configuration and shared fixtures."""

import shutil
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

@pytest.fixture(scope="session")
def session_config_file(tmp_path_factory) -> any:
    # Local paths to your .yaml source files
    fixture_root = Path(__file__).parent.parent.parent.parent / "src/doc_crawler" / "config"
    env_src = fixture_root / "environments"
    sites_src = fixture_root / "sites"

    # Temporary destination directories
    tmp_dir = tmp_path_factory.mktemp("config")

    # Copy .yaml files into temp dirs
    shutil.copytree(env_src, tmp_dir/"environments", dirs_exist_ok=True)

    shutil.copytree(sites_src, tmp_dir/"sites", dirs_exist_ok=True)

    yield tmp_dir

@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with config structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        environments_dir = config_dir / "environments"
        sites_dir = config_dir / "sites"
        
        environments_dir.mkdir()
        sites_dir.mkdir()
        
        yield config_dir

@pytest.fixture
def sample_base_config():
    """Sample base configuration data."""
    return {
        "database": {
            "url": "postgresql://user:pass@localhost:5432/test_db",
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": False
        },
        "security": {
            "secret_key": "test-secret-key-12345",
            "token_expiry": 3600,
            "rate_limit_per_minute": 60
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "max_bytes": 10485760,
            "backup_count": 5
        },
        "crawling": {
            "default_delay": 1.0,
            "max_concurrent_requests": 5,
            "request_timeout": 30,
            "max_retries": 3
        },
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


@pytest.fixture
def sample_dev_config():
    """Sample development environment overrides."""
    return {
        "logging": {
            "level": "DEBUG",
            "file_path": "logs/crawler-dev.log"
        },
        "debug": True,
        "hot_reload": True
    }


@pytest.fixture
def sample_prod_config():
    """Sample production environment overrides."""
    return {
        "logging": {
            "level": "INFO",
            "structured": True
        },
        "crawling": {
            "default_delay": 2.0,
            "max_concurrent_requests": 10
        },
        "debug": False,
        "hot_reload": False
    }


@pytest.fixture
def sample_site_config():
    """Sample site configuration data."""
    return {
        "name": "Test Philosophy Site",
        "base_url": "https://iep.utm.edu/",
        "domains": ["iep.utm.edu"],
        "enabled": True,
        "priority": 1,
        "allowed_urls": [
            {
                "pattern": "^https://iep.utm\\.edu/[a-zA-Z0-9-]+/?$",
                "type": "regex",
                "description": "Main articles"
            }
        ],
        "content_selectors": [
            {
                "name": "main_content",
                "selector": "#main-content",
                "type": "css",
                "required": True
            }
        ],
        "delay": 1.5,
        "max_concurrent": 2,
        "notification_level": "medium"
    }


@pytest.fixture
def populated_config_dir(temp_config_dir, sample_base_config, sample_dev_config, sample_prod_config, sample_site_config):
    """Create a populated configuration directory."""
    environments_dir = temp_config_dir / "environments"
    sites_dir = temp_config_dir / "sites"
    
    # Write configuration files
    with open(environments_dir / "base.yaml", "w") as f:
        yaml.dump(sample_base_config, f)
    
    with open(environments_dir / "dev.yaml", "w") as f:
        yaml.dump(sample_dev_config, f)
    
    with open(environments_dir / "prod.yaml", "w") as f:
        yaml.dump(sample_prod_config, f)
    
    with open(sites_dir / "test_site.yaml", "w") as f:
        yaml.dump(sample_site_config, f)
    
    return temp_config_dir


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    env_vars = {
        "CRAWLER_DATABASE__URL": "postgresql://user:pass@localhost:5432/env_db",
        "CRAWLER_SECURITY__SECRET_KEY": "env-secret-key",
        "ENVIRONMENT": "dev"
    }
    with patch.dict("os.environ", env_vars):
        yield env_vars


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()