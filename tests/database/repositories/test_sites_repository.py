"""
Unit tests for SitesRepository.

Tests site configuration management, domain uniqueness, health tracking,
and crawl schedule functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from bson import ObjectId
from pydantic import ValidationError

from doc_crawler.database.repositories.sites_repository import SitesRepository
from doc_crawler.database.exceptions import DuplicateResourceError, DatabaseConnectionError
from .repository_utils import mock_database, sample_object_ids, sample_site_config, simulate_db_error

class TestSitesRepository:
    """Test suite for SitesRepository."""

    async def test_with_factory_method_mock(self):
        # Mock the entire factory method
        with patch.object(SitesRepository, 'create', new_callable=AsyncMock) as mock_create:
            mock_repo = AsyncMock()
            mock_create.return_value = mock_repo
            
            repo = await SitesRepository.create("conn_string", "db_name")
            
            assert repo == mock_repo
            mock_create.assert_called_once_with("conn_string", "db_name")
    
    async def test_with_setup_indexes_mocked(self):
        # Mock just the _setup_indexes method
        with patch.object(SitesRepository, '_setup_indexes', new_callable=AsyncMock) as mock_setup:
            repo = await SitesRepository.create("conn_string", "db_name")
            
            mock_setup.assert_called_once()
            assert isinstance(repo, SitesRepository)

    @pytest.fixture
    async def repository(self, mock_database):
        """Create SitesRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['sites']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid
            
            with patch.object(SitesRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await SitesRepository.create("mongodb://test", "test_db")
                
                repo.db = mock_database
                repo.collection = mock_database['sites']
                repo.db = mock_database
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.find_many = AsyncMock()
                
                return repo
    
    @pytest.fixture
    def mock_site_config(self, sample_site_config):
        """Create mock SiteConfiguration."""
        config = MagicMock()
        config.model_dump.return_value = sample_site_config
        config.name = sample_site_config['name']
        config.base_url = sample_site_config['base_url']
        config.domains = sample_site_config['domains']
        config.enabled = sample_site_config['enabled']
        config.delay = sample_site_config.get('delay')
        config.allowed_urls = []
        config.denied_urls = []
        return config
    
    async def test_create_site_success(self, repository, mock_site_config, sample_object_ids):
        """Test successful site creation."""
        # Setup
        repository.find_one.return_value = None  # No existing site
        repository.insert_one.return_value = sample_object_ids['site_id_1']
        
        # Execute
        result = await repository.create_site(mock_site_config)
        
        # Assert
        assert result == sample_object_ids['site_id_1']
        repository.find_one.assert_called_once()
        repository.insert_one.assert_called_once()
        
        # Verify inserted data structure
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['name'] == mock_site_config.name
        assert call_args['base_url'] == str(mock_site_config.base_url)
        assert 'monitoring' in call_args
        assert 'politeness' in call_args
    
    async def test_create_site_duplicate_domain(self, repository, mock_site_config):
        """Test site creation with duplicate domain."""
        # Setup
        repository.find_one.return_value = {'_id': ObjectId(), 'base_url': mock_site_config.base_url}
        
        # Execute & Assert
        with pytest.raises(DuplicateResourceError) as exc_info:
            await repository.create_site(mock_site_config)
        
        assert "already exists" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    async def test_get_active_sites(self, repository, sample_object_ids):
        """Test retrieving active sites."""
        # Setup
        mock_sites = [
            {
                '_id': sample_object_ids['site_id_1'],
                'name': 'Site 1',
                'base_url': 'https://site1.com',
                'crawl_patterns': {'allowed_domains': ['site1.com'], 'start_urls': [], 'deny_patterns': [], 'allow_patterns': []},
                'monitoring': {'active': True, 'frequency': 'daily'},
                'tags': [],
                'created_at': datetime.now(UTC),
                'updated_at': datetime.now(UTC),
            }
        ]
        repository.find_many.return_value = mock_sites
        
        # Execute
        result = await repository.get_active_sites()
        
        # Assert
        assert len(result) == 1
        assert result[0].name == 'Site 1'
        repository.find_many.assert_called_once_with(
            {"monitoring.active": True},
            sort=[("monitoring.next_scheduled_crawl", 1)]
        )
    
    async def test_get_site_by_domain_found(self, repository, sample_object_ids):
        """Test finding site by domain."""
        # Setup
        mock_site = {
            '_id': sample_object_ids['site_id_1'],
            'name': 'Test Site',
            'base_url': 'https://example.com',
            'crawl_patterns': {'allowed_domains': ['example.com'], 'start_urls': [], 'deny_patterns': [], 'allow_patterns': []},
            'monitoring': {'active': True, 'frequency': 'daily'},
            'tags': [],
            'created_at': datetime.now(UTC),
            'updated_at': datetime.now(UTC)
        }
        repository.find_one.return_value = mock_site
        
        # Execute
        result = await repository.get_site_by_domain('example.com')
        
        # Assert
        assert result is not None
        assert result.name == 'Test Site'
    
    async def test_get_site_by_domain_not_found(self, repository):
        """Test finding non-existent site by domain."""
        # Setup
        repository.find_one.return_value = None
        
        # Execute
        result = await repository.get_site_by_domain('nonexistent.com')
        
        # Assert
        assert result is None
    
    async def test_update_crawl_settings_success(self, repository, sample_object_ids):
        """Test successful crawl settings update."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        settings = {
            'delay': 2.0,
            'max_concurrent': 3,
            'allowed_domains': ['example.com', 'test.com']
        }
        
        # Execute
        result = await repository.update_crawl_settings(sample_object_ids['site_id_1'], settings)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify update data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert 'politeness.delay' in update_data
        assert update_data['politeness.delay'] == 2.0
    
    async def test_disable_site_success(self, repository, sample_object_ids):
        """Test successful site disabling."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        # Execute
        result = await repository.disable_site(sample_object_ids['site_id_1'], "Maintenance")
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify disable data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['monitoring.active'] is False
        assert update_data['disabled_reason'] == "Maintenance"
    
    async def test_get_sites_for_crawl_schedule(self, repository, sample_object_ids):
        """Test retrieving sites for specific schedule."""
        # Setup
        mock_sites = [
            {
                '_id': sample_object_ids['site_id_1'],
                'name': 'Daily Site',
                'base_url': 'https://daily.com',
                'crawl_patterns': {'allowed_domains': ['daily.com'], 'start_urls': [], 'deny_patterns': [], 'allow_patterns': []},
                'monitoring': {'active': True, 'frequency': 'daily'},
                'tags': [],
                'created_at': datetime.now(UTC),
                'updated_at': datetime.now(UTC)
            }
        ]
        repository.find_many.return_value = mock_sites
        
        # Execute
        result = await repository.get_sites_for_crawl_schedule('daily')
        
        # Assert
        assert len(result) == 1
        assert result[0].name == 'Daily Site'
        
        # Verify query
        call_args = repository.find_many.call_args[0][0]
        assert call_args['monitoring.active'] is True
        assert call_args['monitoring.frequency'] == 'daily'
    
    async def test_update_site_health_status(self, repository, sample_object_ids):
        """Test updating site health status."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        # Execute
        result = await repository.update_site_health_status(sample_object_ids['site_id_1'], 'healthy')
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify health status update
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['health_status'] == 'healthy'
        assert 'health_checked_at' in update_data
    
    async def test_get_crawl_configuration(self, repository, sample_object_ids):
        """Test retrieving crawl configuration."""
        # Setup
        mock_site_doc = {
            '_id': sample_object_ids['site_id_1'],
            'name': 'Test Site',
            'base_url': 'https://test.com',
            'crawl_patterns': {'allowed_domains': ['test.com']},
            'politeness': {'delay': 1.0},
            'monitoring': {'active': True},
            'health_status': 'healthy'
        }
        repository.find_one.return_value = mock_site_doc
        
        # Execute
        result = await repository.get_crawl_configuration(sample_object_ids['site_id_1'])
        
        # Assert
        assert result is not None
        assert result['name'] == 'Test Site'
        assert result['base_url'] == 'https://test.com'
        assert result['health_status'] == 'healthy'
        assert 'crawl_patterns' in result
        assert 'politeness' in result
    
    async def test_get_crawl_configuration_not_found(self, repository, sample_object_ids):
        """Test retrieving non-existent crawl configuration."""
        # Setup
        repository.find_one.return_value = None
        
        # Execute
        result = await repository.get_crawl_configuration(sample_object_ids['site_id_1'])
        
        # Assert
        assert result is None
    
    async def test_error_handling(self, repository, mock_site_config, simulate_db_error):
        """Test error handling in repository methods."""
        # Setup database error
        simulate_db_error(repository.find_one, Exception, "Database connection failed")
        
        # Test that exceptions are properly raised/handled
        with pytest.raises(DatabaseConnectionError):
            await repository.create_site(mock_site_config)
    
    def test_document_to_site_conversion(self, repository, sample_object_ids):
        """Test conversion of MongoDB document to Site object."""
        # Setup
        doc = {
            '_id': sample_object_ids['site_id_1'],
            'name': 'Test Site',
            'base_url': 'https://test.com',
            'crawl_patterns': {
                'allowed_domains': ['test.com'],
                'start_urls': ['https://test.com'],
                'deny_patterns': [],
                'allow_patterns': []
            },
            'monitoring': {
                'active': True,
                'frequency': 'daily',
                'last_crawl_time': None,
                'next_scheduled_crawl': None
            },
            'tags': ['test'],
            'created_at': datetime.now(UTC),
            'updated_at': datetime.now(UTC)
        }
        
        # Execute
        site = repository._document_to_site(doc)
        
        # Assert
        assert site.id == str(sample_object_ids['site_id_1'])
        assert site.name == 'Test Site'
        assert site.base_url == 'https://test.com/'
        assert site.crawl_patterns.allowed_domains == ['test.com']
        assert site.monitoring.active is True
        assert site.tags == ['test']
