from datetime import datetime, UTC
from typing import List, Optional, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
    field_validator,
)

# Helper for ObjectId serialization
PyObjectId = Annotated[
    str,
    BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class SiteMap(BaseModel):
    """Defines the schema for the `site_maps` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the sitemap.")
    site_id: PyObjectId = Field(..., description="Reference to the `sites` collection.")
    url: str = Field(..., description="URL of the sitemap.")
    last_parsed: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the sitemap was last parsed.")
    urls: List[str] = Field(default=[], description="List of URLs extracted from the sitemap.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure the sitemap URL is valid."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Sitemap URL must start with 'http://' or 'https://'.")
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
