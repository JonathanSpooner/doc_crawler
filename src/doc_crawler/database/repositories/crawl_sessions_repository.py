"""
CrawlSessionsRepository implementation for execution tracking and analytics.

This repository manages crawl session lifecycle, progress tracking, concurrent session
limiting, and performance metrics collection.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import ValidationError

from doc_crawler.database.repositories.async_mongo_repository import AsyncMongoDBRepository
from doc_crawler.database.repositories.sites_repository import SitesRepository
from doc_crawler.database.exceptions import ResourceNotFoundError


logger = logging.getLogger(__name__)


class CrawlStats:
    """Statistics for crawl session tracking."""
    def __init__(self, pages_discovered: int = 0, pages_crawled: int = 0, 
                 pages_failed: int = 0, bytes_downloaded: int = 0,
                 errors_count: int = 0, **kwargs):
        self.pages_discovered = pages_discovered
        self.pages_crawled = pages_crawled
        self.pages_failed = pages_failed
        self.bytes_downloaded = bytes_downloaded
        self.errors_count = errors_count
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.duration_seconds = kwargs.get('duration_seconds', 0)


class CrawlSession:
    """Crawl session model for database operations."""
    def __init__(self, id: ObjectId = None, site_id: ObjectId = None, 
                 status: str = "running", config: Dict = None, 
                 stats: CrawlStats = None, **kwargs):
        self.id = id
        self.site_id = site_id
        self.status = status
        self.config = config or {}
        self.stats = stats or CrawlStats()
        self.started_at = kwargs.get('started_at')
        self.completed_at = kwargs.get('completed_at')
        self.error_message = kwargs.get('error_message')


class CrawlSessionsRepository(AsyncMongoDBRepository):
    """Repository for crawl session execution tracking and analytics."""
    
    def __init__(self, connection_string: str, db_name: str, sites_repository: SitesRepository):
        super().__init__(connection_string, db_name, "crawl_sessions")
        self.sites_repository = sites_repository

    @classmethod
    async def create(cls, connection_string: str, db_name: str, sites_repository: SitesRepository):
        """Create and initialize a CrawlSessionRepository instance."""
        instance = cls(connection_string, db_name, sites_repository)
        await instance._setup_indexes()
        return instance
    
    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        indexes = [
            IndexModel([("site_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("started_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("started_at", DESCENDING)]),
            IndexModel([("site_id", ASCENDING), ("started_at", DESCENDING)]),
            IndexModel([("completed_at", DESCENDING)])
        ]
        await self.create_indexes(indexes)
    
    async def start_crawl_session(self, site_id: ObjectId, config: Dict) -> ObjectId:
        """
        Start a new crawl session.
        
        Args:
            site_id: Site identifier
            config: Crawl configuration
            
        Returns:
            ObjectId of created session
            
        Raises:
            ValidationError: If site not found or invalid config
        """
        try:
            # Validate site exists
            site_config = await self.sites_repository.get_crawl_configuration(site_id)
            if not site_config:
                raise ValidationError(f"Site {site_id} not found")
            
            # Check concurrent session limits
            concurrent_count = await self.get_concurrent_session_count(site_id)
            max_concurrent = config.get('max_concurrent_sessions', 1)
            
            if concurrent_count >= max_concurrent:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'max_concurrent_sessions', # Custom error type
                        'Maximum concurrent sessions ({max_concurrent}) reached for site', # Error message template
                        {'max_concurrent': max_concurrent } # Context for the message
                    )
            
            # Create session document
            now = datetime.now(UTC)
            session_data = {
                "site_id": site_id,
                "status": "running",
                "config": config,
                "stats": {
                    "pages_discovered": 0,
                    "pages_crawled": 0,
                    "pages_failed": 0,
                    "bytes_downloaded": 0,
                    "errors_count": 0,
                    "start_time": now
                },
                "started_at": now,
                "last_update": now,
                "worker_id": config.get('worker_id'),
                "user_agent": config.get('user_agent', 'PhilosophyCrawler/1.0')
            }
            
            result = await self.insert_one(session_data, validate=True)
            logger.info(f"Started crawl session {result} for site {site_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to start crawl session: {e}")
            raise
    
    async def update_session_progress(self, session_id: ObjectId, stats: CrawlStats) -> bool:
        """
        Update session progress with real-time statistics.
        
        Args:
            session_id: Session identifier
            stats: Updated statistics
            
        Returns:
            True if update successful
        """
        try:
            validated_session_id = self._validate_object_id(session_id)
            
            # Verify session is still running
            session = await self.find_one({"_id": validated_session_id})
            if not session or session.get("status") != "running":
                logger.warning(f"Attempted to update non-running session {session_id}")
                return False
            
            update_data = {
                "stats.pages_discovered": stats.pages_discovered,
                "stats.pages_crawled": stats.pages_crawled,
                "stats.pages_failed": stats.pages_failed,
                "stats.bytes_downloaded": stats.bytes_downloaded,
                "stats.errors_count": stats.errors_count,
                "last_update": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_session_id, "status": "running"},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Updated progress for session {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update session progress {session_id}: {e}")
            return False
    
    async def complete_crawl_session(self, session_id: ObjectId, final_stats: CrawlStats) -> bool:
        """
        Complete a crawl session with final statistics.
        
        Args:
            session_id: Session identifier
            final_stats: Final session statistics
            
        Returns:
            True if completion successful
        """
        try:
            validated_session_id = self._validate_object_id(session_id)
            
            # Get session start time for duration calculation
            session = await self.find_one({"_id": validated_session_id})
            if not session:
                raise ResourceNotFoundError(f"Session {session_id} not found")
            
            now = datetime.now(UTC)
            duration = (now - session["started_at"]).total_seconds()
            
            update_data = {
                "status": "completed",
                "completed_at": now,
                "stats": {
                    "pages_discovered": final_stats.pages_discovered,
                    "pages_crawled": final_stats.pages_crawled,
                    "pages_failed": final_stats.pages_failed,
                    "bytes_downloaded": final_stats.bytes_downloaded,
                    "errors_count": final_stats.errors_count,
                    "start_time": session["started_at"],
                    "end_time": now,
                    "duration_seconds": duration
                },
                "last_update": now
            }
            
            result = await self.update_one(
                {"_id": validated_session_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Completed crawl session {session_id} in {duration:.2f} seconds")
                
                # Update site's last crawl time
                await self.sites_repository.update_one(
                    {"_id": session["site_id"]},
                    {"$set": {"monitoring.last_crawl_time": now}}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to complete session {session_id}: {e}")
            return False
    
    async def get_active_sessions(self) -> List[CrawlSession]:
        """
        Get all currently active crawl sessions.
        
        Returns:
            List of active sessions
        """
        try:
            cursor = await self.find_many(
                {"status": "running"},
                sort=[("started_at", DESCENDING)]
            )
            
            sessions = []
            for doc in cursor:
                sessions.append(self._document_to_session(doc))
            
            logger.debug(f"Retrieved {len(sessions)} active sessions")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    async def get_session_history(self, site_id: ObjectId, limit: int = 50) -> List[CrawlSession]:
        """
        Get session history for a site.
        
        Args:
            site_id: Site identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of historical sessions
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            cursor = await self.find_many(
                {"site_id": validated_site_id},
                sort=[("started_at", DESCENDING)],
                limit=limit
            )
            
            sessions = []
            for doc in cursor:
                sessions.append(self._document_to_session(doc))
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get session history for site {site_id}: {e}")
            return []
    
    async def get_session_statistics(self, session_id: ObjectId) -> Optional[CrawlStats]:
        """
        Get statistics for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            CrawlStats object or None if not found
        """
        try:
            validated_session_id = self._validate_object_id(session_id)
            
            doc = await self.find_one({"_id": validated_session_id})
            if not doc:
                return None
            
            stats_data = doc.get("stats", {})
            return CrawlStats(
                pages_discovered=stats_data.get("pages_discovered", 0),
                pages_crawled=stats_data.get("pages_crawled", 0),
                pages_failed=stats_data.get("pages_failed", 0),
                bytes_downloaded=stats_data.get("bytes_downloaded", 0),
                errors_count=stats_data.get("errors_count", 0),
                start_time=stats_data.get("start_time"),
                end_time=stats_data.get("end_time"),
                duration_seconds=stats_data.get("duration_seconds", 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get session statistics {session_id}: {e}")
            return None
    
    async def abort_session(self, session_id: ObjectId, reason: str) -> bool:
        """
        Abort a running crawl session.
        
        Args:
            session_id: Session identifier
            reason: Reason for aborting
            
        Returns:
            True if abort successful
        """
        try:
            validated_session_id = self._validate_object_id(session_id)
            
            update_data = {
                "status": "aborted",
                "completed_at": datetime.now(UTC),
                "abort_reason": reason,
                "last_update": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_session_id, "status": "running"},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Aborted session {session_id}: {reason}")
            else:
                logger.warning(f"Failed to abort session {session_id} - may not be running")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to abort session {session_id}: {e}")
            return False
    
    async def get_concurrent_session_count(self, site_id: ObjectId) -> int:
        """
        Get count of concurrent sessions for a site.
        
        Args:
            site_id: Site identifier
            
        Returns:
            Number of running sessions
        """
        try:
            validated_site_id = self._validate_object_id(site_id)
            
            count = await self.collection.count_documents({
                "site_id": validated_site_id,
                "status": "running"
            })
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to get concurrent session count for site {site_id}: {e}")
            return 0
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old completed/aborted sessions.
        
        Args:
            days_old: Age threshold in days
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
            
            result = await self.delete_many({
                "status": {"$in": ["completed", "aborted", "failed"]},
                "completed_at": {"$lt": cutoff_date}
            })
            
            deleted_count = result.deleted_count
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0
    
    def _document_to_session(self, doc: Dict) -> CrawlSession:
        """Convert MongoDB document to CrawlSession object."""
        stats_data = doc.get("stats", {})
        stats = CrawlStats(
            pages_discovered=stats_data.get("pages_discovered", 0),
            pages_crawled=stats_data.get("pages_crawled", 0),
            pages_failed=stats_data.get("pages_failed", 0),
            bytes_downloaded=stats_data.get("bytes_downloaded", 0),
            errors_count=stats_data.get("errors_count", 0),
            start_time=stats_data.get("start_time"),
            end_time=stats_data.get("end_time"),
            duration_seconds=stats_data.get("duration_seconds", 0)
        )
        
        return CrawlSession(
            id=doc["_id"],
            site_id=doc["site_id"],
            status=doc.get("status", "unknown"),
            config=doc.get("config", {}),
            stats=stats,
            started_at=doc.get("started_at"),
            completed_at=doc.get("completed_at"),
            error_message=doc.get("error_message")
        )
