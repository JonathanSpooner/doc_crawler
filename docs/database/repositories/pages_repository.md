### PageStats(total: int, processed: int, unprocessed: int, last_crawled: datetime = None)
- `total`: Total number of pages.
- `processed`: Number of processed pages.
- `unprocessed`: Number of unprocessed pages.
- `last_crawled`: Timestamp of the last crawled page (optional).

### Page(id: ObjectId = None, site_id: ObjectId = None, url: str = None, title: str = None, content: str = None, content_hash: str = None, author: str = None, published_date: datetime = None, processing_status: str = "pending", **kwargs)
- `id`: Unique identifier for the page (optional).
- `site_id`: Identifier for the related site (optional).
- `url`: Page URL string (optional).
- `title`: Title text (optional).
- `content`: Content text of the page (optional).
- `content_hash`: Hash for deduplication purposes (optional).
- `author`: Name of the author (optional).
- `published_date`: Publication date/time info (optional).
- `processing_status`: Processing state string; defaults to "pending".
- Other keyword arguments accepted as metadata.

### PageCreate(site_id: ObjectId, url: str, title: str = None, content: str = None, author: str = None, published_date: datetime = None)
- `site_id`: Identifier for the related site.
- `url`: URL string to associate with this page.
- `title`: Title text to assign at creation time (optional). 
 - `content`: Textual content for this page at creation time (optional). 
 - `author`: Main author name(s) info at creation time  (optional). 
 - `published_date`: When this document was published (optional). 

### PagesRepository(connection_string: str, db_name: str, sites_repository)
 - `connection_string`: MongoDB connection URI. 
 - `db_name`: Database name string. 
 - `sites_repository`: SitesRepository instance associated with this repository.

#### @classmethod
#### PagesRepository.create(connection_string:str , db_name:str , sites_repository )
  - `connection_string`: MongoDB connection URI.  
  -`db_name`: The database name string.  
  -`sites_repository` : Reference SitesRepository instance.

#### PagesRepository._setup_indexes(self)
 - Sets up indexes used by MongoDB collection; no external parameters.

#### PagesRepository._normalize_url(self,url:str)->str
  -`url`: The original URL needing normalization and cleaning before storage or comparison.

#### PagesRepository.create_page(self,page_data :PageCreate )->ObjectId
   –`page_data`: Data object containing all required information needed to create a new page record.

#### PagesRepository.get_page_by_url(self,url :str )->Optional[Page]
   –`url`: A single complete URL pointing to one document.

#### PagesRepository.update_page_content(self,page_id:ObjectId ,content:str ,content_hash:str )->bool
   –`page_id`: Identifier referencing an existing stored document/page record in DB.  
   –`content`: New textual body/content value replacing previous entry.  
   –`content_hash` : Registration hash representing/uniquely identifying provided content argument.

#### PagesRepository.get_pages_by_site(self ,site_id:ObjectId ,limit:int=1000 ) -> List[Page]
    – `site_id` : The unique identifier code referring back to a particular web/crawl source/platform/site set groupings/pages together within DB context .
    –`limit` : Integer controlling returned records paging/batch-volume size cap .

#### PagesRepository.get_pages_modified_since(self ,site_id:ObjectId,since :datetime ) -> List[Page]
    --`site_id`: Site grouping foreign key restriction/scoping results set .
    --`since` =datetime from which only newer-last-modified entries are considered .

#### PagesRepository.mark_page_processed(self,page_id:ObjectId ,
processing_info :Dict ) -> bool
     --`page_id ` Reference id matched against primary key or document/object-id lookup on collection .
     --`processing_info ` Arbitrary dict-of-metadata tied/contextualized with workflow/analysis outcome details .

 ####PagesRepository.get_unprocessed_pages( self , site_id:ObjectId=None ) ->List[Page ]
     -- `site_id ` Optional filter limiting returned list only belonging/linked-to one parent grouping/site . Omitted means scan/global retrieval through available records matching un-finished status .

 ####PagesRepository.check_content_exists( self , content_hash:str )   ->bool
      --`content_hash ` SHA256 computed hash-checking/integrity parameter searched against known values already in system state/store base . 

 ####PagesRepository.get_pages_by_author( self, author_name:str ) -> List[Page]
      --author_name String partial/full pattern match driving case-insensitive search over authors field in all records held within current context/scoped view/set .

 ####PagesRepository.bulk_update_processing_status(self, page_ids: List [ObjectId], status: str ) -> int

      --page_ids Bulk reference keys/id`s representing multiple documents targeted by operation/update together at once batch-run/group-wide scope level .
      --status State transition value assigned across selected/matched batches.

#####PagesRepository.get_page_statistics( self, site _id: ObjectId ) -> PageStats

       --site _id Foreign-key specifying target logical grouping/scoping field restricting computation/query shaping meta-result set extracted/statistics-reported-on accordingly .

#####PagesRepository._document_to_page(
self,
doc :
Dict )
-> Page

        --- doc Raw low-level mongo/document dictionary structure needing conversion/wrapping/mapping into defined strong typed/app-layered explicit model format per codebase convention/refactoring best practices ruleset requirements .