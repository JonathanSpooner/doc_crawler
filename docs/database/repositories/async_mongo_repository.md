### CircuitBreakerConfig(failure_threshold: int = 5, recovery_timeout: int = 60, success_threshold: int = 3)
- `failure_threshold`: Number of failures before opening the circuit.
- `recovery_timeout`: Seconds to wait before moving from OPEN to HALF_OPEN state.
- `success_threshold`: Required successes in HALF_OPEN to close the circuit.

### CircuitBreaker(config: CircuitBreakerConfig)
- `config`: Configuration object for the circuit breaker.

#### can_execute(self) -> bool
- No parameters. Returns whether operations are allowed based on current state.

#### record_success(self)
- No parameters. Records a successful operation and updates state accordingly.

#### record_failure(self)
- No parameters. Records a failed operation and updates state accordingly.

### AsyncMongoDBRepository(
    connection_string: str,
    db_name: str,
    collection_name: str,
    max_pool_size: int = 100,
    min_pool_size: int = 10,
    max_idle_time_ms: int = 30000,
    connect_timeout_ms: int = 10000,
    socket_timeout_ms: int = 5000,
    server_selection_timeout_ms: int = 30000,
    retry_writes: bool = True,
    w: Union[int, str] = "majority",
    read_preference: str = "primaryPreferred"
)
- `connection_string`: MongoDB URI string.
- `db_name`: Database name.
- `collection_name`: Collection name within database.
- `max_pool_size`: Maximum connections in pool.
- `min_pool_size`: Minimum connections in pool.
- `max_idle_time_ms`: Max idle time for connections (ms).
- `connect_timeout_ms`: Timeout for initial connection (ms).
- `socket_timeout_ms`: Timeout for sockets (ms).
- `server_selection_timeout_ms`: How long to try servers (ms).
- `retry_writes`: Whether retryable writes enabled.
- `w`: Write concern; can be integer or string ("majority", etc.).
- `read_preference`: Read preference strategy ("primary", etc.).

#### health_check(self) -> Awaitable[bool]
 - No parameters. Returns True if the DB is healthy, else False.

#### _sanitize_input(self, data: Dict) -> Dict
 - 'data': Input dictionary to sanitize against injection attacks.

#### _generate_content_hash(self, content: str) -> str
 - 'content': String content used for hash generation.

#### _convert_object_ids(self, data: Any) -> Any
 - 'data': Data structure with possible ObjectIds; converts them recursively to strings.

#### _validate_object_id(self, obj_id: str) -> ObjectId
 - 'obj_id': ID string expected as valid MongoDB ObjectId or raises ValidationError on invalid input.

#### _with_retry(
        self,
        operation: Callable[[], Awaitable[Any]],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay=float(60.0),
        exponential_base=float(2.0))
-> Awaitable[Any]
 - 'operation': Async callable representing the action to retry upon failure.
 - 'max_retries': Maximum number of attempts on failure before giving up.
 - 'base_delay': Initial delay between retries in seconds.
 - 'max_delay': Maximum delay between retries in seconds after backoff growth stops increasing it further.
 - ‘exponential_base’: Multiplier applied per attempt when calculating backoff duration.

#### insert_one(
      self, document : Dict ,
      validate : bool=True ) -> Awaitable[str]
   - ‘document’: The document dictionary that will be inserted into collection .
   - ‘validate’ : If true , input gets sanitized .

 #### find_one (
     self , query : Dict ,
     projection : Optional [Dict ]=None )
      -> Awaitable[Optional [Dict]]
   – ‘query’ dictionary specifying search conditions .
   – ‘projection’ optional dict specifying fields returned .

 #### find_many (
     self , query : Dict ,
     projection : Optional [Dict ]=None ,
     sort : Optional [List [tuple]]=None ,
     limit:int=None , skip:int=None )
       →Awaitable[List[Dict]]
   – ‘query’ dict filter;
   – ‘projection’ optional field selector;
   – ‘sort ’ list of key/direction tuples;
   – ’limit ’ maximum docs;
   – ’skip ’ offset .

 #### update_one (
     self , query : Dict ,
     update_data_:Dict ,
     upsert_:bool=False ,
     validate_:bool=True ) 
         →Awaitable[bool]
   --‘query’, filter dict ;
   --‘update_data’, changes ;
   --'upsert', create if missing?;
   --'validate', sanitize fields

 #### update_many (
    self , query_:{dict} , update_data:{dict} , validate:{bool}=True )→Awaitable[int]
-- Query filters docs updated ; 
-- Update_data values set ;
-- Whether inputs are sanitized .

 ##### delete_one (
    self,, query:{dict})->Awaitable[boo l ]
—Query identifies which doc .

##### delete_many(
self,,query:{dict })->Awaitabl e[int ]
—Filter deletes matching documents.

##### insert_many(
self,,documents:[list],validate=True)->Awaita ble[List[str]] 
—Docs inserted ; each gets validated if requested.

##### find_paginated(
self.,query{dict},skip:int,l imit:int,sort=(Opt)[list])→Aw aitab le[{str:any}]
–Filter/docs returned with pagination and metadata info.

##### aggregate (
self,pipeline:[Li st[dic t]])-> Awa i table[List[d ic t] ]
–Aggregation pipeline applied ; returns processed results.

##### transaction (self )  
–Async context manager yielding session object used inside with blocks .

 ##### update_page_and_clear_task(
self,page_id:str,u pdate_da ta::{d ict } task_query::d ict )
 →Await able[b oo l]
 —Atomically updates page then removes processing queue task using transaction.

 ##### create_indexes (se lf.,indexes::Lis t[dic t ])
 —Bulk index creation.; indexes specify keys(+options).

##### get_collection_stats(s elf )  
—No params.; returns size/usage/indexes info dict.

###### close(se lf):
–No params; closes Mongo client connection cleanly .