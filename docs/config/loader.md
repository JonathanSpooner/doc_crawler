### ConfigurationLoader(config_dir: Path = Path("config"))
- `config_dir`: Directory containing configuration files.

### load_configuration(environment: Optional[Environment] = None, overrides: Optional[Dict[str, Any]] = None) -> BaseConfiguration
- `environment`: Target environment (auto-detected if None).
- `overrides`: Runtime configuration overrides.

### _load_environment_variables() -> Dict[str, Any]
- No parameters. Loads mapped environment variables into config structure.

### _detect_environment() -> Environment
- No parameters. Detects which environment is active using env vars or config files.

### _load_base_configuration() -> Dict[str, Any]
- No parameters. Loads base configuration from file.

### _load_environment_configuration(environment: Environment) -> Optional[Dict[str, Any]]
- `environment`: The target environment to load (e.g., production).

### _load_site_configurations() -> Dict[str, SiteConfiguration]
- No parameters. Loads all site-specific configurations from directory.

### _load_yaml_file(file_path: Path) -> Dict[str, Any]
- `file_path`: Path to the YAML file to load and parse.

### _load_json_file(file_path: Path) -> Dict[str, Any]
- `file_path`: Path to the JSON file to load and parse.

### _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]
- `base`: The base dictionary.
- `override`: Dictionary whose values will override those in the base.