### CircuitBreaker(config: CircuitBreakerConfig)
- `config`: Configuration settings for the circuit breaker (thresholds, timeouts).

#### can_execute(self) -> bool
- Returns whether an operation can be executed based on current circuit breaker state.

#### record_success(self)
- Records a successful operation attempt, updating the state as needed.

#### record_failure(self)
- Records a failed operation attempt, updating the state as needed.

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
- `connection_string`: MongoDB URI used to connect.
- `db_name`: Target database name.
- `collection_name`: Target collection name.
- `max_pool_size`: Maximum connections allowed in pool.
- `min_pool_size`: Minimum number of connections maintained in pool.
- `max_idle_time_ms`: Time (ms) before idle pooled connections are closed.
- `connect_timeout_ms`: Connection timeout (ms).
- `socket_timeout_ms`: Socket timeout (ms).
- `server_selection_timeout_ms`: MongoDB server selection timeout (ms).
- `retry_writes`: Whether to enable retryable writes.
- `w`: Write concern value or string ("majority" etc.).
- `read_preference`: Read preference mode.

#### health_check(self) -> Awaitable[bool]
- Performs a database health check and returns result asynchronously.

#### _sanitize_input(self, data: Dict) -> Dict
- Sanitizes input dictionary by stripping potentially dangerous keys/values recursively.

#### _generate_content_hash(self, content: str) -> str
- Generates SHA256 hash string from provided content string.

#### _convert_object_ids(self, data)
 - Recursively converts ObjectId instances within input to strings for serialization.

#### _validate_object_id(self, obj_id: str) -> ObjectId
 - Validates and converts a string into BSON ObjectId type; raises if invalid.

#### _with_retry(
   self,
   operation: Callable[[], Awaitable[Any]],
   max_retries:int=3, base_delay=float=1.0, max_delay=float=60.0, exponential_base=float=2.0
 ) -> Awaitable[Any]
 - Executes an async operation with retry logic and backoff delay; handles transient DB/network failures.

#### insert_one(self, document: Dict, validate=True) -> Awaitable[str]
 - Inserts one document into collection; returns inserted ID as string; validates if specified.

#### find_one(
     self,
     query : Dict ,
     projection : Optional[Dict] = None 
 ) -> Awaitable[Optional[Dict]]
 - Finds one matching document by query with optional projection fields.

#### find_many(
     self ,
     query : Dict ,
     projection : Optional[Dict]=None , 
     sort : Optional[List[tuple]] = None ,
     limit : Optional[int ]=None , 
     skip : Optional[int ]=None  
 ) -> Awaitable[List [Dict]]
 - Finds multiple documents matching query with optional sort/limit/skip/projection options.

#### update_one(
   self , 
   query : Dict , 
   update_data : Dict , 
   upsert=False , 
   validate=True  
 ) -> Awaitable [bool]
 - Updates first matching document using $set; returns true if changed/upserted.

#### update_many(
      self ,
      query : Dict ,
      update_data : Dict ,
      validate=True      
 ) ->Awaitable [int ]
 - Updates all matching documents using $set; returns count modified.

#### delete_one(
        self ,
        query:req.Dict   
 )->Awaitable [bool ]
 - Deletes first matching document by sanitized query dict; returns true if deleted

#### delete_many (
       self ,
       query:req.Dict   
 )->Awaitable[int ]
 - Deletes all matching documents by sanitized query dict ;returns count deleted 

 #### insert_many (
         self ,    
         documents¨List [Dict ],
         validate¨True     
 )->Await able<List[str]>
 – Inserts multiple docs (list). Returns list of inserted IDs as strings

  
 #### find_paginated (
        self ,name=query:Object,int skip,int limit.,sort=None )
– Finds docs w/pagination .Returns paginated result set+metadata dict.
      

##### aggregate( s elf,pipeline,List(Dict)) → Awaitab le[List(Dict)]//
 – Runs aggregation p ipeline,list,result sa s list(dict)
         

##### transaction(s elf )
 –Context manager for MongoDB session-based transact ion.Yields session
 
   

###### update_page_and_clear_task( sel f,page_id:str,,update_data:D ict task_query:D ic t)->A wait ab le[b o ol]/////
–Performs atomic transactional op:update page & clear proc essing task .Returns success boolean.

##### get_collection_stats( s elf)->Awaita ble[D ict ]
–Fetches basic stats about physical collect ion size/storage/index/doc sizes.

##### close( se lf)
/* Closes client/pool connection */