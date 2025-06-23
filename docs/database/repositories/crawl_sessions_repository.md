### CrawlStats(pages_discovered=0, pages_crawled=0, pages_failed=0, bytes_downloaded=0, errors_count=0, **kwargs)
- `pages_discovered`: Number of pages discovered in the crawl.
- `pages_crawled`: Number of pages successfully crawled.
- `pages_failed`: Number of failed crawl attempts.
- `bytes_downloaded`: Total number of bytes downloaded during crawling.
- `errors_count`: Count of errors encountered during the crawl.
- `**kwargs`: Additional statistics such as start_time, end_time, and duration_seconds.

### CrawlSession(id=None, site_id=None, status="running", config=None, stats=None, **kwargs)
- `id`: Unique identifier for the crawl session (MongoDB ObjectId).
- `site_id`: Identifier for the target site (ObjectId).
- `status`: Session status ("running", "completed", etc.).
- `config`: Configuration dictionary for this crawl session.
- `stats`: An instance of CrawlStats tracking this session's progress.
- `**kwargs`: Optional fields such as started_at, completed_at, error_message.

### CrawlSessionsRepository(connection_string: str, db_name: str, sites_repository: SitesRepository)
- `connection_string`: MongoDB connection URI string.
- `db_name`: Name of the MongoDB database to use.
- `sites_repository`: Instance for retrieving and updating site configurations.

### create(connection_string: str, db_name: str, sites_repository: SitesRepository)
- Classmethod. Initializes a repository and collection indexes asynchronously.

### _setup_indexes(self)
- Sets up MongoDB collection indexes required by repository queries.

### start_crawl_session(self, site_id: ObjectId, config: Dict) -> ObjectId
- Starts a new crawl session document in MongoDB with given configuration and checks concurrency limits per site.

### update_session_progress(self, session_id: ObjectId, stats: CrawlStats) -> bool
- Updates statistics for a running session identified by ID using provided CrawlStats object.

### complete_crawl_session(self, session_id: ObjectId, final_stats: CrawlStats) -> bool
- Marks a session as completed in the database with final aggregated statistics and updates last crawl time on associated site entry.

### get_active_sessions(self) -> List[CrawlSession]
- Retrieves all currently running/active sessions from MongoDB collection.

### get_session_history(self, site_id: ObjectId , limit:int = 50) -> List[CrawlSession]
 - Returns recent sessions related to specified site id up to given limit ordered by most recent first. 

### get_session_statistics(self ,session_id:ObjectId)->Optional[CrawlStats]
 - Retrieves statistics object corresponding to given individual session identifier or returns None if not found. 

### abort_session(self ,session_id:ObjectId ,reason:str)->bool
 - Aborts currently running/cancellable crawl job marking it accordingly with reason provided. 

 ### get_concurrent_session_count (self ,site_id :ObjectId )->int 
  - Returns integer count of concurrent/running sessions per target website id .

 ### cleanup_old_sessions (self ,days_old :int =30)->int 
  - Cleans up sessions that have finished (completed/aborted/failed) before age threshold; returns total deleted .

 ### _document_to_session (self ,doc :Dict )->CrawlSession 
  - Converts plain dict/Mongo-style document into strongly typed domain model (`CrawlSession`).