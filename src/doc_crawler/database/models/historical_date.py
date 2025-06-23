"""
Historical Date Library using Pendulum and Pydantic v2
Handles CE/BCE dates with astronomical year numbering (1 BCE = year 0)
"""
from enum import Enum

import pendulum
from pydantic import BaseModel, PrivateAttr, Field, field_validator, model_validator, ConfigDict


class Era(str, Enum):
    """Era enumeration for CE/BCE"""
    CE = "CE"
    BCE = "BCE"


class HistoricalDate(BaseModel):
    """
    A historical date model that handles CE/BCE dates using astronomical year numbering.
    
    In this system:
    - 1 BCE = astronomical year 0
    - 2 BCE = astronomical year -1
    - 1 CE = astronomical year 1
    - etc.
    
    This eliminates the discontinuity between BCE and CE for calculations.
    """
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={
            pendulum.DateTime: lambda v: v.isoformat()
        }
    )
    
    year: int = Field(..., description="Year in astronomical numbering (1 BCE = 0, 2 BCE = -1, 1 CE = 1)")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    day: int = Field(..., ge=1, le=31, description="Day of month")
    hour: int = Field(default=0, ge=0, le=23, description="Hour (0-23)")
    minute: int = Field(default=0, ge=0, le=59, description="Minute (0-59)")
    second: int = Field(default=0, ge=0, le=59, description="Second (0-59)")
    microsecond: int = Field(default=0, ge=0, le=999999, description="Microsecond")
    
    # Internal pendulum datetime object
    _pendulum_dt: pendulum.DateTime = PrivateAttr()
    
    def _create_pendulum_dt(self) -> pendulum.DateTime:
        """Create a pendulum datetime object from current values"""
        # Convert astronomical year to a year that pendulum can handle
        # For BCE dates (year <= 0), we use the absolute value + 1 for pendulum operations
        display_year = abs(self.year) + 1 if self.year <= 0 else self.year
        
        # Ensure we have a valid year for pendulum (minimum year 1)
        pendulum_year = max(1, display_year)
        
        return pendulum.datetime(
            pendulum_year, self.month, self.day,
            self.hour, self.minute, self.second, self.microsecond
        )
    
    def _ensure_pendulum_dt_initialized(self) -> None:
        """Ensure the internal pendulum datetime is properly initialized"""
        if not hasattr(self, '_pendulum_dt') or not isinstance(self._pendulum_dt, pendulum.DateTime):
            raise ValueError("Internal pendulum datetime is not properly initialized")
    
    @model_validator(mode='after')
    def validate_date_and_create_pendulum(self) -> 'HistoricalDate':
        """Validate the complete date and create internal pendulum datetime object"""
        try:
            self._pendulum_dt = self._create_pendulum_dt()
        except ValueError as e:
            raise ValueError(f"Invalid date components: year={self.year}, month={self.month}, day={self.day} - {e}")
        
        return self
    
    @classmethod
    def from_ce_bce(
        cls, 
        year: int, 
        era: Era, 
        month: int, 
        day: int, 
        hour: int = 0, 
        minute: int = 0, 
        second: int = 0, 
        microsecond: int = 0
    ) -> 'HistoricalDate':
        """
        Create a HistoricalDate from CE/BCE notation
        
        Args:
            year: The year in CE/BCE notation (positive integer)
            era: CE or BCE
            month: Month (1-12)
            day: Day of month
            hour: Hour (0-23)
            minute: Minute (0-59)
            second: Second (0-59)
            microsecond: Microsecond (0-999999)
        """
        if year <= 0:
            raise ValueError("Year must be positive when using CE/BCE notation")
        
        # Convert to astronomical year
        astronomical_year = year if era == Era.CE else -(year - 1)
        
        return cls(
            year=astronomical_year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            microsecond=microsecond
        )
    
    @classmethod
    def parse_date_string(cls, date_str: str) -> 'HistoricalDate':
        """
        Parse various date string formats
        
        Supports formats like:
        - "45 BCE"
        - "23 CE"
        - "March 15, 44 BCE"
        - "44-03-15 BCE"
        """
        import re
        from datetime import datetime
        
        # Try to extract era
        era_match = re.search(r'\b(BCE?|CE?|BC|AD)\b', date_str, re.IGNORECASE)
        era = Era.BCE if era_match and era_match.group().upper() in ['BCE', 'BC'] else Era.CE
        
        # Remove era from string for parsing
        clean_str = re.sub(r'\b(BCE?|CE?|BC|AD)\b', '', date_str, flags=re.IGNORECASE).strip()
        
        # Try different parsing approaches
        try:
            # First, try to extract year, month, day using regex patterns
            year = month = day = hour = minute = second = microsecond = None
            
            # Pattern 1: "March 15, 44" or "March 15 44"
            month_day_year_pattern = r'(\w+)\s+(\d+),?\s+(\d+)'
            match = re.search(month_day_year_pattern, clean_str)
            if match:
                month_name, day_str, year_str = match.groups()
                year = int(year_str)
                day = int(day_str)
                
                # Convert month name to number
                month_names = {
                    'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
                    'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                    'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
                    'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
                    'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
                    'december': 12, 'dec': 12
                }
                month = month_names.get(month_name.lower())
                if month is None:
                    raise ValueError(f"Unknown month name: {month_name}")
            
            # Pattern 2: "44-03-15" or "44/03/15"
            if year is None:
                ymd_pattern = r'(\d+)[-/](\d+)[-/](\d+)'
                match = re.search(ymd_pattern, clean_str)
                if match:
                    year, month, day = map(int, match.groups())
            
            # Pattern 3: Just year "44"
            if year is None:
                year_only_pattern = r'^\s*(\d+)\s*$'
                match = re.search(year_only_pattern, clean_str)
                if match:
                    year = int(match.group(1))
                    month = 1
                    day = 1
            
            # If we still don't have year, month, day, try pendulum as fallback
            if year is None or month is None or day is None:
                # For pendulum parsing, we need to handle the year issue
                # Try to make the year 4-digit for pendulum
                year_match = re.search(r'\b(\d{1,4})\b', clean_str)
                if year_match:
                    original_year = int(year_match.group(1))
                    # Convert to 4-digit year for pendulum parsing
                    if original_year < 100:
                        # Assume years 1-99 are ancient dates
                        modified_year = original_year + 2000  # Use 2000+ as a placeholder
                    else:
                        modified_year = original_year
                    
                    # Replace the year in the string
                    modified_str = clean_str.replace(str(original_year), str(modified_year))
                    
                    try:
                        parsed = pendulum.parse(modified_str)
                        year = original_year
                        month = parsed.month
                        day = parsed.day
                        hour = parsed.hour
                        minute = parsed.minute
                        second = parsed.second
                        microsecond = parsed.microsecond
                    except:
                        raise ValueError("Could not parse date components")
            
            # Set default values if not extracted
            if hour is None:
                hour = 0
            if minute is None:
                minute = 0
            if second is None:
                second = 0
            if microsecond is None:
                microsecond = 0
            
            # Validate we have the required components
            if year is None or month is None or day is None:
                raise ValueError("Could not extract year, month, and day from date string")
            
            # Create the HistoricalDate using from_ce_bce
            return cls.from_ce_bce(
                year, era, month, day, hour, minute, second, microsecond
            )
            
        except Exception as e:
            raise ValueError(f"Unable to parse date string: {date_str} - {e}")
        
    @property
    def era(self) -> Era:
        """Get the era (CE or BCE)"""
        return Era.BCE if self.year <= 0 else Era.CE
    
    @property
    def ce_bce_year(self) -> int:
        """Get the year in CE/BCE notation (always positive)"""
        # For BCE dates (year <= 0): astronomical year 0 = 1 BCE, -1 = 2 BCE, etc.
        # So CE/BCE year = abs(astronomical_year) + 1
        # For CE dates (year > 0): CE/BCE year = astronomical year
        return abs(self.year) + 1 if self.year <= 0 else self.year
    
    @property
    def astronomical_year(self) -> int:
        """Get the astronomical year (same as year property)"""
        return self.year
    
    def to_ce_bce_string(self, format_str: str = "{year} {era}") -> str:
        """
        Format as CE/BCE string
        
        Args:
            format_str: Format string with {year} and {era} placeholders
        """
        return format_str.format(year=self.ce_bce_year, era=self.era.value)
    
    def add_years(self, years: int) -> 'HistoricalDate':
        """Add years to the date (handles BCE/CE boundary correctly)"""
        new_year = self.year + years
        return HistoricalDate(
            year=new_year,
            month=self.month,
            day=self.day,
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            microsecond=self.microsecond
        )
    
    def add_months(self, months: int) -> 'HistoricalDate':
        """Add months to the date"""
        # Ensure the internal pendulum datetime is initialized
        self._ensure_pendulum_dt_initialized()
        
        # Add months using the stored pendulum datetime
        new_dt = self._pendulum_dt.add(months=months)
        
        # Calculate the year difference in pendulum space
        current_pendulum_year = self._pendulum_dt.year
        new_pendulum_year = new_dt.year
        year_diff = new_pendulum_year - current_pendulum_year
        
        # Apply the year difference to our astronomical year
        new_astronomical_year = self.year + year_diff
        
        return HistoricalDate(
            year=new_astronomical_year,
            month=new_dt.month,
            day=new_dt.day,
            hour=new_dt.hour,
            minute=new_dt.minute,
            second=new_dt.second,
            microsecond=new_dt.microsecond
        )
    
    def add_days(self, days: int) -> 'HistoricalDate':
        """Add days to the date"""
        # Ensure the internal pendulum datetime is initialized
        self._ensure_pendulum_dt_initialized()
        
        # Add days using the stored pendulum datetime
        new_dt = self._pendulum_dt.add(days=days)
        
        # Calculate the year difference in pendulum space
        current_pendulum_year = self._pendulum_dt.year
        new_pendulum_year = new_dt.year
        year_diff = new_pendulum_year - current_pendulum_year
        
        # Apply the year difference to our astronomical year
        new_astronomical_year = self.year + year_diff
        
        return HistoricalDate(
            year=new_astronomical_year,
            month=new_dt.month,
            day=new_dt.day,
            hour=new_dt.hour,
            minute=new_dt.minute,
            second=new_dt.second,
            microsecond=new_dt.microsecond
        )
    
    def difference_in_years(self, other: 'HistoricalDate') -> int:
        """Calculate difference in years between two dates"""
        return other.year - self.year
    
    def difference_in_days(self, other: 'HistoricalDate') -> int:
        """Calculate approximate difference in days between two dates"""
        try:
            # Create comparable pendulum dates from current values
            self_dt = self._create_pendulum_dt()
            other_dt = other._create_pendulum_dt()
            
            diff = other_dt - self_dt
            # Adjust for astronomical year differences
            year_adjustment = (other.year - self.year) - (other_dt.year - self_dt.year)
            return diff.days + (year_adjustment * 365)
        except Exception:
            # Fallback to rough approximation
            years_diff = self.difference_in_years(other)
            return years_diff * 365
    
    def is_leap_year(self) -> bool:
        """Check if the year is a leap year"""
        # Convert astronomical year to the actual year for leap year calculation
        # For BCE dates: astronomical year 0 = 1 BCE, -1 = 2 BCE, etc.
        actual_year = abs(self.year) + 1 if self.year <= 0 else self.year
        
        # Use the standard leap year calculation
        if actual_year % 4 != 0:
            return False
        elif actual_year % 100 != 0:
            return True
        elif actual_year % 400 != 0:
            return False
        else:
            return True
    
    def format(self, format_str: str) -> str:
        """Format the date using pendulum formatting"""
        try:
            dt = self._create_pendulum_dt()
            return dt.format(format_str)
        except:
            return str(self)
    
    def __str__(self) -> str:
        """String representation in CE/BCE format"""
        return f"{self.ce_bce_year} {self.era.value}"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"HistoricalDate(year={self.year}, month={self.month}, day={self.day}, era={self.era.value})"
    
    def __lt__(self, other: 'HistoricalDate') -> bool:
        """Less than comparison"""
        return self.year < other.year or (
            self.year == other.year and 
            (self.month, self.day, self.hour, self.minute, self.second, self.microsecond) < 
            (other.month, other.day, other.hour, other.minute, other.second, other.microsecond)
        )
    
    def __le__(self, other: 'HistoricalDate') -> bool:
        """Less than or equal comparison"""
        return self < other or self == other
    
    def __gt__(self, other: 'HistoricalDate') -> bool:
        """Greater than comparison"""
        return not self <= other
    
    def __ge__(self, other: 'HistoricalDate') -> bool:
        """Greater than or equal comparison"""
        return not self < other
    
    def __eq__(self, other: object) -> bool:
        """Equality comparison"""
        if not isinstance(other, HistoricalDate):
            return False
        return (
            self.year == other.year and
            self.month == other.month and
            self.day == other.day and
            self.hour == other.hour and
            self.minute == other.minute and
            self.second == other.second and
            self.microsecond == other.microsecond
        )


# Example usage and testing
if __name__ == "__main__":
    # Create dates using different methods
    
    # Method 1: Direct astronomical year
    caesar_death = HistoricalDate(year=-43, month=3, day=15)  # 44 BCE
    print(f"Caesar's death: {caesar_death}")
    print(f"Astronomical year: {caesar_death.astronomical_year}")
    print(f"CE/BCE format: {caesar_death.to_ce_bce_string()}")
    
    # Method 2: From CE/BCE notation
    augustus_birth = HistoricalDate.from_ce_bce(63, Era.BCE, 9, 23)
    print(f"\nAugustus birth: {augustus_birth}")
    print(f"Astronomical year: {augustus_birth.astronomical_year}")
    
    # Method 3: Parse date strings
    cleopatra_death = HistoricalDate.parse_date_string("August 30, 30 BCE")
    print(f"\nCleopatra death: {cleopatra_death}")
    
    # Date arithmetic
    one_year_later = caesar_death.add_years(1)
    print(f"\nOne year after Caesar's death: {one_year_later}")
    
    # Test complex date arithmetic (the failing test case)
    base_date = HistoricalDate(year=100, month=1, day=1)
    result = base_date.add_years(5).add_months(6).add_days(15)
    print(f"\nComplex arithmetic test:")
    print(f"Base date: {base_date} (year={base_date.year})")
    print(f"After adding 5 years, 6 months, 15 days: {result} (year={result.year})")
    
    # Comparisons
    print(f"\nAugustus born before Caesar died: {augustus_birth < caesar_death}")
    
    # Cross BCE/CE boundary
    christ_birth = HistoricalDate.from_ce_bce(1, Era.CE, 12, 25)  # Traditional date
    print(f"\nChrist birth (traditional): {christ_birth}")
    print(f"Years between Augustus birth and Christ birth: {augustus_birth.difference_in_years(christ_birth)}")
    
    # Test leap year
    leap_year_test = HistoricalDate(year=-3, month=1, day=1)  # 4 BCE
    print(f"\n4 BCE is leap year: {leap_year_test.is_leap_year()}")
    
    # JSON serialization
    print(f"\nJSON representation: {caesar_death.model_dump_json()}")