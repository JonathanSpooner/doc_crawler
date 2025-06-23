from pymongo import ASCENDING, DESCENDING, IndexModel
from typing import List

'''
Usage Example
```python
from pymongo import MongoClient
from database.repositories.page_indexes import get_page_indexes

client = MongoClient("mongodb://localhost:27017")
db = client["philosophy_crawler"]
pages_collection = db["pages"]

# Apply indexes
pages_collection.create_indexes(get_page_indexes())
```
'''
def get_page_indexes() -> List[IndexModel]:
    """Define and return the indexes for the `pages` collection."""
    indexes = [
        # Unique index on URL to prevent duplicate pages
        IndexModel([("url", ASCENDING)], unique=True, name="url_unique"),

        # Index on site_id for efficient filtering by site
        IndexModel([("site_id", ASCENDING)], name="site_id_index"),

        # Index on last_modified for sorting and querying by modification time
        IndexModel([("last_modified", DESCENDING)], name="last_modified_desc"),

        # Index on content_hash for deduplication checks
        IndexModel([("content_hash", ASCENDING)], name="content_hash_index"),

        # Index on status for filtering by processing state
        IndexModel([("status", ASCENDING)], name="status_index"),

        # Compound index for dashboard queries (site_id + status + last_modified)
        IndexModel(
            [
                ("site_id", ASCENDING),
                ("status", ASCENDING),
                ("last_modified", DESCENDING),
            ],
            name="dashboard_metrics",
        ),

        # Index on metadata.language for multilingual filtering
        IndexModel([("metadata.language", ASCENDING)], name="language_index"),

        # Index on metadata.word_count for content length queries
        IndexModel([("metadata.word_count", ASCENDING)], name="word_count_index"),
    ]

    return indexes