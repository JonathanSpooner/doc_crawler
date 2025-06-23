### RedirectHistory(from_url: str, to_url: str, timestamp: datetime = ...)
- `from_url`: Original URL before redirection.
- `to_url`: Destination URL after redirection.
- `timestamp`: Time when the redirect occurred.

#### RedirectHistory.validate_url(cls, v: str) -> str
- `v`: URL string (either source or destination) to validate as starting with 'http://' or 'https://'.

### PageMetadata(author: Optional[str] = None, publication_date: Optional[str] = None, language: Optional[str] = None, word_count: Optional[int] = None, reading_time: Optional[int] = None, keywords: List[str] = [])
- `author`: Author of the page content (optional).
- `publication_date`: Publication date of the content (optional).
- `language`: Language of the content (optional).
- `word_count`: Number of words in the content (optional; non-negative).
- `reading_time`: Estimated reading time in minutes (optional; non-negative).
- `keywords`: List of keywords extracted from the content.

### PageVersion(content: str, timestamp: datetime = ...)
- `content`: Snapshot of the page content at this version.
- `timestamp`: Time when this version was captured.

### Page(id: Optional[PyObjectId] = None, url: str, site_id: PyObjectId, title: Optional[str] = None, content: str, content_hash: str,
          redirect_history: List[RedirectHistory]=[], metadata=PageMetadata(), versions=[], last_modified=datetime.utcnow(), status="pending", error=None)
- `id`: Unique identifier for the page (ObjectId as string; optional).
- `url`: URL of the page.
- `site_id`: Reference to a site document by ObjectId.
- `title`: Title of the page (optional).
- `content`: Extracted text/content from this web page.
- `content_hash`: SHA256 hash for deduplication and change tracking.
- redirect_history:` History list with records detailing all redirects leading to this final URL.
    - Each entry is a RedirectHistory model record
    - Defaults to empty list if not provided
  - metadata:` Metadata about authorship etc. (`PageMetadata`)
  - versions:` History/snapshots` List[PageVersion]
  - last_modified:` When it was last changed. Defaults to now on creation/update`
  - status:` Processing state ('pending', 'processed', etc), default "pending"
   error : Output if crawl/processing failed

#### Page.validate_url(cls,v:str)->str
  - v : The value passed into url. Validates that it's a proper HTTP/HTTPS url

#### Page.validate_content_hash(cls,v:str)->str
  - v : Value passed into "content_hash"; must be valid sha256 lowercase hexadecimal digest.