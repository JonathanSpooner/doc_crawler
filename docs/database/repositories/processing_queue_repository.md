### ProcessingTask(id: ObjectId = None, task_type: str = None, priority: int = 5, payload: Dict = None, status: str = "pending", **kwargs)
- `id`: Task document identifier (ObjectId).  
- `task_type`: Type of processing task.  
- `priority`: Priority level of the task (higher runs first; default is 5).  
- `payload`: Task-specific parameters as a dictionary.  
- `status`: Status string (default "pending").  
- Additional fields in kwargs include created_at, scheduled_at, started_at, completed_at, worker_id, error_message, retry_count (defaults to 0), max_retries (defaults to 3).

### QueueStats(pending: int = 0, processing: int = 0, completed: int = 0, failed: int = 0, total: int = 0, **kwargs)
- `pending`: Number of tasks pending.
- `processing`: Number of tasks being processed.
- `completed`: Number of tasks completed.
- `failed`: Number of tasks failed.
- `total`: Total number of tasks in the queue.
- Additional fields in kwargs include oldest_pending and average_processing_time.

### ProcessingQueueRepository(connection_string: str, db_name: str, pages_repository)
- `connection_string`: MongoDB connection string for database access.  
- `db_name`: Name of the target MongoDB database.  
- `pages_repository`: Instance managing page-level metadata.

### create(connection_string: str, db_name: str, pages_repository) -> ProcessingQueueRepository
 - 'connection_string': Connection string for MongoDB instance. 
 - 'db_name': Database name for storing queue collection. 
 - 'pages_repository': PagesRepository dependency injected into repository.

### _setup_indexes()
(No parameters.) Sets up necessary collection indexes for efficient querying and sorting.

### _calculate_next_retry_delay(retry_count: int, base_delay: int=60) -> timedelta
 - 'retry_count': The number of times the task has been retried so far.
 - 'base_delay': Base delay between retries in seconds (default is 60).

### enqueue_task(task) -> ObjectId
 - 'task': ProcessingTask instance containing details about the task to enqueue; returns inserted ObjectId; may raise ValidationError if invalid.

### dequeue_next_task(task_type:str=None) -> Optional[ProcessingTask]
 - 'task_type': Optional filter specifying which type(s) to dequeue next.

### mark_task_processing(task_id:ObjectId , worker_id:str ) -> bool
 - 'task_id': Unique identifier (_id field) for the queued task document.
 - 'worker_id': Identifier associating this assignment with a particular worker/service handling it now.

### complete_task(task_id:ObjectId , result:Dict ) -> bool
 - 'task_id': Task document’s unique identifier (_id).
 - ‘result’: dictionary representing outcome/result metadata from successfully processed job/task completion step.

### fail_task(task_id:ObjectId , error:str , retry :bool=True ) -> bool
 - ‘task_id’: Identifier for failed/errored queued item instance/document (_id).
 – ‘error’: Error message or description as diagnosis/cause text/log info to store on failure state change/update record tracking/history keeping purposes . 
 – ‘retry’: Whether this should reschedule rather than permanently mark as failure/abandonment after failures exceeding limit allowed .

 ### get_queue_status() -> QueueStats 
(No params.) Returns metrics/statistics about current state/counts/times across all main status buckets in queue/job pipeline system .

 ### get_failed_tasks(limit:int=100)->List[ProcessingTask] 
– ‘limit’: Limit maximum number returned from query/filter/search function scan—top N only collected/fetched by descending time order .

 ### retry_failed_tasks(task_ids : List[ObjectId] ) ->int 
 –‘task_ids ’ : List/Object IDs marking those that are requested/manual-forced-reset-to-retry-from-failed-state . Returns count retried/reset/requeued successfully .

 ### purge_completed_tasks(hours_old:int=24)->int 
 –‘hours_old ’ : Age threshold post-completion-aftertime value older than which will be deleted/purged permanently . Int return equals count purged/deleted/completed jobs cleared out after given delta interval/hours gap elapsed since their recorded finish/complete timestamp datetimes

 ### get_worker_tasks(worker_id:str)->List[ProcessingTask]
–’worker_id ’ : Only fetches currently assigned/in-progress jobs/tasks associated with one specific named service agent/work processor worker node/entity ID

 ### _document_to_task(doc : Dict )->ProcessingTask 
–‘doc ’ : Underlying raw dict/MongoDB record returned that’s mapped/wrapped into typed ProcessingTask object/class representation .