### validate_object_id(v: str | ObjectId) -> str
- `v`: Value to validate and convert, accepts a string or ObjectId; returns a valid string ObjectId or raises ValueError.

### ContentIndex(BaseModel)
- `id`: Optional PyObjectId; unique identifier for the content (aliased as `_id`).
- `page_id`: Required PyObjectId; references the associated page in the collection.
- `search_content`: String with processed text for full-text search.
- `metadata`: Dictionary of string keys and values for faceted search fields (default: empty dict).
- `indexed_at`: Datetime when content was indexed (defaults to now, UTC).