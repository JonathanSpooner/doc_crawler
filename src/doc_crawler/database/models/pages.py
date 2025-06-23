# database/models/pages.py
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

class RedirectHistory(BaseModel):
    """Defines a record of URL redirects for a page."""
    from_url: str = Field(..., description="Original URL before redirection.")
    to_url: str = Field(..., description="Destination URL after redirection.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Time when the redirect occurred.")

    @field_validator("from_url", "to_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URLs are valid."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with 'http://' or 'https://'.")
        return v

class PageMetadata(BaseModel):
    """Defines metadata for a crawled page."""
    author: Optional[str] = Field(None, description="Author of the page content.")
    publication_date: Optional[str] = Field(None, description="Publication date of the content.")
    language: Optional[str] = Field(None, description="Language of the content.")
    word_count: Optional[int] = Field(None, ge=0, description="Number of words in the content.")
    reading_time: Optional[int] = Field(None, ge=0, description="Estimated reading time in minutes.")
    keywords: List[str] = Field(default=[], description="Keywords extracted from the content.")

class PageVersion(BaseModel):
    """Defines a versioned snapshot of page content."""
    content: str = Field(..., description="Snapshot of the page content at this version.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Time when this version was captured.")

class Page(BaseModel):
    """Defines the schema for the `pages` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the page.")
    url: str = Field(..., description="URL of the page.")
    site_id: PyObjectId = Field(..., description="Reference to the `sites` collection.")
    title: Optional[str] = Field(None, description="Title of the page.")
    content: str = Field(..., description="Extracted content of the page.")
    content_hash: str = Field(..., description="SHA-256 hash of the content for deduplication.")
    redirect_history: List[RedirectHistory] = Field(default=[], description="History of URL redirects for this page.")
    metadata: PageMetadata = Field(default_factory=PageMetadata, description="Metadata for the page.")
    versions: List[PageVersion] = Field(default=[], description="Versioned snapshots of the page content.")
    last_modified: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Time when the page was last modified.")
    status: str = Field(default="pending", description="Status of the page (e.g., 'pending', 'processed', 'failed').")
    error: Optional[str] = Field(None, description="Error message if the page processing failed.")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure the URL is valid and properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with 'http://' or 'https://'.")
        return v

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, v: str) -> str:
        """Ensure the content hash is a valid SHA-256 string."""
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Content hash must be a valid SHA-256 string (64 hex characters).")
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
