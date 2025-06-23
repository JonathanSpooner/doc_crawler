from datetime import datetime, UTC
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

class ContentDiff(BaseModel):
    """Defines the differences detected in content changes."""
    added: str = Field(..., description="Content added in the new version.")
    removed: str = Field(..., description="Content removed from the old version.")

class ContentChange(BaseModel):
    """Defines the schema for the `content_changes` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the change record.")
    site_id: PyObjectId = Field(..., description="Reference to the `sites` collection.")
    page_id: PyObjectId = Field(..., description="Reference to the `pages` collection.")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the change was detected.")
    change_type: Literal["content", "metadata", "new"] = Field(..., description="Type of change detected.")
    diff: ContentDiff = Field(..., description="Detailed differences between old and new content.")
    severity: Literal["minor", "major", "critical"] = Field(..., description="Severity of the change.")
    old_content_hash: str = Field(..., description="SHA-256 hash of the old content.")
    new_content_hash: str = Field(..., description="SHA-256 hash of the new content.")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
