### get_page_indexes()
- Returns a list of `IndexModel` objects that define the indexes for the `pages` collection.

#### Constructed IndexModel Objects

##### IndexModel([("url", ASCENDING)], unique=True, name="url_unique")
- Single-field unique index on `url` in ascending order.
- Ensures no duplicate URLs are stored and enables efficient lookups by URL.

##### IndexModel([("site_id", ASCENDING)], name="site_id_index")
- Single-field index on `site_id` in ascending order.
- Optimizes queries that filter or group pages by their associated site.

##### IndexModel([("last_modified", DESCENDING)], name="last_modified_desc")
- Single-field index on `last_modified` in descending order.
- Enables sorting and querying by most recently modified pages efficiently.

##### IndexModel([("content_hash", ASCENDING)], name="content_hash_index")
- Single-field index on `content_hash` in ascending order.
- Facilitates quick deduplication checks based on page content hashes.

##### IndexModel([("status", ASCENDING)], name="status_index")
- Single-field index on `status`.
- Speeds up queries filtering or grouping by processing state (e.g., 'crawled', 'pending').

##### IndexModel([
    ("site_id", ASCENDING),
    ("status", ASCENDING),
    ("last_modified", DESCENDING)
], name="dashboard_metrics")
- Compound index over `site_id`, then `status`, then `last_modified`.
- Optimizes multi-condition dashboard metrics queries (e.g., filter by site and status, ordered by most recent) by efficiently combining these three fields[1][2][4].

##### IndexModel([("metadata.language", ASCENDING)], name="language_index")
- Single-field index on nested field `metadata.language`.
- Allows fast filtering for multilingual support or discovery of content language variants.

##### IndexModel([("metadata.word_count", ASCENDING)], name="word_count_index")
- Single-field index on nested field `metadata.word_count`.
- Supports efficient querying or ranking based on document word count.