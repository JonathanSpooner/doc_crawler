### ContentDiff(BaseModel)
- `added`: String representing content added in the new version.
- `removed`: String representing content removed from the old version.

### ContentChange(BaseModel)
- `id`: Optional MongoDB ObjectId (serialized as a string), unique identifier for the change record.
- `site_id`: MongoDB ObjectId (serialized as a string), reference to the sites collection.
- `page_id`: MongoDB ObjectId (serialized as a string), reference to the pages collection.
- `detected_at`: Datetime of when the change was detected, defaults to current UTC time.
- `change_type`: Literal value indicating type of change ("content", "metadata", or "new").
- `diff`: ContentDiff object detailing added/removed content between versions.
- `severity`: Literal value indicating severity of change ("minor", "major", or "critical").
- `old_content_hash`: SHA256 hash string of old content.
- `new_content_hash`: SHA256 hash string of new content.