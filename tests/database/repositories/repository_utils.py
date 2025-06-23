"""
Test fixtures and configuration for repository unit tests.

Provides shared test data, mocks, and utilities for all repository tests.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from typing import Dict, Any, List

# Test Data Fixtures

@pytest.fixture
def sample_object_ids():
    """Generate consistent ObjectIds for testing."""
    return {
        'site_id_1': ObjectId('507f1f77bcf86cd799439011'),
        'site_id_2': ObjectId('507f1f77bcf86cd799439012'),
        'page_id_1': ObjectId('507f1f77bcf86cd799439021'),
        'page_id_2': ObjectId('507f1f77bcf86cd799439022'),
        'session_id_1': ObjectId('507f1f77bcf86cd799439031'),
        'task_id_1': ObjectId('507f1f77bcf86cd799439041'),
        'alert_id_1': ObjectId('507f1f77bcf86cd799439051'),
        'change_id_1': ObjectId('507f1f77bcf86cd799439061')
    }

@pytest.fixture
def test_datetime():
    """Consistent datetime for testing."""
    return datetime(2024, 1, 15, 12, 0, 0)

@pytest.fixture
def sample_site_config():
    """Sample site configuration for testing."""
    return {
        'name': 'Test Philosophy Site',
        'base_url': 'https://example-philosophy.com',
        'domains': ['example-philosophy.com'],
        'enabled': True,
        'delay': 1.0,
        'tags': ['philosophy', 'test'],
        'allowed_urls': [],
        'denied_urls': []
    }

@pytest.fixture
def sample_page_data(sample_object_ids):
    """Sample page data for testing."""
    return {
        'site_id': sample_object_ids['site_id_1'],
        'url': 'https://example-philosophy.com/article1',
        'title': 'Test Philosophical Article',
        'content': 'This is a test philosophical content about ethics and morality.',
        'author': 'Test Philosopher',
        'published_date': datetime(2024, 1, 10)
    }

@pytest.fixture
def sample_crawl_config():
    """Sample crawl configuration for testing."""
    return {
        'max_concurrent_sessions': 2,
        'worker_id': 'test-worker-1',
        'user_agent': 'TestCrawler/1.0',
        'respect_robots_txt': True
    }

@pytest.fixture
def sample_task_data(sample_object_ids):
    """Sample processing task data for testing."""
    return {
        'task_type': 'content_analysis',
        'priority': 5,
        'payload': {
            'page_id': str(sample_object_ids['page_id_1']),
            'analysis_type': 'philosophical_concepts'
        },
        'max_retries': 3
    }

@pytest.fixture
def sample_alert_data(sample_object_ids):
    """Sample alert data for testing."""
    return {
        'alert_type': 'crawl_failure',
        'severity': 'high',
        'title': 'Site Crawl Failed',
        'message': 'Failed to crawl site due to connection timeout',
        'site_id': sample_object_ids['site_id_1'],
        'source_component': 'crawler',
        'context': {
            'error_code': 'TIMEOUT',
            'retry_count': 3
        }
    }

@pytest.fixture
def sample_change_data(sample_object_ids):
    """Sample content change data for testing."""
    return {
        'page_id': sample_object_ids['page_id_1'],
        'change_type': 'modified',
        'site_id': sample_object_ids['site_id_1'],
        'url': 'https://example-philosophy.com/article1',
        'title': 'Updated Philosophical Article',
        'previous_hash': 'old_hash_123',
        'new_hash': 'new_hash_456',
        'context': {
            'content_change_ratio': 0.3,
            'philosophical_content': True
        }
    }

# Mock Classes

class MockAsyncMongoRepository:
    """Mock base repository for testing."""
    
    def __init__(self, connection_string: str, db_name: str, collection_name: str):
        self.connection_string = connection_string
        self.db_name = db_name
        self.collection_name = collection_name
        self.collection = AsyncMock()
        self.db = MagicMock()
        self.db[collection_name] = self.collection
        
    async def _setup_indexes(self):
        pass
        
    async def create_indexes(self, indexes):
        return True
        
    def _validate_object_id(self, obj_id):
        if isinstance(obj_id, str):
            return ObjectId(obj_id)
        return obj_id
        
    def _generate_content_hash(self, content: str) -> str:
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()
        
    async def insert_one(self, document: Dict, validate: bool = True) -> ObjectId:
        new_id = ObjectId()
        document['_id'] = new_id
        return new_id
        
    async def find_one(self, query: Dict) -> Dict:
        return None
        
    async def find_many(self, query: Dict, **kwargs) -> List[Dict]:
        return []
        
    async def update_one(self, query: Dict, update_data: Dict, **kwargs):
        result = MagicMock()
        result.modified_count = 1
        return result
        
    async def update_many(self, query: Dict, update_data: Dict, **kwargs):
        result = MagicMock()
        result.modified_count = 5
        return result
        
    async def delete_one(self, query: Dict):
        result = MagicMock()
        result.deleted_count = 1
        return result
        
    async def delete_many(self, query: Dict):
        result = MagicMock()
        result.deleted_count = 5
        return result
        
    async def aggregate(self, pipeline: List[Dict]):
        cursor = AsyncMock()
        cursor.to_list = AsyncMock(return_value=[])
        return cursor

# Repository Mock Factories

@pytest.fixture
def mock_sites_repository():
    """Mock SitesRepository for dependency injection."""
    mock_repo = AsyncMock()
    mock_repo.get_crawl_configuration = AsyncMock(return_value={
        'site_id': 'test_site_id',
        'name': 'Test Site',
        'base_url': 'https://example.com'
    })
    return mock_repo

@pytest.fixture
def mock_pages_repository():
    """Mock PagesRepository for dependency injection."""
    mock_repo = AsyncMock()
    mock_repo.find_one = AsyncMock(return_value={
        '_id': ObjectId(),
        'url': 'https://example.com/page1',
        'title': 'Test Page'
    })
    return mock_repo

# Database Mocks

@pytest.fixture
def mock_database():
    """Mock database for testing."""
    db = MagicMock()
    collection = AsyncMock()
    
    # Setup common collection methods
    collection.count_documents = AsyncMock(return_value=5)
    collection.find_one_and_update = AsyncMock(return_value=None)
    collection.create_index = AsyncMock()
    
    db.__getitem__ = MagicMock(return_value=collection)
    return db

# Common Test Utilities

def create_mock_document(doc_id: ObjectId, **kwargs) -> Dict[str, Any]:
    """Create a mock MongoDB document with standard fields."""
    doc = {
        '_id': doc_id,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    doc.update(kwargs)
    return doc

def assert_repository_call(mock_method, expected_query: Dict = None, call_count: int = 1):
    """Assert that a repository method was called with expected parameters."""
    assert mock_method.call_count == call_count
    if expected_query and call_count > 0:
        args, kwargs = mock_method.call_args
        if args:
            assert args[0] == expected_query
        elif 'query' in kwargs:
            assert kwargs['query'] == expected_query

# Async Test Decorators

def async_test(func):
    """Decorator to mark tests as async."""
    return pytest.mark.asyncio(func)

# Error Simulation

class DatabaseError(Exception):
    """Simulated database error for testing."""
    pass

@pytest.fixture
def simulate_db_error():
    """Fixture to simulate database errors."""
    def _simulate_error(mock_method, error_type=DatabaseError, error_message="Database error"):
        mock_method.side_effect = error_type(error_message)
    return _simulate_error
