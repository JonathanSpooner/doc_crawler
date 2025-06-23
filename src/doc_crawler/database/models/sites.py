# database/models/sites.py
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

class CrawlPatterns(BaseModel):
    """Defines the crawl patterns for a site."""
    allowed_domains: List[str] = Field(..., description="List of domains allowed for crawling.")
    start_urls: List[str] = Field(..., description="Initial URLs to start crawling from.")
    deny_patterns: List[str] = Field(default=[], description="URL patterns to exclude from crawling.")
    allow_patterns: List[str] = Field(default=[], description="URL patterns to include in crawling.")

class RetryPolicy(BaseModel):
    """Defines the retry policy for failed requests."""
    max_retries: int = Field(default=3, ge=0, description="Maximum number of retry attempts.")
    retry_delay: int = Field(default=1000, ge=100, description="Delay between retries in milliseconds.")

class Politeness(BaseModel):
    """Defines politeness settings for crawling."""
    delay: int = Field(default=1000, ge=100, description="Delay between requests in milliseconds.")
    user_agent: str = Field(default="Mozilla/5.0", description="User agent string for requests.")
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy, description="Retry policy for failed requests.")

class Monitoring(BaseModel):
    """Defines monitoring settings for a site."""
    active: bool = Field(default=True, description="Whether monitoring is active for the site.")
    frequency: str = Field(default="daily", description="Frequency of monitoring (e.g., 'daily', 'weekly').")
    last_crawl_time: Optional[datetime] = Field(None, description="Timestamp of the last crawl.")
    next_scheduled_crawl: Optional[datetime] = Field(None, description="Timestamp of the next scheduled crawl.")

class Site(BaseModel):
    """Defines the schema for the `sites` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the site.")
    name: str = Field(..., description="Name of the site.")
    base_url: str = Field(..., description="Base URL of the site.")
    crawl_patterns: CrawlPatterns = Field(..., description="Crawl patterns for the site.")
    politeness: Politeness = Field(default_factory=Politeness, description="Politeness settings for crawling.")
    monitoring: Monitoring = Field(default_factory=Monitoring, description="Monitoring settings for the site.")
    tags: List[str] = Field(default=[], description="Tags for categorizing the site.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the site was added.")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Timestamp when the site was last updated.")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure the base URL is valid and ends with a slash."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with 'http://' or 'https://'.")
        if not v.endswith("/"):
            v += "/"
        return v

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
