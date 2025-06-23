# database/models/processing_queue.py
from datetime import datetime, UTC
from typing import List, Dict, Optional, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    field_validator,
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

class ProcessingTask(BaseModel):
    """Defines the schema for the `processing_queue` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the task.")
    task_type: str = Field(..., description="Type of task (e.g., 'text_cleaning', 'pdf_conversion').")
    page_id: PyObjectId = Field(..., description="Reference to the `pages` collection for the task.")
    priority: int = Field(default=3, ge=1, le=5, description="Priority level (1=highest, 5=lowest).")
    status: str = Field(default="pending", description="Current status of the task (e.g., 'pending', 'processing', 'completed', 'failed').")
    timeout_seconds: int = Field(default=3600, ge=1, description="Timeout for the task in seconds.")
    dependencies: List[PyObjectId] = Field(default=[], description="List of task IDs this task depends on.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the task was created.")
    processed_at: Optional[datetime] = Field(None, description="Timestamp when the task was processed.")
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retry attempts for the task.")
    error: Optional[str] = Field(None, description="Error message if the task failed.")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Ensure the status is one of the allowed values."""
        allowed_statuses = {"pending", "processing", "completed", "failed"}
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}.")
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
