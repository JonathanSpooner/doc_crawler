### SiteMap(id: Optional[PyObjectId] = ..., site_id: PyObjectId, url: str, last_parsed: datetime = ..., urls: List[str] = ...)
- `id`: Optional unique identifier for the sitemap (`_id` in MongoDB).
- `site_id`: Reference to corresponding `sites` collection.
- `url`: The URL of the sitemap (must start with 'http://' or 'https://').
- `last_parsed`: Timestamp indicating when the sitemap was last parsed.
- `urls`: List of URLs extracted from the sitemap.

### validate_url(v: str) -> str
- `v`: The string value representing the URL to be validated.