from pymongo import IndexModel, ASCENDING, DESCENDING
from doc_crawler.database.indexes.content_changes_indexes import get_content_changes_indexes

def test_get_content_changes_indexes_returns_list():
    """Test that the function returns a list of IndexModel objects."""
    indexes = get_content_changes_indexes()
    assert isinstance(indexes, list)
    assert all(isinstance(index, IndexModel) for index in indexes)

def test_index_names_are_unique():
    """Test that all index names are unique."""
    indexes = get_content_changes_indexes()
    index_names = [index.document["name"] for index in indexes]
    assert len(index_names) == len(set(index_names)), "Duplicate index names found."

def test_site_id_index():
    """Test the site_id index is correctly defined."""
    indexes = get_content_changes_indexes()
    site_id_index = next(
        (index for index in indexes if index.document["name"] == "site_id_index"), None
    )
    assert site_id_index is not None, "site_id_index not found."
    assert site_id_index.document["key"] == {"site_id": ASCENDING}

def test_detected_at_desc_index():
    """Test the detected_at_desc index is correctly defined."""
    indexes = get_content_changes_indexes()
    detected_at_index = next(
        (index for index in indexes if index.document["name"] == "detected_at_desc"), None
    )
    assert detected_at_index is not None, "detected_at_desc index not found."
    assert detected_at_index.document["key"] == {"detected_at": DESCENDING}

def test_change_type_index():
    """Test the change_type index is correctly defined."""
    indexes = get_content_changes_indexes()
    change_type_index = next(
        (index for index in indexes if index.document["name"] == "change_type_index"), None
    )
    assert change_type_index is not None, "change_type_index not found."
    assert change_type_index.document["key"] == {"change_type": ASCENDING}

def test_severity_index():
    """Test the severity index is correctly defined."""
    indexes = get_content_changes_indexes()
    severity_index = next(
        (index for index in indexes if index.document["name"] == "severity_index"), None
    )
    assert severity_index is not None, "severity_index not found."
    assert severity_index.document["key"] == {"severity": ASCENDING}

def test_monitoring_metrics_compound_index():
    """Test the monitoring_metrics compound index is correctly defined."""
    indexes = get_content_changes_indexes()
    monitoring_index = next(
        (index for index in indexes if index.document["name"] == "monitoring_metrics"), None
    )
    assert monitoring_index is not None, "monitoring_metrics index not found."
    assert monitoring_index.document["key"] == {
        "site_id": ASCENDING,
        "detected_at": DESCENDING,
        "change_type": ASCENDING,
    }

def test_ttl_index():
    """Test the TTL index is correctly defined."""
    indexes = get_content_changes_indexes()
    ttl_index = next(
        (index for index in indexes if index.document["name"] == "ttl_index"), None
    )
    assert ttl_index is not None, "ttl_index not found."
    assert ttl_index.document["key"] == {"detected_at": ASCENDING}
    assert ttl_index.document["expireAfterSeconds"] == 31536000