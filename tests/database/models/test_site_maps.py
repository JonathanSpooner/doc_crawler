import pytest
from datetime import datetime
from bson import ObjectId
from pydantic import ValidationError

from doc_crawler.database.models.site_maps import SiteMap

# Test data
VALID_SITEMAP_URL = "https://example.com/sitemap.xml"
INVALID_SITEMAP_URL = "ftp://example.com/sitemap.xml"
SAMPLE_SITE_ID = str(ObjectId())

def test_sitemap_creation_with_valid_data():
    """Test that a SiteMap can be created with valid data."""
    sitemap = SiteMap(
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
        urls=["https://example.com/page1", "https://example.com/page2"],
    )

    assert sitemap.site_id == SAMPLE_SITE_ID
    assert sitemap.url == VALID_SITEMAP_URL
    assert len(sitemap.urls) == 2
    assert isinstance(sitemap.last_parsed, datetime)

def test_sitemap_defaults():
    """Test that default values are set correctly."""
    sitemap = SiteMap(
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
    )

    assert sitemap.urls == []
    assert isinstance(sitemap.last_parsed, datetime)

def test_sitemap_url_validation():
    """Test that the URL validator rejects invalid URLs."""
    with pytest.raises(ValidationError) as excinfo:
        SiteMap(
            site_id=SAMPLE_SITE_ID,
            url=INVALID_SITEMAP_URL,
        )

    assert "must start with 'http://' or 'https://'" in str(excinfo.value)

def test_sitemap_with_empty_url_list():
    """Test that the URLs list can be empty."""
    sitemap = SiteMap(
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
        urls=[],
    )

    assert sitemap.urls == []

def test_sitemap_serialization_with_object_id():
    """Test serialization when an ObjectId is provided for `_id`."""
    object_id = ObjectId()
    sitemap = SiteMap(
        id=object_id,
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
    )

    assert sitemap.id == str(object_id)

def test_sitemap_serialization_with_string_id():
    """Test serialization when a string is provided for `_id`."""
    string_id = "507f1f77bcf86cd799439011"
    sitemap = SiteMap(
        id=string_id,
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
    )

    assert sitemap.id == string_id

def test_sitemap_model_config():
    """Test that the model config allows arbitrary types and populates by name."""
    sitemap = SiteMap(
        _id="507f1f77bcf86cd799439011",  # Testing `populate_by_name`
        site_id=SAMPLE_SITE_ID,
        url=VALID_SITEMAP_URL,
    )

    assert sitemap.id == "507f1f77bcf86cd799439011"
