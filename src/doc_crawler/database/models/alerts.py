# database/models/alerts.py
from datetime import datetime, timezone
from typing import Optional, Literal, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
)

# Helper for ObjectId serialization
PyObjectId = Annotated[
    str,
    BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class Alert(BaseModel):
    """Defines the schema for the `alerts` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the alert.")
    type: Literal["error", "warning", "info"] = Field(..., description="Type of alert (error, warning, or info).")
    message: str = Field(..., min_length=1, description="Detailed message describing the alert.")  # Added min_length=1
    source: str = Field(..., description="Source of the alert (e.g., 'crawler', 'processor', 'monitoring').")
    resolved: bool = Field(default=False, description="Whether the alert has been resolved.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp when the alert was created.")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp when the alert was resolved.")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
