### ProcessingTask(BaseModel)
- `id`: Optional unique identifier for the task (alias for `_id`).
- `task_type`: String indicating type of task (e.g., 'text_cleaning').
- `page_id`: Reference to the `pages` collection as an ObjectId.
- `priority`: Integer priority level (1=highest, 5=lowest), default is 3.
- `status`: Current status string with allowed values ('pending', 'processing', 'completed', 'failed'), default is "pending".
- `timeout_seconds`: Task timeout in seconds, default is 3600.
- `dependencies`: List of ObjectIds this task depends on; defaults to empty list.
- `created_at`: Timestamp when the task was created; defaults to now in UTC.
- `processed_at`: Optional timestamp for when processing occurred.
- `max_retries`: Maximum number of retry attempts (integer, min 0); default is 3.
- `error`: Optional error message string if the task failed.

### validate_status(cls, v: str) -> str
- `cls`: The ProcessingTask class itself for class-level validation context.
- `v`: The value provided for the status field; validated to ensure it matches one of the allowed statuses (`'pending'`, `'processing'`, `'completed'`, `'failed'`).