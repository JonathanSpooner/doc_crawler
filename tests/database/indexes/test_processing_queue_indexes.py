from pymongo import IndexModel, ASCENDING
from doc_crawler.database.indexes.processing_queue_indexes import get_processing_queue_indexes

def test_get_processing_queue_indexes_returns_list_of_index_models():
    """Test that the function returns a list of IndexModel objects."""
    indexes = get_processing_queue_indexes()
    assert isinstance(indexes, list)
    assert all(isinstance(index, IndexModel) for index in indexes)

def test_priority_index_configuration():
    """Test the 'priority' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    priority_index = next(
        (index for index in indexes if index.document["name"] == "priority_index"), None
    )
    assert priority_index is not None
    assert priority_index.document["key"] == {"priority": ASCENDING}

def test_status_index_configuration():
    """Test the 'status' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    status_index = next(
        (index for index in indexes if index.document["name"] == "status_index"), None
    )
    assert status_index is not None
    assert status_index.document["key"] == {"status": ASCENDING}

def test_created_at_index_configuration():
    """Test the 'created_at' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    created_at_index = next(
        (index for index in indexes if index.document["name"] == "created_at_asc"), None
    )
    assert created_at_index is not None
    assert created_at_index.document["key"] == {"created_at": ASCENDING}

def test_task_scheduling_compound_index_configuration():
    """Test the compound 'task_scheduling' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    compound_index = next(
        (index for index in indexes if index.document["name"] == "task_scheduling"), None
    )
    assert compound_index is not None
    assert compound_index.document["key"] == {
        "priority": ASCENDING,
        "status": ASCENDING,
        "created_at": ASCENDING,
    }

def test_task_type_index_configuration():
    """Test the 'task_type' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    task_type_index = next(
        (index for index in indexes if index.document["name"] == "task_type_index"), None
    )
    assert task_type_index is not None
    assert task_type_index.document["key"] == {"task_type": ASCENDING}

def test_max_retries_index_configuration():
    """Test the 'max_retries' index is correctly configured."""
    indexes = get_processing_queue_indexes()
    max_retries_index = next(
        (index for index in indexes if index.document["name"] == "max_retries_index"), None
    )
    assert max_retries_index is not None
    assert max_retries_index.document["key"] == {"max_retries": ASCENDING}

def test_correct_number_of_indexes_generated():
    """Test that exactly 6 indexes are generated."""
    indexes = get_processing_queue_indexes()
    assert len(indexes) == 6  # priority, status, created_at, task_scheduling, task_type, max_retries