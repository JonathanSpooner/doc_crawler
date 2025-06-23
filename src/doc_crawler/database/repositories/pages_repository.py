"""
PagesRepository implementation for content storage and retrieval.

This repository handles URL uniqueness, content deduplication, processing status tracking,
and efficient bulk operations for large-scale content management.
"""

import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, TEXT
from urllib.parse import urlparse

from doc_crawler.database.repositories.async_mongo_repository import AsyncMongoDBRepository
from doc_crawler.database.repositories.sites_repository import SitesRepository
from doc_crawler.database.exceptions import DuplicateResourceError


logger = logging.getLogger(__name__)


class PageStats:
    """Statistics about pages for a site."""
    def __init__(self, total: int, processed: int, unprocessed: int, last_crawled: datetime = None):
        self.total = total
        self.processed = processed
        self.unprocessed = unprocessed
        self.last_crawled = last_crawled


class Page:
    """Page model for database operations."""
    def __init__(self, id: ObjectId = None, site_id: ObjectId = None, url: str = None, 
                 title: str = None, content: str = None, content_hash: str = None,
                 author: str = None, published_date: datetime = None, 
                 processing_status: str = "pending", **kwargs):
        self.id = id
        self.site_id = site_id
        self.url = url
        self.title = title
        self.content = content
        self.content_hash = content_hash
        self.author = author
        self.published_date = published_date
        self.processing_status = processing_status
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')


class PageCreate:
    """Data transfer object for creating pages."""
    def __init__(self, site_id: ObjectId, url: str, title: str = None, content: str = None,
                 author: str = None, published_date: datetime = None):
        self.site_id = site_id
        self.url = url
        self.title = title
        self.content = content
        self.author = author
        self.published_date = published_date


class PagesRepository(AsyncMongoDBRepository):
    """Repository for content storage and retrieval with deduplication and processing tracking."""
    
    def __init__(self, connection_string: str, db_name: str, sites_repository: SitesRepository):
        super().__init__(connection_string, db_name, "pages")
        self.sites_repository = sites_repository

    @classmethod
    async def create(cls, connection_string: str, db_name: str, sites_repository: SitesRepository):
        """Create and initialize a PagesRepository instance."""
        instance = cls(connection_string, db_name, sites_repository)
        await instance._setup_indexes()
        return instance

    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        indexes = [
            IndexModel([("site_id", ASCENDING), ("url", ASCENDING)], unique=True),
            IndexModel([("content_hash", ASCENDING)]),
            IndexModel([("last_modified", ASCENDING)]),
            IndexModel([("processing_status", ASCENDING)]),
            IndexModel([("author", ASCENDING)]),
            IndexModel([("published_date", ASCENDING)]),
            IndexModel([("title", TEXT), ("content", TEXT)]),
            IndexModel([("site_id", ASCENDING), ("processing_status", ASCENDING)])
        ]
        await self.create_indexes(indexes)
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent storage."""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        normalized = normalized.rstrip('/')
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized.rstrip('/')
    
    async def create_page(self, page_data: PageCreate) -> ObjectId:
        """
        Create a new page with content deduplication.
        
        Args:
            page_data: Page creation data
            
        Returns:
            ObjectId of created page
            
        Raises:
            ValidationError: If page data is invalid
            DuplicateResourceError: If URL already exists for site
        """
        try:
            # Validate site exists
            site_config = await self.sites_repository.get_crawl_configuration(page_data.site_id)
            if not site_config:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'site_not_found', # Custom error type
                        'Site {site_id} not found', # Error message template
                        {'site_id': str(page_data.site_id)} # Context for the message
                    )
                       
            # Normalize URL
            normalized_url = self._normalize_url(page_data.url)
            
            # Check for URL uniqueness per site
            existing_page = await self.find_one({
                "site_id": page_data.site_id,
                "url": normalized_url
            })
            if existing_page:
                raise DuplicateResourceError(f"Page with URL {normalized_url} already exists for site")
            
            # Generate content hash for deduplication
            content_hash = None
            if page_data.content:
                content_hash = self._generate_content_hash(page_data.content)
            
            # Create page document
            now = datetime.now(UTC)
            page_doc = {
                "site_id": page_data.site_id,
                "url": normalized_url,
                "title": page_data.title,
                "content": page_data.content,
                "content_hash": content_hash,
                "author": page_data.author,
                "published_date": page_data.published_date,
                "processing_status": "pending",
                "content_length": len(page_data.content) if page_data.content else 0,
                "created_at": now,
                "updated_at": now,
                "last_modified": now
            }
            
            result = await self.insert_one(page_doc, validate=True)
            logger.info(f"Created page {normalized_url} for site {page_data.site_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create page: {e}")
            raise
    
    async def get_page_by_url(self, url: str) -> Optional[Page]:
        """
        Get page by URL.
        
        Args:
            url: Page URL
            
        Returns:
            Page object if found
        """
        try:
            normalized_url = self._normalize_url(url)
            doc = await self.find_one({"url": normalized_url})
            
            if doc:
                return self._document_to_page(doc)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get page by URL {url}: {e}")
            return None
    
    async def update_page_content(self, page_id: ObjectId, content: str, content_hash: str) -> bool:
        """
        Update page content with new hash.
        
        Args:
            page_id: Page identifier
            content: New content
            content_hash: Content hash for deduplication
            
        Returns:
            True if update successful
        """
        try:
            validated_page_id = self._validate_object_id(page_id)
            
            update_data = {
                "content": content,
                "content_hash": content_hash,
                "content_length": len(content),
                "updated_at": datetime.now(UTC),
                "last_modified": datetime.now(UTC),
                "processing_status": "pending"  # Reset processing status
            }
            
            result = await self.update_one(
                {"_id": validated_page_id},
                {"$set": update_data},
                validate=True
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Updated content for page {page_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update page content for {page_id}: {e}")
            return False
    
    async def get_pages_by_site(self, site_id: ObjectId, limit: int = 1000) -> List[Page]:
        """
        Get pages for a specific site with pagination.
        
        Args:
            site_id: Site identifier
            limit: Maximum number of pages to return
            
        Returns:
            List of Page objects
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            cursor = await self.find_many(
                {"site_id": validated_site_id},
                limit=limit,
                sort=[("created_at", ASCENDING)]
            )
            
            pages = []
            for doc in cursor:
                pages.append(self._document_to_page(doc))
                
            logger.debug(f"Retrieved {len(pages)} pages for site {site_id}")
            return pages
            
        except Exception as e:
            logger.error(f"Failed to get pages for site {site_id}: {e}")
            return []
    
    async def get_pages_modified_since(self, site_id: ObjectId, since: datetime) -> List[Page]:
        """
        Get pages modified since a specific time.
        
        Args:
            site_id: Site identifier
            since: DateTime to filter from
            
        Returns:
            List of modified pages
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            query = {
                "site_id": validated_site_id,
                "last_modified": {"$gte": since}
            }
            
            cursor = await self.find_many(
                query,
                sort=[("last_modified", ASCENDING)]
            )
            
            pages = []
            for doc in cursor:
                pages.append(self._document_to_page(doc))
            
            return pages
            
        except Exception as e:
            logger.error(f"Failed to get modified pages for site {site_id}: {e}")
            return []
    
    async def mark_page_processed(self, page_id: ObjectId, processing_info: Dict) -> bool:
        """
        Mark page as processed with processing information.
        
        Args:
            page_id: Page identifier
            processing_info: Processing metadata
            
        Returns:
            True if update successful
        """
        try:
            validated_page_id = self._validate_object_id(page_id)
            
            update_data = {
                "processing_status": "processed",
                "processed_at": datetime.now(UTC),
                "processing_info": processing_info,
                "updated_at": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_page_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to mark page {page_id} as processed: {e}")
            return False
    
    async def get_unprocessed_pages(self, site_id: ObjectId = None) -> List[Page]:
        """
        Get unprocessed pages, optionally filtered by site.
        
        Args:
            site_id: Optional site filter
            
        Returns:
            List of unprocessed pages
        """
        try:
            query = {"processing_status": {"$in": ["pending", "failed"]}}
            if site_id:
                query["site_id"] = self._validate_object_id(site_id)
            
            cursor = await self.find_many(
                query,
                sort=[("created_at", ASCENDING)],
                limit=10000  # Reasonable limit for processing
            )

            pages = []
            for doc in cursor:
                pages.append(self._document_to_page(doc))
            
            return pages
            
        except Exception as e:
            logger.error(f"Failed to get unprocessed pages: {e}")
            return []
    
    async def check_content_exists(self, content_hash: str) -> bool:
        """
        Check if content with hash already exists.
        
        Args:
            content_hash: SHA-256 hash of content
            
        Returns:
            True if content exists
        """
        try:
            doc = await self.find_one({"content_hash": content_hash})
            return doc is not None
            
        except Exception as e:
            logger.error(f"Failed to check content existence: {e}")
            return False
    
    async def get_pages_by_author(self, author_name: str) -> List[Page]:
        """
        Get pages by author name.
        
        Args:
            author_name: Author name to search for
            
        Returns:
            List of pages by author
        """
        try:
            cursor = await self.find_many(
                {"author": {"$regex": author_name, "$options": "i"}},
                sort=[("published_date", ASCENDING)]
            )
            
            pages = []
            for doc in cursor:
                pages.append(self._document_to_page(doc))
            
            return pages
            
        except Exception as e:
            logger.error(f"Failed to get pages by author {author_name}: {e}")
            return []
    
    async def bulk_update_processing_status(self, page_ids: List[ObjectId], status: str) -> int:
        """
        Bulk update processing status for multiple pages.
        
        Args:
            page_ids: List of page identifiers
            status: New processing status
            
        Returns:
            Number of pages updated
        """
        try:
            validated_ids = [self._validate_object_id(pid) for pid in page_ids]
            
            update_data = {
                "processing_status": status,
                "updated_at": datetime.now(UTC)
            }
            
            if status == "processed":
                update_data["processed_at"] = datetime.now(UTC)
            
            result = await self.update_many(
                {"_id": {"$in": validated_ids}},
                {"$set": update_data}
            )
            
            logger.info(f"Bulk updated {result.modified_count} pages to status {status}")
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Failed to bulk update processing status: {e}")
            return 0
    
    async def get_page_statistics(self, site_id: ObjectId) -> PageStats:
        """
        Get statistics about pages for a site.
        
        Args:
            site_id: Site identifier
            
        Returns:
            PageStats object with counts and metadata
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            pipeline = [
                {"$match": {"site_id": validated_site_id}},
                {
                    "$group": {
                        "_id": "$processing_status",
                        "count": {"$sum": 1},
                        "last_modified": {"$max": "$last_modified"}
                    }
                }
            ]
            
            cursor = await self.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            total = 0
            processed = 0
            last_crawled = None
            
            for result in results:
                count = result["count"]
                total += count
                
                if result["_id"] == "processed":
                    processed = count
                
                if result["last_modified"] and (not last_crawled or result["last_modified"] > last_crawled):
                    last_crawled = result["last_modified"]
            
            unprocessed = total - processed
            
            return PageStats(
                total=total,
                processed=processed,
                unprocessed=unprocessed,
                last_crawled=last_crawled
            )
            
        except Exception as e:
            logger.error(f"Failed to get page statistics for site {site_id}: {e}")
            return PageStats(0, 0, 0)
    
    def _document_to_page(self, doc: Dict) -> Page:
        """Convert MongoDB document to Page object."""
        try:
            return Page(
                id=doc["_id"],
                site_id=doc["site_id"],
                url=doc["url"],
                title=doc.get("title"),
                content=doc.get("content"),
                content_hash=doc.get("content_hash"),
                author=doc.get("author"),
                published_date=doc.get("published_date"),
                processing_status=doc.get("processing_status", "pending"),
                created_at=doc.get("created_at"),
                updated_at=doc.get("updated_at")
            )
        except Exception as e:
            print(e)
            logger.error(f"Failed to convert doc to page: {e}")
            raise
