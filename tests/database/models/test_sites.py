# tests/database/test_sites.py
import pytest
from datetime import datetime, UTC
from bson import ObjectId
from pydantic import ValidationError
from doc_crawler.database.models.sites import (
    Site,
    CrawlPatterns,
    Politeness,
    Monitoring,
)

# Test data
VALID_BASE_URL = "https://example.com/"
INVALID_BASE_URL_NO_PROTOCOL = "example.com"
INVALID_BASE_URL_NO_SLASH = "https://example.com"

VALID_CRAWL_PATTERNS = {
    "allowed_domains": ["example.com"],
    "start_urls": ["https://example.com/start"],
    "deny_patterns": ["/exclude"],
    "allow_patterns": ["/include"],
}

VALID_POLITENESS = {
    "delay": 1000,
    "user_agent": "Mozilla/5.0",
    "retry_policy": {"max_retries": 3, "retry_delay": 1000},
}

VALID_MONITORING = {
    "active": True,
    "frequency": "daily",
    "last_crawl_time": datetime.now(UTC),
    "next_scheduled_crawl": datetime.now(UTC),
}

# --- Tests for CrawlPatterns ---
def test_crawl_patterns_valid():
    """Test valid CrawlPatterns initialization."""
    crawl_patterns = CrawlPatterns(**VALID_CRAWL_PATTERNS)
    assert crawl_patterns.allowed_domains == ["example.com"]
    assert crawl_patterns.start_urls == ["https://example.com/start"]
    assert crawl_patterns.deny_patterns == ["/exclude"]
    assert crawl_patterns.allow_patterns == ["/include"]

def test_crawl_patterns_defaults():
    """Test CrawlPatterns with default values."""
    crawl_patterns = CrawlPatterns(
        allowed_domains=["example.com"],
        start_urls=["https://example.com/start"],
    )
    assert crawl_patterns.deny_patterns == []
    assert crawl_patterns.allow_patterns == []

# --- Tests for Politeness ---
def test_politeness_valid():
    """Test valid Politeness initialization."""
    politeness = Politeness(**VALID_POLITENESS)
    assert politeness.delay == 1000
    assert politeness.user_agent == "Mozilla/5.0"
    assert politeness.retry_policy.max_retries == 3
    assert politeness.retry_policy.retry_delay == 1000

def test_politeness_min_delay():
    """Test Politeness enforces minimum delay."""
    with pytest.raises(ValidationError):
        Politeness(delay=50, user_agent="Mozilla/5.0")

# --- Tests for Monitoring ---
def test_monitoring_valid():
    """Test valid Monitoring initialization."""
    monitoring = Monitoring(**VALID_MONITORING)
    assert monitoring.active is True
    assert monitoring.frequency == "daily"
    assert isinstance(monitoring.last_crawl_time, datetime)
    assert isinstance(monitoring.next_scheduled_crawl, datetime)

def test_monitoring_defaults():
    """Test Monitoring with default values."""
    monitoring = Monitoring()
    assert monitoring.active is True
    assert monitoring.frequency == "daily"
    assert monitoring.last_crawl_time is None
    assert monitoring.next_scheduled_crawl is None

# --- Tests for Site ---
def test_site_valid():
    """Test valid Site initialization."""
    site = Site(
        name="Example Site",
        base_url=VALID_BASE_URL,
        crawl_patterns=VALID_CRAWL_PATTERNS,
        politeness=VALID_POLITENESS,
        monitoring=VALID_MONITORING,
        tags=["philosophy", "academic"],
    )
    assert site.name == "Example Site"
    assert site.base_url == VALID_BASE_URL
    assert isinstance(site.crawl_patterns, CrawlPatterns)
    assert isinstance(site.politeness, Politeness)
    assert isinstance(site.monitoring, Monitoring)
    assert site.tags == ["philosophy", "academic"]
    assert isinstance(site.created_at, datetime)
    assert isinstance(site.updated_at, datetime)

def test_site_base_url_validation():
    """Test Site enforces base_url format."""
    # Valid URL with added slash
    site = Site(name="Test", base_url=INVALID_BASE_URL_NO_SLASH, crawl_patterns=VALID_CRAWL_PATTERNS)
    assert site.base_url.endswith("/")

    # Invalid URL (no protocol)
    with pytest.raises(ValidationError):
        Site(name="Test", base_url=INVALID_BASE_URL_NO_PROTOCOL, crawl_patterns=VALID_CRAWL_PATTERNS)

def test_site_defaults():
    """Test Site with default values."""
    site = Site(
        name="Example Site",
        base_url=VALID_BASE_URL,
        crawl_patterns=VALID_CRAWL_PATTERNS,
    )
    assert site.politeness.delay == 1000
    assert site.monitoring.active is True
    assert site.tags == []

def test_site_id_serialization():
    """Test Site handles ObjectId serialization."""
    test_id = ObjectId()
    site = Site(
        _id=test_id,  # Use alias `_id` for MongoDB compatibility
        name="Example Site",
        base_url="https://example.com/",
        crawl_patterns=CrawlPatterns(
            allowed_domains=["example.com"],
            start_urls=["https://example.com/start"],
        ),
    )
    assert site.id == str(test_id)  # Ensure `id` is serialized to string
    assert isinstance(site.model_dump(by_alias=True)["_id"], str)  # Verify serialization in output
