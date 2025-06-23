### Alert(id: ObjectId = None, alert_type: str = None, severity: str = "medium", title: str = None, message: str = None, **kwargs)
- `id`: Unique identifier for the alert (optional).
- `alert_type`: Category/type of this alert.
- `severity`: Severity level ("critical", "high", etc.).
- `title`: Short descriptive title for the alert.
- `message`: Detailed explanatory message (optional).
- Additional properties provided in kwargs are used for fields like site_id, source_component, context, status, created_at, resolved_at, escalated_at, notification_sent.

### AlertSuppression(alert_type: str, suppressed_until: datetime, reason: str = None, **kwargs)
- `alert_type`: Type of alert being suppressed.
- `suppressed_until`: Datetime until which suppression is active.
- `reason`: Optional explanation for suppression.

### AlertStats(total: int = 0, active: int = 0, resolved: int = 0,
by_severity: Dict = None, **kwargs)
- `total`: Total alerts in the stats range.
- `active`: Number of currently active alerts.
- `resolved`: Number of resolved alerts in range.
- `by_severity`: Statistics grouped by severity (dictionary).

### AlertsRepository(connection_string: str,
db_name: str,
sites_repository: SitesRepository)
- Inherits from AsyncMongoDBRepository; manages MongoDB operations for alerts and suppressions.

### create(connection_string: str,
db_name: str,
sites_repository: SitesRepository) -> AlertsRepository
- Instantiate and initialize an AlertsRepository asynchronously with collections/indexes set up.

### _setup_indexes(self)
 - Set up indexes on both main alerts collection and suppressions collection to optimize queries.

### _calculate_alert_hash(self,
alert_type: str,
site_id: ObjectId=None,
context: Dict=None) -> str
 - Compute a unique hash string used to deduplicate incoming alerts based on their key characteristics.

### create_alert(self,
alert:
Alert) -> ObjectId
 - Add a new deduplicated alert if it is not suppressed. Returns new or existing alert's ObjectId.

### get_active_alerts(self,
severity:
str=None) -> List[Alert]
 - Get all current active (non-resolved/suppressed) alerts. Optionally filter by severity level if specified.

### resolve_alert(self,
alert_id:
ObjectId,
resolution:
str) -> bool
 - Mark a specific alert as resolved with an associated resolution text. Returns True if successful.

### get_alert_history(self,
hours:
int=24) -> List[Alert]
 - Retrieve all created/updated/seen alerts within given number of hours from now.

### suppress_alert_type(self,
alert_type:
str,
duration_hours:
int) -> bool
 - Temporarily suppress creation/notification of any new instance(s) of this type. Returns True if OK.

### get_suppressed_alerts(self) -> List[AlertSuppression]
 - Return list describing all currently-active suppressions by type/reason/until time window etc.

### cleanup_old_alerts(self ,days_old:int=30 ) -> int
 - Delete old resolved/closed-out records that are older than given days threshold; returns count removed

### get_alert_statistics(self ,days:int=7 ) -> AlertStats 
 - Collect statistics on recent activity over days specified into an AlertStats result object

### escalate_unresolved_alerts( self,hours_old:int=2 ) -> List[Alert]
  - Find still-active high/critical unresolved issues after threshold time-window; marks and returns those escalated

### _is_alert_suppressed( self ,alert_type:str ) -> bool 
  - Utility to check whether any valid suppression block exists right now for requested category

### _document_to_alert( self ,doc :Dict ) -> Alert 
   - Convert raw Mongo document/dict into typed Alert model object