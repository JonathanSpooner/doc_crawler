"""
Unit tests for CrawlSessionsRepository, ProcessingQueueRepository, AlertsRepository, 
and ContentChangesRepository.

Comprehensive test coverage for all remaining Phase 1 and Phase 2 repositories.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC
from bson import ObjectId
from pydantic import ValidationError
from pydantic_core import PydanticCustomError

from doc_crawler.database.repositories.crawl_sessions_repository import CrawlSessionsRepository, CrawlStats
from doc_crawler.database.repositories.processing_queue_repository import ProcessingQueueRepository, ProcessingTask
from doc_crawler.database.repositories.alerts_repository import AlertsRepository, Alert, AlertStats
from doc_crawler.database.repositories.content_changes_repository import ContentChangesRepository, ContentChange

from ..repositories.repository_utils import mock_database, mock_sites_repository, sample_object_ids, sample_crawl_config, mock_pages_repository


class TestCrawlSessionsRepository:
    """Test suite for CrawlSessionsRepository."""
    
    @pytest.fixture
    async def repository(self, mock_database, mock_sites_repository):
        """Create CrawlSessionsRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['crawl_sessions']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid
            
            with patch.object(CrawlSessionsRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await CrawlSessionsRepository.create("mongodb://test", "test_db", mock_sites_repository)
                repo.collection = mock_database['crawl_sessions']
                repo.db = mock_database
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.find_many = AsyncMock()
                repo.delete_many = AsyncMock()
                
                return repo
    
    
    async def test_start_crawl_session_success(self, repository, sample_object_ids, sample_crawl_config):
        """Test successful crawl session start."""
        # Setup
        repository.sites_repository.get_crawl_configuration.return_value = {'site_id': 'test'}
        repository.get_concurrent_session_count = AsyncMock(return_value=0)
        repository.insert_one.return_value = sample_object_ids['session_id_1']
        
        # Execute
        result = await repository.start_crawl_session(sample_object_ids['site_id_1'], sample_crawl_config)
        
        # Assert
        assert result == sample_object_ids['session_id_1']
        repository.insert_one.assert_called_once()
        
        # Verify session data
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['site_id'] == sample_object_ids['site_id_1']
        assert call_args['status'] == 'running'
        assert 'stats' in call_args
    
    
    async def test_start_crawl_session_concurrent_limit(self, repository, sample_object_ids, sample_crawl_config):
        """Test crawl session start with concurrent limit reached."""
        # Setup
        repository.sites_repository.get_crawl_configuration.return_value = {'site_id': 'test'}
        repository.get_concurrent_session_count = AsyncMock(return_value=2)
        sample_crawl_config['max_concurrent_sessions'] = 1
        
        # Execute & Assert
        with pytest.raises(PydanticCustomError) as exc_info:
            await repository.start_crawl_session(sample_object_ids['site_id_1'], sample_crawl_config)
        
        assert "Maximum concurrent sessions" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    
    async def test_update_session_progress(self, repository, sample_object_ids):
        """Test updating session progress."""
        # Setup
        repository.find_one.return_value = {'_id': sample_object_ids['session_id_1'], 'status': 'running'}
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        stats = CrawlStats(pages_discovered=100, pages_crawled=50, pages_failed=2)
        
        # Execute
        result = await repository.update_session_progress(sample_object_ids['session_id_1'], stats)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify update data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['stats.pages_discovered'] == 100
        assert update_data['stats.pages_crawled'] == 50
    
    
    async def test_complete_crawl_session(self, repository, sample_object_ids):
        """Test completing crawl session."""
        # Setup
        start_time = datetime.now(UTC) - timedelta(hours=1)
        repository.find_one.return_value = {
            '_id': sample_object_ids['session_id_1'],
            'started_at': start_time,
            'site_id': sample_object_ids['site_id_1']
        }
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        repository.sites_repository.update_one = AsyncMock()
        
        final_stats = CrawlStats(pages_discovered=200, pages_crawled=190, pages_failed=5)
        
        # Execute
        result = await repository.complete_crawl_session(sample_object_ids['session_id_1'], final_stats)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify completion data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['status'] == 'completed'
        assert 'completed_at' in update_data
        assert 'duration_seconds' in update_data['stats']


class TestProcessingQueueRepository:
    """Test suite for ProcessingQueueRepository."""
    
    @pytest.fixture
    async def repository(self, mock_database, mock_pages_repository):
        """Create ProcessingQueueRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['processing_queue']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid

            with patch.object(ProcessingQueueRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await ProcessingQueueRepository.create("mongodb://test", "test_db", mock_pages_repository)
                repo.collection = mock_database['processing_queue']
                repo.db = mock_database
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.update_many = AsyncMock()
                repo.find_many = AsyncMock()
                repo.aggregate = AsyncMock()
                
                return repo
    
    @pytest.fixture
    def sample_processing_task(self, sample_object_ids):
        """Create sample ProcessingTask."""
        return ProcessingTask(
            task_type='content_analysis',
            priority=5,
            payload={
                'page_id': str(sample_object_ids['page_id_1']),
                'analysis_type': 'philosophical_concepts'
            },
            max_retries=3
        )
    
    
    async def test_enqueue_task_success(self, repository, sample_processing_task, sample_object_ids):
        """Test successful task enqueuing."""
        # Setup
        repository.insert_one.return_value = sample_object_ids['task_id_1']
        
        # Execute
        result = await repository.enqueue_task(sample_processing_task)
        
        # Assert
        assert result == sample_object_ids['task_id_1']
        repository.insert_one.assert_called_once()
        
        # Verify task data
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['task_type'] == 'content_analysis'
        assert call_args['priority'] == 5
        assert call_args['status'] == 'pending'
    
    
    async def test_enqueue_task_invalid_data(self, repository):
        """Test enqueuing task with invalid data."""
        # Create task without required fields
        invalid_task = ProcessingTask(priority=5)
        
        # Execute & Assert
        with pytest.raises(PydanticCustomError) as exc_info:
            await repository.enqueue_task(invalid_task)
        
        assert "Task type is required" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    
    async def test_dequeue_next_task_success(self, repository, sample_object_ids):
        """Test successful task dequeuing."""
        # Setup
        mock_task_doc = {
            '_id': sample_object_ids['task_id_1'],
            'task_type': 'content_analysis',
            'priority': 5,
            'payload': {'test': 'data'},
            'status': 'processing',
            'created_at': datetime.now(UTC)
        }
        repository.collection.find_one_and_update.return_value = mock_task_doc
        
        # Execute
        result = await repository.dequeue_next_task('content_analysis')
        
        # Assert
        assert result is not None
        assert result.task_type == 'content_analysis'
        assert result.priority == 5
        repository.collection.find_one_and_update.assert_called_once()
    
    
    async def test_complete_task(self, repository, sample_object_ids):
        """Test completing a task."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        task_result = {
            'status': 'success',
            'keywords_extracted': ['philosophy', 'ethics'],
            'processing_time': 2.5
        }
        
        # Execute
        result = await repository.complete_task(sample_object_ids['task_id_1'], task_result)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify completion data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['status'] == 'completed'
        assert update_data['result'] == task_result
    
    
    async def test_fail_task_with_retry(self, repository, sample_object_ids):
        """Test failing a task with retry."""
        # Setup
        repository.find_one.return_value = {
            '_id': sample_object_ids['task_id_1'],
            'retry_count': 1,
            'max_retries': 3
        }
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        # Execute
        result = await repository.fail_task(sample_object_ids['task_id_1'], "Processing error", retry=True)
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify retry scheduling
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['status'] == 'pending'  # Scheduled for retry
        assert update_data['retry_count'] == 2
        assert 'scheduled_at' in update_data


class TestAlertsRepository:
    """Test suite for AlertsRepository."""
    
    @pytest.fixture
    async def repository(self, mock_database, mock_sites_repository):
        """Create AlertsRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['alerts']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid
            
            with patch.object(AlertsRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await AlertsRepository.create("mongodb://test", "test_db", mock_sites_repository)
                repo.collection = mock_database['alerts']
                repo.db = mock_database
                repo.suppressions_collection = mock_database['alert_suppressions']
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.find_many = AsyncMock()
                repo.delete_many = AsyncMock()
                repo.aggregate = AsyncMock()
                repo._is_alert_suppressed = AsyncMock(return_value=False)
                
                return repo
        
    @pytest.fixture
    def sample_alert(self, sample_object_ids):
        """Create sample Alert."""
        return Alert(
            alert_type='crawl_failure',
            severity='high',
            title='Site Crawl Failed',
            message='Failed to crawl site due to connection timeout',
            site_id=sample_object_ids['site_id_1'],
            source_component='crawler',
            context={'error_code': 'TIMEOUT', 'retry_count': 3}
        )
    
    
    async def test_create_alert_success(self, repository, sample_alert, sample_object_ids):
        """Test successful alert creation."""
        # Setup
        repository.find_one.return_value = None  # No existing alert
        repository.insert_one.return_value = sample_object_ids['alert_id_1']
        repository.sites_repository.get_crawl_configuration.return_value = {'site_id': 'test'}
        
        # Execute
        result = await repository.create_alert(sample_alert)
        
        # Assert
        assert result == sample_object_ids['alert_id_1']
        repository.insert_one.assert_called_once()
        
        # Verify alert data
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['alert_type'] == 'crawl_failure'
        assert call_args['severity'] == 'high'
        assert call_args['status'] == 'active'
    
    
    async def test_create_alert_duplicate(self, repository, sample_alert, sample_object_ids):
        """Test creating duplicate alert updates existing."""
        # Setup
        existing_alert = {
            '_id': sample_object_ids['alert_id_1'],
            'alert_hash': 'test_hash',
            'status': 'active'
        }
        repository.find_one.return_value = existing_alert
        repository.update_one = AsyncMock()
        
        # Execute
        result = await repository.create_alert(sample_alert)
        
        # Assert
        assert result == sample_object_ids['alert_id_1']
        repository.update_one.assert_called_once()  # Updated existing
        repository.insert_one.assert_not_called()  # Did not create new
    
    
    async def test_resolve_alert(self, repository, sample_object_ids):
        """Test resolving an alert."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        # Execute
        result = await repository.resolve_alert(sample_object_ids['alert_id_1'], "Issue fixed")
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify resolution data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['status'] == 'resolved'
        assert update_data['resolution'] == "Issue fixed"
        assert 'resolved_at' in update_data
    
    
    async def test_suppress_alert_type(self, repository):
        """Test suppressing alert type."""
        # Setup
        repository.suppressions_collection.update_one = AsyncMock()
        
        # Execute
        result = await repository.suppress_alert_type('crawl_failure', 24)
        
        # Assert
        assert result is True
        repository.suppressions_collection.update_one.assert_called_once()
        
        # Verify suppression data
        call_args = repository.suppressions_collection.update_one.call_args
        suppression_data = call_args[0][1]['$set']
        assert suppression_data['alert_type'] == 'crawl_failure'
        assert 'suppressed_until' in suppression_data


class TestContentChangesRepository:
    """Test suite for ContentChangesRepository."""
    
    @pytest.fixture
    async def repository(self, mock_database, mock_pages_repository):
        """Create ContentChangesRepository instance with mocked dependencies."""
        with patch('doc_crawler.database.repositories.async_mongo_repository.AsyncMongoDBRepository') as mock_base:
            mock_base.return_value.collection = mock_database['content_changes']
            mock_base.return_value.db = mock_database
            mock_base.return_value.create_indexes = AsyncMock()
            mock_base.return_value._validate_object_id = lambda self, oid: ObjectId(oid) if isinstance(oid, str) else oid
            
            with patch.object(ContentChangesRepository, '_setup_indexes', new_callable=AsyncMock):
                repo = await ContentChangesRepository.create("mongodb://test", "test_db", mock_pages_repository)
                repo.collection = mock_database['content_changes']
                repo.db = mock_database
                repo.find_one = AsyncMock()
                repo.insert_one = AsyncMock()
                repo.update_one = AsyncMock()
                repo.find_many = AsyncMock()
                repo.delete_many = AsyncMock()
                repo.aggregate = AsyncMock()
                
                return repo
    
    @pytest.fixture
    def sample_content_change(self, sample_object_ids):
        """Create sample ContentChange."""
        return ContentChange(
            page_id=sample_object_ids['page_id_1'],
            change_type='modified',
            site_id=sample_object_ids['site_id_1'],
            url='https://example.com/article1',
            title='Updated Article',
            previous_hash='old_hash',
            new_hash='new_hash',
            context={'content_change_ratio': 0.3}
        )
    
    
    async def test_record_content_change_success(self, repository, sample_content_change, sample_object_ids):
        """Test successful content change recording."""
        # Setup
        repository.pages_repository.find_one.return_value = {
            '_id': sample_object_ids['page_id_1'],
            'url': 'https://example.com/article1',
            'title': 'Article'
        }
        repository.insert_one.return_value = sample_object_ids['change_id_1']
        
        # Execute
        result = await repository.record_content_change(sample_content_change)
        
        # Assert
        assert result == sample_object_ids['change_id_1']
        repository.insert_one.assert_called_once()
        
        # Verify change data
        call_args = repository.insert_one.call_args[0][0]
        assert call_args['change_type'] == 'modified'
        assert call_args['priority'] == 'medium'  # Auto-determined
        assert call_args['notification_sent'] is False
    
    
    async def test_record_content_change_invalid_type(self, repository, sample_content_change):
        """Test recording change with invalid type."""
        # Setup
        sample_content_change.change_type = 'invalid_type'
        
        # Execute & Assert
        with pytest.raises(PydanticCustomError) as exc_info:
            await repository.record_content_change(sample_content_change)
        
        assert "Invalid change type" in str(exc_info.value)
        repository.insert_one.assert_not_called()
    
    
    async def test_get_changes_since(self, repository, sample_object_ids):
        """Test retrieving changes since specific time."""
        # Setup
        since_time = datetime.now(UTC) - timedelta(hours=24)
        mock_changes = [
            {
                '_id': sample_object_ids['change_id_1'],
                'change_type': 'new',
                'detected_at': datetime.now(UTC),
                'site_id': sample_object_ids['site_id_1']
            }
        ]
        repository.find_many.return_value = mock_changes
        
        # Execute
        result = await repository.get_changes_since(sample_object_ids['site_id_1'], since_time)
        
        # Assert
        assert len(result) == 1
        assert result[0].change_type == 'new'
        
        # Verify query
        call_args = repository.find_many.call_args[0][0]
        assert call_args['site_id'] == sample_object_ids['site_id_1']
        assert call_args['detected_at']['$gte'] == since_time
    
    
    async def test_mark_change_notified(self, repository, sample_object_ids):
        """Test marking change as notified."""
        # Setup
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repository.update_one.return_value = mock_result
        
        # Execute
        result = await repository.mark_change_notified(sample_object_ids['change_id_1'])
        
        # Assert
        assert result is True
        repository.update_one.assert_called_once()
        
        # Verify notification data
        call_args = repository.update_one.call_args
        update_data = call_args[0][1]['$set']
        assert update_data['notification_sent'] is True
        assert 'notified_at' in update_data
    
    def test_determine_change_priority(self, repository):
        """Test change priority determination logic."""
        # Test deleted content (high priority)
        priority = repository._determine_change_priority('deleted')
        assert priority == 'high'
        
        # Test new content from known author (high priority)
        context = {'author_known': True, 'philosophical_content': True}
        priority = repository._determine_change_priority('new', context)
        assert priority == 'high'
        
        # Test minor modification (low priority)
        context = {'content_change_ratio': 0.05}
        priority = repository._determine_change_priority('modified', context)
        assert priority == 'low'
        
        # Test major modification (high priority)
        context = {'content_change_ratio': 0.7}
        priority = repository._determine_change_priority('modified', context)
        assert priority == 'high'
