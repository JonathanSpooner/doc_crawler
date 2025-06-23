# database/models/crawl_sessions.py
from datetime import datetime, UTC
from typing import Optional, Dict
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
    field_validator
)
from typing_extensions import Annotated

# Helper for ObjectId serialization
PyObjectId = Annotated[
    str,
    BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class CrawlStats(BaseModel):
    """Defines statistics for a crawl session."""
    pages_crawled: int = Field(..., ge=0, description="Number of pages successfully crawled (must be >= 0).")
    pages_failed: int = Field(..., ge=0, description="Number of pages that failed to crawl (must be >= 0).")
    avg_response_time: float = Field(..., ge=0, description="Average response time in milliseconds (must be >= 0).")
    resource_usage: Dict[str, float] = Field(
        default={"cpu": 0.0, "memory_mb": 0.0},
        description="Resource usage metrics (CPU and memory).",
    )

    @field_validator('resource_usage')
    def validate_resource_usage(cls, v):
        if any(value < 0 for value in v.values()):
            raise ValueError("Resource usage values cannot be negative.")
        return v

class CrawlSession(BaseModel):
    """Defines the schema for the `crawl_sessions` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the crawl session.")
    site_id: PyObjectId = Field(..., description="Reference to the `sites` collection.")
    start_time: datetime = Field(..., description="Timestamp when the crawl session started.")
    end_time: Optional[datetime] = Field(None, description="Timestamp when the crawl session ended.")
    trigger: str = Field(
        default="manual",
        description="Trigger for the crawl (e.g., 'manual', 'scheduled', 'monitoring')."
    )
    status: str = Field(
        default="running",
        description="Status of the crawl (e.g., 'running', 'completed', 'failed')."
    )
    stats: CrawlStats = Field(..., description="Statistics for the crawl session.")
    error: Optional[str] = Field(None, description="Error message if the crawl failed.")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
