# Scrapy Philosophy Text Crawler - Development Outline

## Project Overview
A long-term philosophical text collection system, respectfully scraping academic philosophy sites with intelligent monitoring, clean text extraction, and modular architecture for multi-environment deployment.

## Phase 1: Foundation & Core Architecture (Weeks 1-2)

### 1.1 Project Structure & Environment Setup
```

text_crawler/
├── scrapy_project/
│   ├── doc_scraper/
│   │   ├── spiders/
│   │   │    ├── iep_spider.py
│   │   │    ├── gutenberg_spider.py
│   │   │    ├── earlymodern_spider.py
│   │   │    ├── classics_spider.py
│   │   │    └── sep_spider.py
│   │   ├── items.py
│   │   ├── pipelines.py
│   │   ├── middlewares.py
│   │   └── settings.py
│   └── scrapy.cfg
├── database/
|   ├── indexes/ 
│   │   ├── [complete] content_changes_indexes.py
│   │   ├── [complete] crawl_sessions_indexes.py
│   │   ├── [complete] page_indexes.py
│   │   └── [complete] processing_queue_indexes.py
│   ├── models/ 
│   │   ├── [complete] alerts.py
│   │   ├── [complete] author_works.py
│   │   ├── [complete] content_changes.py
│   │   ├── [complete] content_index.py
│   │   ├── [complete] crawl_sessions.py
│   │   ├── [complete] historical_dates.py
│   │   ├── [complete] pages.py
│   │   ├── [complete] processing_queue.py
│   │   ├── [complete] site_maps.py
│   │   └── [complete] sites.py
│   ├── repositories/
│   │   ├── [complete] async_mongo_repository.py
│   │   ├── [complete] alerts_repository.py
│   │   ├── [complete] author_works_repository.py
│   │   ├── [complete] content_changes_repository.py
│   │   ├──            content_index_repository.py
│   │   ├── [complete] crawl_sessions_repository.py
│   │   ├── [complete] pages_repository.py
│   │   ├── [complete] processing_queue_repository.py
│   │   ├── [complete] site_maps_repository.py
│   │   └── [complete] sites_repository.py
│   └── migrations/
├── processors/
│   ├── text_cleaner.py
│   ├── pdf_converter.py
│   ├── metadata_extractor.py
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
│   └── All [complete] files have matching `.md` files with signatures 
└── config/
    ├── environments
    │   ├── [complete] base.yaml
    │   ├── [complete] dev.yaml
    │   └── [complete] prod.yaml
    ├── sites
    │   ├── [complete] iep.yaml
    │   ├── gutenberg.yaml
    │   ├── earlymodern.yaml
    │   ├── classics_spider.yaml
    │   └── sep.yaml
    ├── [complete] exceptions.py
    ├── [complete] loader.py
    ├── [complete] manager.py
    ├── [complete] models.py
    └── [complete] validator.py
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

```
### CircuitBreaker(config: CircuitBreakerConfig)
- `config`: Configuration settings for the circuit breaker (thresholds, timeouts).

#### can_execute(self) -> bool
- Returns whether an operation can be executed based on current circuit breaker state.

#### record_success(self)
- Records a successful operation attempt, updating the state as needed.

#### record_failure(self)
- Records a failed operation attempt, updating the state as needed.

### AsyncMongoDBRepository(
    connection_string: str,
    db_name: str,
    collection_name: str,
    max_pool_size: int = 100,
    min_pool_size: int = 10,
    max_idle_time_ms: int = 30000,
    connect_timeout_ms: int = 10000,
    socket_timeout_ms: int = 5000,
    server_selection_timeout_ms: int = 30000,
    retry_writes: bool = True,
    w: Union[int, str] = "majority",
    read_preference: str = "primaryPreferred"
)
- `connection_string`: MongoDB URI used to connect.
- `db_name`: Target database name.
- `collection_name`: Target collection name.
- `max_pool_size`: Maximum connections allowed in pool.
- `min_pool_size`: Minimum number of connections maintained in pool.
- `max_idle_time_ms`: Time (ms) before idle pooled connections are closed.
- `connect_timeout_ms`: Connection timeout (ms).
- `socket_timeout_ms`: Socket timeout (ms).
- `server_selection_timeout_ms`: MongoDB server selection timeout (ms).
- `retry_writes`: Whether to enable retryable writes.
- `w`: Write concern value or string ("majority" etc.).
- `read_preference`: Read preference mode.

#### health_check(self) -> Awaitable[bool]
- Performs a database health check and returns result asynchronously.

#### _sanitize_input(self, data: Dict) -> Dict
- Sanitizes input dictionary by stripping potentially dangerous keys/values recursively.

#### _generate_content_hash(self, content: str) -> str
- Generates SHA256 hash string from provided content string.

#### _convert_object_ids(self, data)
 - Recursively converts ObjectId instances within input to strings for serialization.

#### _validate_object_id(self, obj_id: str) -> ObjectId
 - Validates and converts a string into BSON ObjectId type; raises if invalid.

#### _with_retry(
   self,
   operation: Callable[[], Awaitable[Any]],
   max_retries:int=3, base_delay=float=1.0, max_delay=float=60.0, exponential_base=float=2.0
 ) -> Awaitable[Any]
 - Executes an async operation with retry logic and backoff delay; handles transient DB/network failures.

#### insert_one(self, document: Dict, validate=True) -> Awaitable[str]
 - Inserts one document into collection; returns inserted ID as string; validates if specified.

#### find_one(
     self,
     query : Dict ,
     projection : Optional[Dict] = None 
 ) -> Awaitable[Optional[Dict]]
 - Finds one matching document by query with optional projection fields.

#### find_many(
     self ,
     query : Dict ,
     projection : Optional[Dict]=None , 
     sort : Optional[List[tuple]] = None ,
     limit : Optional[int ]=None , 
     skip : Optional[int ]=None  
 ) -> Awaitable[List [Dict]]
 - Finds multiple documents matching query with optional sort/limit/skip/projection options.

#### update_one(
   self , 
   query : Dict , 
   update_data : Dict , 
   upsert=False , 
   validate=True  
 ) -> Awaitable [bool]
 - Updates first matching document using $set; returns true if changed/upserted.

#### update_many(
      self ,
      query : Dict ,
      update_data : Dict ,
      validate=True      
 ) ->Awaitable [int ]
 - Updates all matching documents using $set; returns count modified.

#### delete_one(
        self ,
        query:req.Dict   
 )->Awaitable [bool ]
 - Deletes first matching document by sanitized query dict; returns true if deleted

#### delete_many (
       self ,
       query:req.Dict   
 )->Awaitable[int ]
 - Deletes all matching documents by sanitized query dict ;returns count deleted 

 #### insert_many (
         self ,    
         documents¨List [Dict ],
         validate¨True     
 )->Await able<List[str]>
 – Inserts multiple docs (list). Returns list of inserted IDs as strings

  
 #### find_paginated (
        self ,name=query:Object,int skip,int limit.,sort=None )
– Finds docs w/pagination .Returns paginated result set+metadata dict.
      

##### aggregate( s elf,pipeline,List(Dict)) → Awaitab le[List(Dict)]//
 – Runs aggregation p ipeline,list,result sa s list(dict)
         

##### transaction(s elf )
 –Context manager for MongoDB session-based transact ion.Yields session
 
   

###### update_page_and_clear_task( sel f,page_id:str,,update_data:D ict task_query:D ic t)->A wait ab le[b o ol]/////
–Performs atomic transactional op:update page & clear proc essing task .Returns success boolean.

##### get_collection_stats( s elf)->Awaita ble[D ict ]
–Fetches basic stats about physical collect ion size/storage/index/doc sizes.

##### close( se lf)
/* Closes client/pool connection */
```

```
# database/models/content_index.py
from datetime import datetime, UTC
from typing import Dict, Optional, Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    BeforeValidator,
    PlainSerializer,
    field_validator,
)

# Helper for ObjectId serialization with strict validation
def validate_object_id(v: str | ObjectId) -> str:
    print(f"Validating: {v}")  # Debugging
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        try:
            ObjectId(v)  # Validate if string is a valid ObjectId
            return v
        except Exception:
            raise ValueError("Invalid ObjectId")
    raise ValueError("Invalid ObjectId: must be str or ObjectId")

PyObjectId = Annotated[
    str,
    BeforeValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
]

class ContentIndex(BaseModel):
    """Defines the schema for the `content_index` collection."""
    id: Optional[PyObjectId] = Field(None, alias="_id", description="Unique identifier for the indexed content.")
    page_id: PyObjectId = Field(..., description="Reference to the `pages` collection.")
    search_content: str = Field(..., description="Processed text for full-text search.")
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Faceted search fields (e.g., author, publication date)."
    )
    indexed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the content was indexed."
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,  # Allow aliasing (e.g., `_id` -> `id`)
    )
```

Implement `content_index_repository.py`