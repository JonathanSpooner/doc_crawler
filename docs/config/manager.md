### ConfigurationChangeHandler(manager: 'ConfigurationManager')
- `manager`: Configuration manager instance to receive change notifications.

#### on_modified(self, event)
- `event`: Filesystem event representing a file modification.

---
### ConfigurationManager(config_dir: Path = Path("config"), auto_reload: bool = False, validator_timeout: int = 10)
- `config_dir`: Directory where configuration files are located.
- `auto_reload`: Enable or disable hot reloading of configuration files.
- `validator_timeout`: Time in seconds to wait for validation tasks.

#### config(self) -> BaseConfiguration
- Returns the current loaded configuration (thread-safe).

#### get_site_config(self, site_name: str) -> Optional[Any]
- `site_name`: Name of the site for which to retrieve configuration; returns config or None.

#### register_change_callback(self, callback: Callable[[BaseConfiguration], None])
- `callback`: Function called when the configuration changes; receives new configuration as argument.

#### unregister_change_callback(self, callback: Callable[[BaseConfiguration], None])
- `callback`: Registered change notification function to remove.

#### reload_configuration(self, environment: Optional[Environment] = None, validate: bool = True) -> bool
- `environment`: (Optional) Target environment to load; defaults to current if not specified.
- `validate`: Whether the new config should be validated before being applied.
  
#### update_runtime_config(self, updates: Dict[str, Any], validate: bool = True) -> bool
- `updates`: Dictionary with keys/values reflecting config attributes and their new values.
- `validate`: Whether updated config should be validated after applying changes.

#### get_masked_config(self) -> Dict[str, Any]
- Returns a dictionary with sensitive values masked in current loaded config.

#### shutdown(self)
- Shuts down background watchers and prepares manager for app shutdown/disposal.

---
#### _load_initial_configuration(self)
No arguments. Loads initial app/config state synchronously during setup/init flow.

#### _setup_hot_reloading(self)
Sets up filesystem monitoring only if allowed by current environment/configuration state (internal use).

#### _handle_config_change(self, file_path: Path)
 - 'file_path': Path object referring to changed YAML file handled by async logic internally. 

#### _schedule_reload(self)
Schedules an asynchronous reload operation from threadsafe context (internal use).

#### _notify_change_callbacks(self, new_config: BaseConfiguration)
 - 'new_config': New full-app/BaseConfiguration model used as arg for registered callbacks after reloading/updating internal state. 

#### _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]
 - 'base': The master/default dictionary underpinning existing settings/state.
 - 'override': A second dictionary providing key/value overrides that will recursively merge into base settings/dict before constructing a candidate replacement/applying updates atomically.