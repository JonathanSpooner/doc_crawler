import pytest
from datetime import datetime, UTC
from bson import ObjectId
from pydantic import ValidationError

from doc_crawler.database.models.content_changes import ContentDiff, ContentChange

# Test data
TEST_SITE_ID = ObjectId()
TEST_PAGE_ID = ObjectId()
TEST_DIFF = {"added": "new content", "removed": "old content"}

def test_content_diff_valid():
    """Test valid ContentDiff creation."""
    diff = ContentDiff(added="new content", removed="old content")
    assert diff.added == "new content"
    assert diff.removed == "old content"

def test_content_diff_empty_strings():
    """Test ContentDiff with empty strings."""
    diff = ContentDiff(added="", removed="")
    assert diff.added == ""
    assert diff.removed == ""

def test_content_diff_missing_fields():
    """Test ContentDiff with missing fields."""
    with pytest.raises(ValidationError):
        ContentDiff(added="new content")  # Missing `removed`

def test_content_change_valid():
    """Test valid ContentChange creation."""
    change = ContentChange(
        site_id=TEST_SITE_ID,
        page_id=TEST_PAGE_ID,
        change_type="content",
        diff=ContentDiff(**TEST_DIFF),
        severity="major",
        old_content_hash="abc123",
        new_content_hash="def456",
    )
    assert str(change.site_id) == str(TEST_SITE_ID)
    assert change.change_type == "content"
    assert change.diff.added == "new content"
    assert isinstance(change.detected_at, datetime)

def test_content_change_with_none_id():
    """Test ContentChange with None for optional id."""
    change = ContentChange(
        id=None,
        site_id=TEST_SITE_ID,
        page_id=TEST_PAGE_ID,
        change_type="content",
        diff=ContentDiff(**TEST_DIFF),
        severity="major",
        old_content_hash="abc123",
        new_content_hash="def456",
    )
    assert change.id is None

def test_content_change_invalid_change_type():
    """Test ContentChange with invalid change_type."""
    with pytest.raises(ValidationError):
        ContentChange(
            site_id=TEST_SITE_ID,
            page_id=TEST_PAGE_ID,
            change_type="invalid",  # Invalid value
            diff=ContentDiff(**TEST_DIFF),
            severity="major",
            old_content_hash="abc123",
            new_content_hash="def456",
        )

def test_content_change_invalid_severity():
    """Test ContentChange with invalid severity."""
    with pytest.raises(ValidationError):
        ContentChange(
            site_id=TEST_SITE_ID,
            page_id=TEST_PAGE_ID,
            change_type="content",
            diff=ContentDiff(**TEST_DIFF),
            severity="invalid",  # Invalid value
            old_content_hash="abc123",
            new_content_hash="def456",
        )

def test_content_change_missing_required_fields():
    """Test ContentChange with missing required fields."""
    with pytest.raises(ValidationError):
        ContentChange(
            site_id=TEST_SITE_ID,
            page_id=TEST_PAGE_ID,
            change_type="content",
            # Missing `diff`, `severity`, etc.
        )

def test_content_change_default_detected_at():
    """Test ContentChange auto-generates detected_at if not provided."""
    change = ContentChange(
        site_id=TEST_SITE_ID,
        page_id=TEST_PAGE_ID,
        change_type="content",
        diff=ContentDiff(**TEST_DIFF),
        severity="major",
        old_content_hash="abc123",
        new_content_hash="def456",
    )
    assert isinstance(change.detected_at, datetime)

def test_content_change_custom_detected_at():
    """Test ContentChange accepts a custom detected_at."""
    custom_time = datetime(2023, 1, 1, tzinfo=UTC)
    change = ContentChange(
        site_id=TEST_SITE_ID,
        page_id=TEST_PAGE_ID,
        change_type="content",
        diff=ContentDiff(**TEST_DIFF),
        severity="major",
        old_content_hash="abc123",
        new_content_hash="def456",
        detected_at=custom_time,
    )
    assert change.detected_at == custom_time
