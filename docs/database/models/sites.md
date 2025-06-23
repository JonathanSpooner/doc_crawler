### CrawlPatterns(allowed_domains, start_urls, deny_patterns=..., allow_patterns=...)
- `allowed_domains`: List of domains allowed for crawling.
- `start_urls`: Initial URLs to start crawling from.
- `deny_patterns`: URL patterns to exclude from crawling.
- `allow_patterns`: URL patterns to include in crawling.

### RetryPolicy(max_retries=..., retry_delay=...)
- `max_retries`: Maximum number of retry attempts.
- `retry_delay`: Delay between retries in milliseconds.

### Politeness(delay=..., user_agent=..., retry_policy=...)
- `delay`: Delay between requests in milliseconds.
- `user_agent`: User agent string for requests.
- `retry_policy`: Retry policy for failed requests.

### Monitoring(active=..., frequency=..., last_crawl_time=None, next_scheduled_crawl=None)
- `active`: Whether monitoring is active for the site.
- `frequency`: Frequency of monitoring (e.g., 'daily', 'weekly').
- `last_crawl_time`: Timestamp of the last crawl (optional).
- `next_scheduled_crawl`: Timestamp of the next scheduled crawl (optional).

### Site(id=None, name, base_url, crawl_patterns, politeness=..., monitoring=..., tags=..., created_at=..., updated_at=...)
- `id`: Unique identifier for the site (optional).
- `name`: Name of the site.
- `base_url`: Base URL of the site.
- `crawl_patterns`: Crawl patterns for the site (`CrawlPatterns` model).
- `politeness`: Politeness settings for crawling (`Politeness` model).
- `monitoring`: Monitoring settings for the site (`Monitoring` model).
- `tags`: Tags for categorizing the site.
- `created_at': Timestamp when added (defaults to now).
 - ‘updated_at’: Timestamp when last updated (defaults to now).

### validate_base_url(v: str) -> str
 - 'v': The base URL string being validated or modified by this classmethod validator. 