# tests/database/models/test_alerts.py
import pytest
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import ValidationError

from doc_crawler.database.models.alerts import Alert

def test_alert_creation_valid():
    """Test creating an Alert with valid data."""
    alert_data = {
        "type": "error",
        "message": "Failed to crawl page: example.com",
        "source": "crawler",
    }
    alert = Alert(**alert_data)

    assert alert.type == "error"
    assert alert.message == "Failed to crawl page: example.com"
    assert alert.source == "crawler"
    assert alert.resolved is False
    assert isinstance(alert.created_at, datetime)
    assert alert.resolved_at is None

def test_alert_with_resolved_timestamp():
    """Test Alert with resolved_at timestamp."""
    resolved_at = datetime.now(timezone.utc)
    alert_data = {
        "type": "warning",
        "message": "High CPU usage detected",
        "source": "monitoring",
        "resolved": True,
        "resolved_at": resolved_at,
    }
    alert = Alert(**alert_data)

    assert alert.resolved is True
    assert alert.resolved_at == resolved_at

def test_alert_invalid_type():
    """Test Alert with invalid type (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        Alert(
            type="critical",  # Invalid (not in Literal["error", "warning", "info"])
            message="Invalid alert type",
            source="processor",
        )

def test_alert_serialization_with_id():
    """Test Alert serialization with MongoDB ObjectId."""
    alert_id = ObjectId()
    alert_data = {
        "_id": alert_id,
        "type": "info",
        "message": "New content detected",
        "source": "monitoring",
    }
    alert = Alert(**alert_data)

    assert alert.id == str(alert_id)
    assert alert.model_dump(by_alias=True)["_id"] == str(alert_id)

def test_alert_defaults():
    """Test Alert default values."""
    alert_data = {
        "type": "info",
        "message": "System backup completed",
        "source": "system",
    }
    alert = Alert(**alert_data)

    assert alert.resolved is False
    assert alert.resolved_at is None
    assert isinstance(alert.created_at, datetime)

def test_alert_empty_message():
    """Test Alert with empty message (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        Alert(
            type="error",
            message="",  # Empty message (invalid)
            source="crawler",
        )

def test_alert_missing_required_fields():
    """Test Alert missing required fields (should raise ValidationError)."""
    with pytest.raises(ValidationError):
        Alert(
            type="error",
            # Missing "message" and "source"
        )
