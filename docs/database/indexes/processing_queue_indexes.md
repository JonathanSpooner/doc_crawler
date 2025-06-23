### get_processing_queue_indexes()

- Returns a list of `IndexModel` objects that define indexes for a MongoDB `processing_queue` collection.

#### Parameters

This function does not take any parameters.

#### Returns

- A list of PyMongo `IndexModel` instances, each specifying an index for the collection.

#### Indexes Defined

- `priority_index`: Single-field ascending index on "priority" for task ordering.
- `status_index`: Single-field ascending index on "status" to filter tasks by state.
- `created_at_asc`: Single-field ascending index on "created_at" for age-based sorting.
- `task_scheduling`: Compound index (priority, status, created_at) optimized for efficient task scheduling queries and sort operations[2][4][5].
- `task_type_index`: Single-field ascending index on "task_type" to enable filtering by type of task.
- `max_retries_index`: Single-field ascending index on "max_retries" to find tasks with specific retry constraints.