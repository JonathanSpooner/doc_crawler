from pymongo import ASCENDING, DESCENDING, IndexModel
from typing import List

def get_processing_queue_indexes() -> List[IndexModel]:
    """Define and return the indexes for the `processing_queue` collection."""
    indexes = [
        # Index on priority for task scheduling (ascending for FIFO within priority)
        IndexModel([("priority", ASCENDING)], name="priority_index"),

        # Index on status for filtering tasks by state (e.g., pending, completed)
        IndexModel([("status", ASCENDING)], name="status_index"),

        # Index on created_at for sorting tasks by age (oldest first)
        IndexModel([("created_at", ASCENDING)], name="created_at_asc"),

        # Compound index for task scheduling (priority + status + created_at)
        IndexModel(
            [
                ("priority", ASCENDING),
                ("status", ASCENDING),
                ("created_at", ASCENDING),
            ],
            name="task_scheduling",
        ),

        # Index on task_type for filtering by task type (e.g., text_cleaning)
        IndexModel([("task_type", ASCENDING)], name="task_type_index"),

        # Index on max_retries for monitoring tasks with retry limits
        IndexModel([("max_retries", ASCENDING)], name="max_retries_index"),
    ]

    return indexes