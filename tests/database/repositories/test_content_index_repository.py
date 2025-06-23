"""
Unit tests for ContentIndexRepository

Tests all methods in the ContentIndexRepository class with comprehensive
coverage including success cases, error handling, and edge cases.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, UTC
from typing import Dict, List, Any
from bson import ObjectId

# Import the classes to test
from doc_crawler.database.repositories.content_index_repository import ContentIndexRepository
from doc_crawler.database.models.content_index import ContentIndex


@pytest.fixture
def mock_connection_string():
    """Mock MongoDB connection string."""
    return "mongodb://localhost:27017"


@pytest.fixture
def mock_db_name():
    """Mock database name."""
    return "test_philosophy_db"


@pytest.fixture
def content_index_repo(mock_connection_string, mock_db_name):
    """Create ContentIndexRepository instance with mocked dependencies."""
    with patch('doc_crawler.database.repositories.content_index_repository.AsyncMongoDBRepository.__init__') as mock_init:
        mock_init.return_value = None
        repo = ContentIndexRepository(mock_connection_string, mock_db_name)
        # Mock inherited methods
        repo.insert_one = AsyncMock()
        repo.find_one = AsyncMock()
        repo.find_many = AsyncMock()
        repo.update_one = AsyncMock()
        repo.delete_one = AsyncMock()
        repo.delete_many = AsyncMock()
        repo.aggregate = AsyncMock()
        repo.get_collection_stats = AsyncMock()
        repo._generate_content_hash = Mock()
        repo._convert_object_ids = Mock()
        return repo


@pytest.fixture
def sample_content_index():
    """Create a sample ContentIndex instance."""
    return ContentIndex(
        page_id="507f1f77bcf86cd799439011",
        search_content="This is a sample philosophical text about consciousness and reality.",
        metadata={
            "author": "John Doe",
            "title": "On Consciousness",
            "publication_date": "2023"
        }
    )


@pytest.fixture
def sample_content_dict():
    """Create a sample content index dictionary."""
    return {
        "_id": "507f1f77bcf86cd799439012",
        "page_id": "507f1f77bcf86cd799439011",
        "search_content": "This is a sample philosophical text about consciousness and reality.",
        "metadata": {
            "author": "John Doe",
            "title": "On Consciousness",
            "publication_date": "2023"
        },
        "indexed_at": datetime.now(UTC),
        "content_hash": "abc123hash"
    }


class TestContentIndexRepository:
    """Test cases for ContentIndexRepository."""

    @pytest.mark.asyncio
    async def test_create_content_index_success(self, content_index_repo, sample_content_index):
        """Test successful creation of content index."""
        # Setup
        expected_id = "507f1f77bcf86cd799439012"
        content_index_repo.insert_one.return_value = expected_id
        content_index_repo._generate_content_hash.return_value = "abc123hash"
        
        # Execute
        result = await content_index_repo.create_content_index(sample_content_index)
        
        # Assert
        assert result == expected_id
        content_index_repo.insert_one.assert_called_once()
        content_index_repo._generate_content_hash.assert_called_once()
        
        # Verify the document structure passed to insert_one
        call_args = content_index_repo.insert_one.call_args
        document = call_args[0][0]
        assert 'page_id' in document
        assert 'search_content' in document
        assert 'metadata' in document
        assert 'content_hash' in document
        assert 'indexed_at' in document

    @pytest.mark.asyncio
    async def test_create_content_index_failure(self, content_index_repo, sample_content_index):
        """Test content index creation failure."""
        # Setup
        content_index_repo.insert_one.side_effect = Exception("Database error")
        content_index_repo._generate_content_hash.return_value = "abc123hash"
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.create_content_index(sample_content_index)
        
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_page_id_found(self, content_index_repo, sample_content_dict):
        """Test successful retrieval of content index by page ID."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.find_one.return_value = sample_content_dict
        content_index_repo._convert_object_ids.return_value = sample_content_dict
        
        # Execute
        result = await content_index_repo.get_by_page_id(page_id)
        
        # Assert
        assert result == sample_content_dict
        content_index_repo.find_one.assert_called_once_with({"page_id": page_id})
        content_index_repo._convert_object_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_page_id_not_found(self, content_index_repo):
        """Test content index retrieval when not found."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.find_one.return_value = None
        
        # Execute
        result = await content_index_repo.get_by_page_id(page_id)
        
        # Assert
        assert result is None
        content_index_repo.find_one.assert_called_once_with({"page_id": page_id})

    @pytest.mark.asyncio
    async def test_get_by_page_id_failure(self, content_index_repo):
        """Test content index retrieval failure."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.find_one.side_effect = Exception("Database error")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_by_page_id(page_id)
        
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_content_index_success(self, content_index_repo):
        """Test successful content index update."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        update_data = {"search_content": "Updated content"}
        content_index_repo.update_one.return_value = True
        content_index_repo._generate_content_hash.return_value = "newhash123"
        
        # Execute
        result = await content_index_repo.update_content_index(page_id, update_data)
        
        # Assert
        assert result is True
        content_index_repo.update_one.assert_called_once()
        call_args = content_index_repo.update_one.call_args
        assert call_args[0][0] == {"page_id": page_id}
        updated_data = call_args[0][1]
        assert 'indexed_at' in updated_data
        assert 'content_hash' in updated_data

    @pytest.mark.asyncio
    async def test_update_content_index_not_found(self, content_index_repo):
        """Test content index update when document not found."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        update_data = {"search_content": "Updated content"}
        content_index_repo.update_one.return_value = False
        content_index_repo._generate_content_hash.return_value = "newhash123"
        
        # Execute
        result = await content_index_repo.update_content_index(page_id, update_data)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_upsert_content_index_update_existing(self, content_index_repo, sample_content_index, sample_content_dict):
        """Test upsert when content index already exists (update case)."""
        # Setup
        content_index_repo.get_by_page_id = AsyncMock(return_value=sample_content_dict)
        content_index_repo.update_content_index = AsyncMock(return_value=True)
        
        # Execute
        result = await content_index_repo.upsert_content_index(sample_content_index)
        
        # Assert
        assert result == sample_content_dict["_id"]
        content_index_repo.get_by_page_id.assert_called_once()
        content_index_repo.update_content_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_content_index_create_new(self, content_index_repo, sample_content_index):
        """Test upsert when content index doesn't exist (create case)."""
        # Setup
        new_id = "507f1f77bcf86cd799439013"
        content_index_repo.get_by_page_id = AsyncMock(return_value=None)
        content_index_repo.create_content_index = AsyncMock(return_value=new_id)
        
        # Execute
        result = await content_index_repo.upsert_content_index(sample_content_index)
        
        # Assert
        assert result == new_id
        content_index_repo.get_by_page_id.assert_called_once()
        content_index_repo.create_content_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_content_success(self, content_index_repo, sample_content_dict):
        """Test successful content search."""
        # Setup
        search_terms = ["consciousness", "reality"]
        metadata_filters = {"author": "John Doe"}
        expected_results = [sample_content_dict]
        
        content_index_repo.find_many.return_value = expected_results
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute
        result = await content_index_repo.search_content(
            search_terms=search_terms,
            metadata_filters=metadata_filters,
            limit=50,
            skip=0
        )
        
        # Assert
        assert result == expected_results
        content_index_repo.find_many.assert_called_once()
        
        # Verify query structure
        call_args = content_index_repo.find_many.call_args
        query = call_args[1]["query"]
        assert "$text" in query
        assert query["$text"]["$search"] == "consciousness reality"
        assert query["metadata.author"] == "John Doe"

    @pytest.mark.asyncio
    async def test_search_content_no_metadata_filters(self, content_index_repo, sample_content_dict):
        """Test content search without metadata filters."""
        # Setup
        search_terms = ["consciousness"]
        expected_results = [sample_content_dict]
        
        content_index_repo.find_many.return_value = expected_results
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute
        result = await content_index_repo.search_content(search_terms=search_terms)
        
        # Assert
        assert result == expected_results
        call_args = content_index_repo.find_many.call_args
        query = call_args[1]["query"]
        assert "$text" in query
        assert len(query) == 1  # Only text search, no metadata filters

    @pytest.mark.asyncio
    async def test_get_by_author_success(self, content_index_repo, sample_content_dict):
        """Test successful retrieval by author."""
        # Setup
        author = "John Doe"
        expected_results = [sample_content_dict]
        
        content_index_repo.find_many.return_value = expected_results
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute
        result = await content_index_repo.get_by_author(author, limit=50)
        
        # Assert
        assert result == expected_results
        content_index_repo.find_many.assert_called_once()
        
        # Verify query
        call_args = content_index_repo.find_many.call_args
        query = call_args[1]["query"]
        assert "metadata.author" in query
        assert query["metadata.author"]["$regex"] == author
        assert query["metadata.author"]["$options"] == "i"

    @pytest.mark.asyncio
    async def test_get_recent_content_success(self, content_index_repo, sample_content_dict):
        """Test successful retrieval of recent content."""
        # Setup
        expected_results = [sample_content_dict]
        content_index_repo.find_many.return_value = expected_results
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute
        result = await content_index_repo.get_recent_content(hours=24, limit=100)
        
        # Assert
        assert result == expected_results
        content_index_repo.find_many.assert_called_once()
        
        # Verify query has time filter
        call_args = content_index_repo.find_many.call_args
        query = call_args[1]["query"]
        assert "indexed_at" in query
        assert "$gte" in query["indexed_at"]

    @pytest.mark.asyncio
    async def test_get_metadata_facets_success(self, content_index_repo):
        """Test successful retrieval of metadata facets."""
        # Setup
        aggregation_results = [
            {"_id": "author", "values": ["John Doe", "Jane Smith"]},
            {"_id": "publication_date", "values": ["2022", "2023"]},
            {"_id": None, "values": ["ignored"]}  # Should be filtered out
        ]
        content_index_repo.aggregate.return_value = aggregation_results
        
        # Execute
        result = await content_index_repo.get_metadata_facets()
        
        # Assert
        expected_facets = {
            "author": ["Jane Smith", "John Doe"],  # Should be sorted
            "publication_date": ["2022", "2023"]
        }
        assert result == expected_facets
        content_index_repo.aggregate.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_statistics_success(self, content_index_repo):
        """Test successful retrieval of content statistics."""
        # Setup
        aggregation_results = [{
            "total_documents": 100,
            "avg_content_length": 500.5,
            "total_content_length": 50050,
            "unique_author_count": 25,
            "earliest_indexed": datetime(2023, 1, 1),
            "latest_indexed": datetime(2023, 12, 31)
        }]
        collection_stats = {"storage_size": 1024000, "index_size": 256000}
        
        content_index_repo.aggregate.return_value = aggregation_results
        content_index_repo.get_collection_stats.return_value = collection_stats
        
        # Execute
        result = await content_index_repo.get_content_statistics()
        
        # Assert
        expected_stats = {**aggregation_results[0], **collection_stats}
        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_get_content_statistics_empty_collection(self, content_index_repo):
        """Test content statistics with empty collection."""
        # Setup
        content_index_repo.aggregate.return_value = []
        content_index_repo.get_collection_stats.return_value = {"storage_size": 0}
        
        # Execute
        result = await content_index_repo.get_content_statistics()
        
        # Assert
        assert result == {"storage_size": 0}

    @pytest.mark.asyncio
    async def test_delete_by_page_id_success(self, content_index_repo):
        """Test successful deletion by page ID."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.delete_one.return_value = True
        
        # Execute
        result = await content_index_repo.delete_by_page_id(page_id)
        
        # Assert
        assert result is True
        content_index_repo.delete_one.assert_called_once_with({"page_id": page_id})

    @pytest.mark.asyncio
    async def test_delete_by_page_id_not_found(self, content_index_repo):
        """Test deletion when page ID not found."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.delete_one.return_value = False
        
        # Execute
        result = await content_index_repo.delete_by_page_id(page_id)
        
        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_entries_success(self, content_index_repo):
        """Test successful cleanup of orphaned entries."""
        # Setup
        valid_page_ids = ["id1", "id2", "id3"]
        deleted_count = 5
        content_index_repo.delete_many.return_value = deleted_count
        
        # Execute
        result = await content_index_repo.cleanup_orphaned_entries(valid_page_ids)
        
        # Assert
        assert result == deleted_count
        content_index_repo.delete_many.assert_called_once()
        
        # Verify query
        call_args = content_index_repo.delete_many.call_args
        query = call_args[0][0]
        assert query == {"page_id": {"$nin": valid_page_ids}}

    @pytest.mark.asyncio
    async def test_get_duplicate_content_success(self, content_index_repo, sample_content_dict):
        """Test successful retrieval of duplicate content."""
        # Setup
        content_hash = "abc123hash"
        expected_results = [sample_content_dict, sample_content_dict.copy()]
        
        content_index_repo.find_many.return_value = expected_results
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute
        result = await content_index_repo.get_duplicate_content(content_hash)
        
        # Assert
        assert result == expected_results
        content_index_repo.find_many.assert_called_once_with({"content_hash": content_hash})

    @pytest.mark.asyncio
    async def test_update_search_content_success(self, content_index_repo):
        """Test successful update of search content."""
        # Setup
        page_id = "507f1f77bcf86cd799439011"
        search_content = "New search content"
        content_index_repo.update_content_index = AsyncMock(return_value=True)
        content_index_repo._generate_content_hash.return_value = "newhash456"
        
        # Execute
        result = await content_index_repo.update_search_content(page_id, search_content)
        
        # Assert
        assert result is True
        content_index_repo.update_content_index.assert_called_once()
        
        # Verify update data
        call_args = content_index_repo.update_content_index.call_args
        update_data = call_args[0][1]
        assert update_data['search_content'] == search_content
        assert 'content_hash' in update_data
        assert 'indexed_at' in update_data

    @pytest.mark.asyncio
    async def test_bulk_upsert_content_indexes_success(self, content_index_repo, sample_content_index):
        """Test successful bulk upsert of content indexes."""
        # Setup
        content_indexes = [sample_content_index for _ in range(3)]
        returned_ids = ["id1", "id2", "id3"]
        
        content_index_repo.upsert_content_index = AsyncMock()
        content_index_repo.upsert_content_index.side_effect = returned_ids
        
        # Execute
        result = await content_index_repo.bulk_upsert_content_indexes(content_indexes)
        
        # Assert
        assert result == returned_ids
        assert content_index_repo.upsert_content_index.call_count == 3

    @pytest.mark.asyncio
    async def test_bulk_upsert_content_indexes_large_batch(self, content_index_repo, sample_content_index):
        """Test bulk upsert with large batch (tests batching logic)."""
        # Setup - Create 250 items to test batching (batch_size=100)
        content_indexes = [sample_content_index for _ in range(250)]
        returned_ids = [f"id{i}" for i in range(250)]
        
        content_index_repo.upsert_content_index = AsyncMock()
        content_index_repo.upsert_content_index.side_effect = returned_ids
        
        # Execute
        result = await content_index_repo.bulk_upsert_content_indexes(content_indexes)
        
        # Assert
        assert result == returned_ids
        assert content_index_repo.upsert_content_index.call_count == 250

    @pytest.mark.asyncio
    async def test_bulk_upsert_content_indexes_failure(self, content_index_repo, sample_content_index):
        """Test bulk upsert failure handling."""
        # Setup
        content_indexes = [sample_content_index]
        content_index_repo.upsert_content_index = AsyncMock(side_effect=Exception("Upsert failed"))
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.bulk_upsert_content_indexes(content_indexes)
        
        assert "Upsert failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_content_failure(self, content_index_repo):
        """Test search content failure handling."""
        # Setup
        content_index_repo.find_many.side_effect = Exception("Search failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.search_content(["test"])
        
        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_author_failure(self, content_index_repo):
        """Test get by author failure handling."""
        # Setup
        content_index_repo.find_many.side_effect = Exception("Query failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_by_author("John Doe")
        
        assert "Query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_recent_content_failure(self, content_index_repo):
        """Test get recent content failure handling."""
        # Setup
        content_index_repo.find_many.side_effect = Exception("Query failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_recent_content()
        
        assert "Query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_metadata_facets_failure(self, content_index_repo):
        """Test get metadata facets failure handling."""
        # Setup
        content_index_repo.aggregate.side_effect = Exception("Aggregation failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_metadata_facets()
        
        assert "Aggregation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_content_statistics_failure(self, content_index_repo):
        """Test get content statistics failure handling."""
        # Setup
        content_index_repo.aggregate.side_effect = Exception("Stats failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_content_statistics()
        
        assert "Stats failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_by_page_id_failure(self, content_index_repo):
        """Test delete by page ID failure handling."""
        # Setup
        content_index_repo.delete_one.side_effect = Exception("Delete failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.delete_by_page_id("test_id")
        
        assert "Delete failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_entries_failure(self, content_index_repo):
        """Test cleanup orphaned entries failure handling."""
        # Setup
        content_index_repo.delete_many.side_effect = Exception("Cleanup failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.cleanup_orphaned_entries(["id1", "id2"])
        
        assert "Cleanup failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_duplicate_content_failure(self, content_index_repo):
        """Test get duplicate content failure handling."""
        # Setup
        content_index_repo.find_many.side_effect = Exception("Query failed")
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.get_duplicate_content("hash123")
        
        assert "Query failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_search_content_failure(self, content_index_repo):
        """Test update search content failure handling."""
        # Setup
        content_index_repo.update_content_index = AsyncMock(side_effect=Exception("Update failed"))
        content_index_repo._generate_content_hash.return_value = "hash123"
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.update_search_content("page_id", "content")
        
        assert "Update failed" in str(exc_info.value)

    def test_repository_initialization(self, mock_connection_string, mock_db_name):
        """Test repository initialization with correct parameters."""
        with patch('doc_crawler.database.repositories.content_index_repository.AsyncMongoDBRepository.__init__') as mock_init:
            mock_init.return_value = None
            
            repo = ContentIndexRepository(mock_connection_string, mock_db_name, max_pool_size=200)
            
            # Verify parent constructor was called with correct parameters
            mock_init.assert_called_once_with(
                connection_string=mock_connection_string,
                db_name=mock_db_name,
                collection_name="content_index",
                max_pool_size=200
            )

    @pytest.mark.asyncio
    async def test_upsert_content_index_failure(self, content_index_repo, sample_content_index):
        """Test upsert content index failure handling."""
        # Setup
        content_index_repo.get_by_page_id = AsyncMock(side_effect=Exception("Database error"))
        
        # Execute & Assert
        with pytest.raises(Exception) as exc_info:
            await content_index_repo.upsert_content_index(sample_content_index)
        
        assert "Database error" in str(exc_info.value)


# Integration-style tests that test multiple operations together
class TestContentIndexRepositoryIntegration:
    """Integration-style tests for ContentIndexRepository."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_workflow(self, content_index_repo, sample_content_index, sample_content_dict):
        """Test the complete workflow of creating and retrieving content index."""
        # Setup create
        created_id = "507f1f77bcf86cd799439012"
        content_index_repo.insert_one.return_value = created_id
        content_index_repo._generate_content_hash.return_value = "abc123hash"
        
        # Setup retrieve
        content_index_repo.find_one.return_value = sample_content_dict
        content_index_repo._convert_object_ids.return_value = sample_content_dict
        
        # Execute create
        result_id = await content_index_repo.create_content_index(sample_content_index)
        assert result_id == created_id
        
        # Execute retrieve
        retrieved = await content_index_repo.get_by_page_id(sample_content_index.page_id)
        assert retrieved == sample_content_dict

    @pytest.mark.asyncio
    async def test_update_and_search_workflow(self, content_index_repo, sample_content_dict):
        """Test updating content and then searching for it."""
        # Setup update
        page_id = "507f1f77bcf86cd799439011"
        content_index_repo.update_one.return_value = True
        content_index_repo._generate_content_hash.return_value = "newhash123"
        
        # Setup search
        updated_dict = sample_content_dict.copy()
        updated_dict['search_content'] = "Updated philosophical content"
        content_index_repo.find_many.return_value = [updated_dict]
        content_index_repo._convert_object_ids.side_effect = lambda x: x
        
        # Execute update
        update_result = await content_index_repo.update_content_index(
            page_id, 
            {"search_content": "Updated philosophical content"}
        )
        assert update_result is True
        
        # Execute search
        search_results = await content_index_repo.search_content(["philosophical"])
        assert len(search_results) == 1
        assert search_results[0]['search_content'] == "Updated philosophical content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])