"""
Author Works Repository

Repository for managing philosophical works with author metadata, deduplication,
and domain-specific query operations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import logging
from bson import ObjectId

from .async_mongo_repository import AsyncMongoDBRepository
from ..models.author_works import AuthorWork


logger = logging.getLogger(__name__)


class AuthorWorksRepository(AsyncMongoDBRepository):
    """Repository for managing author works with philosophical text metadata."""
    
    def __init__(self, connection_string: str, db_name: str, **kwargs):
        """Initialize the Author Works repository.
        
        Args:
            connection_string: MongoDB connection URI
            db_name: Database name
            **kwargs: Additional MongoDB connection parameters
        """
        super().__init__(
            connection_string=connection_string,
            db_name=db_name,
            collection_name="author_works",
            **kwargs
        )
    
    async def create_work(self, work_data: Dict) -> str:
        """Create a new author work with validation.
        
        Args:
            work_data: Dictionary containing work information
            
        Returns:
            String ID of the created work
            
        Raises:
            ValidationError: If work data is invalid
            DuplicateError: If work already exists (based on work_id)
        """
        try:
            # Validate using Pydantic model
            work = AuthorWork(**work_data)
            work_dict = work.model_dump(exclude={'id'})
            
            # Check for existing work by work_id if provided
            if work.work_id:
                existing = await self.find_by_work_id(work.work_id)
                if existing:
                    raise ValueError(f"Work with work_id '{work.work_id}' already exists")
            
            # Check for potential duplicate by author + title
            duplicate = await self.find_duplicate_work(
                work.author_name, 
                work.work_title, 
                work.site_id
            )
            if duplicate:
                logger.warning(f"Potential duplicate work found: {work.author_name} - {work.work_title}")
            
            work_id = await self.insert_one(work_dict)
            logger.info(f"Created work: {work.author_name} - {work.work_title} (ID: {work_id})")
            return work_id
            
        except Exception as e:
            logger.error(f"Failed to create work: {e}")
            raise
    
    async def find_by_work_id(self, work_id: str) -> Optional[Dict]:
        """Find a work by its external work ID (DOI, ISBN, etc.).
        
        Args:
            work_id: External identifier for the work
            
        Returns:
            Work document or None if not found
        """
        return await self.find_one({"work_id": work_id})
    
    async def find_by_author(self, author_name: str, limit: int = 100) -> List[Dict]:
        """Find all works by a specific author.
        
        Args:
            author_name: Name of the author (case-insensitive)
            limit: Maximum number of results to return
            
        Returns:
            List of work documents
        """
        query = {"author_name": {"$regex": f"^{author_name}$", "$options": "i"}}
        return await self.find_many(
            query=query,
            sort=[("work_title", 1)],
            limit=limit
        )
    
    async def find_by_site(self, site_id: str, limit: int = 1000) -> List[Dict]:
        """Find all works from a specific site.
        
        Args:
            site_id: Site identifier
            limit: Maximum number of results to return
            
        Returns:
            List of work documents
        """
        query = {"site_id": self._validate_object_id(site_id)}
        return await self.find_many(
            query=query,
            sort=[("author_name", 1), ("work_title", 1)],
            limit=limit
        )
    
    async def find_by_tags(self, tags: List[str], match_all: bool = False, limit: int = 100) -> List[Dict]:
        """Find works by tags.
        
        Args:
            tags: List of tags to search for
            match_all: If True, work must have all tags; if False, any tag matches
            limit: Maximum number of results to return
            
        Returns:
            List of work documents
        """
        if match_all:
            query = {"tags": {"$all": tags}}
        else:
            query = {"tags": {"$in": tags}}
        
        return await self.find_many(
            query=query,
            sort=[("author_name", 1), ("work_title", 1)],
            limit=limit
        )
    
    async def find_duplicate_work(self, author_name: str, work_title: str, site_id: str) -> Optional[Dict]:
        """Find potential duplicate work by author and title.
        
        Args:
            author_name: Author name
            work_title: Work title
            site_id: Site ID to check within
            
        Returns:
            Existing work document or None
        """
        query = {
            "author_name": {"$regex": f"^{author_name}$", "$options": "i"},
            "work_title": {"$regex": f"^{work_title}$", "$options": "i"},
            "site_id": self._validate_object_id(site_id)
        }
        return await self.find_one(query)
    
    async def find_works_by_date_range(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Find works by publication date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)
            limit: Maximum number of results to return
            
        Returns:
            List of work documents
        """
        query = {}
        date_filter = {}
        
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
            
        if date_filter:
            query["publication_date"] = date_filter
        
        return await self.find_many(
            query=query,
            sort=[("publication_date", 1), ("author_name", 1)],
            limit=limit
        )
    
    async def update_work(self, work_id: str, update_data: Dict) -> bool:
        """Update an existing work.
        
        Args:
            work_id: ID of the work to update
            update_data: Dictionary of fields to update
            
        Returns:
            True if work was updated, False otherwise
        """
        # Add updated timestamp
        update_data["updated_at"] = datetime.now(UTC)
        
        # Validate the update data by creating a partial model
        try:
            # Create a minimal valid work for validation
            temp_work_data = {
                "author_name": "temp",
                "work_title": "temp",
                "site_id": ObjectId(),
                "page_id": ObjectId(),
                **update_data
            }
            AuthorWork(**temp_work_data)  # This will raise if invalid
        except Exception as e:
            logger.error(f"Invalid update data: {e}")
            raise ValueError(f"Invalid update data: {e}")
        
        query = {"_id": self._validate_object_id(work_id)}
        return await self.update_one(query, update_data)
    
    async def add_tags_to_work(self, work_id: str, tags: List[str]) -> bool:
        """Add tags to an existing work.
        
        Args:
            work_id: ID of the work
            tags: List of tags to add
            
        Returns:
            True if work was updated, False otherwise
        """
        query = {"_id": self._validate_object_id(work_id)}
        update = {
            "$addToSet": {"tags": {"$each": tags}},
            "$set": {"updated_at": datetime.now(UTC)}
        }
        
        result = await self.collection.update_one(query, update)
        return result.modified_count > 0
    
    async def remove_tags_from_work(self, work_id: str, tags: List[str]) -> bool:
        """Remove tags from an existing work.
        
        Args:
            work_id: ID of the work
            tags: List of tags to remove
            
        Returns:
            True if work was updated, False otherwise
        """
        query = {"_id": self._validate_object_id(work_id)}
        update = {
            "$pullAll": {"tags": tags},
            "$set": {"updated_at": datetime.now(UTC)}
        }
        
        result = await self.collection.update_one(query, update)
        return result.modified_count > 0
    
    async def get_authors_list(self, limit: int = 1000) -> List[str]:
        """Get a list of all unique authors.
        
        Args:
            limit: Maximum number of authors to return
            
        Returns:
            List of unique author names
        """
        pipeline = [
            {"$group": {"_id": "$author_name"}},
            {"$sort": {"_id": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "author": "$_id"}}
        ]
        
        results = await self.aggregate(pipeline)
        return [result["author"] for result in results]
    
    async def get_author_statistics(self) -> Dict[str, Any]:
        """Get statistics about authors and their works.
        
        Returns:
            Dictionary containing author statistics
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$author_name",
                    "work_count": {"$sum": 1},
                    "sites": {"$addToSet": "$site_id"},
                    "earliest_work": {"$min": "$publication_date"},
                    "latest_work": {"$max": "$publication_date"}
                }
            },
            {
                "$project": {
                    "author": "$_id",
                    "work_count": 1,
                    "site_count": {"$size": "$sites"},
                    "earliest_work": 1,
                    "latest_work": 1,
                    "_id": 0
                }
            },
            {"$sort": {"work_count": -1}}
        ]
        
        results = await self.aggregate(pipeline)
        
        total_authors = len(results)
        total_works = sum(author["work_count"] for author in results)
        avg_works_per_author = total_works / total_authors if total_authors > 0 else 0
        
        return {
            "total_authors": total_authors,
            "total_works": total_works,
            "average_works_per_author": round(avg_works_per_author, 2),
            "top_authors": results[:10],  # Top 10 most prolific authors
            "authors_by_work_count": results
        }
    
    async def get_site_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics about works per site.
        
        Returns:
            List of site statistics
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$site_id",
                    "work_count": {"$sum": 1},
                    "unique_authors": {"$addToSet": "$author_name"},
                    "latest_addition": {"$max": "$created_at"}
                }
            },
            {
                "$project": {
                    "site_id": "$_id",
                    "work_count": 1,
                    "author_count": {"$size": "$unique_authors"},
                    "latest_addition": 1,
                    "_id": 0
                }
            },
            {"$sort": {"work_count": -1}}
        ]
        
        return await self.aggregate(pipeline)
    
    async def find_works_needing_work_id(self, limit: int = 100) -> List[Dict]:
        """Find works that don't have an external work_id assigned.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of works without work_id
        """
        query = {
            "$or": [
                {"work_id": None},
                {"work_id": {"$exists": False}},
                {"work_id": ""}
            ]
        }
        
        return await self.find_many(
            query=query,
            sort=[("created_at", 1)],  # Oldest first
            limit=limit
        )
    
    async def search_works(
        self, 
        search_term: str, 
        fields: List[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search for works across multiple fields.
        
        Args:
            search_term: Text to search for
            fields: List of fields to search in (default: author_name, work_title)
            limit: Maximum number of results to return
            
        Returns:
            List of matching works
        """
        if fields is None:
            fields = ["author_name", "work_title"]
        
        # Create regex pattern for case-insensitive search
        pattern = {"$regex": search_term, "$options": "i"}
        
        # Build OR query across specified fields
        or_conditions = [{field: pattern} for field in fields]
        query = {"$or": or_conditions}
        
        return await self.find_many(
            query=query,
            sort=[("author_name", 1), ("work_title", 1)],
            limit=limit
        )
    
    async def get_works_by_page_ids(self, page_ids: List[str]) -> List[Dict]:
        """Get all works associated with specific page IDs.
        
        Args:
            page_ids: List of page ID strings
            
        Returns:
            List of works associated with the pages
        """
        object_ids = [self._validate_object_id(pid) for pid in page_ids]
        query = {"page_id": {"$in": object_ids}}
        
        return await self.find_many(
            query=query,
            sort=[("author_name", 1), ("work_title", 1)]
        )
    
    async def delete_works_by_site(self, site_id: str) -> int:
        """Delete all works from a specific site.
        
        Args:
            site_id: Site identifier
            
        Returns:
            Number of works deleted
        """
        query = {"site_id": self._validate_object_id(site_id)}
        count = await self.delete_many(query)
        
        if count > 0:
            logger.info(f"Deleted {count} works from site {site_id}")
        
        return count
    
    async def bulk_update_tags(self, work_ids: List[str], tags_to_add: List[str] = None, tags_to_remove: List[str] = None) -> int:
        """Bulk update tags for multiple works.
        
        Args:
            work_ids: List of work IDs to update
            tags_to_add: Tags to add to all specified works
            tags_to_remove: Tags to remove from all specified works
            
        Returns:
            Number of works updated
        """
        if not tags_to_add and not tags_to_remove:
            return 0
        
        object_ids = [self._validate_object_id(wid) for wid in work_ids]
        query = {"_id": {"$in": object_ids}}
        
        update_ops = {"$set": {"updated_at": datetime.now(UTC)}}
        
        if tags_to_add:
            update_ops["$addToSet"] = {"tags": {"$each": tags_to_add}}
        
        if tags_to_remove:
            update_ops["$pullAll"] = {"tags": tags_to_remove}
        
        result = await self.collection.update_many(query, update_ops)
        return result.modified_count