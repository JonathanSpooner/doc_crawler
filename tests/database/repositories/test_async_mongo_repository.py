"""
Unit tests for AsyncMongoDBRepository

This test suite covers:
- CRUD operations
- Error handling and retry logic
- Circuit breaker functionality
- Transaction support
- Input validation and sanitization
- Connection and health checks
- Utility methods
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pymongo
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Import the classes to test
from doc_crawler.database.repositories.async_mongo_repository import (
    AsyncMongoDBRepository,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    RepositoryError,
    ConnectionError,
    ValidationError,
    TransactionError
)


import warnings
def api_v1():
    warnings.warn(UserWarning("api v1, should use functions from v2"))
    return 1


class TestCircuitBreaker:
    """Test suite for CircuitBreaker class"""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker(CircuitBreakerConfig())
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.can_execute() is True
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)
        
        # Record failures up to threshold
        for i in range(3):
            cb.record_failure()
            if i < 2:
                assert cb.state == CircuitBreakerState.CLOSED
            else:
                assert cb.state == CircuitBreakerState.OPEN
                assert cb.can_execute() is False
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to HALF_OPEN after timeout"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        cb = CircuitBreaker(config)
        
        # Force to OPEN state
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        
        # Simulate timeout passage by setting past time
        cb.last_failure_time = datetime.now() - timedelta(seconds=2)
        
        # Should transition to HALF_OPEN
        assert cb.can_execute() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN
    
    def test_circuit_breaker_closes_after_successes(self):
        """Test circuit breaker closes after successful operations in HALF_OPEN"""
        config = CircuitBreakerConfig(success_threshold=2)
        cb = CircuitBreaker(config)
        
        # Force to HALF_OPEN state
        cb.state = CircuitBreakerState.HALF_OPEN
        
        # Record successes
        cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


def create_mock_cursor(documents):
    """Create a properly mocked Motor cursor that supports method chaining"""
    cursor = MagicMock()
    
    # Make chaining methods return the cursor itself (not coroutines)
    cursor.sort.return_value = cursor
    cursor.skip.return_value = cursor
    cursor.limit.return_value = cursor
    
    # Make to_list return an awaitable
    async def mock_to_list(length=None):
        return documents
    
    cursor.to_list = mock_to_list
    return cursor


class MockTransactionContext:
    """Mock transaction context manager"""
    def __init__(self):
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def create_mock_session():
    """Create a properly mocked Motor session"""
    session = AsyncMock()
    session.end_session = AsyncMock()
    
    # start_transaction returns a transaction context manager
    def start_transaction():
        return MockTransactionContext()
    
    session.start_transaction = start_transaction
    return session


@pytest.fixture
def mock_collection():
    """Create a mock MongoDB collection"""
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.find_one = AsyncMock()
    collection.find = MagicMock()  # Returns cursor, not awaitable
    collection.update_one = AsyncMock()
    collection.update_many = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.insert_many = AsyncMock()
    collection.count_documents = AsyncMock()
    collection.aggregate = MagicMock()  # Returns cursor, not awaitable
    collection.create_indexes = AsyncMock()
    collection.create_index = AsyncMock()
    return collection


@pytest.fixture
def mock_database(mock_collection):
    """Create a mock MongoDB database"""
    db = AsyncMock()
    db.command = AsyncMock()
    db.pages = mock_collection
    db.processing_queue = mock_collection
    # Support both attribute access and item access
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db


@pytest.fixture
def mock_admin():
    """Create a mock admin interface"""
    admin = AsyncMock()
    admin.command = AsyncMock(return_value={"ok": 1})
    return admin


@pytest.fixture
def mock_client(mock_admin, mock_database):
    """Create a properly configured mock MongoDB client"""
    client = AsyncMock(spec=AsyncIOMotorClient)
    client.admin = mock_admin
    client.close = MagicMock()
    client.__getitem__ = MagicMock(return_value=mock_database)
    
    # Mock start_session to return a coroutine that yields a session
    async def start_session():
        return create_mock_session()
    
    client.start_session = start_session
    return client


@pytest.fixture
def repository(mock_client, mock_database, mock_collection):
    """Create repository instance with mocked dependencies"""
    with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncIOMotorClient') as mock_motor_client:
        mock_motor_client.return_value = mock_client
        
        repo = AsyncMongoDBRepository(
            connection_string="mongodb://localhost:27017/",
            db_name="test_db",
            collection_name="test_collection"
        )
        
        # Override the created instances with our mocks
        repo.client = mock_client
        repo.db = mock_database
        repo.collection = mock_collection
        
        return repo


@pytest.fixture
def sample_document():
    """Sample document for testing"""
    return {
        "title": "Test Document",
        "content": "This is test content",
        "author": "Test Author",
        "url": "https://example.com/test"
    }


class TestAsyncMongoDBRepository:
    """Test suite for AsyncMongoDBRepository class"""
    
    class TestInitialization:
        """Test repository initialization"""
        
        def test_init_with_default_params(self, mock_client):
            """Test initialization with default parameters"""
            with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncIOMotorClient') as mock_motor_client:
                mock_motor_client.return_value = mock_client
                
                repo = AsyncMongoDBRepository(
                    connection_string="mongodb://localhost:27017/",
                    db_name="test_db",
                    collection_name="test_collection"
                )
                
                assert repo.db_name == "test_db"
                assert repo.collection_name == "test_collection"
                assert isinstance(repo.circuit_breaker, CircuitBreaker)
                mock_motor_client.assert_called_once()
        
        def test_init_with_ssl_connection(self, mock_client):
            """Test initialization with SSL connection string"""
            with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncIOMotorClient') as mock_motor_client:
                mock_motor_client.return_value = mock_client
                
                repo = AsyncMongoDBRepository(
                    connection_string="mongodb://localhost:27017/?ssl=true",
                    db_name="test_db",
                    collection_name="test_collection"
                )
                
                # Verify SSL was detected and configured
                call_args = mock_motor_client.call_args
                assert call_args[1]['ssl'] is True
    
    class TestHealthCheck:
        """Test health check functionality"""
        
        
        async def test_health_check_success(self, repository):
            """Test successful health check"""
            repository.client.admin.command.return_value = {"ok": 1}
            
            result = await repository.health_check()
            assert result is True
            repository.client.admin.command.assert_called_once_with('ping')
        
        
        async def test_health_check_failure(self, repository):
            """Test failed health check"""
            repository.client.admin.command.side_effect = Exception("Connection failed")
            
            result = await repository.health_check()
            assert result is False
    
    class TestInputSanitization:
        """Test input validation and sanitization"""
        
        def test_sanitize_input_removes_dangerous_keys(self, repository):
            """Test that dangerous keys starting with $ are removed"""
            dangerous_input = {
                "title": "Test",
                "$where": "malicious code",
                "$ne": {"password": "admin"},
                "safe_key": "safe_value"
            }
            
            result = repository._sanitize_input(dangerous_input)
            
            assert "$where" not in result
            assert "$ne" not in result
            assert result["title"] == "Test"
            assert result["safe_key"] == "safe_value"
        
        def test_sanitize_input_nested_objects(self, repository):
            """Test sanitization of nested objects"""
            nested_input = {
                "user": {
                    "name": "John",
                    "$admin": True
                },
                "filters": [
                    {"type": "active"},
                    {"$or": [{"a": 1}]}
                ]
            }
            
            result = repository._sanitize_input(nested_input)
            
            assert "$admin" not in result["user"]
            assert result["user"]["name"] == "John"
            assert len(result["filters"]) == 2
            # Check that the dangerous operator was removed from the list item
            assert not any("$or" in str(item) for item in result["filters"] if isinstance(item, dict))
        
        def test_sanitize_input_invalid_type(self, repository):
            """Test sanitization with invalid input type"""
            with pytest.raises(ValidationError, match="Input must be a dictionary"):
                repository._sanitize_input("not a dict")
    
    class TestContentHash:
        """Test content hash generation"""
        
        def test_generate_content_hash_string(self, repository):
            """Test hash generation for string content"""
            content = "This is test content"
            hash_result = repository._generate_content_hash(content)
            
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64  # SHA-256 produces 64-character hex string
        
        def test_generate_content_hash_non_string(self, repository):
            """Test hash generation for non-string content"""
            content = 12345
            hash_result = repository._generate_content_hash(content)
            
            assert isinstance(hash_result, str)
            assert len(hash_result) == 64
    
    class TestObjectIdHandling:
        """Test ObjectId conversion and validation"""
        
        def test_convert_object_ids_simple(self, repository):
            """Test ObjectId conversion in simple document"""
            doc = {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "title": "Test"
            }
            
            result = repository._convert_object_ids(doc)
            assert result["_id"] == "507f1f77bcf86cd799439011"
            assert result["title"] == "Test"
        
        def test_convert_object_ids_nested(self, repository):
            """Test ObjectId conversion in nested structures"""
            doc = {
                "refs": [
                    {"_id": ObjectId("507f1f77bcf86cd799439011")},
                    {"_id": ObjectId("507f1f77bcf86cd799439012")}
                ],
                "metadata": {
                    "author_id": ObjectId("507f1f77bcf86cd799439013")
                }
            }
            
            result = repository._convert_object_ids(doc)
            assert result["refs"][0]["_id"] == "507f1f77bcf86cd799439011"
            assert result["refs"][1]["_id"] == "507f1f77bcf86cd799439012"
            assert result["metadata"]["author_id"] == "507f1f77bcf86cd799439013"
        
        def test_validate_object_id_valid(self, repository):
            """Test valid ObjectId validation"""
            valid_id = "507f1f77bcf86cd799439011"
            result = repository._validate_object_id(valid_id)
            assert isinstance(result, ObjectId)
            assert str(result) == valid_id
        
        def test_validate_object_id_invalid(self, repository):
            """Test invalid ObjectId validation"""
            invalid_id = "invalid_object_id"
            with pytest.raises(ValidationError, match="Invalid ObjectId"):
                repository._validate_object_id(invalid_id)
    
    class TestCRUDOperations:
        """Test CRUD operations"""
        
        
        async def test_insert_one_success(self, repository, sample_document):
            """Test successful document insertion"""
            mock_result = MagicMock()
            mock_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
            repository.collection.insert_one.return_value = mock_result
            
            result = await repository.insert_one(sample_document)
            
            assert result == "507f1f77bcf86cd799439011"
            repository.collection.insert_one.assert_called_once()
            
            # Verify metadata was added
            call_args = repository.collection.insert_one.call_args[0][0]
            assert "created_at" in call_args
            assert "updated_at" in call_args
            assert "content_hash" in call_args
        
        
        async def test_find_one_success(self, repository):
            """Test successful document retrieval"""
            mock_doc = {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "title": "Test Document"
            }
            repository.collection.find_one.return_value = mock_doc
            
            result = await repository.find_one({"title": "Test Document"})
            
            assert result["_id"] == "507f1f77bcf86cd799439011"
            assert result["title"] == "Test Document"
            repository.collection.find_one.assert_called_once()
        
        
        async def test_find_one_not_found(self, repository):
            """Test document not found"""
            repository.collection.find_one.return_value = None
            
            result = await repository.find_one({"title": "Nonexistent"})
            
            assert result is None
        
        
        async def test_find_many_success(self, repository):
            """Test successful multiple document retrieval"""
            mock_docs = [
                {"_id": ObjectId("507f1f77bcf86cd799439011"), "title": "Doc 1"},
                {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Doc 2"}
            ]
            
            # Create properly mocked cursor
            mock_cursor = create_mock_cursor(mock_docs)
            repository.collection.find.return_value = mock_cursor
            
            result = await repository.find_many(
                {"status": "active"},
                sort=[("created_at", -1)],
                limit=10,
                skip=5  # Use non-zero skip to test the conditional call
            )
            
            assert len(result) == 2
            assert result[0]["_id"] == "507f1f77bcf86cd799439011"
            assert result[1]["_id"] == "507f1f77bcf86cd799439012"
            
            # Verify cursor methods were called
            mock_cursor.sort.assert_called_once_with([("created_at", -1)])
            mock_cursor.skip.assert_called_once_with(5)
            mock_cursor.limit.assert_called_once_with(10)
        
        
        async def test_find_many_no_skip(self, repository):
            """Test find_many without skip parameter"""
            mock_docs = [
                {"_id": ObjectId("507f1f77bcf86cd799439011"), "title": "Doc 1"}
            ]
            
            mock_cursor = create_mock_cursor(mock_docs)
            repository.collection.find.return_value = mock_cursor
            
            result = await repository.find_many({"status": "active"})
            
            assert len(result) == 1
            # Skip should not be called when skip is None or 0
            mock_cursor.skip.assert_not_called()
        
        
        async def test_update_one_success(self, repository):
            """Test successful document update"""
            mock_result = MagicMock()
            mock_result.modified_count = 1
            mock_result.upserted_id = None
            repository.collection.update_one.return_value = mock_result
            
            result = await repository.update_one(
                {"_id": "507f1f77bcf86cd799439011"},
                {"title": "Updated Title"}
            )
            
            assert result is True
            repository.collection.update_one.assert_called_once()
            
            # Verify updated_at was added
            call_args = repository.collection.update_one.call_args[0][1]["$set"]
            assert "updated_at" in call_args
        
        
        async def test_update_one_with_upsert(self, repository):
            """Test update with upsert"""
            mock_result = MagicMock()
            mock_result.modified_count = 0
            mock_result.upserted_id = ObjectId("507f1f77bcf86cd799439011")
            repository.collection.update_one.return_value = mock_result
            
            result = await repository.update_one(
                {"title": "New Document"},
                {"content": "New content"},
                upsert=True
            )
            
            assert result is True
        
        
        async def test_delete_one_success(self, repository):
            """Test successful document deletion"""
            mock_result = MagicMock()
            mock_result.deleted_count = 1
            repository.collection.delete_one.return_value = mock_result
            
            result = await repository.delete_one({"_id": "507f1f77bcf86cd799439011"})
            
            assert result is True
            repository.collection.delete_one.assert_called_once()
        
        
        async def test_insert_many_success(self, repository):
            """Test successful multiple document insertion"""
            docs = [
                {"title": "Doc 1", "content": "Content 1"},
                {"title": "Doc 2", "content": "Content 2"}
            ]
            
            mock_result = MagicMock()
            mock_result.inserted_ids = [
                ObjectId("507f1f77bcf86cd799439011"),
                ObjectId("507f1f77bcf86cd799439012")
            ]
            repository.collection.insert_many.return_value = mock_result
            
            result = await repository.insert_many(docs)
            
            assert len(result) == 2
            assert result[0] == "507f1f77bcf86cd799439011"
            assert result[1] == "507f1f77bcf86cd799439012"
    
    class TestPagination:
        """Test pagination functionality"""
        
        
        async def test_find_paginated_success(self, repository):
            """Test successful paginated query"""
            mock_docs = [
                {"_id": ObjectId("507f1f77bcf86cd799439011"), "title": "Doc 1"},
                {"_id": ObjectId("507f1f77bcf86cd799439012"), "title": "Doc 2"}
            ]
            
            repository.collection.count_documents.return_value = 10
            
            # Create properly mocked cursor
            mock_cursor = create_mock_cursor(mock_docs)
            repository.collection.find.return_value = mock_cursor
            
            result = await repository.find_paginated(
                query={"status": "active"},
                skip=5,  # Use non-zero skip
                limit=5,
                sort=[("created_at", -1)]
            )
            
            assert result["total_count"] == 10
            assert result["skip"] == 5
            assert result["limit"] == 5
            assert result["has_more"] is False  # 5 + 5 = 10, so no more
            assert len(result["documents"]) == 2
            
            # Verify cursor methods were called
            mock_cursor.sort.assert_called_once_with([("created_at", -1)])
            mock_cursor.skip.assert_called_once_with(5)
            mock_cursor.limit.assert_called_once_with(5)
    
    class TestAggregation:
        """Test aggregation functionality"""
        
        
        async def test_aggregate_success(self, repository):
            """Test successful aggregation"""
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}}
            ]
            
            mock_results = [
                {"_id": "philosophy", "count": 5},
                {"_id": "science", "count": 3}
            ]
            
            # Create properly mocked cursor for aggregation
            mock_cursor = create_mock_cursor(mock_results)
            repository.collection.aggregate.return_value = mock_cursor
            
            result = await repository.aggregate(pipeline)
            
            assert len(result) == 2
            assert result[0]["_id"] == "philosophy"
            assert result[1]["count"] == 3
            
            repository.collection.aggregate.assert_called_once_with(pipeline)
    
    class TestRetryLogic:
        """Test retry logic and error handling"""
        
        @pytest.mark.slow
        
        async def test_retry_success_after_failure(self, repository):
            """Test successful operation after initial failure"""
            mock_result = MagicMock()
            mock_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
            
            # First call fails, second succeeds
            repository.collection.insert_one.side_effect = [
                pymongo.errors.NetworkTimeout("Network timeout"),
                mock_result
            ]
            
            result = await repository.insert_one({"title": "Test"})
            
            assert result == "507f1f77bcf86cd799439011"
            assert repository.collection.insert_one.call_count == 2
        
        @pytest.mark.slow
        
        async def test_retry_exhaustion(self, repository):
            """Test operation failure after exhausting retries"""
            repository.collection.insert_one.side_effect = pymongo.errors.NetworkTimeout("Network timeout")
            
            with pytest.raises(ConnectionError, match="Operation failed after"):
                await repository.insert_one({"title": "Test"})
            
            # Should have tried max_retries + 1 times (default is 3 + 1 = 4)
            assert repository.collection.insert_one.call_count == 4
        
        
        async def test_non_retryable_error(self, repository):
            """Test immediate failure for non-retryable errors"""
            repository.collection.insert_one.side_effect = ValueError("Invalid input")
            
            with pytest.raises(RepositoryError, match="Operation failed"):
                await repository.insert_one({"title": "Test"})
            
            # Should only try once for non-retryable errors
            assert repository.collection.insert_one.call_count == 1
        
        
        async def test_circuit_breaker_blocks_operation(self, repository):
            """Test circuit breaker blocking operations when open"""
            # Force circuit breaker to OPEN state
            repository.circuit_breaker.state = CircuitBreakerState.OPEN
            
            with pytest.raises(ConnectionError, match="Circuit breaker is OPEN"):
                await repository.insert_one({"title": "Test"})
            
            # Should not attempt operation
            repository.collection.insert_one.assert_not_called()
    
    class TestTransactions:
        """Test transaction functionality"""
        
        
        async def test_transaction_context_manager_success(self, repository):
            """Test successful transaction context manager"""
            # Mock start_session returns a coroutine that yields a session
            async with repository.transaction() as session:
                assert session is not None
            
            # Verify the transaction context manager worked correctly
            assert True  # If we get here, the transaction completed successfully
        
        
        async def test_update_page_and_clear_task_success(self, repository):
            """Test successful atomic operation"""
            page_id = "507f1f77bcf86cd799439011"
            update_data = {"status": "processed"}
            task_query = {"page_id": ObjectId(page_id)}
            
            # Mock successful updates
            mock_page_result = MagicMock()
            mock_page_result.modified_count = 1
            repository.db.pages.update_one.return_value = mock_page_result
            
            mock_task_result = MagicMock()
            mock_task_result.deleted_count = 1
            repository.db.processing_queue.delete_one.return_value = mock_task_result
            
            result = await repository.update_page_and_clear_task(page_id, update_data, task_query)
            
            assert result is True
            repository.db.pages.update_one.assert_called_once()
            repository.db.processing_queue.delete_one.assert_called_once()
        
        
        async def test_update_page_and_clear_task_invalid_id(self, repository):
            """Test atomic operation with invalid ObjectId"""
            invalid_id = "invalid_object_id"
            
            with pytest.raises(TransactionError, match="Atomic operation failed"):
                await repository.update_page_and_clear_task(invalid_id, {}, {})
    
    class TestStatistics:
        """Test collection statistics"""
        
        
        async def test_get_collection_stats_success(self, repository):
            """Test successful collection statistics retrieval"""
            mock_stats = {
                "count": 1000,
                "storageSize": 5242880,
                "totalIndexSize": 1048576,
                "avgObjSize": 512
            }
            repository.db.command.return_value = mock_stats
            
            result = await repository.get_collection_stats()
            
            assert result["document_count"] == 1000
            assert result["storage_size"] == 5242880
            assert result["index_size"] == 1048576
            assert result["avg_document_size"] == 512
    
    class TestCleanup:
        """Test connection cleanup"""
        
        
        async def test_close_connection(self, repository):
            """Test proper connection closure"""
            await repository.close()
            repository.client.close.assert_called_once()



async def test_integration_workflow():
    """Integration test simulating a typical workflow"""
    # Create mocks for integration test
    mock_admin = AsyncMock()
    mock_admin.command = AsyncMock(return_value={"ok": 1})
    
    mock_client = AsyncMock()
    mock_client.admin = mock_admin
    mock_client.close = MagicMock()
    
    # Mock start_session for integration test - return a coroutine
    async def start_session():
        return create_mock_session()
    
    mock_client.start_session = start_session
    
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    
    mock_client.__getitem__ = MagicMock(return_value=mock_db)
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncIOMotorClient') as mock_motor_client:
        mock_motor_client.return_value = mock_client
        
        # Create repository
        repo = AsyncMongoDBRepository(
            connection_string="mongodb://localhost:27017/",
            db_name="test_db",
            collection_name="pages"
        )
        repo.client = mock_client
        repo.db = mock_db
        repo.collection = mock_collection
        
        # Mock responses
        insert_result = MagicMock()
        insert_result.inserted_id = ObjectId("507f1f77bcf86cd799439011")
        mock_collection.insert_one.return_value = insert_result
        
        find_result = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "url": "https://example.com/test",
            "title": "Test Page"
        }
        mock_collection.find_one.return_value = find_result
        
        update_result = MagicMock()
        update_result.modified_count = 1
        update_result.upserted_id = None
        mock_collection.update_one.return_value = update_result
        
        # Simulate workflow: insert -> find -> update
        doc = {
            "url": "https://example.com/test",
            "title": "Test Page",
            "content": "Test content"
        }
        
        # Insert document
        doc_id = await repo.insert_one(doc)
        assert doc_id == "507f1f77bcf86cd799439011"
        
        # Find document
        found_doc = await repo.find_one({"_id": "507f1f77bcf86cd799439011"})
        assert found_doc["_id"] == "507f1f77bcf86cd799439011"
        
        # Update document
        success = await repo.update_one(
            {"_id": "507f1f77bcf86cd799439011"},
            {"status": "processed"}
        )
        assert success is True
        
        await repo.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])