### get_content_changes_indexes()
- Returns a list of `IndexModel` objects that define the indexes for the `content_changes` collection.

#### Constructed IndexModel Objects

##### IndexModel([("site_id", ASCENDING)], name="site_id_index")
- Single-field index on `site_id` in ascending order.
- Optimizes queries filtering documents by `site_id`.

##### IndexModel([("detected_at", DESCENDING)], name="detected_at_desc")
- Single-field index on `detected_at` in descending order.
- Enables efficient querying and sorting by detection time.

##### IndexModel([("change_type", ASCENDING)], name="change_type_index")
- Single-field index on `change_type` in ascending order.
- Speeds up queries filtering by type of change.

##### IndexModel([("severity", ASCENDING)], name="severity_index")
- Single-field index on `severity` in ascending order.
- Facilitates prioritization or filtering based on severity level.

##### IndexModel([
    ("site_id", ASCENDING),
    ("detected_at", DESCENDING),
    ("change_type", ASCENDING),
], name="monitoring_metrics")
- Compound index over `site_id`, then `detected_at`, then `change_type`.
- Optimizes multi-condition lookups involving these fields, such as monitoring or reporting queries that filter and sort simultaneously[2][4][5].

##### IndexModel(
    [("detected_at", ASCENDING)],
    expireAfterSeconds=31536000,
    name="ttl_index"
)
- TTL (Time-To-Live) index on the field `detected_at`.
- Documents automatically expire after one year (31,536,000 seconds), supporting automatic cleanup[4].

#### Parameters for Each
None required; each constructed directly with field specifications and options needed for their function.