### HistoricalDate(year, month, day, hour=0, minute=0, second=0, microsecond=0)
- `year`: Year in astronomical numbering (1 BCE = 0, 2 BCE = -1, 1 CE = 1).
- `month`: Month (1-12).
- `day`: Day of month.
- `hour`: Hour (0-23).
- `minute`: Minute (0-59).
- `second`: Second (0-59).
- `microsecond`: Microsecond.

### _create_pendulum_dt()
- No parameters.

### _ensure_pendulum_dt_initialized()
- No parameters.

### validate_date_and_create_pendulum()
- No parameters.

### from_ce_bce(year: int, era: Era, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0)
- `year`: The year in CE/BCE notation (positive integer).
- `era`: CE or BCE.
- `month`: Month (1-12).
- `day`: Day of month.
- `hour`: Hour (0-23).
- `minute`: Minute (0-59).
- `second`: Second (0-59).
- `microsecond`: Microsecond (0-999999).

### parse_date_string(date_str: str)
- `date_str`: The date string to parse.

### era()
- No parameters.

### ce_bce_year()
- No parameters.

### astronomical_year()
- No parameters.

### to_ce_bce_string(format_str: str = "{year} {era}")
- `format_str`: Format string with {year} and {era} placeholders.

### add_years(years: int)
- `years`: Number of years to add.

### add_months(months: int)
- `months`: Number of months to add.

### add_days(days: int)
- `days`: Number of days to add.

### difference_in_years(other: 'HistoricalDate')
- `other`: The other HistoricalDate object to compare with.

### difference_in_days(other: 'HistoricalDate')
- `other`: The other HistoricalDate object to compare with.

### is_leap_year()
- No parameters.

### format(format_str: str)
- `format_str`: The format string used by pendulum for formatting.

### __str__()
- No parameters.

### __repr__()
- No parameters.

### __lt__(other: 'HistoricalDate')
- `other`: The other HistoricalDate object for comparison.

### __le__(other: 'HistoricalDate')
- `other`: The other HistoricalDate object for comparison.

### __gt__(other: 'HistoricalDate')
- `other`: The other HistoricalDate object for comparison.

### __ge__(other: 'HistoricalDate')
- `other`: The other HistoricalDate object for comparison.

### __eq__(other: object)
- `other`: The other object for equality comparison.