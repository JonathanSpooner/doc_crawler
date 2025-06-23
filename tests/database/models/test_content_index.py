# tests/database/models/test_content_index.py
import pytest
from datetime import datetime, UTC
from bson import ObjectId
from doc_crawler.database.models.content_index import ContentIndex

def test_content_index_schema():
    """Test the ContentIndex schema with valid data."""
    # Create a sample ObjectId for testing
    test_page_id = ObjectId()
    test_metadata = {"author": "Immanuel Kant", "publication_date": "1781"}

    # Create a ContentIndex instance
    content_index = ContentIndex(
        page_id=test_page_id,
        search_content="Critique of Pure Reason",
        metadata=test_metadata,
    )

    # Validate the schema
    assert content_index.page_id == str(test_page_id)
    assert content_index.search_content == "Critique of Pure Reason"
    assert content_index.metadata == test_metadata
    assert isinstance(content_index.indexed_at, datetime)
    assert content_index.id is None  # Auto-populated by MongoDB

def test_content_index_without_optional_fields():
    """Test the ContentIndex schema with minimal required fields."""
    test_page_id = ObjectId()

    # Create a ContentIndex instance without optional fields
    content_index = ContentIndex(
        page_id=test_page_id,
        search_content="Meditations on First Philosophy",
    )

    # Validate defaults
    assert content_index.metadata == {}
    assert isinstance(content_index.indexed_at, datetime)

def test_content_index_serialization():
    """Test serialization of ContentIndex to dict."""
    test_page_id = ObjectId()
    test_metadata = {"author": "René Descartes", "publication_date": "1641"}

    content_index = ContentIndex(
        page_id=test_page_id,
        search_content="Cogito, ergo sum",
        metadata=test_metadata,
    )

    # Serialize to dict
    content_index_dict = content_index.model_dump(by_alias=True)

    # Validate serialized fields
    assert content_index_dict["_id"] is None  # Not set yet
    assert content_index_dict["page_id"] == str(test_page_id)
    assert content_index_dict["search_content"] == "Cogito, ergo sum"
    assert content_index_dict["metadata"] == test_metadata
    assert "indexed_at" in content_index_dict

def test_content_index_deserialization():
    """Test deserialization of ContentIndex from dict."""
    test_page_id = ObjectId()
    test_metadata = {"author": "Friedrich Nietzsche", "publication_date": "1883"}

    # Simulate a MongoDB document
    document = {
        "_id": ObjectId(),
        "page_id": test_page_id,
        "search_content": "Thus Spoke Zarathustra",
        "metadata": test_metadata,
        "indexed_at": datetime.now(UTC),
    }

    # Deserialize into ContentIndex
    content_index = ContentIndex.model_validate(document)

    # Validate deserialized fields
    assert str(content_index.id) == str(document["_id"])
    assert content_index.page_id == str(test_page_id)
    assert content_index.search_content == "Thus Spoke Zarathustra"
    assert content_index.metadata == test_metadata
    assert content_index.indexed_at == document["indexed_at"]

def test_pyobjectid_validation():
    """Test PyObjectId validation and serialization."""
    from doc_crawler.database.models.content_index import validate_object_id

    # Test the validator directly
    valid_id = ObjectId()
    assert validate_object_id(valid_id) == str(valid_id)

    valid_str = str(ObjectId())
    assert validate_object_id(valid_str) == valid_str

    # Invalid input (non-ObjectId string)
    with pytest.raises(ValueError, match="Invalid ObjectId"):
        validate_object_id("invalid_id")

    # Invalid input (wrong type)
    with pytest.raises(ValueError, match="Invalid ObjectId: must be str or ObjectId"):
        validate_object_id(123)  # Not a string or ObjectId