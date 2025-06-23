"""
ContentChangesRepository implementation for change detection and monitoring.

This repository handles change type classification, timestamp-based queries,
notification status tracking, and change frequency analytics.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import ValidationError

from .async_mongo_repository import AsyncMongoDBRepository
from .pages_repository import PagesRepository


logger = logging.getLogger(__name__)


class ContentChange:
    """Content change model for tracking modifications."""
    def __init__(self, id: ObjectId = None, page_id: ObjectId = None,
                 change_type: str = None, site_id: ObjectId = None, **kwargs):
        self.id = id
        self.page_id = page_id
        self.change_type = change_type  # new, modified, deleted
        self.site_id = site_id
        self.url = kwargs.get('url')
        self.title = kwargs.get('title')
        self.previous_hash = kwargs.get('previous_hash')
        self.new_hash = kwargs.get('new_hash')
        self.priority = kwargs.get('priority', 'medium')
        self.notification_sent = kwargs.get('notification_sent', False)
        self.detected_at = kwargs.get('detected_at')
        self.notified_at = kwargs.get('notified_at')
        self.context = kwargs.get('context', {})


class ChangeFrequency:
    """Change frequency analytics."""
    def __init__(self, site_id: ObjectId, days_analyzed: int, **kwargs):
        self.site_id = site_id
        self.days_analyzed = days_analyzed
        self.total_changes = kwargs.get('total_changes', 0)
        self.new_pages = kwargs.get('new_pages', 0)
        self.modified_pages = kwargs.get('modified_pages', 0)
        self.deleted_pages = kwargs.get('deleted_pages', 0)
        self.changes_per_day = kwargs.get('changes_per_day', 0.0)
        self.most_active_day = kwargs.get('most_active_day')
        self.trend = kwargs.get('trend', 'stable')  # increasing, decreasing, stable


class ContentChangesRepository(AsyncMongoDBRepository):
    """Repository for change detection and monitoring with notification tracking."""
    
    # Change type classifications
    CHANGE_TYPES = ["new", "modified", "deleted"]
    PRIORITY_LEVELS = ["low", "medium", "high", "critical"]
    
    def __init__(self, connection_string: str, db_name: str, pages_repository: PagesRepository):
        super().__init__(connection_string, db_name, "content_changes")
        self.pages_repository = pages_repository

    @classmethod
    async def create(cls, connection_string: str, db_name: str, pages_repository: PagesRepository):
        """Create and initialize a AlertsRepository instance."""
        instance = cls(connection_string, db_name, pages_repository)
        await instance._setup_indexes()
        return instance
    
    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        indexes = [
            IndexModel([("site_id", ASCENDING), ("detected_at", DESCENDING)]),
            IndexModel([("change_type", ASCENDING), ("priority", ASCENDING), ("detected_at", DESCENDING)]),
            IndexModel([("notification_sent", ASCENDING), ("priority", ASCENDING)]),
            IndexModel([("page_id", ASCENDING), ("detected_at", DESCENDING)]),
            IndexModel([("detected_at", DESCENDING)]),
            IndexModel([("site_id", ASCENDING), ("change_type", ASCENDING), ("detected_at", DESCENDING)])
        ]
        await self.create_indexes(indexes)
    
    def _determine_change_priority(self, change_type: str, context: Dict = None) -> str:
        """Determine priority based on change type and context."""
        context = context or {}
        
        # Priority rules
        if change_type == "deleted":
            return "high"
        elif change_type == "new":
            # Check if it's from a high-value author or contains keywords
            if context.get('author_known', False) or context.get('philosophical_content', False):
                return "high"
            return "medium"
        elif change_type == "modified":
            # Check significance of modifications
            content_change_ratio = context.get('content_change_ratio', 0)
            if content_change_ratio > 0.5:  # Major changes
                return "high"
            elif content_change_ratio > 0.1:  # Minor changes
                return "medium"
            return "low"
        
        return "medium"
    
    async def record_content_change(self, change: ContentChange) -> ObjectId:
        """
        Record a content change event.
        
        Args:
            change: ContentChange object to record
            
        Returns:
            ObjectId of recorded change
            
        Raises:
            ValidationError: If change data is invalid
        """
        try:
            # Validate required fields
            if not change.page_id:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'missing_page_id', # Custom error type
                        'Page ID is required', # Error message template
                    )
            if not change.change_type or change.change_type not in self.CHANGE_TYPES:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'invalid_change_type', # Custom error type
                        'Invalid change type: {change_type}', # Error message template
                        {'change_type': str(change.change_type)} # Context for the message
                    )
            if not change.site_id:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'missing_site_id', # Custom error type
                        'Site ID is required', # Error message template
                    )
            
            # Validate page exists (for new/modified) or existed (for deleted)
            if change.change_type in ["new", "modified"]:
                page = await self.pages_repository.find_one({"_id": change.page_id})
                if not page:
                    from pydantic_core import PydanticCustomError
                    raise PydanticCustomError(
                            'missing_page_id', # Custom error type
                            'Page {page_id} not found', # Error message template
                            {'page_id': str(change.page_id)} # Context for the message
                        )
                
                # Auto-populate fields from page if not provided
                if not change.url:
                    change.url = page.get("url")
                if not change.title:
                    change.title = page.get("title")
            
            # Determine priority if not set
            if not change.priority:
                change.priority = self._determine_change_priority(change.change_type, change.context)
            
            # Create change document
            now = datetime.now(UTC)
            change_data = {
                "page_id": change.page_id,
                "change_type": change.change_type,
                "site_id": change.site_id,
                "url": change.url,
                "title": change.title,
                "previous_hash": change.previous_hash,
                "new_hash": change.new_hash,
                "priority": change.priority,
                "notification_sent": False,
                "detected_at": now,
                "context": change.context
            }
            
            result = await self.insert_one(change_data, validate=True)
            logger.info(f"Recorded {change.change_type} change for page {change.page_id}: {change.url}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to record content change: {e}")
            raise
    
    async def get_changes_since(self, site_id: ObjectId, since: datetime) -> List[ContentChange]:
        """
        Get changes for a site since specific time.
        
        Args:
            site_id: Site identifier
            since: DateTime to filter from
            
        Returns:
            List of changes since specified time
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            query = {
                "site_id": validated_site_id,
                "detected_at": {"$gte": since}
            }
            
            cursor = await self.find_many(
                query,
                sort=[("detected_at", DESCENDING)]
            )
            
            changes = []
            for doc in cursor:
                changes.append(self._document_to_change(doc))
            
            logger.debug(f"Retrieved {len(changes)} changes for site {site_id} since {since}")
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get changes since {since} for site {site_id}: {e}")
            return []
    
    async def get_new_pages_today(self, site_id: ObjectId = None) -> List[ContentChange]:
        """
        Get new pages discovered today.
        
        Args:
            site_id: Optional site filter
            
        Returns:
            List of new page changes today
        """
        try:
            today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
            
            query = {
                "change_type": "new",
                "detected_at": {"$gte": today_start}
            }
            
            if site_id:
                query["site_id"] = self._validate_object_id(site_id)
            
            cursor = await self.find_many(
                query,
                sort=[("detected_at", DESCENDING)]
            )
            
            changes = []
            for doc in cursor:
                changes.append(self._document_to_change(doc))
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get new pages today: {e}")
            return []
    
    async def get_modified_pages_summary(self, days: int = 7) -> Dict[str, int]:
        """
        Get summary of modified pages over specified period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Summary dictionary with change counts by type
        """
        try:
            since = datetime.now(UTC) - timedelta(days=days)
            
            pipeline = [
                {"$match": {"detected_at": {"$gte": since}}},
                {
                    "$group": {
                        "_id": "$change_type",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = await self.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            summary = {
                "new": 0,
                "modified": 0,
                "deleted": 0,
                "total": 0
            }
            
            for result in results:
                change_type = result["_id"]
                count = result["count"]
                
                if change_type in summary:
                    summary[change_type] = count
                summary["total"] += count
            
            logger.debug(f"Generated modified pages summary for {days} days: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get modified pages summary: {e}")
            return {"new": 0, "modified": 0, "deleted": 0, "total": 0}
    
    async def mark_change_notified(self, change_id: ObjectId) -> bool:
        """
        Mark a change as notified.
        
        Args:
            change_id: Change identifier
            
        Returns:
            True if successfully marked
        """
        try:
            validated_change_id = self._validate_object_id(change_id)
            
            update_data = {
                "notification_sent": True,
                "notified_at": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_change_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Marked change {change_id} as notified")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to mark change {change_id} as notified: {e}")
            return False
    
    async def get_unnotified_changes(self, priority: str = None) -> List[ContentChange]:
        """
        Get unnotified changes, optionally filtered by priority.
        
        Args:
            priority: Optional priority filter
            
        Returns:
            List of unnotified changes
        """
        try:
            query = {"notification_sent": False}
            
            if priority:
                if priority not in self.PRIORITY_LEVELS:
                    raise ValidationError(f"Invalid priority: {priority}")
                query["priority"] = priority
            
            cursor = await self.find_many(
                query,
                sort=[
                    ("priority", DESCENDING),  # High priority first
                    ("detected_at", ASCENDING)  # Oldest first
                ],
                limit=1000  # Reasonable limit for notifications
            )
            
            changes = []
            for doc in cursor:
                changes.append(self._document_to_change(doc))
            
            # Sort by actual priority order
            priority_order = {p: i for i, p in enumerate(reversed(self.PRIORITY_LEVELS))}
            changes.sort(key=lambda c: priority_order.get(c.priority, 0), reverse=True)
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to get unnotified changes: {e}")
            return []
    
    async def get_change_frequency(self, site_id: ObjectId, days: int = 30) -> ChangeFrequency:
        """
        Analyze change frequency patterns for a site.
        
        Args:
            site_id: Site identifier
            days: Analysis period in days
            
        Returns:
            ChangeFrequency object with analytics
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            since = datetime.now(UTC) - timedelta(days=days)
            
            # Aggregate changes by type
            type_pipeline = [
                {
                    "$match": {
                        "site_id": validated_site_id,
                        "detected_at": {"$gte": since}
                    }
                },
                {
                    "$group": {
                        "_id": "$change_type",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = await self.aggregate(type_pipeline)
            type_results = await cursor.to_list(length=None)
            
            change_counts = {"new": 0, "modified": 0, "deleted": 0}
            total_changes = 0
            
            for result in type_results:
                change_type = result["_id"]
                count = result["count"]
                if change_type in change_counts:
                    change_counts[change_type] = count
                total_changes += count
            
            # Aggregate by day to find most active day
            daily_pipeline = [
                {
                    "$match": {
                        "site_id": validated_site_id,
                        "detected_at": {"$gte": since}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$detected_at"
                            }
                        },
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 1}
            ]
            
            daily_cursor = await self.aggregate(daily_pipeline)
            daily_results = await daily_cursor.to_list(length=1)
            
            most_active_day = None
            if daily_results:
                most_active_day = daily_results[0]["_id"]
            
            # Calculate metrics
            changes_per_day = total_changes / days if days > 0 else 0
            
            # Determine trend (simplified - compare first half vs second half)
            mid_point = since + timedelta(days=days//2)
            
            first_half_count = await self.collection.count_documents({
                "site_id": validated_site_id,
                "detected_at": {"$gte": since, "$lt": mid_point}
            })
            
            second_half_count = await self.collection.count_documents({
                "site_id": validated_site_id,
                "detected_at": {"$gte": mid_point}
            })
            
            if second_half_count > first_half_count * 1.2:
                trend = "increasing"
            elif second_half_count < first_half_count * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
            
            return ChangeFrequency(
                site_id=validated_site_id,
                days_analyzed=days,
                total_changes=total_changes,
                new_pages=change_counts["new"],
                modified_pages=change_counts["modified"],
                deleted_pages=change_counts["deleted"],
                changes_per_day=changes_per_day,
                most_active_day=most_active_day,
                trend=trend
            )
            
        except Exception as e:
            logger.error(f"Failed to get change frequency for site {site_id}: {e}")
            return ChangeFrequency(site_id, days)
    
    async def cleanup_old_changes(self, days_old: int = 90) -> int:
        """
        Clean up old change records.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of changes cleaned up
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            
            result = await self.delete_many({
                "detected_at": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old content changes")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old changes: {e}")
            return 0
    
    def _document_to_change(self, doc: Dict) -> ContentChange:
        """Convert MongoDB document to ContentChange object."""
        return ContentChange(
            id=doc["_id"],
            page_id=doc.get("page_id"),
            change_type=doc.get("change_type"),
            site_id=doc.get("site_id"),
            url=doc.get("url"),
            title=doc.get("title"),
            previous_hash=doc.get("previous_hash"),
            new_hash=doc.get("new_hash"),
            priority=doc.get("priority", "medium"),
            notification_sent=doc.get("notification_sent", False),
            detected_at=doc.get("detected_at"),
            notified_at=doc.get("notified_at"),
            context=doc.get("context", {})
        )
