from pymongo import ASCENDING, DESCENDING
from typing import List
from motor.motor_asyncio import AsyncIOMotorCollection

async def create_crawl_sessions_indexes(collection: AsyncIOMotorCollection) -> List[str]:
    """
    Creates indexes for the `crawl_sessions` collection to optimize query performance.
    
    Args:
        collection: The MongoDB collection for `crawl_sessions`.
    
    Returns:
        List of index names that were created.
    """
    indexes = [
        # Index for querying by `site_id` and `status`
        {
            "name": "site_status",
            "keys": [("site_id", ASCENDING), ("status", ASCENDING)],
            "background": True  # Non-blocking index creation
        },
        # Index for querying by `start_time` (descending for recent crawls)
        {
            "name": "start_time_desc",
            "keys": [("start_time", DESCENDING)],
            "background": True
        },
        # Compound index for dashboard queries (site_id + status + start_time)
        {
            "name": "dashboard_metrics",
            "keys": [
                ("site_id", ASCENDING),
                ("status", ASCENDING),
                ("start_time", DESCENDING)
            ],
            "background": True
        }
    ]
    
    created_indexes = []
    for index_spec in indexes:
        await collection.create_index(index_spec["keys"], name=index_spec["name"], background=index_spec["background"])
        created_indexes.append(index_spec["name"])
    
    return created_indexes