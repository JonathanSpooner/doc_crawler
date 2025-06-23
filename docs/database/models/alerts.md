### Alert(BaseModel)
- `id`: Optional unique identifier for the alert as a MongoDB ObjectId (aliased as `_id`).
- `type`: Type of alert, limited to "error", "warning", or "info".
- `message`: Detailed message describing the alert; must have at least 1 character.
- `source`: Source of the alert (e.g., 'crawler', 'processor', 'monitoring').
- `resolved`: Boolean indicating whether the alert has been resolved; defaults to False.
- `created_at`: Timestamp when the alert was created; defaults to current UTC time.
- `resolved_at`: Optional timestamp when the alert was resolved.