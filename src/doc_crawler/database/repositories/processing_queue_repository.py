"""
ProcessingQueueRepository implementation for asynchronous task management.

This repository handles priority-based task queuing, worker assignment, retry mechanisms,
and processing status monitoring for the content processing pipeline.
"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
import json
from pydantic import ValidationError

from .async_mongo_repository import AsyncMongoDBRepository
from .pages_repository import PagesRepository
from ..exceptions import ResourceNotFoundError


logger = logging.getLogger(__name__)


class ProcessingTask:
    """Processing task model for queue management."""
    def __init__(self, id: ObjectId = None, task_type: str = None, 
                 priority: int = 5, payload: Dict = None, 
                 status: str = "pending", **kwargs):
        self.id = id
        self.task_type = task_type
        self.priority = priority
        self.payload = payload or {}
        self.status = status
        self.created_at = kwargs.get('created_at')
        self.scheduled_at = kwargs.get('scheduled_at')
        self.started_at = kwargs.get('started_at')
        self.completed_at = kwargs.get('completed_at')
        self.worker_id = kwargs.get('worker_id')
        self.error_message = kwargs.get('error_message')
        self.retry_count = kwargs.get('retry_count', 0)
        self.max_retries = kwargs.get('max_retries', 3)


class QueueStats:
    """Queue statistics for monitoring."""
    def __init__(self, pending: int = 0, processing: int = 0, completed: int = 0,
                 failed: int = 0, total: int = 0, **kwargs):
        self.pending = pending
        self.processing = processing
        self.completed = completed
        self.failed = failed
        self.total = total
        self.oldest_pending = kwargs.get('oldest_pending')
        self.average_processing_time = kwargs.get('average_processing_time', 0)


class ProcessingQueueRepository(AsyncMongoDBRepository):
    """Repository for asynchronous task management with priority queuing and retry logic."""
    
    def __init__(self, connection_string: str, db_name: str, pages_repository: PagesRepository):
        super().__init__(connection_string, db_name, "processing_queue")
        self.pages_repository = pages_repository

    @classmethod
    async def create(cls, connection_string: str, db_name: str, pages_repository: PagesRepository):
        """Create and initialize a ProcessingQueueRepository instance."""
        instance = cls(connection_string, db_name, pages_repository)
        await instance._setup_indexes()
        return instance
    
    async def _setup_indexes(self):
        """Set up collection indexes for optimal performance."""
        indexes = [
            IndexModel([("status", ASCENDING), ("priority", DESCENDING), ("created_at", ASCENDING)]),
            IndexModel([("task_type", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("worker_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("scheduled_at", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("completed_at", DESCENDING)]),
            IndexModel([("retry_count", ASCENDING), ("status", ASCENDING)])
        ]
        await self.create_indexes(indexes)
    
    def _calculate_next_retry_delay(self, retry_count: int, base_delay: int = 60) -> timedelta:
        """Calculate exponential backoff delay for retries."""
        # Exponential backoff: base_delay * (2 ^ retry_count)
        delay_seconds = base_delay * (2 ** retry_count)
        # Cap at 1 hour
        delay_seconds = min(delay_seconds, 3600)
        return timedelta(seconds=delay_seconds)
    
    async def enqueue_task(self, task: ProcessingTask) -> ObjectId:
        """
        Enqueue a new processing task.
        
        Args:
            task: Processing task to enqueue
            
        Returns:
            ObjectId of enqueued task
            
        Raises:
            ValidationError: If task data is invalid
        """
        try:
            # Validate task data
            if not task.task_type:
                from pydantic_core import PydanticCustomError
                raise PydanticCustomError(
                        'missing_task_type', # Custom error type
                        'Task type is required', # Error message template
                    )
            
            # Validate payload if present
            if task.payload:
                try:
                    json.dumps(task.payload)  # Ensure JSON serializable
                except (TypeError, ValueError) as e:
                    raise ValidationError(f"Task payload must be JSON serializable: {e}")
            
            # Create task document
            now = datetime.now(UTC)
            task_data = {
                "task_type": task.task_type,
                "priority": task.priority,
                "payload": task.payload,
                "status": "pending",
                "created_at": now,
                "scheduled_at": task.scheduled_at or now,
                "retry_count": 0,
                "max_retries": task.max_retries
            }
            
            result = await self.insert_one(task_data, validate=True)
            logger.info(f"Enqueued task {task.task_type} with ID {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            raise
    
    async def dequeue_next_task(self, task_type: str = None) -> Optional[ProcessingTask]:
        """
        Dequeue the next available task for processing.
        
        Args:
            task_type: Optional filter by task type
            
        Returns:
            Next available task or None
        """
        try:
            now = datetime.now(UTC)
            
            # Build query for available tasks
            query = {
                "status": "pending",
                "scheduled_at": {"$lte": now}
            }
            
            if task_type:
                query["task_type"] = task_type
            
            # Find and update in atomic operation
            update_data = {
                "status": "processing",
                "started_at": now,
                "last_update": now
            }
            
            # Sort by priority (higher first) then creation time
            sort = [("priority", DESCENDING), ("created_at", ASCENDING)]
            
            doc = await self.collection.find_one_and_update(
                query,
                {"$set": update_data},
                sort=sort,
                return_document=True
            )
            
            if doc:
                task = self._document_to_task(doc)
                logger.debug(f"Dequeued task {task.id} of type {task.task_type}")
                return task
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None
    
    async def mark_task_processing(self, task_id: ObjectId, worker_id: str) -> bool:
        """
        Mark task as being processed by a specific worker.
        
        Args:
            task_id: Task identifier
            worker_id: Worker identifier
            
        Returns:
            True if successfully marked
        """
        try:
            validated_task_id = self._validate_object_id(task_id)
            
            update_data = {
                "worker_id": worker_id,
                "last_update": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_task_id, "status": "processing"},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Marked task {task_id} as processing by worker {worker_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to mark task {task_id} as processing: {e}")
            return False
    
    async def complete_task(self, task_id: ObjectId, result: Dict) -> bool:
        """
        Mark task as completed with result.
        
        Args:
            task_id: Task identifier
            result: Task execution result
            
        Returns:
            True if successfully completed
        """
        try:
            validated_task_id = self._validate_object_id(task_id)
            
            # Validate result is serializable
            try:
                json.dumps(result)
            except (TypeError, ValueError) as e:
                logger.warning(f"Task result not JSON serializable, storing simplified version: {e}")
                result = {"status": "completed", "error": "Result not serializable"}
            
            update_data = {
                "status": "completed",
                "completed_at": datetime.now(UTC),
                "result": result,
                "last_update": datetime.now(UTC)
            }
            
            result = await self.update_one(
                {"_id": validated_task_id, "status": "processing"},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.debug(f"Completed task {task_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    async def fail_task(self, task_id: ObjectId, error: str, retry: bool = True) -> bool:
        """
        Mark task as failed and optionally schedule retry.
        
        Args:
            task_id: Task identifier
            error: Error message
            retry: Whether to schedule retry
            
        Returns:
            True if successfully updated
        """
        try:
            validated_task_id = self._validate_object_id(task_id)
            
            # Get current task to check retry count
            task_doc = await self.find_one({"_id": validated_task_id})
            if not task_doc:
                logger.error(f"Task {task_id} not found for failure handling")
                return False
            
            retry_count = task_doc.get("retry_count", 0)
            max_retries = task_doc.get("max_retries", 3)
            
            now = datetime.now(UTC)
            update_data = {
                "error_message": error,
                "last_update": now,
                "retry_count": retry_count + 1
            }
            
            # Determine if we should retry
            should_retry = retry and (retry_count < max_retries)
            
            if should_retry:
                # Schedule retry with exponential backoff
                retry_delay = self._calculate_next_retry_delay(retry_count)
                update_data.update({
                    "status": "pending",
                    "scheduled_at": now + retry_delay,
                    "worker_id": None,
                    "started_at": None
                })
                logger.info(f"Scheduled retry for task {task_id} in {retry_delay}")
            else:
                # Mark as permanently failed
                update_data.update({
                    "status": "failed",
                    "failed_at": now
                })
                logger.warning(f"Task {task_id} permanently failed after {retry_count} retries: {error}")
            
            result = await self.update_one(
                {"_id": validated_task_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to handle task failure {task_id}: {e}")
            return False
    
    async def get_queue_status(self) -> QueueStats:
        """
        Get comprehensive queue statistics.
        
        Returns:
            QueueStats object with current queue metrics
        """
        try:
            # Aggregate stats by status
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "oldest": {"$min": "$created_at"}
                    }
                }
            ]
            
            cursor = await self.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            
            stats = {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
            oldest_pending = None
            total = 0
            
            for result in results:
                status = result["_id"]
                count = result["count"]
                total += count
                
                if status in stats:
                    stats[status] = count
                
                if status == "pending" and result["oldest"]:
                    oldest_pending = result["oldest"]
            
            # Calculate average processing time for completed tasks
            avg_pipeline = [
                {
                    "$match": {
                        "status": "completed",
                        "started_at": {"$exists": True},
                        "completed_at": {"$exists": True}
                    }
                },
                {
                    "$project": {
                        "processing_time": {
                            "$subtract": ["$completed_at", "$started_at"]
                        }
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_time": {"$avg": "$processing_time"}
                    }
                }
            ]
            
            avg_cursor = await self.aggregate(avg_pipeline)
            avg_results = await avg_cursor.to_list(length=1)
            avg_processing_time = avg_results[0]["avg_time"] / 1000 if avg_results else 0  # Convert to seconds
            
            return QueueStats(
                pending=stats["pending"],
                processing=stats["processing"],
                completed=stats["completed"],
                failed=stats["failed"],
                total=total,
                oldest_pending=oldest_pending,
                average_processing_time=avg_processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            return QueueStats()
    
    async def get_failed_tasks(self, limit: int = 100) -> List[ProcessingTask]:
        """
        Get failed tasks for manual review.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of failed tasks
        """
        try:
            cursor = await self.find_many(
                {"status": "failed"},
                sort=[("failed_at", DESCENDING)],
                limit=limit
            )
            
            tasks = []
            for doc in cursor:
                tasks.append(self._document_to_task(doc))
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get failed tasks: {e}")
            return []
    
    async def retry_failed_tasks(self, task_ids: List[ObjectId]) -> int:
        """
        Retry specific failed tasks.
        
        Args:
            task_ids: List of task identifiers to retry
            
        Returns:
            Number of tasks successfully retried
        """
        try:
            validated_ids = [self._validate_object_id(tid) for tid in task_ids]
            
            now = datetime.now(UTC)
            update_data = {
                "status": "pending",
                "scheduled_at": now,
                "worker_id": None,
                "started_at": None,
                "error_message": None,
                "retry_count": 0,  # Reset retry count for manual retry
                "last_update": now
            }
            
            result = await self.update_many(
                {
                    "_id": {"$in": validated_ids},
                    "status": "failed"
                },
                {"$set": update_data}
            )
            
            retried_count = result.modified_count
            logger.info(f"Retried {retried_count} failed tasks")
            return retried_count
            
        except Exception as e:
            logger.error(f"Failed to retry tasks: {e}")
            return 0
    
    async def purge_completed_tasks(self, hours_old: int = 24) -> int:
        """
        Remove old completed tasks to maintain performance.
        
        Args:
            hours_old: Age threshold in hours
            
        Returns:
            Number of tasks purged
        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours_old)
            
            result = await self.delete_many({
                "status": "completed",
                "completed_at": {"$lt": cutoff_time}
            })
            
            purged_count = result.deleted_count
            if purged_count > 0:
                logger.info(f"Purged {purged_count} completed tasks")
            
            return purged_count
            
        except Exception as e:
            logger.error(f"Failed to purge completed tasks: {e}")
            return 0
    
    async def get_worker_tasks(self, worker_id: str) -> List[ProcessingTask]:
        """
        Get tasks assigned to a specific worker.
        
        Args:
            worker_id: Worker identifier
            
        Returns:
            List of tasks assigned to worker
        """
        try:
            cursor = await self.find_many(
                {"worker_id": worker_id, "status": "processing"},
                sort=[("started_at", ASCENDING)]
            )
            
            tasks = []
            for doc in cursor:
                tasks.append(self._document_to_task(doc))
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get worker tasks for {worker_id}: {e}")
            return []
    
    def _document_to_task(self, doc: Dict) -> ProcessingTask:
        """Convert MongoDB document to ProcessingTask object."""
        return ProcessingTask(
            id=doc["_id"],
            task_type=doc.get("task_type"),
            priority=doc.get("priority", 5),
            payload=doc.get("payload", {}),
            status=doc.get("status", "pending"),
            created_at=doc.get("created_at"),
            scheduled_at=doc.get("scheduled_at"),
            started_at=doc.get("started_at"),
            completed_at=doc.get("completed_at"),
            worker_id=doc.get("worker_id"),
            error_message=doc.get("error_message"),
            retry_count=doc.get("retry_count", 0),
            max_retries=doc.get("max_retries", 3)
        )
