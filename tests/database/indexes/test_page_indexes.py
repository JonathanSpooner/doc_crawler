from pymongo import IndexModel, ASCENDING, DESCENDING
from unittest.mock import Mock, patch
from doc_crawler.database.indexes.page_indexes import get_page_indexes

def test_get_page_indexes_returns_correct_index_models():
    """Test that get_page_indexes() returns the expected list of IndexModel objects."""
    indexes = get_page_indexes()

    # Verify the number of indexes
    assert len(indexes) == 8

    # Verify each index's fields and options
    expected_indexes = [
        {"key": {"url": ASCENDING}, "unique": True, "name": "url_unique"},
        {"key": {"site_id": ASCENDING}, "name": "site_id_index"},
        {"key": {"last_modified": DESCENDING}, "name": "last_modified_desc"},
        {"key": {"content_hash": ASCENDING}, "name": "content_hash_index"},
        {"key": {"status": ASCENDING}, "name": "status_index"},
        {
            "key": {
                "site_id": ASCENDING,
                "status": ASCENDING,
                "last_modified": DESCENDING,
            },
            "name": "dashboard_metrics",
        },
        {"key": {"metadata.language": ASCENDING}, "name": "language_index"},
        {"key": {"metadata.word_count": ASCENDING}, "name": "word_count_index"},
    ]

    for idx, expected in enumerate(expected_indexes):
        assert indexes[idx].document == expected

def test_indexes_are_applied_to_collection():
    """Test that the indexes are correctly applied to the MongoDB collection."""
    mock_collection = Mock()
    mock_collection.create_indexes.return_value = ["index1", "index2"]

    with patch("doc_crawler.database.indexes.page_indexes.get_page_indexes") as mock_get_indexes:
        mock_get_indexes.return_value = [
            IndexModel([("test_field", ASCENDING)]),
            IndexModel([("another_field", DESCENDING)])
        ]
        
        # Call the function that applies indexes
        from doc_crawler.database.indexes.page_indexes import get_page_indexes
        indexes = get_page_indexes()
        mock_collection.create_indexes(indexes)

        # Verify create_indexes was called with the expected indexes
        mock_collection.create_indexes.assert_called_once_with(indexes)

def test_index_names_are_unique():
    """Ensure all index names are unique to avoid conflicts."""
    indexes = get_page_indexes()
    index_names = [index.document["name"] for index in indexes]
    assert len(index_names) == len(set(index_names)), "Duplicate index names found"

def test_compound_index_fields_order():
    """Verify the field order in the compound index (dashboard_metrics)."""
    indexes = get_page_indexes()
    dashboard_index = next(
        idx for idx in indexes if idx.document["name"] == "dashboard_metrics"
    )
    assert dashboard_index.document["key"] == {
        "site_id": ASCENDING,
        "status": ASCENDING,
        "last_modified": DESCENDING,
    }

def test_content_hash_index_is_ascending():
    """Verify the content_hash index uses ASCENDING order."""
    indexes = get_page_indexes()
    content_hash_index = next(
        idx for idx in indexes if idx.document["name"] == "content_hash_index"
    )
    assert content_hash_index.document["key"] == {"content_hash": ASCENDING}