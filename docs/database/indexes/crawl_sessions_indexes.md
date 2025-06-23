### create_crawl_sessions_indexes(collection)
- `collection`: The MongoDB collection for `crawl_sessions`.

##### IndexModel([("site_id", ASCENDING), ("status", ASCENDING)], name="site_status")
- Compound index on `site_id` and `status` in ascending order.
- Optimizes queries filtering documents by `site_id` and `status`.

##### IndexModel([("start_time", DESCENDING)], name="start_time_desc")
- Single-field index on `start_time` in descending order.
- Enables efficient querying and sorting by start time in descending order.

##### IndexModel([
    ("site_id", ASCENDING),
    ("status", ASCENDING),
    ("start_time", DESCENDING)
], name="dashboard_metrics")
- Compound index over `site_id`, then `status`, then `start_time`.
- Optimizes queries involving these fields for dashboard metric queries.