# tests/database/models/test_pages.py
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import ValidationError
from doc_crawler.database.models.pages import (
    RedirectHistory,
    PageMetadata,
    PageVersion,
    Page,
    PyObjectId,
)

# Test data
TEST_URL = "https://example.com/page"
TEST_SITE_ID = ObjectId()
TEST_CONTENT = "Sample philosophical text."
TEST_CONTENT_HASH = "a" * 64  # Valid SHA-256 hash (64 hex chars)
TEST_INVALID_HASH = "invalid_hash"

# Fixtures
@pytest.fixture
def sample_redirect_history() -> RedirectHistory:
    return RedirectHistory(
        from_url="https://old.example.com",
        to_url=TEST_URL,
        timestamp=datetime.now(timezone.utc),
    )

@pytest.fixture
def sample_page_metadata() -> PageMetadata:
    return PageMetadata(
        author="Plato",
        publication_date="380 BCE",
        language="en",
        word_count=1500,
        reading_time=10,
        keywords=["philosophy", "dialogue"],
    )

@pytest.fixture
def sample_page_version() -> PageVersion:
    return PageVersion(
        content="Original content",
        timestamp=datetime.now(timezone.utc),
    )

@pytest.fixture
def sample_page(
    sample_redirect_history: RedirectHistory,
    sample_page_metadata: PageMetadata,
    sample_page_version: PageVersion,
) -> Page:
    return Page(
        url=TEST_URL,
        site_id=TEST_SITE_ID,
        title="The Republic",
        content=TEST_CONTENT,
        content_hash=TEST_CONTENT_HASH,
        redirect_history=[sample_redirect_history],
        metadata=sample_page_metadata,
        versions=[sample_page_version],
        status="processed",
    )

# --- Tests for RedirectHistory ---
def test_redirect_history_valid(sample_redirect_history: RedirectHistory):
    assert sample_redirect_history.from_url.startswith("https://")
    assert sample_redirect_history.to_url == TEST_URL
    assert isinstance(sample_redirect_history.timestamp, datetime)

def test_redirect_history_invalid_url():
    with pytest.raises(ValidationError):
        RedirectHistory(from_url="invalid", to_url=TEST_URL, timestamp=datetime.now(timezone.utc))

# --- Tests for PageMetadata ---
def test_page_metadata_valid(sample_page_metadata: PageMetadata):
    assert sample_page_metadata.author == "Plato"
    assert sample_page_metadata.word_count >= 0

def test_page_metadata_empty():
    metadata = PageMetadata()
    assert metadata.author is None
    assert metadata.keywords == []

# --- Tests for PageVersion ---
def test_page_version_valid(sample_page_version: PageVersion):
    assert sample_page_version.content == "Original content"
    assert isinstance(sample_page_version.timestamp, datetime)

# --- Tests for Page ---
def test_page_valid(sample_page: Page):
    assert sample_page.url == TEST_URL
    assert sample_page.site_id == str(TEST_SITE_ID)
    assert sample_page.content_hash == TEST_CONTENT_HASH
    assert len(sample_page.redirect_history) == 1
    assert sample_page.status == "processed"

def test_page_default_values():
    page = Page(
        url=TEST_URL,
        site_id=TEST_SITE_ID,
        content=TEST_CONTENT,
        content_hash=TEST_CONTENT_HASH,
    )
    assert page.title is None
    assert page.redirect_history == []
    assert page.versions == []
    assert page.status == "pending"

def test_page_invalid_url():
    with pytest.raises(ValidationError):
        Page(
            url="invalid",
            site_id=TEST_SITE_ID,
            content=TEST_CONTENT,
            content_hash=TEST_CONTENT_HASH,
        )

def test_page_invalid_hash():
    with pytest.raises(ValidationError):
        Page(
            url=TEST_URL,
            site_id=TEST_SITE_ID,
            content=TEST_CONTENT,
            content_hash=TEST_INVALID_HASH,
        )

def test_page_serialization(sample_page: Page):
    page_dict = sample_page.model_dump(by_alias=True)
    assert page_dict["_id"] is None  # Explicitly check for None
    assert page_dict["url"] == TEST_URL
    assert page_dict["site_id"] == str(TEST_SITE_ID)

def test_page_deserialization():
    page_data = {
        "_id": str(ObjectId()),
        "url": TEST_URL,
        "site_id": str(TEST_SITE_ID),
        "content": TEST_CONTENT,
        "content_hash": TEST_CONTENT_HASH,
        "status": "failed",
        "error": "Timeout",
    }
    page = Page.model_validate(page_data)
    assert page.id == page_data["_id"]
    assert page.error == "Timeout"

# --- Tests for PyObjectId ---
def test_pyobjectid_serialization():
    obj_id = ObjectId()
    py_obj_id = PyObjectId(obj_id)
    assert py_obj_id == str(obj_id)

def test_pyobjectid_validation():
    obj_id = ObjectId()
    assert PyObjectId(obj_id) == str(obj_id)
    assert PyObjectId(str(obj_id)) == str(obj_id)
