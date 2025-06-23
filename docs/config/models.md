### Environment(str, Enum)
- `DEVELOPMENT`: Development environment option.
- `STAGING`: Staging environment option.
- `PRODUCTION`: Production environment option.

### LogLevel(str, Enum)
- `DEBUG`: Debug logging level.
- `INFO`: Info logging level.
- `WARNING`: Warning logging level.
- `ERROR`: Error logging level.
- `CRITICAL`: Critical error logging level.

### NotificationLevel(str, Enum)
- `LOW`: Low notification severity.
- `MEDIUM`: Medium notification severity.
- `HIGH`: High notification severity.
- `CRITICAL`: Critical notification severity.

### DatabaseConfiguration(url, pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=3600, echo=False)
- `url`: Database connection URL as SecretStr (required).
- `pool_size`: Connection pool size (default 5).
- `max_overflow`: Max overflow connections (default 10).
- `pool_timeout`: Pool timeout in seconds (default 30).
- `pool_recycle`: Pool recycle time in seconds (default 3600).
- `echo`: Enable SQL query logging (default False).

#### validate_database_url(v: SecretStr) -> SecretStr
 - 'v': The database URL to validate for correctness.

### LoggingConfiguration(level=..., format='...', file_path=None, max_bytes=10485760, backup_count=5, structured=False,
crawler_level=..., config_level=..., database_level=...)
 - 'level': Global log verbosity (`LogLevel` enum; default INFO).
 - 'format': Log message format string. 
 - 'file_path': Path for log output file if any. 
 - 'max_bytes': Maximum single log file size in bytes. 
 - 'backup_count': Number of backup files retained. 
 - 'structured': Enable structured/JSON logs if True. 
 - 'crawler_level', 'config_level', 'database_level': Subsystem-specific log levels (`LogLevel` enums).

### SecurityConfiguration(api_key=None, secret_key=..., token_expiry=3600,
rate_limit_per_minute=60, allowed_hosts=[], cors_origins=[])
 - ‘api_key’: Optional API authentication key as SecretStr.  
 - ‘secret_key’: Main app signing key as SecretStr.  
 - ‘token_expiry’: Token lifetime in seconds; default 3600  
 - ‘rate_limit_per_minute’: API rate limit/min; default 60    
 - ‘allowed_hosts’: List of allowed host/domain patterns    
 - ‘cors_origins’: List of allowed CORS origins    

#### validate_host_patterns(v: List[str]) -> List[str]
   *v*: Each host pattern string to validate for proper format/wildcards.

#### validate_cors_origins_patterns(v: List[str]) -> List[str]
   *v*: Each CORS origin URL string for validation against http(s) origin regex.

### CrawlingConfiguration(
    default_delay = ..., max_concurrent_requests = ..., request_timeout = ..., max_retries = ...,
    retry_delay = ..., user_agent = ..., respect_robots_txt = ..., max_page_size = ...,
    allowed_content_types = {"text/html", "application/xhtml+xml"},
    min_delay = ..., burst_delay = ...,
    max_pages_per_domain = ...
)
   *All parameters have defaults and type/description hints.*

#### validate_delays(v: float, info) -> float
   *v*: Delay numeric value being validated per field context ('info.field_name').

### EmailConfiguration(
    smtp_server,... smtp_port,... username,... password,... use_tls=True,
    from_address,... recipients...
 )
   *smtp_server*: Hostname of SMTP server  
   *smtp_port*: Port integer; defaults to 587   
   *username/password*: SMTP credentials         
   *use_tls*: Use TLS boolean                   
   *from_address*: From email address           
   *recipients*: To/alert recipient email list

#### validate_email_addresses(v: List[str]) -> List[str]
*Each recipient address is validated as an email.*

### SlackConfiguration(webhook_url,... channel='#alerts', username='PhilosophyCrawler', icon_emoji=':robot_face:', mention_users=list())
*webhook_url:* Slack webhook url as SecretStr        
*channel:* Channel string                         
*username:* Bot display name                       
*icon_emoji:* Emoji code                          
*mention_users:* Optional users list              

### NotificationConfiguration(
     enabled=True,
     email=None,
     slack=None,
     error_threshold=10,...
     failure_rate_threshold=.1,...
     queue_size_threshold=1000,...
     quiet_hours_start=None,...
     quiet_hours_end=None,...
     max_alerts_per_hour = 5
 )
 – All sub-settings and threshold details are annotated above –

#### validate_notification_settings(self) -> NotificationConfiguration
 Ensures at least one method is enabled if notifications are active and checks that quiet hours aren’t identical.

### URLPattern(pattern:str,type:str="regex",description:str|None=None)
– pattern: Regex or glob pattern          
– type: Type indicator “regex” or “glob” 
– description: Optional text             

#### validate_pattern(v:str,info) → str
 Validates regex syntax for the pattern value.

### ContentSelector(name:str , selector:str , type="css" , required=False , multiple=False )
– name : Identifier                
– selector : CSS/XPath rule       
– type : “css” / “xpath”           
– required : Selector is mandatory?
– multiple : Select all matches?   

---

### SiteConfiguration(
      name,path,..,[full field list omitted],..content_selectors=[],title_selector="title",
      author_selector=None,date_selector=None,..[many other fields documented above]..
 )

 – See class fields inline above –

#### validate_domains(cls,v:list)->list
 Validates domain strings per spec /doesn’t allow malformed domains/

#### validate_site_configuration(self)->SiteConfiguration
 Verifies base url’s netloc matches one domain from the domains list and ensures unique content selectors.

---

### BaseConfiguration( BaseSettings subclass—all sections combined )
 – All keys listed/described above –
 – Inherits hierarchical loading support from pydantic_settings.BaseSettings –

#### validate_hot_reload(cls,v,bool/info)->bool
 Allows hot reload only when not in production at configuration manager layer

#### apply_defaults_and_validate(cls,values:any)->any [Model Validator before instantiation]
 Does pre-instantiation logic—enforces constraints by environment/debug/hotreload consistency etc., applies relevant file path defaults if needed

##### mask_sensitive_values(self)->dict[str:any]
 Returns a model_dump() dictionary with secrets masked out using preset sensitive paths logic