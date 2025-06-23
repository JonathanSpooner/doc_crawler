"""
Unit tests for AuthorWorksRepository

Comprehensive test suite covering all CRUD operations, search methods, 
tag management, duplicate detection, statistics, and batch operations.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from bson import ObjectId

# Import the repository and related models
from doc_crawler.database.repositories.author_works_repository import AuthorWorksRepository
from .repository_utils import mock_database, sample_work_data

class TestAuthorWorksRepository:
    """Test suite for AuthorWorksRepository."""
    
    @pytest.fixture
    def repository(self):
        """Fixture for a mocked AuthorWorksRepository instance."""
        # Here, we create a concrete instance, but then mock its underlying database methods.
        # This is generally better for testing the actual logic of AuthorWorksRepository.
        repo = AuthorWorksRepository(connection_string="mongodb://localhost:27017/", db_name="test_db")
        
        # Mock the specific methods that interact with the database
        # These are inherited from AsyncMongoDBRepository
        repo.insert_one = AsyncMock()
        repo.find_one = AsyncMock()
        repo.find_many = AsyncMock()
        repo.update_one = AsyncMock()
        repo.collection = AsyncMock() # Mock the collection attribute if used directly
        repo.aggregate = AsyncMock()
        repo.delete_many = AsyncMock()
        
        # Mock the internal _validate_object_id to prevent actual ObjectId conversion issues
        # especially if the input strings are not valid.
        # For this test, simply returning the input or a fixed ObjectId is fine.
        repo._validate_object_id = lambda x: ObjectId(x) if ObjectId.is_valid(x) else x
        
        return repo
    
    @pytest.fixture
    def sample_work_document(self, sample_work_data):
        """Sample work document as it would appear in MongoDB."""
        doc = sample_work_data.copy()
        doc["_id"] = ObjectId()
        doc["created_at"] = datetime.now(UTC)
        doc["updated_at"] = datetime.now(UTC)
        return doc

    # Test create_work
    @pytest.mark.asyncio
    async def test_create_work_success(self, repository, sample_work_data):
        """Test successful work creation."""
        repository.find_by_work_id = AsyncMock()
        repository.find_by_work_id.return_value = None
        repository.find_duplicate_work = AsyncMock()
        repository.find_duplicate_work.return_value = None
        repository.insert_one.return_value = "work_id_123"
        
        result = await repository.create_work(sample_work_data)
        
        assert result == "work_id_123"
        repository.insert_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_work_duplicate_work_id(self, repository, sample_work_data):
        """Test work creation with duplicate work_id."""
        repository.find_by_work_id = AsyncMock()
        repository.find_by_work_id.return_value = {"_id": ObjectId()}
        
        with pytest.raises(ValueError, match="Work with work_id .* already exists"):
            await repository.create_work(sample_work_data)
    
    @pytest.mark.asyncio
    async def test_create_work_invalid_data(self, repository):
        """Test work creation with invalid data."""
        invalid_data = {"author_name": ""}  # Missing required fields
        
        with pytest.raises(Exception):  # Pydantic validation error
            await repository.create_work(invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_work_with_duplicate_warning(self, repository, sample_work_data):
        """Test work creation with duplicate detection warning."""
        repository.find_by_work_id = AsyncMock()
        repository.find_by_work_id.return_value = None
        repository.find_duplicate_work = AsyncMock()
        repository.find_duplicate_work.return_value = {"_id": ObjectId()}
        repository.insert_one.return_value = "work_id_123"
        
        result = await repository.create_work(sample_work_data)
        
        assert result == "work_id_123"
        repository.find_duplicate_work.assert_called_once()

    # Test find_by_work_id
    @pytest.mark.asyncio
    async def test_find_by_work_id_found(self, repository, sample_work_document):
        """Test finding work by external work ID."""
        repository.find_one.return_value = sample_work_document
        
        result = await repository.find_by_work_id("aristotle-ethics-1")
        
        assert result == sample_work_document
        repository.find_one.assert_called_once_with({"work_id": "aristotle-ethics-1"})
    
    @pytest.mark.asyncio
    async def test_find_by_work_id_not_found(self, repository):
        """Test finding work by non-existent work ID."""
        repository.find_one.return_value = None
        
        result = await repository.find_by_work_id("non-existent")
        
        assert result is None

    # Test find_by_author
    @pytest.mark.asyncio
    async def test_find_by_author(self, repository, sample_work_document):
        """Test finding works by author."""
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.find_by_author("Aristotle")
        
        assert result == [sample_work_document]
        repository.find_many.assert_called_once()
        call_args = repository.find_many.call_args
        assert call_args[1]["query"]["author_name"]["$regex"] == "^Aristotle$"
        assert call_args[1]["query"]["author_name"]["$options"] == "i"
    
    @pytest.mark.asyncio
    async def test_find_by_author_with_limit(self, repository):
        """Test finding works by author with custom limit."""
        repository.find_many.return_value = []
        
        await repository.find_by_author("Plato", limit=50)
        
        call_args = repository.find_many.call_args
        assert call_args[1]["limit"] == 50

    # Test find_by_site
    @pytest.mark.asyncio
    async def test_find_by_site(self, repository, sample_work_document):
        """Test finding works by site."""
        site_id = str(ObjectId())
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.find_by_site(site_id)
        
        assert result == [sample_work_document]
        repository.find_many.assert_called_once()
        call_args = repository.find_many.call_args
        assert "site_id" in call_args[1]["query"]

    # Test find_by_tags
    @pytest.mark.asyncio
    async def test_find_by_tags_any_match(self, repository, sample_work_document):
        """Test finding works by tags with ANY match."""
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.find_by_tags(["ethics", "virtue"], match_all=False)
        
        assert result == [sample_work_document]
        call_args = repository.find_many.call_args
        assert call_args[1]["query"]["tags"]["$in"] == ["ethics", "virtue"]
    
    @pytest.mark.asyncio
    async def test_find_by_tags_all_match(self, repository, sample_work_document):
        """Test finding works by tags with ALL match."""
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.find_by_tags(["ethics", "virtue"], match_all=True)
        
        assert result == [sample_work_document]
        call_args = repository.find_many.call_args
        assert call_args[1]["query"]["tags"]["$all"] == ["ethics", "virtue"]

    # Test find_duplicate_work
    @pytest.mark.asyncio
    async def test_find_duplicate_work_found(self, repository, sample_work_document):
        """Test finding duplicate work."""
        site_id = str(ObjectId())
        repository.find_one.return_value = sample_work_document
        
        result = await repository.find_duplicate_work("Aristotle", "Nicomachean Ethics", site_id)
        
        assert result == sample_work_document
        call_args = repository.find_one.call_args
        query = call_args[0][0]
        assert query["author_name"]["$regex"] == "^Aristotle$"
        assert query["work_title"]["$regex"] == "^Nicomachean Ethics$"
    
    @pytest.mark.asyncio
    async def test_find_duplicate_work_not_found(self, repository):
        """Test finding duplicate work when none exists."""
        repository.find_one.return_value = None
        site_id = str(ObjectId())
        
        result = await repository.find_duplicate_work("Unknown", "Unknown Work", site_id)
        
        assert result is None

    # Test find_works_by_date_range
    @pytest.mark.asyncio
    async def test_find_works_by_date_range_both_dates(self, repository, sample_work_document):
        """Test finding works by date range with both start and end dates."""
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.find_works_by_date_range("300-BCE", "400-BCE")
        
        assert result == [sample_work_document]
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert query["publication_date"]["$gte"] == "300-BCE"
        assert query["publication_date"]["$lte"] == "400-BCE"
    
    @pytest.mark.asyncio
    async def test_find_works_by_date_range_start_only(self, repository):
        """Test finding works by date range with start date only."""
        repository.find_many.return_value = []
        
        await repository.find_works_by_date_range(start_date="300-BCE")
        
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert query["publication_date"]["$gte"] == "300-BCE"
        assert "$lte" not in query["publication_date"]
    
    @pytest.mark.asyncio
    async def test_find_works_by_date_range_no_dates(self, repository):
        """Test finding works by date range with no date constraints."""
        repository.find_many.return_value = []
        
        await repository.find_works_by_date_range()
        
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert query == {}

    # Test update_work
    @pytest.mark.asyncio
    async def test_update_work_success(self, repository):
        """Test successful work update."""
        repository.update_one.return_value = True
        
        update_data = {"tags": ["updated_tag"]}
        result = await repository.update_work("work_id_123", update_data)
        
        assert result is True
        repository.update_one.assert_called_once()
        call_args = repository.update_one.call_args
        assert "updated_at" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_update_work_invalid_data(self, repository):
        """Test work update with invalid data."""
        # Invalid data that would fail Pydantic validation
        invalid_update = {"author_name": None}
        
        with pytest.raises(ValueError, match="Invalid update data"):
            await repository.update_work("work_id_123", invalid_update)

    # Test tag management
    @pytest.mark.asyncio
    async def test_add_tags_to_work(self, repository):
        """Test adding tags to a work."""
        work_id = str(ObjectId())
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.collection.update_one.return_value = mock_result
        
        result = await repository.add_tags_to_work(work_id, ["new_tag", "another_tag"])
        
        assert result is True
        repository.collection.update_one.assert_called_once()
        call_args = repository.collection.update_one.call_args
        update_op = call_args[0][1]
        assert "$addToSet" in update_op
        assert update_op["$addToSet"]["tags"]["$each"] == ["new_tag", "another_tag"]
    
    @pytest.mark.asyncio
    async def test_remove_tags_from_work(self, repository):
        """Test removing tags from a work."""
        work_id = str(ObjectId())
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.collection.update_one.return_value = mock_result
        
        result = await repository.remove_tags_from_work(work_id, ["old_tag"])
        
        assert result is True
        repository.collection.update_one.assert_called_once()
        call_args = repository.collection.update_one.call_args
        update_op = call_args[0][1]
        assert "$pullAll" in update_op
        assert update_op["$pullAll"]["tags"] == ["old_tag"]

    # Test bulk_update_tags
    @pytest.mark.asyncio
    async def test_bulk_update_tags_add_only(self, repository):
        """Test bulk updating tags with add operation only."""
        work_ids = [str(ObjectId()), str(ObjectId())]
        mock_result = MagicMock()
        mock_result.modified_count = 2
        repository.collection.update_many.return_value = mock_result
        
        result = await repository.bulk_update_tags(work_ids, tags_to_add=["bulk_tag"])
        
        assert result == 2
        repository.collection.update_many.assert_called_once()
        call_args = repository.collection.update_many.call_args
        update_op = call_args[0][1]
        assert "$addToSet" in update_op
        assert update_op["$addToSet"]["tags"]["$each"] == ["bulk_tag"]
    
    @pytest.mark.asyncio
    async def test_bulk_update_tags_no_changes(self, repository):
        """Test bulk updating tags with no operations."""
        work_ids = [str(ObjectId())]
        
        result = await repository.bulk_update_tags(work_ids)
        
        assert result == 0
        repository.collection.update_many.assert_not_called()

    # Test get_authors_list
    @pytest.mark.asyncio
    async def test_get_authors_list(self, repository):
        """Test getting list of unique authors."""
        mock_authors = [{"author": "Aristotle"}, {"author": "Plato"}]
        repository.aggregate.return_value = mock_authors
        
        result = await repository.get_authors_list()
        
        assert result == ["Aristotle", "Plato"]
        repository.aggregate.assert_called_once()
        pipeline = repository.aggregate.call_args[0][0]
        assert len(pipeline) == 4  # group, sort, limit, project

    # Test get_author_statistics
    @pytest.mark.asyncio
    async def test_get_author_statistics(self, repository):
        """Test getting author statistics."""
        mock_stats = [
            {
                "author": "Aristotle",
                "work_count": 10,
                "site_count": 2,
                "earliest_work": "350-BCE",
                "latest_work": "320-BCE"
            },
            {
                "author": "Plato",
                "work_count": 8,
                "site_count": 1,
                "earliest_work": "380-BCE",
                "latest_work": "360-BCE"
            }
        ]
        repository.aggregate.return_value = mock_stats
        
        result = await repository.get_author_statistics()
        
        assert result["total_authors"] == 2
        assert result["total_works"] == 18
        assert result["average_works_per_author"] == 9.0
        assert len(result["top_authors"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_author_statistics_empty(self, repository):
        """Test getting author statistics with no authors."""
        repository.aggregate.return_value = []
        
        result = await repository.get_author_statistics()
        
        assert result["total_authors"] == 0
        assert result["total_works"] == 0
        assert result["average_works_per_author"] == 0

    # Test get_site_statistics
    @pytest.mark.asyncio
    async def test_get_site_statistics(self, repository):
        """Test getting site statistics."""
        mock_stats = [
            {
                "site_id": ObjectId(),
                "work_count": 100,
                "author_count": 20,
                "latest_addition": datetime.now(UTC)
            }
        ]
        repository.aggregate.return_value = mock_stats
        
        result = await repository.get_site_statistics()
        
        assert result == mock_stats
        repository.aggregate.assert_called_once()

    # Test find_works_needing_work_id
    @pytest.mark.asyncio
    async def test_find_works_needing_work_id(self, repository, sample_work_document):
        """Test finding works that need work_id assignment."""
        works_without_id = [sample_work_document]
        repository.find_many.return_value = works_without_id
        
        result = await repository.find_works_needing_work_id()
        
        assert result == works_without_id
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert "$or" in query
        assert len(query["$or"]) == 3  # None, not exists, empty string

    # Test search_works
    @pytest.mark.asyncio
    async def test_search_works_default_fields(self, repository, sample_work_document):
        """Test searching works with default fields."""
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.search_works("Aristotle")
        
        assert result == [sample_work_document]
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert "$or" in query
        assert len(query["$or"]) == 2  # author_name and work_title
    
    @pytest.mark.asyncio
    async def test_search_works_custom_fields(self, repository):
        """Test searching works with custom fields."""
        repository.find_many.return_value = []
        
        await repository.search_works("ethics", fields=["tags", "work_title"])
        
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert len(query["$or"]) == 2  # tags and work_title

    # Test get_works_by_page_ids
    @pytest.mark.asyncio
    async def test_get_works_by_page_ids(self, repository, sample_work_document):
        """Test getting works by page IDs."""
        page_ids = [str(ObjectId()), str(ObjectId())]
        repository.find_many.return_value = [sample_work_document]
        
        result = await repository.get_works_by_page_ids(page_ids)
        
        assert result == [sample_work_document]
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert "page_id" in query
        assert "$in" in query["page_id"]

    # Test delete_works_by_site
    @pytest.mark.asyncio
    async def test_delete_works_by_site(self, repository):
        """Test deleting works by site."""
        site_id = str(ObjectId())
        repository.delete_many.return_value = 5
        
        result = await repository.delete_works_by_site(site_id)
        
        assert result == 5
        repository.delete_many.assert_called_once()

    # Test error scenarios
    @pytest.mark.asyncio
    async def test_create_work_database_error(self, repository, sample_work_data):
        """Test work creation with database error."""
        repository.find_by_work_id = AsyncMock()
        repository.find_by_work_id.return_value = None
        repository.find_duplicate_work = AsyncMock()
        repository.find_duplicate_work.return_value = None
        repository.insert_one.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await repository.create_work(sample_work_data)
    
    @pytest.mark.asyncio
    async def test_add_tags_no_modification(self, repository):
        """Test adding tags when no modification occurs."""
        work_id = str(ObjectId())
        mock_result = MagicMock()
        mock_result.modified_count = 0
        repository.collection.update_one.return_value = mock_result
        
        result = await repository.add_tags_to_work(work_id, ["existing_tag"])
        
        assert result is False

    # Test edge cases
    @pytest.mark.asyncio
    async def test_find_by_author_empty_result(self, repository):
        """Test finding works by author with no results."""
        repository.find_many.return_value = []
        
        result = await repository.find_by_author("NonExistentAuthor")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_search_works_empty_search_term(self, repository):
        """Test searching with empty search term."""
        repository.find_many.return_value = []
        
        result = await repository.search_works("")
        
        assert result == []
        # Should still make the query but with empty regex
        repository.find_many.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_bulk_update_tags_both_operations(self, repository):
        """Test bulk updating tags with both add and remove operations."""
        work_ids = [str(ObjectId())]
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.collection.update_many.return_value = mock_result
        
        result = await repository.bulk_update_tags(
            work_ids, 
            tags_to_add=["new_tag"], 
            tags_to_remove=["old_tag"]
        )
        
        assert result == 1
        call_args = repository.collection.update_many.call_args
        update_op = call_args[0][1]
        assert "$addToSet" in update_op
        assert "$pullAll" in update_op

    # Test validation edge cases
    @pytest.mark.asyncio
    async def test_update_work_partial_validation(self, repository):
        """Test work update with partial data validation."""
        repository.update_one.return_value = True
        
        # Valid partial update
        update_data = {"tags": ["philosophy", "ethics"]}
        result = await repository.update_work("work_id_123", update_data)
        
        assert result is True
    
    @pytest.mark.asyncio 
    async def test_find_works_by_date_range_edge_dates(self, repository):
        """Test finding works with edge case dates."""
        repository.find_many.return_value = []
        
        # Test with very old dates
        await repository.find_works_by_date_range("1000-BCE", "1-CE")
        
        call_args = repository.find_many.call_args
        query = call_args[1]["query"]
        assert query["publication_date"]["$gte"] == "1000-BCE"
        assert query["publication_date"]["$lte"] == "1-CE"


# Integration test helpers
class TestAuthorWorksRepositoryIntegration:
    """Integration-style tests that test method interactions."""
    
    @pytest_asyncio.fixture
    async def repository(self):
        """Create repository with more realistic mocking."""
        with patch('doc_crawler.database.repositories.author_works_repository.AsyncMongoDBRepository.__init__'):
            repo = AuthorWorksRepository(
                connection_string="mongodb://test:27017",
                db_name="test_db"
            )
            
            repo.collection = AsyncMock()
            repo.db = AsyncMock()
            repo._validate_object_id = MagicMock(side_effect=lambda x: ObjectId(x) if isinstance(x, str) else x)
            
            return repo
    
    @pytest.mark.asyncio
    async def test_create_and_find_workflow(self, repository, sample_work_data):
        """Test complete workflow of creating and finding a work."""
        # Mock the create workflow
        repository.find_one = AsyncMock(side_effect=[
            None,  # find_by_work_id returns None (no duplicate)
            None,  # find_duplicate_work returns None
            sample_work_data  # Later find_by_work_id returns the created work
        ])
        repository.insert_one = AsyncMock(return_value="work_id_123")
        
        # Create the work
        work_id = await repository.create_work(sample_work_data)
        assert work_id == "work_id_123"
        
        # Find the work
        found_work = await repository.find_by_work_id(sample_work_data["work_id"])
        assert found_work == sample_work_data


# Test fixtures and utilities
@pytest.fixture
def mock_object_id():
    """Generate a mock ObjectId for testing."""
    return ObjectId()


@pytest.fixture
def sample_aggregation_result():
    """Sample aggregation result for statistics tests."""
    return [
        {
            "author": "Aristotle",
            "work_count": 15,
            "site_count": 3,
            "earliest_work": "350-BCE",
            "latest_work": "320-BCE"
        },
        {
            "author": "Plato", 
            "work_count": 12,
            "site_count": 2,
            "earliest_work": "380-BCE",
            "latest_work": "360-BCE"
        }
    ]


# Run tests with: python -m pytest test_author_works_repository.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])