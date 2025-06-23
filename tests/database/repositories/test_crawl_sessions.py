# tests/database/models/test_crawl_sessions.py
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import ValidationError
from doc_crawler.database.models.crawl_sessions import CrawlSession, CrawlStats

def test_crawl_stats_schema():
    """Test the CrawlStats schema."""
    # Valid data
    stats = CrawlStats(
        pages_crawled=100,
        pages_failed=5,
        avg_response_time=200.5,
        resource_usage={"cpu": 50.0, "memory_mb": 1024.0},
    )
    assert stats.pages_crawled == 100
    assert stats.pages_failed == 5
    assert stats.avg_response_time == 200.5
    assert stats.resource_usage == {"cpu": 50.0, "memory_mb": 1024.0}

    # Test defaults
    stats_default = CrawlStats(
        pages_crawled=50,
        pages_failed=2,
        avg_response_time=150.0,
    )
    assert stats_default.resource_usage == {"cpu": 0.0, "memory_mb": 0.0}

    # Invalid data (negative values)
    with pytest.raises(ValidationError):
        CrawlStats(
            pages_crawled=-1,
            pages_failed=0,
            avg_response_time=100.0,
        )

    with pytest.raises(ValidationError):
        CrawlStats(
            pages_crawled=0,
            pages_failed=-1,
            avg_response_time=100.0,
        )

    with pytest.raises(ValidationError):
        CrawlStats(
            pages_crawled=0,
            pages_failed=0,
            avg_response_time=-100.0,
        )

    with pytest.raises(ValueError):
        CrawlStats(
            pages_crawled=0,
            pages_failed=0,
            avg_response_time=100.0,
            resource_usage={"cpu": -50.0, "memory_mb": 1024.0},
        )
def test_crawl_session_schema():
    """Test the CrawlSession schema."""
    # Valid data
    session = CrawlSession(
        site_id=str(ObjectId()),
        start_time=datetime.now(timezone.utc),
        stats=CrawlStats(
            pages_crawled=100,
            pages_failed=5,
            avg_response_time=200.5,
        ),
    )
    assert session.site_id is not None
    assert session.start_time is not None
    assert session.stats.pages_crawled == 100
    assert session.trigger == "manual"  # Default
    assert session.status == "running"  # Default
    assert session.error is None

    # Test with optional fields
    session_with_end_time = CrawlSession(
        site_id=str(ObjectId()),
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        stats=CrawlStats(
            pages_crawled=50,
            pages_failed=2,
            avg_response_time=150.0,
        ),
        trigger="scheduled",
        status="completed",
        error="Connection timeout",
    )
    assert session_with_end_time.end_time is not None
    assert session_with_end_time.trigger == "scheduled"
    assert session_with_end_time.status == "completed"
    assert session_with_end_time.error == "Connection timeout"

    # Invalid data (missing required fields)
    with pytest.raises(ValidationError):
        CrawlSession()  # Missing site_id, start_time, stats

def test_pyobjectid_serialization():
    """Test PyObjectId serialization/deserialization."""
    obj_id = ObjectId()
    session = CrawlSession(
        id=obj_id,  # Pass ObjectId directly
        site_id=str(ObjectId()),
        start_time=datetime.now(timezone.utc),
        stats=CrawlStats(
            pages_crawled=100,
            pages_failed=5,
            avg_response_time=200.5,
        ),
    )
    assert session.id == str(obj_id)  # Serialized to string
    assert isinstance(session.id, str)

    # Deserialize from string
    session_from_str = CrawlSession(
        id=str(obj_id),
        site_id=str(ObjectId()),
        start_time=datetime.now(timezone.utc),
        stats=CrawlStats(
            pages_crawled=100,
            pages_failed=5,
            avg_response_time=200.5,
        ),
    )
    assert session_from_str.id == str(obj_id)
