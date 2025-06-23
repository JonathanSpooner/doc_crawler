### ConfigurationValidator(timeout: int = 10)
- `timeout`: HTTP request timeout in seconds.

### validate_configuration(self, config: BaseConfiguration) -> List[str]
- `config`: Configuration to validate (expects a BaseConfiguration instance).

### _validate_business_rules(self, config: BaseConfiguration) -> tuple[List[str], List[str]]
- `config`: The configuration object to be checked for business rules.

### _validate_site_configurations(self, sites: Dict[str, SiteConfiguration]) -> tuple[List[str], List[str]]
- `sites`: Dictionary mapping site names to their configurations (`SiteConfiguration` objects).

### _validate_external_resources(self, config: BaseConfiguration) -> tuple[List[str], List[str]]
- `config`: The configuration object from which external resources are validated.

### _check_site_accessibility(self, site_name: str, site_config: SiteConfiguration) -> Optional[str]
- `site_name`: Name of the site being checked.
- `site_config`: The site's configuration object (`SiteConfiguration`).