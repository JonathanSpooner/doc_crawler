# Scrapy Philosophy Text Crawler - Development Outline

## Project Overview
A respectful, long-term philosophical text collection system targeting academic philosophy sites with intelligent monitoring, clean text extraction, and modular architecture for multi-environment deployment.

## Phase 1: Foundation & Core Architecture (Weeks 1-2)

### 1.1 Project Structure & Environment Setup
```
philosophy_crawler/
├── scrapy_project/
│   ├── philosophy_scraper/
│   │   ├── spiders/
│   │   ├── items.py
│   │   ├── pipelines.py
│   │   ├── middlewares.py
│   │   └── settings.py
│   └── scrapy.cfg
├── database/
│   ├── models/
│   ├── repositories/
│   └── migrations/
├── processors/
│   ├── text_cleaner.py
│   ├── pdf_converter.py
│   └── content_analyzer.py
├── monitoring/
│   ├── dashboard/
│   ├── alerts/
│   └── reporting/
├── deployment/
│   ├── ansible/
│   ├── aws_cdk/
│   └── docker/
├── tests/
├── docs/
└── config/
```

### 1.2 Database Design (MongoDB with Abstraction Layer)
**Collections:**
- `sites`: Site configuration, crawl patterns, monitoring settings
- `pages`: Individual page records with content and metadata
- `crawl_sessions`: Crawl execution history and statistics  
- `content_changes`: Change detection for monitoring
- `processing_queue`: Async processing tasks with priority levels
- `alerts`: Error tracking and notification history
- `site_maps`: Cached sitemap data for efficient discovery
- `author_works`: Structured philosophical work metadata
- `content_index`: Search-ready content preparation (OpenSearch integration)

**Key Indexes:**
- `pages`: url (unique), site_id, last_modified, content_hash
- `crawl_sessions`: site_id, start_time, status
- `content_changes`: site_id, detected_at, change_type
- `processing_queue`: priority, status, created_at

**Abstraction Layer:**
- Repository pattern for database operations
- Interface definitions for easy migration to other document DBs
- Connection pooling and retry logic
- Async operation support for high-throughput scenarios

### 1.3 Core Configuration System
- Environment-based configuration (dev/staging/prod)
- Site-specific crawling rules and patterns
- Rate limiting and politeness settings
- Notification preferences and thresholds

## Phase 2: Spider Development & Content Processing (Weeks 3-4)

### 2.1 Base Spider Architecture
**Generic Philosophy Spider:**
- Configurable URL patterns and extraction rules
- Intelligent content type detection
- Respectful crawling with delays and user-agent rotation
- Duplicate detection and URL canonicalization
- Sitemap.xml parsing for efficient discovery
- Robots.txt compliance checking

**Site-Specific Spiders:**
- `IEPSpider`: Internet Encyclopedia of Philosophy patterns
- `GutenbergSpider`: Project Gutenberg navigation and catalog parsing
- `EarlyModernSpider`: Early Modern Texts (one-time complete crawl)
- `ClassicsSpider`: MIT Classics collection structure
- `SEPSpider`: Stanford Encyclopedia of Philosophy (you listed IEP twice)

### 2.2 Content Processing Pipeline
**Text Extraction Pipeline:**
1. HTML cleaning and text extraction
2. PDF to text conversion (using PyPDF2/pdfplumber)
3. Character encoding normalization (UTF-8/UTF-16)
4. Philosophical text structure detection
5. Metadata extraction (author, title, publication info)

**Quality Assurance:**
- Minimum content length validation
- Language detection and filtering
- Duplicate content detection
- Format consistency checking

### 2.3 Monitoring & Change Detection
**Site Monitoring System:**
- Daily crawl scheduling for active sites
- Sitemap parsing and comparison
- Content fingerprinting for change detection
- New page discovery algorithms

## Phase 3: Advanced Features & Reliability (Weeks 5-6)

### 3.1 Error Handling & Recovery
**Robust Error Management:**
- Categorized error handling (network, parsing, storage)
- Automatic retry mechanisms with exponential backoff
- Circuit breaker pattern for failing sites
- Graceful degradation strategies

**Crawl State Management:**
- Checkpoint system for resuming interrupted crawls
- Progress tracking and partial success handling
- Queue management for large crawls
- Memory usage optimization

### 3.2 Monitoring Dashboard
**Web-based Dashboard:**
- Real-time crawl status and statistics
- Site health monitoring
- Content growth tracking
- Error rate visualization
- Performance metrics

**Key Metrics:**
- Pages crawled per site
- Success/failure rates
- Processing times
- Storage utilization
- Change detection results

### 3.3 Notification System
**Alert Categories:**
- **Critical (Slack)**: Site completely inaccessible, database failures
- **High (Daily Email)**: Parsing errors, significant rate drops
- **Medium (Weekly Report)**: New content summaries, performance trends
- **Low (Monthly)**: System health, optimization suggestions

**Notification Templates:**
- Weekly summary with new content highlights
- Error aggregation with actionable insights
- Performance reports with recommendations

## Phase 4: Deployment & Scaling (Weeks 7-8)

### 4.1 Local Development Environment
**Ansible Playbook for Local Setup:**
- MongoDB installation and configuration
- Python environment setup
- Scrapy project deployment
- Monitoring stack installation
- Backup and maintenance scripts

### 4.2 AWS Serverless Architecture
**CDK Infrastructure:**
- ECS Fargate for Scrapy containers
- DocumentDB for MongoDB compatibility
- CloudWatch for monitoring and alerting
- S3 for content storage and backups
- Lambda for scheduled triggers
- SES for email notifications
- Secrets Manager for configuration

### 4.3 Containerization
**Docker Setup:**
- Multi-stage builds for optimization
- Environment-specific configurations
- Health checks and monitoring hooks
- Volume management for persistent data

## Phase 6: Integration & Future-Proofing (Week 9)

### 6.1 OpenSearch Integration Preparation
**Search Infrastructure:**
- Content indexing pipeline for full-text search
- Structured metadata extraction for faceted search
- Author and work relationship mapping
- Search API layer for future applications

### 6.2 Content Quality & Validation
**Philosophical Content Validation:**
- Author name standardization and verification
- Work title consistency and canonical forms  
- Publication date validation and historical context
- Content completeness scoring
- Duplicate work detection across sites

### 6.3 Performance Optimization
**System Optimization:**
- Database query optimization and indexing strategy
- Concurrent crawling limits and resource management
- Memory usage profiling and optimization
- Caching strategies for frequently accessed data
- Async processing for non-blocking operations

## Phase 5: Testing & Documentation (Ongoing)

### 5.1 Testing Strategy
**Unit Tests:**
- Spider logic and extraction rules
- Database operations and repositories  
- Content processing functions
- Notification system components

**Integration Tests:**
- End-to-end crawling scenarios
- Database consistency checks
- Pipeline processing validation
- Alert system functionality
- Multi-site crawling coordination

**Performance Tests:**
- Load testing with large datasets
- Memory usage profiling
- Database query performance
- Concurrent crawling stress tests
- Long-running stability tests

### 5.2 Documentation
**Technical Documentation:**
- API documentation for all components
- Database schema and relationships
- Deployment guides for each environment
- Configuration reference and examples
- Troubleshooting guides and common issues
- Performance tuning recommendations

**User Documentation:**
- Getting started guide
- Adding new sites procedures
- Monitoring and maintenance workflows
- Best practices and optimization tips
- Backup and recovery procedures

## Technology Stack Summary

### Core Technologies
- **Scrapy**: Web scraping framework
- **MongoDB**: Primary document database
- **Python 3.9+**: Programming language
- **Docker**: Containerization
- **Ansible**: Local deployment automation
- **AWS CDK**: Cloud infrastructure as code

### Supporting Libraries
- **PyPDF2/pdfplumber**: PDF text extraction
- **BeautifulSoup4**: HTML parsing and cleaning
- **chardet**: Character encoding detection
- **APScheduler**: Advanced task scheduling with persistence
- **loguru**: Structured logging with rotation
- **pymongo**: MongoDB driver with connection pooling
- **motor**: Async MongoDB driver for high-performance operations
- **aiohttp**: Async HTTP client for concurrent requests
- **selenium**: JavaScript rendering (future enhancement)
- **bleach**: HTML sanitization for security
- **langdetect**: Language identification for content filtering

### Monitoring & Alerting
- **Prometheus**: Metrics collection
- **Grafana**: Dashboard visualization
- **SMTP/SES**: Email notifications
- **Slack API**: Critical alerts
- **CloudWatch**: AWS monitoring

## Development Milestones

### Week 1-2: Foundation
- [ ] Project structure setup
- [ ] Database design and abstraction layer
- [ ] Basic spider framework
- [ ] Local development environment

### Week 3-4: Core Functionality
- [ ] Site-specific spiders implementation
- [ ] Content processing pipeline
- [ ] Change detection system
- [ ] Basic monitoring

### Week 5-6: Reliability & Monitoring
- [ ] Error handling and recovery
- [ ] Monitoring dashboard
- [ ] Notification system
- [ ] Performance optimization

### Week 7-8: Deployment
- [ ] Ansible playbooks for local server deployment
- [ ] AWS CDK infrastructure with cost optimization
- [ ] Docker containerization with multi-stage builds
- [ ] Production deployment with blue-green strategy
- [ ] Backup and disaster recovery implementation

### Week 9: Integration & Future-Proofing  
- [ ] OpenSearch integration preparation
- [ ] Content quality validation system
- [ ] Performance optimization and profiling
- [ ] Long-term maintenance automation
- [ ] Documentation completion and review

### Ongoing: Testing & Documentation
- [ ] Comprehensive test suite
- [ ] Documentation completion
- [ ] Performance tuning
- [ ] Feature enhancements

## Risk Mitigation

### Technical Risks
- **Site Structure Changes**: Implement flexible extraction rules
- **Rate Limiting**: Implement adaptive delays and monitoring
- **Data Volume**: Use efficient storage and processing strategies
- **Service Dependencies**: Implement circuit breakers and fallbacks

### Operational Risks
- **Maintenance Overhead**: Automate monitoring and alerts
- **Cost Management**: Implement usage tracking and optimization
- **Security**: Use secrets management and access controls
- **Backup Strategy**: Automated backups with restoration testing

## Success Metrics

### Functional Metrics
- Successfully crawl and process all target sites
- Achieve >95% uptime for monitoring system
- Detect new content within 24 hours
- Maintain <1% error rate for content processing

### Operational Metrics
- Zero-downtime deployments
- Automated recovery from common failures
- Clear documentation for all procedures
- Predictable and manageable costs

This outline provides a comprehensive roadmap for building a professional-grade philosophical text collection system that can scale from local development to cloud deployment while maintaining respect for target sites and providing reliable long-term operation.

[AI Chat](https://lw.longgonemedia.com/bookstack/attachments/128)

# Scrapy Philosophy Text Crawler - Development Outline

## Project Overview
A respectful, long-term philosophical text collection system targeting academic philosophy sites with intelligent monitoring, clean text extraction, and modular architecture for multi-environment deployment.

## Phase 1: Foundation & Core Architecture (Weeks 1-2)

### 1.1 Project Structure & Environment Setup
```
philosophy_crawler/
├── scrapy_project/
│   ├── philosophy_scraper/
│   │   ├── spiders/
│   │   ├── items.py
│   │   ├── pipelines.py
│   │   ├── middlewares.py
│   │   └── settings.py
│   └── scrapy.cfg
├── database/
│   ├── models/
│   ├── repositories/
│   └── migrations/
├── processors/
│   ├── text_cleaner.py
│   ├── pdf_converter.py
│   └── content_analyzer.py
├── monitoring/
│   ├── dashboard/
│   ├── alerts/
│   └── reporting/
├── deployment/
│   ├── ansible/
│   ├── aws_cdk/
│   └── docker/
├── tests/
├── docs/
└── config/
```

### 1.2 Database Design (MongoDB with Abstraction Layer)
**Collections:**
- `sites`: Site configuration, crawl patterns, monitoring settings
- `pages`: Individual page records with content and metadata
- `crawl_sessions`: Crawl execution history and statistics  
- `content_changes`: Change detection for monitoring
- `processing_queue`: Async processing tasks with priority levels
- `alerts`: Error tracking and notification history
- `site_maps`: Cached sitemap data for efficient discovery
- `author_works`: Structured philosophical work metadata
- `content_index`: Search-ready content preparation (OpenSearch integration)

**Key Indexes:**
- `pages`: url (unique), site_id, last_modified, content_hash
- `crawl_sessions`: site_id, start_time, status
- `content_changes`: site_id, detected_at, change_type
- `processing_queue`: priority, status, created_at

**Abstraction Layer:**
- Repository pattern for database operations
- Interface definitions for easy migration to other document DBs
- Connection pooling and retry logic
- Async operation support for high-throughput scenarios

### **1.2 Database Design (MongoDB with Abstraction Layer)**

#### **Collections & Schemas**
We'll define the collections and their schemas using Python dictionaries (for clarity) and later implement them using `pymongo` or `motor` (for async operations).

1. **`sites` Collection**
   - **Purpose**: Store site configurations, crawl patterns, and monitoring settings.
   - **Schema**:
     ```python
     {
        "_id": ObjectId,  # Auto-generated
        "name": str,
        "base_url": str,
        "crawl_patterns": {
            "allowed_domains": [str],
            "start_urls": [str],
            "deny_patterns": [str],
            "allow_patterns": [str]
        },
        "politeness": {
            "delay": int,
            "user_agent": str,
            "retry_policy": {
                "max_retries": int,
                "retry_delay": int
            }
        },
        "monitoring": {
            "active": bool,
            "frequency": str,
            "last_crawl_time": datetime,
            "next_scheduled_crawl": datetime
        },
        "tags": [str],
        "created_at": datetime,
        "updated_at": datetime
    }
     ```

2. **`pages` Collection**
   - **Purpose**: Store individual page records with content and metadata.
   - **Schema**:
     ```python
     {
        "_id": ObjectId,
        "url": str,
        "site_id": ObjectId,
        "title": str,
        "content": str,
        "content_hash": str,
        "redirect_history": [{"from": str, "to": str, "timestamp": datetime}],
        "metadata": {
            "author": str,
            "publication_date": str,
            "language": str,
            "word_count": int,
            "reading_time": int,
            "keywords": [str]
        },
        "versions": [{"content": str, "timestamp": datetime}],
        "last_modified": datetime,
        "status": str,
        "error": str
    }
     ```

3. **`crawl_sessions` Collection**
   - **Purpose**: Track crawl execution history and statistics.
   - **Schema**:
     ```python
     {
        "_id": ObjectId,
        "site_id": ObjectId,
        "start_time": datetime,
        "end_time": datetime,
        "trigger": str,
        "status": str,
        "stats": {
            "pages_crawled": int,
            "pages_failed": int,
            "avg_response_time": float,
            "resource_usage": {"cpu": float, "memory_mb": float}
        },
        "error": str
    }
     ```

4. **`content_changes` Collection**
   - **Purpose**: Track changes detected in crawled content.
   - **Schema**:
     ```python
     {
        "_id": ObjectId,
        "site_id": ObjectId,
        "page_id": ObjectId,
        "detected_at": datetime,
        "change_type": str,
        "diff": {"added": str, "removed": str},
        "severity": str,
        "old_content_hash": str,
        "new_content_hash": str
    }
     ```

5. **`processing_queue` Collection**
   - **Purpose**: Manage async processing tasks with priority levels.
   - **Schema**:
     ```python
     {
        "_id": ObjectId,
        "task_type": str,
        "page_id": ObjectId,
        "priority": int,
        "status": str,
        "timeout_seconds": int,
        "dependencies": [ObjectId],
        "created_at": datetime,
        "processed_at": datetime,
        "max_retries":                 # Per task to avoid infinite loops.
    }
     ```

6. **`alerts` Collection**
   - **Purpose**: Track errors and notifications.
   - **Schema**:
     ```python
     {
         "_id": ObjectId,
         "type": str,                  # "error", "warning", "info"
         "message": str,
         "source": str,                # "crawler", "processor", "monitoring"
         "resolved": bool,
         "created_at": datetime,
         "resolved_at": datetime
     }
     ```

7. **`site_maps` Collection**
   - **Purpose**: Cache sitemap data for efficient discovery.
   - **Schema**:
     ```python
     {
         "_id": ObjectId,
         "site_id": ObjectId,          # Reference to `sites` collection
         "url": str,                   # Sitemap URL
         "last_parsed": datetime,
         "urls": [str]                 # Extracted URLs from sitemap
     }
     ```

8. **`author_works` Collection**
   - **Purpose**: Store structured philosophical work metadata.
   - **Schema**:
     ```python
     {
         "_id": ObjectId,
         "author_name": str,
         "work_title": str,
         "publication_date": str,
         "site_id": ObjectId,          # Reference to `sites` collection
         "page_id": ObjectId,          # Reference to `pages` collection
         "work_id":                    # For deduplication (e.g., DOI or ISBN if available).
     }
     ```

9. **`content_index` Collection**
   - **Purpose**: Prepare search-ready content for OpenSearch integration.
   - **Schema**:
     ```python
     {
         "_id": ObjectId,
         "page_id": ObjectId,          # Reference to `pages` collection
         "search_content": str,       # Processed text for search
         "metadata": dict              # Faceted search fields
     }
     ```

---

#### **Key Indexes**
To optimize query performance, we'll create the following indexes:

1. **`pages` Collection**:
   - `url` (unique)
   - `site_id`
   - `last_modified`
   - `content_hash`
   - `metadata.language` for multilingual filtering.
   - `metadata.word_count` for content length queries.

2. **`crawl_sessions` Collection**:
   - `site_id`
   - `start_time`
   - `status`

3. **`content_changes` Collection**:
   - `site_id`
   - `detected_at`
   - `change_type`
   - `severity` for prioritization.

4. **`processing_queue` Collection**:
   - `priority`
   - `status`
   - `created_at`
   - `task_type` for task-specific queries.

#### **Index Optimization**
##### **Covering Indexes for Critical Queries**
- **`pages`**: Add a covering index for dashboard queries:
  ```python
  db.pages.create_index([
      ("site_id", pymongo.ASCENDING),
      ("status", pymongo.ASCENDING),
      ("last_modified", pymongo.DESCENDING)
  ], name="dashboard_metrics")
  ```
- **`processing_queue`**: Optimize for task scheduling:
  ```python
  db.processing_queue.create_index([
      ("status", pymongo.ASCENDING),
      ("priority", pymongo.ASCENDING),
      ("created_at", pymongo.ASCENDING)
  ], name="task_scheduling")
  ```

---

#### **Abstraction Layer**
We'll implement a repository pattern to abstract database operations. Here's a Python example using `pymongo`:

```python
from pymongo import MongoClient
from typing import Dict, List, Optional
from datetime import datetime

class MongoDBRepository:
    def __init__(self, db_name: str, collection_name: str):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_one(self, document: Dict) -> str:
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def find_one(self, query: Dict) -> Optional[Dict]:
        return self.collection.find_one(query)

    def find_many(self, query: Dict) -> List[Dict]:
        return list(self.collection.find(query))

    def update_one(self, query: Dict, update_data: Dict) -> bool:
        result = self.collection.update_one(query, {"$set": update_data})
        return result.modified_count > 0

    def delete_one(self, query: Dict) -> bool:
        result = self.collection.delete_one(query)
        return result.deleted_count > 0
```

For async operations, we'll use `motor`:
```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional, Callable, Awaitable

# Configure `maxPoolSize` and `minPoolSize` in `AsyncIOMotorClient` for load balancing.
class AsyncMongoDBRepository:
    def __init__(self, db_name: str, collection_name: str):
        self.client = AsyncIOMotorClient("mongodb://localhost:27017/")
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def insert_one(self, document: Dict) -> str:
        async def op():
            result = await self.collection.insert_one(document)
            return str(result.inserted_id)
        return await self._with_retry(op)

    async def find_one(self, query: Dict) -> Optional[Dict]:
        async def op():
            return await self.collection.find_one(query)
        return await self._with_retry(op)

    async def find_many(self, query: Dict) -> List[Dict]:
        async def op():
            return await self.collection.find(query).to_list(None)
        return await self._with_retry(op)

    async def update_one(self, query: Dict, update_data: Dict) -> bool:
        async def op():
            result = await self.collection.update_one(query, {"$set": update_data})
            return result.modified_count > 0
        return await self._with_retry(op)

    async def delete_one(self, query: Dict) -> bool:
        async def op():
            result = await self.collection.delete_one(query)
            return result.deleted_count > 0
        return await self._with_retry(op)

    async def update_many(self, query: Dict, update_data: Dict) -> int:
        async def op():
            result = await self.collection.update_many(query, {"$set": update_data})
            return result.modified_count
        return await self._with_retry(op)

    async def insert_many(self, documents: List[Dict]) -> List[str]:
        async def op():
            result = await self.collection.insert_many(documents)
            return [str(id) for id in result.inserted_ids]
        return await self._with_retry(op)

    async def find_paginated(self, query: Dict, skip: int, limit: int) -> List[Dict]:
        async def op():
            cursor = self.collection.find(query).skip(skip).limit(limit)
            return await cursor.to_list(length=limit)
        return await self._with_retry(op)

    # Critical operations (e.g., moving a task from `processing_queue` to `pages`) should use MongoDB transactions.
    async def update_page_and_clear_task(session, page_id: ObjectId, update_data: Dict):
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                await self.pages.update_one({"_id": page_id}, {"$set": update_data}, session=session)
                await self.processing_queue.delete_one({"page_id": page_id}, session=session)

    async def _with_retry(self, operation: Callable[[], Awaitable], max_retries: int = 3, delay: float = 1.0):
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(delay)
```

### **Schema Validations**
#### **Field Constraints**
- **`sites.politeness.delay`**: Minimum value of 100ms to avoid accidental DDoS.
- **`pages.content_hash`**: Enforce SHA-256 hashing for consistency.
- **`processing_queue.priority`**: Range validation (1–5).
- **`content_changes.severity`**: Enum validation (`minor/major/critical`).

#### **Example (Using Pydantic for Validation)**
```python
from pydantic import BaseModel, Field, conint
from typing import Literal

class PolitenessPolicy(BaseModel):
    delay: conint(ge=100)  # Minimum 100ms delay
    user_agent: str
    max_retries: conint(ge=0)

class ContentChange(BaseModel):
    change_type: Literal["content", "metadata", "new"]
    severity: Literal["minor", "major", "critical"]
    diff: dict
```

### **Error Handling**
#### **Circuit Breaker Pattern**
- **For `crawl_sessions`**: Automatically pause crawls for a site if error rate exceeds 5%.
  ```python
  async def check_site_health(site_id: ObjectId):
      error_rate = await db.crawl_sessions.aggregate([
          {"$match": {"site_id": site_id, "status": "failed"}},
          {"$group": {"_id": None, "count": {"$sum": 1}}}
      ]).to_list(1)
      if error_rate and error_rate[0]["count"] > 0.05 * total_crawls:
          await db.sites.update_one({"_id": site_id}, {"$set": {"monitoring.active": False}})
  ```

### **Data Retention Policies**
- **`content_changes`**: Auto-expire records after 1 year:
  ```python
  db.content_changes.create_index(
      [("detected_at", pymongo.ASCENDING)],
      expireAfterSeconds=31536000  # 1 year in seconds
  )
  ```
- **`crawl_sessions`**: Archive old sessions to cold storage (e.g., S3) after 3 months.

### **6. Security**
- **Encryption-at-Rest**: Ensure MongoDB uses WiredTiger encryption.
- **Field-Level Redaction**:
  - Mask sensitive fields (e.g., `politeness.user_agent`) in logs.

### **Additional Recommendations**
2. **Caching**:
   - Implement Redis for frequently accessed data (e.g., `sites` configurations).
3. **Backup Strategy**:
   - Automate MongoDB backups with `mongodump` and store in S3.
4. **Sharding**:
   - Plan for sharding `pages` by `site_id` if the dataset grows beyond a single node’s capacity.

To generate the **1.2 Database Design** section systematically, we need a clear plan that outlines the order of code generation, dependencies between components, and the logical flow of implementation. Below is the **AI Generation Plan** for this spec:

---

### **AI Generation Plan for Database Design**

#### **1. Define the MongoDB Collections and Schemas**
- **Order**: Start with the collections that are foundational and have no dependencies on other collections.
- **Dependencies**: None.
- **Steps**:
  1. Generate the `sites` collection schema (base configuration).
  2. Generate the `pages` collection schema (stores crawled data).
  3. Generate the `crawl_sessions` collection schema (tracks crawl history).
  4. Generate the `content_changes` collection schema (tracks content updates).
  5. Generate the `processing_queue` collection schema (manages async tasks).
  6. Generate the `alerts` collection schema (tracks errors/notifications).
  7. Generate the `site_maps` collection schema (caches sitemap data).
  8. Generate the `author_works` collection schema (stores structured metadata).
  9. Generate the `content_index` collection schema (prepares search-ready content).

#### **2. Implement Key Indexes**
- **Order**: After defining schemas, create indexes to optimize queries.
- **Dependencies**: Requires the collections to be defined first.
- **Steps**:
  1. Generate indexes for the `pages` collection (`url`, `site_id`, `last_modified`, etc.).
  2. Generate indexes for the `crawl_sessions` collection (`site_id`, `start_time`, `status`).
  3. Generate indexes for the `content_changes` collection (`site_id`, `detected_at`, `change_type`).
  4. Generate indexes for the `processing_queue` collection (`priority`, `status`, `created_at`).
  5. Generate covering indexes for critical queries (e.g., `dashboard_metrics` for `pages`).

#### **3. Implement the Abstraction Layer**
- **Order**: After collections and indexes are defined, implement the repository pattern.
- **Dependencies**: Requires the schemas and indexes to be in place.
- **Steps**:
  1. Generate the synchronous `MongoDBRepository` class (using `pymongo`).
  2. Generate the asynchronous `AsyncMongoDBRepository` class (using `motor`).
  3. Include methods for CRUD operations (`insert_one`, `find_one`, `update_one`, etc.).
  4. Add transaction support for critical operations (e.g., `update_page_and_clear_task`).
  5. Implement retry logic (`_with_retry` method) for resilience.

#### **4. Add Schema Validations**
- **Order**: After the abstraction layer, add validation logic.
- **Dependencies**: Requires the schemas to be defined.
- **Steps**:
  1. Generate `Pydantic` models for field constraints (e.g., `PolitenessPolicy`, `ContentChange`).
  2. Add validation for:
     - Minimum delay (`sites.politeness.delay`).
     - SHA-256 hashing (`pages.content_hash`).
     - Priority range (`processing_queue.priority`).
     - Severity enum (`content_changes.severity`).

#### **5. Implement Error Handling and Circuit Breaker**
- **Order**: After the repository layer, add error handling.
- **Dependencies**: Requires the `crawl_sessions` collection and repository methods.
- **Steps**:
  1. Generate the `check_site_health` function to monitor error rates.
  2. Implement auto-pausing logic for sites exceeding error thresholds.

#### **6. Define Data Retention Policies**
- **Order**: After collections are defined, add retention policies.
- **Dependencies**: Requires the collections to be in place.
- **Steps**:
  1. Generate TTL (Time-To-Live) indexes for `content_changes` (1-year expiry).
  2. Add logic for archiving `crawl_sessions` to cold storage (e.g., S3).

#### **7. Add Security Measures**
- **Order**: Final step, after all other components are in place.
- **Dependencies**: Requires the schemas and repositories.
- **Steps**:
  1. Generate encryption-at-rest configuration (WiredTiger encryption).
  2. Add field-level redaction for sensitive data (e.g., `politeness.user_agent`).

#### **8. Additional Recommendations**
- **Order**: Optional, can be generated alongside other components.
- **Steps**:
  1. Generate Redis caching logic for frequently accessed data (e.g., `sites`).
  2. Add backup automation scripts (`mongodump` + S3 storage).
  3. Plan sharding for `pages` by `site_id` (if needed).

---

### **Code Generation Order and Dependencies**
| Step | Component | Dependencies |
|------|-----------|--------------|
| 1    | Collections & Schemas | None |
| 2    | Key Indexes | Collections |
| 3    | Abstraction Layer | Collections, Indexes |
| 4    | Schema Validations | Collections |
| 5    | Error Handling | Collections, Abstraction Layer |
| 6    | Data Retention | Collections |
| 7    | Security | Collections, Abstraction Layer |
| 8    | Additional Recommendations | None |

---

### **Implementation Notes**
1. **Modularity**: Each component (e.g., schemas, repositories) should be generated as a separate module/file for maintainability.
2. **Testing**: After generating each component, include unit tests (e.g., `pytest` for sync, `pytest-asyncio` for async).
3. **Documentation**: Add docstrings and usage examples for each generated class/method.
4. **Iteration**: Use feedback loops to refine generated code (e.g., adjust schemas based on real-world usage).

This plan ensures a logical, dependency-aware approach to generating the **Database Design** section.