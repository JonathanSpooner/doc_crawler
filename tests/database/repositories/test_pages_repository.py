"""
Unit tests for PagesRepository.

Tests content storage, URL normalization, deduplication, processing status,
and bulk operations functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC
from bson import ObjectId
import hashlib
from pydantic_core import PydanticCustomError 

from doc_crawler.database.repositories.pages_repository import PagesRepository, PageCreate, PageStats
from doc_crawler.database.exceptions import DuplicateResourceError
from ..repositories.repository_utils import mock_database, mock_sites_repository, sample_object_ids, simulate_db_error


class TestPagesRepository:
    """Test suite for PagesRepository."""
    
    @pytest.fixture
    async def repository(self, mock_database, mock_sites_repository):
        """Create PagesRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['pages']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid
            mock_base.return_value._generate_content_hash = lambda self, content: hashlib.sha256(content.encode()).hexdigest()

            with patch.object(PagesRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await PagesRepository.create("mongodb://test", "test_db", mock_sites_repository)
                
                repo.collection = mock_database['pages']
                repo.db = mock_database
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.update_many = AsyncMock()
                repo.find_many = AsyncMock()
                repo.aggregate = AsyncMock()
                
                return repo
    
    @pytest.fixture
    def sample_page_create(self, sample_object_ids):
        """Create sample PageCreate object."""
        return PageCreate(
            site_id=sample_object_ids['site_id_1'],
            url='https://example.com/test-article',
            title='Test Philosophical Article',
            content='This is test content about philosophical concepts.',
            author='Test Author',
            published_date=datetime(2024, 1, 10)
        )
    
    
    async def test_create_page_success(self, repository, sample_page_create, sample_object_ids):
        """Test successful page creation."""
        # Setup
        repository.sites_repository.get_crawl_configuration.return_value = {'site_id': 'test'}
        repository.find_one.return_value = None  # No existing page
        repository.insert_one.return_value = sample_object_ids['page_id_1']
        
        # Execute
        result = await repository.create_page(sample_page_create)
        
        # Assert
        assert result == sample_object_ids['page_id_1']
        repository.insert_one.assert_called_once()
        
        # Verify inserted data
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['url'] == 'https://example.com/test-article'
        assert call_args['title'] == 'Test Philosophical Article'
        assert call_args['processing_status'] == 'pending'
        assert 'content_hash' in call_args
    
    
    async def test_create_page_duplicate_url(self, repository, sample_page_create, sample_object_ids):
        """Test page creation with duplicate URL."""
        # Setup
        repository.sites_repository.get_crawl_configuration.return_value = {'site_id': 'test'}
        repository.find_one.return_value = {'_id': sample_object_ids['page_id_1']}  # Existing page
        
        # Execute & Assert
        with pytest.raises(DuplicateResourceError) as exc_info:
            await repository.create_page(sample_page_create)
        
        assert "already exists" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    
    async def test_create_page_invalid_site(self, repository, sample_page_create):
        """Test page creation with invalid site."""
        # Setup
        repository.sites_repository.get_crawl_configuration.return_value = None
        
        # Execute & Assert
        with pytest.raises(PydanticCustomError) as exc_info:
            await repository.create_page(sample_page_create)
        
        assert "not found" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    def test_normalize_url(self, repository):
        """Test URL normalization."""
        # Test cases
        test_cases = [
            ('https://example.com/path/', 'https://example.com/path'),
            ('https://example.com/path?query=1', 'https://example.com/path?query=1'),
            ('https://example.com/path#fragment', 'https://example.com/path'),
            ('https://example.com/path/?query=1#fragment', 'https://example.com/path?query=1')
        ]
        
        for input_url, expected in test_cases:
            result = repository._normalize_url(input_url)
            assert result == expected
    
    
    async def test_get_page_by_url_found(self, repository, sample_object_ids):
        """Test finding page by URL."""
        # Setup
        mock_page = {
            '_id': sample_object_ids['page_id_1'],
            'site_id': sample_object_ids['site_id_1'],
            'url': 'https://example.com/article',
            'title': 'Test Article',
            'processing_status': 'processed'
        }
        repository.find_one.return_value = mock_page
        
        # Execute
        result = await repository.get_page_by_url('https://example.com/article')
        
        # Assert
        assert result is not None
        assert result.id == sample_object_ids['page_id_1']
        assert result.title == 'Test Article'
    
    
    async def test_get_page_by_url_not_found(self, repository):
        """Test finding non-existent page by URL."""
        # Setup
        repository.find_one.return_value = None
        
        # Execute
        result = await repository.get_page_by_url('https://example.com/nonexistent')
        
        # Assert
        assert result is None
    
    
    async def test_update_page_content(self, repository, sample_object_ids):
        """Test updating page content."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        new_content = "Updated philosophical content"
        new_hash = "new_hash_123"
        
        # Execute
        result = await repository.update_page_content(
            sample_object_ids['page_id_1'], 
            new_content, 
            new_hash
        )
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify update data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['content'] == new_content
        assert update_data['content_hash'] == new_hash
        assert update_data['processing_status'] == 'pending'
    
    
    async def test_get_pages_by_site(self, repository, sample_object_ids):
        """Test retrieving pages by site."""
        # Setup
        mock_pages = [
            {
                '_id': sample_object_ids['page_id_1'],
                'site_id': sample_object_ids['site_id_1'],
                'url': 'https://example.com/page1',
                'title': 'Page 1',
                'processing_status': 'processed'
            },
            {
                '_id': sample_object_ids['page_id_2'],
                'site_id': sample_object_ids['site_id_1'],
                'url': 'https://example.com/page2',
                'title': 'Page 2',
                'processing_status': 'pending'
            }
        ]
        repository.find_many.return_value = mock_pages
        # Execute
        result = await repository.get_pages_by_site(sample_object_ids['site_id_1'])
        
        # Assert
        assert len(result) == 2
        assert result[0].title == 'Page 1'
        assert result[1].title == 'Page 2'
        
        # Verify query
        call_args = repository.find_many.call_args
        assert call_args[0][0]['site_id'] == sample_object_ids['site_id_1']
    
    
    async def test_get_pages_modified_since(self, repository, sample_object_ids):
        """Test retrieving pages modified since specific time."""
        # Setup
        since_time = datetime.now(UTC) - timedelta(hours=24)
        mock_pages = [
            {
                '_id': sample_object_ids['page_id_1'],
                'site_id': sample_object_ids['site_id_1'],
                'url': 'https://example.com/page1',
                'last_modified': datetime.now(UTC)
            }
        ]
        repository.find_many.return_value = mock_pages
        
        # Execute
        result = await repository.get_pages_modified_since(sample_object_ids['site_id_1'], since_time)
        
        # Assert
        assert len(result) == 1
        
        # Verify query
        call_args = repository.find_many.call_args[0][0]
        assert call_args['site_id'] == sample_object_ids['site_id_1']
        assert call_args['last_modified']['$gte'] == since_time
    
    
    async def test_mark_page_processed(self, repository, sample_object_ids):
        """Test marking page as processed."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        processing_info = {
            'processor': 'content_analyzer',
            'keywords': ['philosophy', 'ethics'],
            'analysis_score': 0.85
        }
        
        # Execute
        result = await repository.mark_page_processed(sample_object_ids['page_id_1'], processing_info)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify update data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['processing_status'] == 'processed'
        assert update_data['processing_info'] == processing_info
        assert 'processed_at' in update_data
    
    
    async def test_get_unprocessed_pages(self, repository, sample_object_ids):
        """Test retrieving unprocessed pages."""
        # Setup
        mock_pages = [
            {
                '_id': sample_object_ids['page_id_1'],
                'site_id': sample_object_ids['site_id_1'],
                'processing_status': 'pending',
                'url': 'https://example.com/page1'
            },
            {
                '_id': sample_object_ids['page_id_2'],
                'site_id': sample_object_ids['site_id_2'],
                'processing_status': 'failed',
                'url': 'https://example.com/page2'
            }
        ]
        repository.find_many.return_value = mock_pages
        
        # Execute
        result = await repository.get_unprocessed_pages()
        
        # Assert
        assert len(result) == 2
        
        # Verify query
        call_args = repository.find_many.call_args[0][0]
        assert call_args['processing_status']['$in'] == ['pending', 'failed']
    
    
    async def test_check_content_exists(self, repository):
        """Test checking if content exists by hash."""
        # Test content exists
        repository.find_one.return_value = {'_id': ObjectId()}
        result = await repository.check_content_exists('test_hash_123')
        assert result is True
        
        # Test content doesn't exist
        repository.find_one.return_value = None
        result = await repository.check_content_exists('nonexistent_hash')
        assert result is False
    
    
    async def test_get_pages_by_author(self, repository, sample_object_ids):
        """Test retrieving pages by author."""
        # Setup
        mock_pages = [
            {
                '_id': sample_object_ids['page_id_1'],
                'site_id': sample_object_ids['site_id_1'],
                'author': 'Test Philosopher',
                'url': 'https://example.com/page1'
            }
        ]
        repository.find_many.return_value = mock_pages
        
        # Execute
        result = await repository.get_pages_by_author('Test Philosopher')
        
        # Assert
        assert len(result) == 1
        assert result[0].author == 'Test Philosopher'
        
        # Verify regex query
        call_args = repository.find_many.call_args[0][0]
        assert '$regex' in call_args['author']
    
    
    async def test_bulk_update_processing_status(self, repository, sample_object_ids):
        """Test bulk updating processing status."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 3
        repository.update_many.return_value = mock_result
        
        page_ids = [sample_object_ids['page_id_1'], sample_object_ids['page_id_2']]
        
        # Execute
        result = await repository.bulk_update_processing_status(page_ids, 'processed')
        
        # Assert
        assert result == 3
        repository.update_many.assert_called_once()
        
        # Verify update
        call_args = repository.update_many.call_args
        assert call_args[0][0]['_id']['$in'] == page_ids
        assert call_args[0][1]['$set']['processing_status'] == 'processed'
    
    
    async def test_get_page_statistics(self, repository, sample_object_ids):
        """Test retrieving page statistics."""
        # Setup
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {'_id': 'processed', 'count': 10, 'last_modified': datetime.now(UTC)},
            {'_id': 'pending', 'count': 5, 'last_modified': datetime.now(UTC)}
        ]
        repository.aggregate.return_value = mock_cursor
        
        # Execute
        result = await repository.get_page_statistics(sample_object_ids['site_id_1'])
        
        # Assert
        assert isinstance(result, PageStats)
        assert result.total == 15
        assert result.processed == 10
        assert result.unprocessed == 5
        assert result.last_crawled is not None
    
    
    async def test_error_handling(self, repository, sample_page_create, simulate_db_error):
        """Test error handling in repository methods."""
        # Setup database error
        simulate_db_error(repository.sites_repository.get_crawl_configuration, Exception, "Site lookup failed")
        
        # Test that exceptions are properly raised
        with pytest.raises(Exception):
            await repository.create_page(sample_page_create)
    
    def test_document_to_page_conversion(self, repository, sample_object_ids):
        """Test conversion of MongoDB document to Page object."""
        # Setup
        doc = {
            '_id': sample_object_ids['page_id_1'],
            'site_id': sample_object_ids['site_id_1'],
            'url': 'https://example.com/article',
            'title': 'Test Article',
            'content': 'Test content',
            'content_hash': 'hash123',
            'author': 'Test Author',
            'published_date': datetime(2024, 1, 10),
            'processing_status': 'processed',
            'created_at': datetime.now(UTC),
            'updated_at': datetime.now(UTC)
        }
        
        # Execute
        page = repository._document_to_page(doc)
        
        # Assert
        assert page.id == sample_object_ids['page_id_1']
        assert page.site_id == sample_object_ids['site_id_1']
        assert page.url == 'https://example.com/article'
        assert page.title == 'Test Article'
        assert page.content == 'Test content'
        assert page.author == 'Test Author'
        assert page.processing_status == 'processed'
