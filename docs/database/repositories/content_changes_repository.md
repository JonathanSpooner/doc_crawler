### ContentChange(id: ObjectId = None, page_id: ObjectId = None, change_type: str = None, site_id: ObjectId = None, **kwargs)
- `id`: Optional unique identifier for the content change.
- `page_id`: Identifier of the associated page.
- `change_type`: Type of change ("new", "modified", "deleted").
- `site_id`: Identifier for the affected site.
- `**kwargs`: Additional attributes (url, title, hashes, priority, notification status/times, context).

### ChangeFrequency(site_id: ObjectId, days_analyzed: int, **kwargs)
- `site_id`: Identifier for the analyzed site.
- `days_analyzed`: Number of days over which analytics are computed.
- `**kwargs`: Additional analytic metrics (total/typed counts per change type/day/trend).

### ContentChangesRepository(connection_string: str, db_name: str, pages_repository: PagesRepository)
- `connection_string`: MongoDB connection string.
- `db_name`: Name of the database to use.
- `pages_repository`: Reference to an existing PagesRepository instance.

### create(connection_string: str, db_name: str, pages_repository: PagesRepository)
- `connection_string`: MongoDB connection string to initialize repository instance.
- `db_name`: Database name for initialization.
- `pages_repository`: Pages repository dependency.

### _setup_indexes(self)
(No parameters)  
Sets up optimal indexes on content_changes collection for query performance.

### _determine_change_priority(self, change_type: str, context: Dict = None) -> str
- `change_type`: The type/classification of detected content change event. 
- 'context': Optional dictionary with extra factors affecting priority assessment.

### record_content_change(self, change: ContentChange) -> ObjectId
 - 'change': The ContentChange object representing a detected event being recorded in storage. 

### get_changes_since(self, site_id: ObjectId, since: datetime) -> List[ContentChange]
 - 'site_id': Targeted site's unique identifier. 
 - 'since': Datetime after which qualifying changes should be returned.

### get_new_pages_today(self, site_id: ObjectId = None) -> List[ContentChange]
 - 'site_id': If provided filters new-page events to a specific site; otherwise all sites are considered. 

### get_modified_pages_summary(self, days:int=7)->Dict[str,int]
 - 'days': Number of most recent days to include in summary aggregations by change type.

### mark_change_notified(self ,change_id:ObjectId)-> bool
  - 'change_id' : Unique identifier for a previously-recorded content-change event whose notification state is being updated.  

### get_unnotified_changes (self ,priority:str=None)->List[ContentChange]
  - ‘priority’: If supplied restricts returned un-notified changes by specified urgency/criticality level—otherwise all priorities included.

### get_change_frequency (self ,site_id:ObjectId ,days:int=30 )-> ChangeFrequency
  - ‘site_id’: Identifier specifying target resource/site across which frequency analytics will be computed 
  - ‘days’ : Analysis window width expressed as integer day-count

 ### cleanup_old_changes( self ,days_old:int=90 )-> int
   - ‘days_old’: Integer cut-off specifying minimum age (in days from now); older records will be purged

 ### _document_to_change( self ,doc : Dict ) -> ContentChange
   - ‘doc’: Raw dict/MongoDB document representing stored event — converted into model object