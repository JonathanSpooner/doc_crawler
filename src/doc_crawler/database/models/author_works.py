from datetime import datetime, UTC
from typing import Optional, List, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    computed_field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
)

from doc_crawler.database.models.historical_date import HistoricalDate

# Helper for ObjectId serialization
PyObjectId = Annotated[
    str,
    BeforeValidator(lambda x: str(x) if isinstance(x, ObjectId) else x),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class AuthorWork(BaseModel):
    """Defines the schema for the `author_works` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the work.")
    author_name: str = Field(..., description="Name of the author.")
    work_title: str = Field(..., description="Title of the philosophical work.")
    publication_date: Optional[HistoricalDate] = Field(None, description="Publication date of the work (e.g., '2023-01-01').")
    site_id: PyObjectId = Field(..., description="Reference to the `sites` collection where the work was found.")
    page_id: PyObjectId = Field(..., description="Reference to the `pages` collection where the work is stored.")
    work_id: Optional[str] = Field(None, description="External identifier for deduplication (e.g., DOI, ISBN).")
    tags: List[str] = Field(default=[], description="Tags for categorizing the work.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the work was added.")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the work was last updated.")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
