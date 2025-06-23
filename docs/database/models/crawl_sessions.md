### CrawlStats(pages_crawled, pages_failed, avg_response_time, resource_usage={'cpu': 0.0, 'memory_mb': 0.0})
- `pages_crawled`: Number of pages successfully crawled (integer >= 0).
- `pages_failed`: Number of pages that failed to crawl (integer >= 0).
- `avg_response_time`: Average response time in milliseconds (float >= 0).
- `resource_usage`: Dictionary for resource usage metrics with keys like "cpu" and "memory_mb" (floats >= 0).

### validate_resource_usage(cls, v)
- `v`: The dictionary to validate; ensures all values are non-negative.

### CrawlSession(id=None, site_id, start_time, end_time=None, trigger='manual', status='running', stats, error=None)
- `id`: Optional unique identifier for the crawl session (`PyObjectId`, handles ObjectId or string).
- `site_id`: Reference to a site document (`PyObjectId` type; expects ObjectId or string convertible value).
- `start_time`: Timestamp when the crawl session started (`datetime` object).
- `end_time`: Optional timestamp when the crawl session ended.
- `trigger`: Trigger source for the crawl e.g., 'manual'/'scheduled'/'monitoring' (string; default is 'manual').
- `status`: Status of the crawling process e.g., 'running'/'completed'/'failed' (string; default is 'running').
- `stats`: Statistics related to this session (`CrawlStats` model instance).
- `error`: Optional error message if the crawl failed.