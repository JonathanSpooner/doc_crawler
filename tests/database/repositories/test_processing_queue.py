import pytest
from datetime import datetime
from bson import ObjectId
from pydantic import ValidationError
from doc_crawler.database.models.processing_queue import ProcessingTask

# Sample valid task data for reuse in tests
VALID_TASK_DATA = {
    "task_type": "text_cleaning",
    "page_id": str(ObjectId()),
    "priority": 3,
    "status": "pending",
    "timeout_seconds": 3600,
    "dependencies": [str(ObjectId())],
    "max_retries": 3,
}

def test_processing_task_creation():
    """Test successful creation of a ProcessingTask with valid data."""
    task = ProcessingTask(**VALID_TASK_DATA)
    assert task.task_type == "text_cleaning"
    assert isinstance(task.created_at, datetime)
    assert task.status == "pending"

def test_priority_validation():
    """Test priority field constraints (1-5)."""
    # Valid priorities (1-5)
    for priority in [1, 3, 5]:
        task = ProcessingTask(**{**VALID_TASK_DATA, "priority": priority})
        assert task.priority == priority

    # Invalid priority (<1)
    with pytest.raises(ValidationError, match="Input should be greater than or equal to 1"):
        ProcessingTask(**{**VALID_TASK_DATA, "priority": 0})

    # Invalid priority (>5)
    with pytest.raises(ValidationError, match="Input should be less than or equal to 5"):
        ProcessingTask(**{**VALID_TASK_DATA, "priority": 6})

def test_status_validation():
    """Test status field constraints (pending/processing/completed/failed)."""
    # Valid statuses
    for status in ["pending", "processing", "completed", "failed"]:
        task = ProcessingTask(**{**VALID_TASK_DATA, "status": status})
        assert task.status == status

    # Invalid status
    with pytest.raises(ValidationError, match="Status must be one of"):
        ProcessingTask(**{**VALID_TASK_DATA, "status": "invalid_status"})

def test_pyobjectid_serialization():
    """Test PyObjectId serialization/deserialization."""
    object_id = ObjectId()
    task = ProcessingTask(**{**VALID_TASK_DATA, "page_id": str(object_id)})
    assert task.page_id == str(object_id)  # Serialized to string

def test_default_values():
    """Test default values (status=pending, created_at=now)."""
    task = ProcessingTask(
        task_type="pdf_conversion",
        page_id=str(ObjectId()),
    )
    assert task.status == "pending"
    assert isinstance(task.created_at, datetime)
    assert task.dependencies == []  # Default empty list

def test_error_field_optional():
    """Test error field is optional."""
    task = ProcessingTask(**VALID_TASK_DATA)
    assert task.error is None

    task_with_error = ProcessingTask(**{**VALID_TASK_DATA, "error": "Failed to process"})
    assert task_with_error.error == "Failed to process"

def test_dependencies_list():
    """Test dependencies field accepts a list of PyObjectId strings."""
    dependencies = [str(ObjectId()), str(ObjectId())]
    task = ProcessingTask(**{**VALID_TASK_DATA, "dependencies": dependencies})
    assert task.dependencies == dependencies

    # Empty list is allowed
    task_empty_deps = ProcessingTask(**{**VALID_TASK_DATA, "dependencies": []})
    assert task_empty_deps.dependencies == []
