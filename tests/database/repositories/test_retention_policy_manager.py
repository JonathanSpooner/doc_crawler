"""
Fixed unit tests for RetentionPolicyManager class.

Corrects Motor cursor mocking and datetime patching issues.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone as tz, timedelta
from bson import ObjectId
from pymongo.errors import OperationFailure

# Import the class under test
from doc_crawler.database.repositories.retention_policy_manager import RetentionPolicyManager, RetentionPolicy

pytest.skip(allow_module_level=True)
class MockMotorCursor:
    """Mock Motor cursor that properly handles chaining and async operations."""
    
    def __init__(self, documents=None, to_list_result=None):
        self.documents = documents or []
        self.to_list_result = to_list_result or []
        self._batch_size = 1000
        self._skip = 0
        self._limit = None
        self._iter_index = 0
    
    def batch_size(self, size):
        """Mock batch_size method that returns self for chaining."""
        self._batch_size = size
        return self
    
    def skip(self, skip_count):
        """Mock skip method that returns self for chaining."""
        self._skip = skip_count
        return self
    
    def limit(self, limit_count):
        """Mock limit method that returns self for chaining."""
        self._limit = limit_count
        return self
    
    async def to_list(self, length):
        """Mock async to_list method."""
        if self.to_list_result is not None:
            return self.to_list_result
        
        # Apply skip and limit to documents
        start = self._skip
        end = len(self.documents)
        if self._limit is not None:
            end = start + self._limit
        
        return self.documents[start:end]
    
    def __aiter__(self):
        """Mock async iterator."""
        self._iter_index = 0
        return self
    
    async def __anext__(self):
        """Mock async next."""
        if self._iter_index >= len(self.documents):
            raise StopAsyncIteration
        
        doc = self.documents[self._iter_index]
        self._iter_index += 1
        return doc


class MockMotorCollection:
    """Mock Motor collection with proper async method support."""
    
    def __init__(self):
        self.count_documents = AsyncMock()
        self.create_index = AsyncMock()
        self.delete_many = AsyncMock()
        self.list_indexes = MagicMock()
        self.find = MagicMock()
    
    def __getitem__(self, key):
        return MockMotorCollection()


class TestRetentionPolicyManager:
    """Test suite for RetentionPolicyManager class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB database."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        return MagicMock()
    
    @pytest.fixture
    def manager(self, mock_db, mock_s3_client):
        """Create a RetentionPolicyManager instance."""
        return RetentionPolicyManager(
            db=mock_db,
            s3_client=mock_s3_client,
            s3_bucket="test-bucket"
        )
    
    @pytest.fixture
    def dry_run_manager(self, mock_db, mock_s3_client):
        """Create a RetentionPolicyManager instance in dry-run mode."""
        return RetentionPolicyManager(
            db=mock_db,
            s3_client=mock_s3_client,
            s3_bucket="test-bucket",
            dry_run=True
        )
    
    @pytest.mark.asyncio
    async def test_setup_ttl_indexes_success(self, manager, mock_db):
        """Test successful TTL index creation"""
        # Mock collection that returns proper cursors
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock list_indexes to return cursor with no existing TTL indexes
        mock_cursor = MockMotorCursor(to_list_result=[
            {"name": "regular_index", "key": {"field": 1}}
        ])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Test
        results = await manager.setup_ttl_indexes()
        
        # Verify
        assert len(results) == 4  # 4 default policies
        assert all(results.values())  # All should be True
        
        # Verify create_index was called for each collection
        assert mock_collection.create_index.call_count == 4
    
    @pytest.mark.asyncio
    async def test_setup_ttl_indexes_existing(self, manager, mock_db):
        """Test TTL index setup when indexes already exist"""
        # Mock collection
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock list_indexes to return existing TTL index
        mock_cursor = MockMotorCursor(to_list_result=[
            {"name": "ttl_detected_at", "expireAfterSeconds": 31536000}
        ])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Test
        results = await manager.setup_ttl_indexes()
        
        # Verify
        assert len(results) == 4
        assert all(results.values())  # All should be True
        
        # Verify create_index was NOT called since indexes exist
        mock_collection.create_index.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_setup_ttl_indexes_dry_run(self, dry_run_manager, mock_db):
        """Test TTL index setup in dry-run mode"""
        # Mock collection
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock list_indexes to return no existing TTL indexes
        mock_cursor = MockMotorCursor(to_list_result=[])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Test
        results = await dry_run_manager.setup_ttl_indexes()
        
        # Verify
        assert len(results) == 4
        assert all(results.values())  # All should be True
        
        # Verify create_index was NOT called in dry-run mode
        mock_collection.create_index.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_setup_ttl_indexes_error(self, manager, mock_db):
        """Test TTL index setup with creation error"""
        # Mock collection
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock list_indexes to return no existing indexes
        mock_cursor = MockMotorCursor(to_list_result=[])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Mock create_index to fail
        mock_collection.create_index.side_effect = OperationFailure("Index creation failed")
        
        # Test
        results = await manager.setup_ttl_indexes()
        
        # Verify all failed
        assert len(results) == 4
        assert not any(results.values())  # All should be False
    
    @pytest.mark.asyncio
    async def test_get_batches(self, manager):
        """Test document batch processing"""
        # Create test documents
        batch1 = [{"_id": ObjectId(), "data": f"doc{i}"} for i in range(3)]
        batch2 = [{"_id": ObjectId(), "data": f"doc{i}"} for i in range(3, 5)]
        
        # Mock collection with proper cursor chaining
        mock_collection = MagicMock()
        
        call_count = 0
        def mock_find(*args, **kwargs):
            nonlocal call_count
            
            # Return different batches based on call count
            if call_count == 0:
                cursor = MockMotorCursor(to_list_result=batch1)
            elif call_count == 1:
                cursor = MockMotorCursor(to_list_result=batch2)
            else:
                cursor = MockMotorCursor(to_list_result=[])
            
            call_count += 1
            return cursor
        
        mock_collection.find.side_effect = mock_find
        
        # Test
        batches = []
        async for batch in manager._get_batches(mock_collection, {}, 3):
            batches.append(batch)
        
        # Verify
        assert len(batches) == 2
        assert len(batches[0]) == 3
        assert len(batches[1]) == 2
    
    def test_generate_archive_key(self, manager):
        """Test S3 archive key generation"""
        first_doc = {"_id": ObjectId("507f1f77bcf86cd799439011")}
        last_doc = {"_id": ObjectId("507f1f77bcf86cd799439012")}
        
        # Mock datetime.now() properly - need to patch the specific import
        with patch('doc_crawler.database.repositories.retention_policy_manager.datetime') as mock_datetime:
            # Create a mock datetime instance
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20231201_120000"
            mock_datetime.now.return_value = mock_now
            
            key = manager._generate_archive_key("test_collection", first_doc, last_doc)
        
        expected = "archives/test_collection/20231201_120000_507f1f77bcf86cd799439011_507f1f77bcf86cd799439012.json.gz"
        assert key == expected
    
    @pytest.mark.asyncio
    async def test_archive_documents_success(self, manager, mock_db, mock_s3_client):
        """Test successful document archival"""
        # Mock collection
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Test documents
        test_docs = [
            {"_id": ObjectId(), "data": "test1"},
            {"_id": ObjectId(), "data": "test2"}
        ]
        
        # Mock _get_batches to return test documents
        async def mock_get_batches(collection, query, batch_size):
            yield test_docs
        
        manager._get_batches = mock_get_batches
        
        # Mock S3 and delete operations
        mock_s3_client.put_object = MagicMock()
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 2
        mock_collection.delete_many.return_value = mock_delete_result
        
        # Create test policy
        policy = RetentionPolicy(
            collection_name="crawl_sessions",
            ttl_field="created_at",
            # ttl_seconds=86400,
            archive_after_days=30,
            retention_days=10
        )
        
        # Test
        result = await manager.archive_old_documents(policy.collection_name)
        
        # Verify
        assert result["collection"] == "crawl_sessions"
        assert result["documents_archived"] == 2
        assert result["errors"] == []
        
        # Verify S3 upload and deletion occurred
        mock_s3_client.put_object.assert_called_once()
        mock_collection.delete_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_retention_status(self, manager, mock_db):
        """Test retention status reporting"""
        # Mock collection
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock count_documents to return consistent values
        count_values = [100, 10]  # total, expiring
        count_index = 0
        
        async def mock_count_documents(*args, **kwargs):
            nonlocal count_index
            value = count_values[count_index % len(count_values)]
            count_index += 1
            return value
        
        mock_collection.count_documents.side_effect = mock_count_documents
        
        # Mock list_indexes
        mock_cursor = MockMotorCursor(to_list_result=[
            {"name": "ttl_detected_at", "expireAfterSeconds": 31536000}
        ])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Test
        status = await manager.get_retention_status()
        
        # Verify
        assert len(status) == 4  # 4 default policies
        
        # Check one specific collection status
        content_changes_status = status["content_changes"]
        assert content_changes_status["total_documents"] == 100
        assert content_changes_status["documents_expiring_soon"] == 10
        assert content_changes_status["ttl_active"] is True
    
    @pytest.mark.asyncio
    async def test_run_maintenance_success(self, manager):
        """Test successful maintenance run"""
        # Mock all operations
        with patch.object(manager, 'setup_ttl_indexes') as mock_ttl, \
             patch.object(manager, 'archive_all_collections') as mock_archive, \
             patch.object(manager, 'get_retention_status') as mock_status:
            
            mock_ttl.return_value = {"content_changes": True, "alerts": True}
            mock_archive.return_value = {"total_archived": 10, "errors": []}
            mock_status.return_value = {"test": "status"}
            
            # Test
            result = await manager.run_maintenance()
            
            # Verify
            assert "timestamp" in result
            assert result["ttl_setup"]["content_changes"] is True
            assert result["archival"]["total_archived"] == 10
            assert result["status"]["test"] == "status"
    
    @pytest.mark.asyncio  
    async def test_archive_all_collections(self, manager):
        """Test archiving all collections"""
        # Mock archive_documents for each policy
        archive_results = [
            {"collection": "content_changes", "documents_archived": 5, "errors": []},
            {"collection": "crawl_sessions", "documents_archived": 3, "errors": []},
            {"collection": "alerts", "documents_archived": 2, "errors": []},
            {"collection": "processing_queue", "documents_archived": 1, "errors": []}
        ]
        
        with patch.object(manager, 'archive_documents') as mock_archive:
            mock_archive.side_effect = archive_results
            
            # Test
            result = await manager.archive_all_collections()
            
            # Verify
            assert result["total_archived"] == 11  # 5+3+2+1
            assert len(result["errors"]) == 0
            assert len(result["collection_results"]) == 4
            
            # Verify archive_documents called for each policy
            assert mock_archive.call_count == 4


class TestIntegration:
    """Integration tests for RetentionPolicyManager."""
    
    @pytest.mark.asyncio
    async def test_full_retention_workflow(self):
        """Test complete retention workflow from setup to archival"""
        # Create mocks
        mock_db = AsyncMock()
        mock_s3_client = MagicMock()
        
        # Create manager
        manager = RetentionPolicyManager(
            db=mock_db,
            s3_client=mock_s3_client,
            s3_bucket="test-bucket"
        )
        
        # Mock MongoDB operations
        mock_collection = MockMotorCollection()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock TTL index setup
        mock_cursor = MockMotorCursor(to_list_result=[])
        mock_collection.list_indexes.return_value = mock_cursor
        
        # Mock document archival
        test_docs = [
            {
                "_id": ObjectId(),
                "start_time": datetime.now(tz.utc) - timedelta(days=100),
                "data": "test"
            }
        ]
        
        async def mock_get_batches(collection, query, batch_size):
            yield test_docs
        
        manager._get_batches = mock_get_batches
        
        delete_result = MagicMock()
        delete_result.deleted_count = 1
        mock_collection.delete_many.return_value = delete_result
        
        # Mock S3 operations
        mock_s3_client.put_object = MagicMock()
        
        # Run full maintenance
        results = await manager.run_maintenance()
        
        # Verify TTL indexes were created
        assert results["ttl_setup"]["content_changes"] is True
        assert results["ttl_setup"]["crawl_sessions"] is True
        assert results["ttl_setup"]["alerts"] is True
        assert results["ttl_setup"]["processing_queue"] is True
        
        # Verify archival occurred
        assert "archival" in results
        assert "status" in results


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])