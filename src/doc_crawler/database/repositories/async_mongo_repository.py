"""
Asynchronous MongoDB Repository with Connection Pooling, Retry Logic, and Security

This module provides a robust abstraction layer for MongoDB operations with:
- Async/await support using motor
- Connection pooling and retry logic
- Circuit breaker pattern for resilience
- Comprehensive logging and error handling
- Transaction support for critical operations
- Security measures and input validation
"""

import asyncio
import hashlib
import logging
from datetime import datetime, UTC
from typing import List, Dict, Optional, Callable, Awaitable, Any, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum

from pymongo import IndexModel
from pymongo.errors import NetworkTimeout, ServerSelectionTimeoutError, AutoReconnect
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from loguru import logger

# Configure structured logging
logging.getLogger("motor").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)


class RepositoryError(Exception):
    """Base exception for repository operations"""
    pass


class ConnectionError(RepositoryError):
    """Raised when database connection fails"""
    pass


class ValidationError(RepositoryError):
    """Raised when document validation fails"""
    pass


class TransactionError(RepositoryError):
    """Raised when transaction operations fail"""
    pass


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3  # for half-open state


class CircuitBreaker:
    """Circuit breaker pattern implementation for database resilience"""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        
    def can_execute(self) -> bool:
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                (datetime.now() - self.last_failure_time).total_seconds() >= self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to HALF_OPEN state")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker moved to CLOSED state")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker moved to OPEN state from HALF_OPEN")
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker moved to OPEN state after {self.failure_count} failures")


class AsyncMongoDBRepository:
    """
    Asynchronous MongoDB repository with comprehensive error handling and security
    
    Features:
    - Connection pooling with configurable limits
    - Retry logic with exponential backoff
    - Circuit breaker pattern for resilience
    - Transaction support for critical operations
    - Input validation and sanitization
    - Comprehensive logging and monitoring
    """
    
    def __init__(
        self,
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
    ):
        """
        Initialize the async MongoDB repository
        
        Args:
            connection_string: MongoDB connection string
            db_name: Database name
            collection_name: Collection name
            max_pool_size: Maximum number of connections in pool
            min_pool_size: Minimum number of connections in pool
            max_idle_time_ms: Maximum idle time for connections
            connect_timeout_ms: Connection timeout in milliseconds
            socket_timeout_ms: Socket timeout in milliseconds
            server_selection_timeout_ms: Server selection timeout
            retry_writes: Enable retryable writes
            w: Write concern
            read_preference: Read preference strategy
        """
        self.db_name = db_name
        self.collection_name = collection_name
        self.circuit_breaker = CircuitBreaker(CircuitBreakerConfig())
        
        # Parse connection string for SSL and auth settings
        use_ssl = any(param in connection_string.lower() for param in ['ssl=true', 'tls=true'])
        auth_source = None
        if 'authsource=' not in connection_string.lower():
            auth_source = "admin"
        
        # MongoDB client configuration with security and performance settings
        client_kwargs = {
            "maxPoolSize": max_pool_size,
            "minPoolSize": min_pool_size,
            "maxIdleTimeMS": max_idle_time_ms,
            "connectTimeoutMS": connect_timeout_ms,
            "socketTimeoutMS": socket_timeout_ms,
            "serverSelectionTimeoutMS": server_selection_timeout_ms,
            "retryWrites": retry_writes,
            "w": w,
            "readPreference": read_preference,
        }
        
        if use_ssl:
            client_kwargs["ssl"] = True
        if auth_source:
            client_kwargs["authSource"] = auth_source
            
        self.client = AsyncIOMotorClient(connection_string, **client_kwargs)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        
        logger.info(
            f"Initialized AsyncMongoDBRepository for {db_name}.{collection_name} "
            f"with pool size {min_pool_size}-{max_pool_size}"
        )
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def _sanitize_input(self, data: Dict) -> Dict:
        """Sanitize input data to prevent injection attacks"""
        if not isinstance(data, dict):
            raise ValidationError("Input must be a dictionary")
        
        # Remove any keys that start with '$' to prevent operator injection
        sanitized = {}
        for key, value in data.items():
            if isinstance(key, str) and key.startswith('$'):
                logger.warning(f"Removed potentially dangerous key: {key}")
                continue
            
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_input(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash for content integrity"""
        if not isinstance(content, str):
            content = str(content)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _convert_object_ids(self, data: Any) -> Any:
        """Recursively convert ObjectIds to strings for JSON serialization"""
        if isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, dict):
            return {key: self._convert_object_ids(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_object_ids(item) for item in data]
        else:
            return data
    
    def _validate_object_id(self, obj_id: str) -> ObjectId:
        """Validate and convert string to ObjectId"""
        try:
            return ObjectId(obj_id)
        except Exception as e:
            raise ValidationError(f"Invalid ObjectId: {obj_id}") from e
    
    async def _with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ) -> Any:
        """
        Execute operation with exponential backoff retry logic
        
        Args:
            operation: Async operation to execute
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        
        Returns:
            Result of the operation
        
        Raises:
            RepositoryError: If all retries are exhausted
        """
        if not self.circuit_breaker.can_execute():
            raise ConnectionError("Circuit breaker is OPEN - operation blocked")
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await operation()
                self.circuit_breaker.record_success()
                
                if attempt > 0:
                    logger.info(f"Operation succeeded on attempt {attempt + 1}")
                
                return result
                
            except (NetworkTimeout, ServerSelectionTimeoutError, AutoReconnect) as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                if attempt == max_retries:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                
                logger.warning(
                    f"Operation failed on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Non-retryable exceptions
                self.circuit_breaker.record_failure()
                logger.error(f"Non-retryable error in operation: {e}")
                raise RepositoryError(f"Operation failed: {e}") from e
        
        # All retries exhausted
        self.circuit_breaker.record_failure()
        error_msg = f"Operation failed after {max_retries + 1} attempts: {last_exception}"
        logger.error(error_msg)
        raise ConnectionError(error_msg) from last_exception
    
    async def insert_one(self, document: Dict, validate: bool = True) -> str:
        """
        Insert a single document
        
        Args:
            document: Document to insert
            validate: Whether to validate/sanitize input
        
        Returns:
            String representation of inserted document ID
        """
        if validate:
            document = self._sanitize_input(document)
        
        # Add metadata
        document.update({
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        })
        
        # Add content hash if content field exists
        if "content" in document:
            document["content_hash"] = self._generate_content_hash(document["content"])
        
        async def operation():
            result = await self.collection.insert_one(document)
            logger.debug(f"Inserted document with ID: {result.inserted_id}")
            return str(result.inserted_id)
        
        return await self._with_retry(operation)
    
    async def find_one(self, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        """Find a single document"""
        query = self._sanitize_input(query)
        
        async def operation():
            result = await self.collection.find_one(query, projection)
            return self._convert_object_ids(result) if result else None
        
        return await self._with_retry(operation)
    
    async def find_many(
        self,
        query: Dict,
        projection: Optional[Dict] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[Dict]:
        """Find multiple documents with optional sorting, limiting, and skipping"""
        query = self._sanitize_input(query)
        
        async def operation():
            cursor = self.collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            results = await cursor.to_list(length=limit)
            return [self._convert_object_ids(result) for result in results]
        
        return await self._with_retry(operation)
    
    async def update_one(
        self,
        query: Dict,
        update_data: Dict,
        upsert: bool = False,
        validate: bool = True
    ) -> bool:
        """Update a single document"""
        query = self._sanitize_input(query)
        
        if validate:
            update_data = self._sanitize_input(update_data)
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.now(UTC)
        
        # Update content hash if content is being updated
        if "content" in update_data:
            update_data["content_hash"] = self._generate_content_hash(update_data["content"])
        
        async def operation():
            result = await self.collection.update_one(
                query,
                {"$set": update_data},
                upsert=upsert
            )
            return result.modified_count > 0 or (upsert and result.upserted_id is not None)
        
        return await self._with_retry(operation)
    
    async def update_many(self, query: Dict, update_data: Dict, validate: bool = True) -> int:
        """Update multiple documents"""
        query = self._sanitize_input(query)
        
        if validate:
            update_data = self._sanitize_input(update_data)
        
        update_data["updated_at"] = datetime.now(UTC)
        
        async def operation():
            result = await self.collection.update_many(query, {"$set": update_data})
            return result.modified_count
        
        return await self._with_retry(operation)
    
    async def delete_one(self, query: Dict) -> bool:
        """Delete a single document"""
        query = self._sanitize_input(query)
        
        async def operation():
            result = await self.collection.delete_one(query)
            return result.deleted_count > 0
        
        return await self._with_retry(operation)
    
    async def delete_many(self, query: Dict) -> int:
        """Delete multiple documents"""
        query = self._sanitize_input(query)
        
        async def operation():
            result = await self.collection.delete_many(query)
            return result.deleted_count
        
        return await self._with_retry(operation)
    
    async def insert_many(self, documents: List[Dict], validate: bool = True) -> List[str]:
        """Insert multiple documents"""
        if validate:
            documents = [self._sanitize_input(doc) for doc in documents]
        
        # Add metadata to all documents
        now = datetime.now(UTC)
        for doc in documents:
            doc.update({
                "created_at": now,
                "updated_at": now
            })
            
            # Add content hash if content exists
            if "content" in doc:
                doc["content_hash"] = self._generate_content_hash(doc["content"])
        
        async def operation():
            result = await self.collection.insert_many(documents, ordered=False)
            return [str(id) for id in result.inserted_ids]
        
        return await self._with_retry(operation)
    
    async def find_paginated(
        self,
        query: Dict,
        skip: int,
        limit: int,
        sort: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """Find documents with pagination support"""
        query = self._sanitize_input(query)
        
        async def operation():
            # Get total count for pagination metadata
            total_count = await self.collection.count_documents(query)
            
            # Get paginated results
            cursor = self.collection.find(query)
            if sort:
                cursor = cursor.sort(sort)
            
            results = await cursor.skip(skip).limit(limit).to_list(length=limit)
            
            return {
                "documents": [self._convert_object_ids(result) for result in results],
                "total_count": total_count,
                "skip": skip,
                "limit": limit,
                "has_more": skip + limit < total_count
            }
        
        return await self._with_retry(operation)
    
    async def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        """Execute aggregation pipeline"""
        # Note: Aggregation pipelines are complex and may contain operators
        # Consider implementing specific validation for your use cases
        
        async def operation():
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=None)
            return [self._convert_object_ids(result) for result in results]
        
        return await self._with_retry(operation)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transaction support"""
        session = None
        try:
            session = await self.client.start_session()
            async with session.start_transaction():
                yield session
                logger.debug("Transaction completed successfully")
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise TransactionError(f"Transaction failed: {e}") from e
        finally:
            if session:
                await session.end_session()
    
    async def update_page_and_clear_task(
        self,
        page_id: str,
        update_data: Dict,
        task_query: Dict
    ) -> bool:
        """
        Atomic operation: update a page and clear its processing task
        Example of using transactions for critical operations
        """
        try:
            page_object_id = self._validate_object_id(page_id)
            
            async with self.transaction() as session:
                # Update page
                page_result = await self.db.pages.update_one(
                    {"_id": page_object_id},
                    {"$set": {**update_data, "updated_at": datetime.now(UTC)}},
                    session=session
                )
                
                # Clear processing task
                task_result = await self.db.processing_queue.delete_one(
                    task_query,
                    session=session
                )
                
                success = page_result.modified_count > 0 and task_result.deleted_count > 0
                logger.info(f"Atomic operation {'succeeded' if success else 'failed'} for page {page_id}")
                return success
                
        except Exception as e:
            logger.error(f"Atomic operation failed for page {page_id}: {e}")
            raise TransactionError(f"Atomic operation failed: {e}") from e
    
    async def get_collection_stats(self) -> Dict:
        """Get collection statistics for monitoring"""
        async def operation():
            stats = await self.db.command("collStats", self.collection_name)
            return {
                "document_count": stats.get("count", 0),
                "storage_size": stats.get("storageSize", 0),
                "index_size": stats.get("totalIndexSize", 0),
                "avg_document_size": stats.get("avgObjSize", 0)
            }
        
        return await self._with_retry(operation)
    
    async def close(self):
        """Close the database connection"""
        if self.client:
            self.client.close()
            logger.info(f"Closed connection to {self.db_name}.{self.collection_name}")