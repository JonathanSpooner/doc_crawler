### AuthorWork(id: Optional[PyObjectId]=None, author_name: str, work_title: str, publication_date: Optional[str]=None, site_id: PyObjectId, page_id: PyObjectId, work_id: Optional[str]=None, tags: List[str]=[], created_at: datetime=..., updated_at: datetime=...)
- `id`: Unique identifier for the work (as MongoDB ObjectId; optional).
- `author_name`: Name of the author.
- `work_title`: Title of the philosophical work.
- `publication_date`: Publication date in "YYYY-MM-DD" format (optional).
- `site_id`: Reference to associated site (MongoDB ObjectId).
- `page_id`: Reference to associated page (MongoDB ObjectId).
- `work_id`: External deduplication identifier like DOI or ISBN (optional).
- `tags`: List of string tags for categorizing the work.
- `created_at`: Timestamp of when item was added; defaults to now.
- `updated_at`: Timestamp of last update; defaults to now.

### validate_publication_date(cls, v: Optional[str]) -> Optional[str]
- `v`: String value representing a publication date; returned only if valid or None.