"""
Content Index Repository

Handles database operations for the content_index collection, which stores
search-ready content for OpenSearch integration and faceted search functionality.

This repository provides specialized methods for:
- Content indexing and search preparation
- Metadata management for faceted search
- Efficient querying for search operations
- Integration with the content processing pipeline
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any

from .async_mongo_repository import AsyncMongoDBRepository
from ..models.content_index import ContentIndex


logger = logging.getLogger(__name__)


class ContentIndexRepository(AsyncMongoDBRepository):
    """Repository for managing content index operations."""
    
    def __init__(self, connection_string: str, db_name: str, **kwargs):
        """
        Initialize the ContentIndexRepository.
        
        Args:
            connection_string: MongoDB connection URI
            db_name: Database name
            **kwargs: Additional connection parameters
        """
        super().__init__(
            connection_string=connection_string,
            db_name=db_name,
            collection_name="content_index",
            **kwargs
        )
    
    async def create_content_index(self, content_index: ContentIndex) -> str:
        """
        Create a new content index entry.
        
        Args:
            content_index: ContentIndex model instance
            
        Returns:
            str: The created document ID
            
        Raises:
            ValueError: If validation fails
            Exception: If database operation fails
        """
        try:
            # Convert Pydantic model to dict, excluding None values
            document = content_index.model_dump(exclude_none=True, by_alias=True)
            
            # Ensure indexed_at is set
            if 'indexed_at' not in document:
                document['indexed_at'] = datetime.now(UTC)
            
            # Generate content hash for duplicate detection
            content_hash = self._generate_content_hash(document['search_content'])
            document['content_hash'] = content_hash
            
            result_id = await self.insert_one(document, validate=True)
            logger.info(f"Created content index entry: {result_id}")
            return result_id
            
        except Exception as e:
            logger.error(f"Failed to create content index: {e}")
            raise
    
    async def get_by_page_id(self, page_id: str) -> Optional[Dict]:
        """
        Retrieve content index by page ID.
        
        Args:
            page_id: The page ID to search for
            
        Returns:
            Optional[Dict]: Content index document or None if not found
        """
        try:
            query = {"page_id": page_id}
            result = await self.find_one(query)
            
            if result:
                result = self._convert_object_ids(result)
                logger.debug(f"Found content index for page: {page_id}")
            else:
                logger.debug(f"No content index found for page: {page_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get content index by page_id {page_id}: {e}")
            raise
    
    async def update_content_index(self, page_id: str, update_data: Dict) -> bool:
        """
        Update content index for a specific page.
        
        Args:
            page_id: The page ID to update
            update_data: Dictionary containing fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Add timestamp for the update
            update_data['indexed_at'] = datetime.now(UTC)
            
            # Generate new content hash if search_content is being updated
            if 'search_content' in update_data:
                update_data['content_hash'] = self._generate_content_hash(
                    update_data['search_content']
                )
            
            query = {"page_id": page_id}
            result = await self.update_one(query, update_data, validate=True)
            
            if result:
                logger.info(f"Updated content index for page: {page_id}")
            else:
                logger.warning(f"No content index found to update for page: {page_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update content index for page {page_id}: {e}")
            raise
    
    async def upsert_content_index(self, content_index: ContentIndex) -> str:
        """
        Insert or update content index based on page_id.
        
        Args:
            content_index: ContentIndex model instance
            
        Returns:
            str: The document ID (existing or newly created)
        """
        try:
            # Check if content index already exists for this page
            existing = await self.get_by_page_id(content_index.page_id)
            
            if existing:
                # Update existing record
                update_data = content_index.model_dump(
                    exclude={'id', 'page_id'}, 
                    exclude_none=True
                )
                await self.update_content_index(content_index.page_id, update_data)
                return existing['_id']
            else:
                # Create new record
                return await self.create_content_index(content_index)
                
        except Exception as e:
            logger.error(f"Failed to upsert content index: {e}")
            raise
    
    async def search_content(
        self, 
        search_terms: List[str], 
        metadata_filters: Optional[Dict] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """
        Search content using text search and metadata filters.
        
        Args:
            search_terms: List of terms to search for
            metadata_filters: Optional metadata field filters
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            List[Dict]: List of matching content index documents
        """
        try:
            # Build text search query
            text_query = " ".join(search_terms)
            query = {"$text": {"$search": text_query}}
            
            # Add metadata filters if provided
            if metadata_filters:
                for key, value in metadata_filters.items():
                    query[f"metadata.{key}"] = value
            
            # Execute search with sorting by text score
            sort = [("score", {"$meta": "textScore"})]
            results = await self.find_many(
                query=query,
                sort=sort,
                limit=limit,
                skip=skip
            )
            
            # Convert ObjectIds for serialization
            results = [self._convert_object_ids(doc) for doc in results]
            
            logger.info(f"Content search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search content: {e}")
            raise
    
    async def get_by_author(self, author: str, limit: int = 50) -> List[Dict]:
        """
        Retrieve content index entries by author.
        
        Args:
            author: Author name to search for
            limit: Maximum number of results
            
        Returns:
            List[Dict]: List of content index documents
        """
        try:
            query = {"metadata.author": {"$regex": author, "$options": "i"}}
            results = await self.find_many(
                query=query,
                sort=[("indexed_at", -1)],
                limit=limit
            )
            
            results = [self._convert_object_ids(doc) for doc in results]
            logger.debug(f"Found {len(results)} content entries for author: {author}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get content by author {author}: {e}")
            raise
    
    async def get_recent_content(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        Retrieve recently indexed content.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of results
            
        Returns:
            List[Dict]: List of recently indexed content
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
            
            query = {"indexed_at": {"$gte": cutoff_time}}
            results = await self.find_many(
                query=query,
                sort=[("indexed_at", -1)],
                limit=limit
            )
            
            results = [self._convert_object_ids(doc) for doc in results]
            logger.info(f"Found {len(results)} recently indexed content entries")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get recent content: {e}")
            raise
    
    async def get_metadata_facets(self) -> Dict[str, List[str]]:
        """
        Get available metadata facets for search filtering.
        
        Returns:
            Dict[str, List[str]]: Dictionary of metadata fields and their values
        """
        try:
            pipeline = [
                {"$project": {"metadata": 1}},
                {"$unwind": {"path": "$metadata", "preserveNullAndEmptyArrays": True}},
                {"$group": {
                    "_id": "$metadata.k",
                    "values": {"$addToSet": "$metadata.v"}
                }},
                {"$sort": {"_id": 1}}
            ]
            
            results = await self.aggregate(pipeline)
            
            # Convert to facet dictionary
            facets = {}
            for result in results:
                if result['_id']:  # Skip null keys
                    facets[result['_id']] = sorted(result['values'])
            
            logger.info(f"Retrieved {len(facets)} metadata facets")
            return facets
            
        except Exception as e:
            logger.error(f"Failed to get metadata facets: {e}")
            raise
    
    async def get_content_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about indexed content.
        
        Returns:
            Dict[str, Any]: Statistics about the content index
        """
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_documents": {"$sum": 1},
                        "avg_content_length": {"$avg": {"$strLenCP": "$search_content"}},
                        "total_content_length": {"$sum": {"$strLenCP": "$search_content"}},
                        "unique_authors": {"$addToSet": "$metadata.author"},
                        "earliest_indexed": {"$min": "$indexed_at"},
                        "latest_indexed": {"$max": "$indexed_at"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "total_documents": 1,
                        "avg_content_length": {"$round": ["$avg_content_length", 2]},
                        "total_content_length": 1,
                        "unique_author_count": {"$size": "$unique_authors"},
                        "earliest_indexed": 1,
                        "latest_indexed": 1
                    }
                }
            ]
            
            results = await self.aggregate(pipeline)
            stats = results[0] if results else {}
            
            # Add collection stats
            collection_stats = await self.get_collection_stats()
            stats.update(collection_stats)
            
            logger.info("Retrieved content index statistics")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get content statistics: {e}")
            raise
    
    async def delete_by_page_id(self, page_id: str) -> bool:
        """
        Delete content index entry by page ID.
        
        Args:
            page_id: The page ID to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            query = {"page_id": page_id}
            result = await self.delete_one(query)
            
            if result:
                logger.info(f"Deleted content index for page: {page_id}")
            else:
                logger.warning(f"No content index found to delete for page: {page_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete content index for page {page_id}: {e}")
            raise
    
    async def cleanup_orphaned_entries(self, valid_page_ids: List[str]) -> int:
        """
        Remove content index entries that don't have corresponding pages.
        
        Args:
            valid_page_ids: List of valid page IDs to keep
            
        Returns:
            int: Number of orphaned entries removed
        """
        try:
            query = {"page_id": {"$nin": valid_page_ids}}
            deleted_count = await self.delete_many(query)
            
            logger.info(f"Cleaned up {deleted_count} orphaned content index entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup orphaned entries: {e}")
            raise
    
    async def get_duplicate_content(self, content_hash: str) -> List[Dict]:
        """
        Find content entries with the same content hash (potential duplicates).
        
        Args:
            content_hash: Content hash to search for
            
        Returns:
            List[Dict]: List of documents with matching content hash
        """
        try:
            query = {"content_hash": content_hash}
            results = await self.find_many(query)
            
            results = [self._convert_object_ids(doc) for doc in results]
            logger.debug(f"Found {len(results)} entries with content hash: {content_hash}")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get duplicate content: {e}")
            raise
    
    async def update_search_content(self, page_id: str, search_content: str) -> bool:
        """
        Update only the search content for a specific page.
        
        Args:
            page_id: The page ID to update
            search_content: New search content
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            update_data = {
                'search_content': search_content,
                'content_hash': self._generate_content_hash(search_content),
                'indexed_at': datetime.now(UTC)
            }
            
            return await self.update_content_index(page_id, update_data)
            
        except Exception as e:
            logger.error(f"Failed to update search content for page {page_id}: {e}")
            raise
    
    async def bulk_upsert_content_indexes(self, content_indexes: List[ContentIndex]) -> List[str]:
        """
        Bulk upsert multiple content index entries efficiently.
        
        Args:
            content_indexes: List of ContentIndex model instances
            
        Returns:
            List[str]: List of document IDs (existing or newly created)
        """
        try:
            result_ids = []
            
            # Process in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(content_indexes), batch_size):
                batch = content_indexes[i:i + batch_size]
                
                for content_index in batch:
                    doc_id = await self.upsert_content_index(content_index)
                    result_ids.append(doc_id)
            
            logger.info(f"Bulk upserted {len(result_ids)} content index entries")
            return result_ids
            
        except Exception as e:
            logger.error(f"Failed to bulk upsert content indexes: {e}")
            raise