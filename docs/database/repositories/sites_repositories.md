### SitesRepository(connection_string: str, db_name: str)
- `connection_string`: MongoDB connection URI string.
- `db_name`: Name of the MongoDB database.

#### create(connection_string: str, db_name: str)
- `connection_string`: MongoDB connection URI string.
- `db_name`: Name of the MongoDB database.

#### _setup_indexes(self)
- No parameters. Sets up indexes for the sites collection.

#### create_site(self, site_config: SiteConfiguration) -> ObjectId
- `site_config`: Site configuration data object to be created.

#### get_active_sites(self) -> List[Site]
- No parameters. Returns all active sites marked for crawling.

#### get_site_by_domain(self, domain: str) -> Optional[Site]
- `domain`: Domain name to search for as a string.

#### update_crawl_settings(self, site_id: ObjectId, settings: Dict) -> bool
- `site_id`: Unique identifier (ObjectId) of the site.
- `settings`: Dictionary of crawl settings to update (e.g., delay).

#### disable_site(self, site_id: ObjectId, reason: str) -> bool
- `site_id`: Unique identifier (ObjectId) of the site.
- `reason`: Reason for disabling as a string.

#### get_sites_for_crawl_schedule(self, schedule_type: str) -> List[Site]
- `schedule_type`: Type of schedule (e.g., 'daily', 'weekly') as a string.

#### update_site_health_status(self, site_id: ObjectId, status: str) -> bool
- `site_id`: Unique identifier (ObjectId) of the site.
- `status`: Health status value ('healthy', 'unhealthy', etc.).

#### get_crawl_configuration(self, site_id: ObjectId) -> Optional[Dict]
- `site_id`: Unique identifier (ObjectId) of the desired site configuration.

#### _document_to_site(self, doc: Dict) -> Site
 -`doc`: Raw dictionary document from MongoDB representing a single site's data.