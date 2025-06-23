# database/models/content_index.py
from datetime import datetime, UTC
from typing import Dict, Optional, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
    field_validator,
)

# Helper for ObjectId serialization with strict validation
def validate_object_id(v: str | ObjectId) -> str:
    print(f"Validating: {v}")  # Debugging
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        try:
            ObjectId(v)  # Validate if string is a valid ObjectId
            return v
        except Exception:
            raise ValueError("Invalid ObjectId")
    raise ValueError("Invalid ObjectId: must be str or ObjectId")

PyObjectId = Annotated[
    str,
    BeforeValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class ContentIndex(BaseModel):
    """Defines the schema for the `content_index` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the indexed content.")
    page_id: PyObjectId = Field(..., description="Reference to the `pages` collection.")
    search_content: str = Field(..., description="Processed text for full-text search.")
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Faceted search fields (e.g., author, publication date)."
    )
    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the content was indexed."
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )