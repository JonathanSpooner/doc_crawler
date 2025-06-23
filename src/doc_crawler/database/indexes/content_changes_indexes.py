from pymongo import ASCENDING, DESCENDING, IndexModel
from typing import List

def get_content_changes_indexes() -> List[IndexModel]:
    """Define and return the indexes for the `content_changes` collection."""
    indexes = [
        # Index on site_id for efficient filtering by site
        IndexModel([("site_id", ASCENDING)], name="site_id_index"),

        # Index on detected_at for sorting and querying by detection time
        IndexModel([("detected_at", DESCENDING)], name="detected_at_desc"),

        # Index on change_type for filtering by type of change
        IndexModel([("change_type", ASCENDING)], name="change_type_index"),

        # Index on severity for prioritizing change handling
        IndexModel([("severity", ASCENDING)], name="severity_index"),

        # Compound index for monitoring queries (site_id + detected_at + change_type)
        IndexModel(
            [
                ("site_id", ASCENDING),
                ("detected_at", DESCENDING),
                ("change_type", ASCENDING),
            ],
            name="monitoring_metrics",
        ),

        # TTL index for auto-expiring records after 1 year (31536000 seconds)
        IndexModel(
            [("detected_at", ASCENDING)],
            expireAfterSeconds=31536000,
            name="ttl_index",
        ),
    ]

    return indexes