import unittest
import json
from unittest.mock import patch, MagicMock
import pendulum
from pydantic import ValidationError, PrivateAttr

from doc_crawler.database.models.historical_date import HistoricalDate, Era

class TestEra(unittest.TestCase):
    """Test cases for Era enumeration"""
    
    def test_era_values(self):
        """Test Era enum values"""
        self.assertEqual(Era.CE.value, "CE")
        self.assertEqual(Era.BCE.value, "BCE")
    
    def test_era_string_conversion(self):
        """Test Era enum string conversion"""
        self.assertEqual(Era.CE, "CE")
        self.assertEqual(Era.BCE, "BCE")
    
    def test_era_equality(self):
        """Test Era enum equality"""
        self.assertEqual(Era.CE, "CE")
        self.assertEqual(Era.BCE, "BCE")


class TestHistoricalDate(unittest.TestCase):
    """Test cases for HistoricalDate class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_ce_date = {
            'year': 1,
            'month': 1,
            'day': 1
        }
        self.valid_bce_date = {
            'year': -1,  # 2 BCE
            'month': 12,
            'day': 31
        }
    
    def test_basic_construction_ce(self):
        """Test basic construction with CE date"""
        date = HistoricalDate(**self.valid_ce_date)
        self.assertEqual(date.year, 1)
        self.assertEqual(date.month, 1)
        self.assertEqual(date.day, 1)
        self.assertEqual(date.hour, 0)
        self.assertEqual(date.minute, 0)
        self.assertEqual(date.second, 0)
        self.assertEqual(date.microsecond, 0)
    
    def test_basic_construction_bce(self):
        """Test basic construction with BCE date"""
        date = HistoricalDate(**self.valid_bce_date)
        self.assertEqual(date.year, -1)
        self.assertEqual(date.month, 12)
        self.assertEqual(date.day, 31)
    
    def test_construction_with_time(self):
        """Test construction with time components"""
        date = HistoricalDate(
            year=100,
            month=6,
            day=15,
            hour=14,
            minute=30,
            second=45,
            microsecond=123456
        )
        self.assertEqual(date.hour, 14)
        self.assertEqual(date.minute, 30)
        self.assertEqual(date.second, 45)
        self.assertEqual(date.microsecond, 123456)
    
    def test_invalid_month(self):
        """Test validation with invalid month"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=13, day=1)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=0, day=1)
    
    def test_invalid_day(self):
        """Test validation with invalid day"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=32)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=0)
    
    def test_invalid_hour(self):
        """Test validation with invalid hour"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, hour=24)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, hour=-1)
    
    def test_invalid_minute(self):
        """Test validation with invalid minute"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, minute=60)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, minute=-1)
    
    def test_invalid_second(self):
        """Test validation with invalid second"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, second=60)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, second=-1)
    
    def test_invalid_microsecond(self):
        """Test validation with invalid microsecond"""
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, microsecond=1000000)
        
        with self.assertRaises(ValidationError):
            HistoricalDate(year=1, month=1, day=1, microsecond=-1)
    
    def test_invalid_date_combination(self):
        """Test validation with invalid date combinations"""
        # February 30th
        with self.assertRaises(ValueError):
            HistoricalDate(year=1, month=2, day=30)
        
        # April 31st
        with self.assertRaises(ValueError):
            HistoricalDate(year=1, month=4, day=31)
    
    def test_pendulum_dt_creation(self):
        """Test that internal pendulum datetime is created correctly"""
        date = HistoricalDate(year=100, month=3, day=15)
        self.assertIsNotNone(date._pendulum_dt)
        self.assertIsInstance(date._pendulum_dt, pendulum.DateTime)


class TestHistoricalDateClassMethods(unittest.TestCase):
    """Test class methods of HistoricalDate"""
    
    def test_from_ce_bce_ce_date(self):
        """Test from_ce_bce with CE date"""
        date = HistoricalDate.from_ce_bce(
            year=100,
            era=Era.CE,
            month=3,
            day=15
        )
        self.assertEqual(date.year, 100)
        self.assertEqual(date.month, 3)
        self.assertEqual(date.day, 15)
        self.assertEqual(date.era, Era.CE)
    
    def test_from_ce_bce_bce_date(self):
        """Test from_ce_bce with BCE date"""
        date = HistoricalDate.from_ce_bce(
            year=44,
            era=Era.BCE,
            month=3,
            day=15
        )
        self.assertEqual(date.year, -43)  # 44 BCE = -43 astronomical
        self.assertEqual(date.month, 3)
        self.assertEqual(date.day, 15)
        self.assertEqual(date.era, Era.BCE)
    
    def test_from_ce_bce_year_1_bce(self):
        """Test from_ce_bce with 1 BCE (year 0)"""
        date = HistoricalDate.from_ce_bce(
            year=1,
            era=Era.BCE,
            month=12,
            day=31
        )
        self.assertEqual(date.year, 0)  # 1 BCE = 0 astronomical
        self.assertEqual(date.era, Era.BCE)
    
    def test_from_ce_bce_with_time(self):
        """Test from_ce_bce with time components"""
        date = HistoricalDate.from_ce_bce(
            year=50,
            era=Era.CE,
            month=6,
            day=15,
            hour=14,
            minute=30,
            second=45,
            microsecond=123456
        )
        self.assertEqual(date.hour, 14)
        self.assertEqual(date.minute, 30)
        self.assertEqual(date.second, 45)
        self.assertEqual(date.microsecond, 123456)
    
    def test_from_ce_bce_invalid_year(self):
        """Test from_ce_bce with invalid year"""
        with self.assertRaises(ValueError):
            HistoricalDate.from_ce_bce(
                year=0,
                era=Era.CE,
                month=1,
                day=1
            )
        
        with self.assertRaises(ValueError):
            HistoricalDate.from_ce_bce(
                year=-1,
                era=Era.BCE,
                month=1,
                day=1
            )
    
    @patch('pendulum.parse')
    def test_parse_date_string_bce(self, mock_parse):
        """Test parse_date_string with BCE date"""
        mock_dt = MagicMock()
        mock_dt.year = 44
        mock_dt.month = 3
        mock_dt.day = 15
        mock_dt.hour = 0
        mock_dt.minute = 0
        mock_dt.second = 0
        mock_dt.microsecond = 0
        mock_parse.return_value = mock_dt
        
        date = HistoricalDate.parse_date_string("March 15, 44 BCE")
        self.assertEqual(date.year, -43)  # 44 BCE = -43 astronomical
        self.assertEqual(date.era, Era.BCE)
    
    @patch('pendulum.parse')
    def test_parse_date_string_ce(self, mock_parse):
        """Test parse_date_string with CE date"""
        mock_dt = MagicMock()
        mock_dt.year = 100
        mock_dt.month = 1
        mock_dt.day = 1
        mock_dt.hour = 0
        mock_dt.minute = 0
        mock_dt.second = 0
        mock_dt.microsecond = 0
        mock_parse.return_value = mock_dt
        
        date = HistoricalDate.parse_date_string("100 CE")
        self.assertEqual(date.year, 100)
        self.assertEqual(date.era, Era.CE)
    
    @patch('pendulum.parse')
    def test_parse_date_string_bc_format(self, mock_parse):
        """Test parse_date_string with BC format"""
        mock_dt = MagicMock()
        mock_dt.year = 50
        mock_dt.month = 6
        mock_dt.day = 15
        mock_dt.hour = 0
        mock_dt.minute = 0
        mock_dt.second = 0
        mock_dt.microsecond = 0
        mock_parse.return_value = mock_dt
        
        date = HistoricalDate.parse_date_string("50 BC")
        self.assertEqual(date.year, -49)  # 50 BC = -49 astronomical
        self.assertEqual(date.era, Era.BCE)
    
    @patch('pendulum.parse')
    def test_parse_date_string_default_ce(self, mock_parse):
        """Test parse_date_string defaults to CE when no era specified"""
        mock_dt = MagicMock()
        mock_dt.year = 2023
        mock_dt.month = 1
        mock_dt.day = 1
        mock_dt.hour = 0
        mock_dt.minute = 0
        mock_dt.second = 0
        mock_dt.microsecond = 0
        mock_parse.return_value = mock_dt
        
        date = HistoricalDate.parse_date_string("2023-01-01")
        self.assertEqual(date.year, 2023)
        self.assertEqual(date.era, Era.CE)
    
    @patch('pendulum.parse')
    def test_parse_date_string_parse_error(self, mock_parse):
        """Test parse_date_string with parsing error"""
        mock_parse.side_effect = Exception("Parse error")
        
        with self.assertRaises(ValueError):
            HistoricalDate.parse_date_string("invalid date")


class TestHistoricalDateProperties(unittest.TestCase):
    """Test properties of HistoricalDate"""
    
    def test_era_property_ce(self):
        """Test era property for CE dates"""
        date = HistoricalDate(year=100, month=1, day=1)
        self.assertEqual(date.era, Era.CE)
    
    def test_era_property_bce(self):
        """Test era property for BCE dates"""
        date = HistoricalDate(year=-50, month=1, day=1)
        self.assertEqual(date.era, Era.BCE)
    
    def test_era_property_year_zero(self):
        """Test era property for year 0 (1 BCE)"""
        date = HistoricalDate(year=0, month=1, day=1)
        self.assertEqual(date.era, Era.BCE)
    
    def test_ce_bce_year_property_ce(self):
        """Test ce_bce_year property for CE dates"""
        date = HistoricalDate(year=100, month=1, day=1)
        self.assertEqual(date.ce_bce_year, 100)
    
    def test_ce_bce_year_property_bce(self):
        """Test ce_bce_year property for BCE dates"""
        date = HistoricalDate(year=-43, month=1, day=1)
        self.assertEqual(date.ce_bce_year, 44)  # -43 astronomical = 44 BCE
    
    def test_ce_bce_year_property_year_zero(self):
        """Test ce_bce_year property for year 0"""
        date = HistoricalDate(year=0, month=1, day=1)
        self.assertEqual(date.ce_bce_year, 1)  # 0 astronomical = 1 BCE
    
    def test_astronomical_year_property(self):
        """Test astronomical_year property"""
        date = HistoricalDate(year=-43, month=1, day=1)
        self.assertEqual(date.astronomical_year, -43)
        self.assertEqual(date.astronomical_year, date.year)


class TestHistoricalDateFormatting(unittest.TestCase):
    """Test formatting methods of HistoricalDate"""
    
    def test_to_ce_bce_string_default(self):
        """Test to_ce_bce_string with default format"""
        date = HistoricalDate(year=-43, month=3, day=15)
        result = date.to_ce_bce_string()
        self.assertEqual(result, "44 BCE")
    
    def test_to_ce_bce_string_custom_format(self):
        """Test to_ce_bce_string with custom format"""
        date = HistoricalDate(year=100, month=1, day=1)
        result = date.to_ce_bce_string("Year {year} {era}")
        self.assertEqual(result, "Year 100 CE")
    
    def test_str_representation(self):
        """Test __str__ method"""
        date = HistoricalDate(year=-43, month=3, day=15)
        self.assertEqual(str(date), "44 BCE")
        
        date_ce = HistoricalDate(year=100, month=1, day=1)
        self.assertEqual(str(date_ce), "100 CE")
    
    def test_repr_representation(self):
        """Test __repr__ method"""
        date = HistoricalDate(year=-43, month=3, day=15)
        expected = "HistoricalDate(year=-43, month=3, day=15, era=BCE)"
        self.assertEqual(repr(date), expected)
    
    def test_format_method(self):
        """Test format method"""
        date = HistoricalDate(year=100, month=3, day=15)
        # This test assumes the format method works with the internal pendulum datetime
        result = date.format("YYYY-MM-DD")
        self.assertIsInstance(result, str)


class TestHistoricalDateArithmetic(unittest.TestCase):
    """Test arithmetic operations on HistoricalDate"""
    
    def test_add_years_positive(self):
        """Test adding positive years"""
        date = HistoricalDate(year=100, month=3, day=15)
        new_date = date.add_years(50)
        self.assertEqual(new_date.year, 150)
        self.assertEqual(new_date.month, 3)
        self.assertEqual(new_date.day, 15)
    
    def test_add_years_negative(self):
        """Test adding negative years"""
        date = HistoricalDate(year=100, month=3, day=15)
        new_date = date.add_years(-50)
        self.assertEqual(new_date.year, 50)
        self.assertEqual(new_date.month, 3)
        self.assertEqual(new_date.day, 15)
    
    def test_add_years_cross_bce_ce_boundary(self):
        """Test adding years across BCE/CE boundary"""
        date = HistoricalDate(year=-5, month=6, day=15)  # 6 BCE
        new_date = date.add_years(10)
        self.assertEqual(new_date.year, 5)  # 5 CE
        self.assertEqual(new_date.era, Era.CE)
    
    def test_add_months_same_year(self):
        """Test adding months within same year"""
        date = HistoricalDate(year=100, month=3, day=15)
        new_date = date.add_months(3)
        self.assertEqual(new_date.year, 100)
        self.assertEqual(new_date.month, 6)
        self.assertEqual(new_date.day, 15)
    
    def test_add_months_cross_year(self):
        """Test adding months across year boundary"""
        date = HistoricalDate(year=100, month=10, day=15)
        new_date = date.add_months(6)
        self.assertEqual(new_date.year, 101)
        self.assertEqual(new_date.month, 4)
        self.assertEqual(new_date.day, 15)
    
    def test_add_months_negative(self):
        """Test adding negative months"""
        date = HistoricalDate(year=100, month=6, day=15)
        new_date = date.add_months(-3)
        self.assertEqual(new_date.year, 100)
        self.assertEqual(new_date.month, 3)
        self.assertEqual(new_date.day, 15)
    
    def test_add_days_same_month(self):
        """Test adding days within same month"""
        date = HistoricalDate(year=100, month=3, day=15)
        new_date = date.add_days(10)
        self.assertEqual(new_date.year, 100)
        self.assertEqual(new_date.month, 3)
        self.assertEqual(new_date.day, 25)
    
    def test_add_days_cross_month(self):
        """Test adding days across month boundary"""
        date = HistoricalDate(year=100, month=3, day=25)
        new_date = date.add_days(10)
        self.assertEqual(new_date.year, 100)
        self.assertEqual(new_date.month, 4)
        self.assertEqual(new_date.day, 4)
    
    def test_add_days_negative(self):
        """Test adding negative days"""
        date = HistoricalDate(year=100, month=3, day=15)
        new_date = date.add_days(-10)
        self.assertEqual(new_date.year, 100)
        self.assertEqual(new_date.month, 3)
        self.assertEqual(new_date.day, 5)
    
    def test_add_methods_with_uninitialized_pendulum(self):
        """Test add_months and add_days with uninitialized pendulum datetime"""
        date = HistoricalDate(year=100, month=3, day=15)
        date._pendulum_dt = PrivateAttr()
        
        with self.assertRaises(ValueError):
            date.add_months(1)
        
        with self.assertRaises(ValueError):
            date.add_days(1)


class TestHistoricalDateComparisons(unittest.TestCase):
    """Test comparison operations on HistoricalDate"""
    
    def test_difference_in_years(self):
        """Test difference_in_years calculation"""
        date1 = HistoricalDate(year=100, month=1, day=1)
        date2 = HistoricalDate(year=150, month=1, day=1)
        
        diff = date1.difference_in_years(date2)
        self.assertEqual(diff, 50)
        
        diff_reverse = date2.difference_in_years(date1)
        self.assertEqual(diff_reverse, -50)
    
    def test_difference_in_years_bce_ce(self):
        """Test difference_in_years across BCE/CE boundary"""
        bce_date = HistoricalDate(year=-49, month=1, day=1)  # 50 BCE
        ce_date = HistoricalDate(year=50, month=1, day=1)   # 50 CE
        
        diff = bce_date.difference_in_years(ce_date)
        self.assertEqual(diff, 99)  # 50 BCE to 50 CE = 99 years
    
    def test_difference_in_days_same_year(self):
        """Test difference_in_days within same year"""
        date1 = HistoricalDate(year=100, month=1, day=1)
        date2 = HistoricalDate(year=100, month=1, day=31)
        
        diff = date1.difference_in_days(date2)
        self.assertEqual(diff, 30)
    
    def test_difference_in_days_fallback(self):
        """Test difference_in_days with fallback calculation"""
        date1 = HistoricalDate(year=100, month=1, day=1)
        date2 = HistoricalDate(year=101, month=1, day=1)
        
        # Set pendulum_dt to None to force fallback
        date1._pendulum_dt = None
        date2._pendulum_dt = None
        
        diff = date1.difference_in_days(date2)
        self.assertEqual(diff, 365)  # Approximate


class TestHistoricalDateOperators(unittest.TestCase):
    """Test comparison operators of HistoricalDate"""
    
    def setUp(self):
        """Set up test dates"""
        self.early_date = HistoricalDate(year=100, month=1, day=1)
        self.late_date = HistoricalDate(year=200, month=1, day=1)
        self.same_date = HistoricalDate(year=100, month=1, day=1)
        self.same_year_later = HistoricalDate(year=100, month=6, day=1)
    
    def test_less_than(self):
        """Test less than operator"""
        self.assertTrue(self.early_date < self.late_date)
        self.assertFalse(self.late_date < self.early_date)
        self.assertFalse(self.early_date < self.same_date)
        self.assertTrue(self.early_date < self.same_year_later)
    
    def test_less_than_equal(self):
        """Test less than or equal operator"""
        self.assertTrue(self.early_date <= self.late_date)
        self.assertTrue(self.early_date <= self.same_date)
        self.assertFalse(self.late_date <= self.early_date)
    
    def test_greater_than(self):
        """Test greater than operator"""
        self.assertTrue(self.late_date > self.early_date)
        self.assertFalse(self.early_date > self.late_date)
        self.assertFalse(self.early_date > self.same_date)
        self.assertTrue(self.same_year_later > self.early_date)
    
    def test_greater_than_equal(self):
        """Test greater than or equal operator"""
        self.assertTrue(self.late_date >= self.early_date)
        self.assertTrue(self.early_date >= self.same_date)
        self.assertFalse(self.early_date >= self.late_date)
    
    def test_equality(self):
        """Test equality operator"""
        self.assertTrue(self.early_date == self.same_date)
        self.assertFalse(self.early_date == self.late_date)
        self.assertFalse(self.early_date == "not a date")
        self.assertFalse(self.early_date == None)
    
    def test_detailed_time_comparison(self):
        """Test comparison with detailed time components"""
        date1 = HistoricalDate(year=100, month=1, day=1, hour=10, minute=30)
        date2 = HistoricalDate(year=100, month=1, day=1, hour=10, minute=31)
        
        self.assertTrue(date1 < date2)
        self.assertFalse(date1 == date2)


class TestHistoricalDateUtilityMethods(unittest.TestCase):
    """Test utility methods of HistoricalDate"""
    
    def test_is_leap_year_divisible_by_4(self):
        """Test leap year for years divisible by 4"""
        date = HistoricalDate(year=2000, month=1, day=1)
        self.assertTrue(date.is_leap_year())
        
        date = HistoricalDate(year=2004, month=1, day=1)
        self.assertTrue(date.is_leap_year())
    
    def test_is_leap_year_not_divisible_by_4(self):
        """Test leap year for years not divisible by 4"""
        date = HistoricalDate(year=2001, month=1, day=1)
        self.assertFalse(date.is_leap_year())
        
        date = HistoricalDate(year=2003, month=1, day=1)
        self.assertFalse(date.is_leap_year())
    
    def test_is_leap_year_century_not_divisible_by_400(self):
        """Test leap year for century years not divisible by 400"""
        date = HistoricalDate(year=1900, month=1, day=1)
        self.assertFalse(date.is_leap_year())
        
        date = HistoricalDate(year=1800, month=1, day=1)
        self.assertFalse(date.is_leap_year())
    
    def test_is_leap_year_divisible_by_400(self):
        """Test leap year for years divisible by 400"""
        date = HistoricalDate(year=2000, month=1, day=1)
        self.assertTrue(date.is_leap_year())
        
        date = HistoricalDate(year=1600, month=1, day=1)
        self.assertTrue(date.is_leap_year())
    
    def test_is_leap_year_bce_dates(self):
        """Test leap year for BCE dates"""
        date = HistoricalDate(year=-3, month=1, day=1)  # 4 BCE
        self.assertTrue(date.is_leap_year())
        
        date = HistoricalDate(year=-2, month=1, day=1)  # 3 BCE
        self.assertFalse(date.is_leap_year())


class TestHistoricalDateSerialization(unittest.TestCase):
    """Test serialization and JSON functionality"""
    
    def test_model_dump(self):
        """Test model dump functionality"""
        date = HistoricalDate(year=100, month=3, day=15, hour=10, minute=30)
        dumped = date.model_dump()
        
        expected_keys = ['year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond']
        for key in expected_keys:
            self.assertIn(key, dumped)
        
        self.assertEqual(dumped['year'], 100)
        self.assertEqual(dumped['month'], 3)
        self.assertEqual(dumped['day'], 15)
        self.assertEqual(dumped['hour'], 10)
        self.assertEqual(dumped['minute'], 30)
    
    def test_model_dump_json(self):
        """Test JSON serialization"""
        date = HistoricalDate(year=100, month=3, day=15)
        json_str = date.model_dump_json()
        
        # Parse back to verify
        parsed = json.loads(json_str)
        self.assertEqual(parsed['year'], 100)
        self.assertEqual(parsed['month'], 3)
        self.assertEqual(parsed['day'], 15)
    
    def test_model_validate_json(self):
        """Test JSON deserialization"""
        json_data = '{"year": 100, "month": 3, "day": 15, "hour": 10}'
        date = HistoricalDate.model_validate_json(json_data)
        
        self.assertEqual(date.year, 100)
        self.assertEqual(date.month, 3)
        self.assertEqual(date.day, 15)
        self.assertEqual(date.hour, 10)
    
    def test_exclude_private_field(self):
        """Test that private _pendulum_dt field is excluded from serialization"""
        date = HistoricalDate(year=100, month=3, day=15)
        dumped = date.model_dump()
        
        self.assertNotIn('_pendulum_dt', dumped)


class TestHistoricalDateEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_year_zero(self):
        """Test year 0 (1 BCE)"""
        date = HistoricalDate(year=0, month=1, day=1)
        self.assertEqual(date.year, 0)
        self.assertEqual(date.era, Era.BCE)
        self.assertEqual(date.ce_bce_year, 1)
    
    def test_very_large_positive_year(self):
        """Test very large positive year"""
        date = HistoricalDate(year=9999, month=1, day=1)
        self.assertEqual(date.year, 9999)
        self.assertEqual(date.era, Era.CE)
    
    def test_very_large_negative_year(self):
        """Test very large negative year"""
        date = HistoricalDate(year=-9998, month=1, day=1)
        self.assertEqual(date.year, -9998)
        self.assertEqual(date.era, Era.BCE)
        self.assertEqual(date.ce_bce_year, 9999)
    
    def test_february_29_leap_year(self):
        """Test February 29 in leap year"""
        date = HistoricalDate(year=2000, month=2, day=29)
        self.assertEqual(date.day, 29)
        self.assertTrue(date.is_leap_year())
    
    def test_february_29_non_leap_year(self):
        """Test February 29 in non-leap year (should fail)"""
        with self.assertRaises(ValueError):
            HistoricalDate(year=1900, month=2, day=29)
    
    def test_boundary_months(self):
        """Test boundary months (1 and 12)"""
        date_jan = HistoricalDate(year=100, month=1, day=15)
        date_dec = HistoricalDate(year=100, month=12, day=15)
        
        self.assertEqual(date_jan.month, 1)
        self.assertEqual(date_dec.month, 12)
    
    def test_boundary_days(self):
        """Test boundary days"""
        date_first = HistoricalDate(year=100, month=1, day=1)
        date_last = HistoricalDate(year=100, month=1, day=31)
        
        self.assertEqual(date_first.day, 1)
        self.assertEqual(date_last.day, 31)
    
    def test_boundary_time_components(self):
        """Test boundary time components"""
        date = HistoricalDate(
            year=100, month=1, day=1,
            hour=23, minute=59, second=59, microsecond=999999
        )
        
        self.assertEqual(date.hour, 23)
        self.assertEqual(date.minute, 59)
        self.assertEqual(date.second, 59)
        self.assertEqual(date.microsecond, 999999)
    
    def test_copy_and_update(self):
        """Test model_copy with updates"""
        original = HistoricalDate(year=100, month=1, day=1)
        updated = original.model_copy(update={'year': 200})
        
        self.assertEqual(original.year, 100)
        self.assertEqual(updated.year, 200)
        self.assertEqual(updated.month, 1)
        self.assertEqual(updated.day, 1)


class TestHistoricalDateIntegration(unittest.TestCase):
    """Integration tests with real scenarios"""
    
    def test_historical_events_timeline(self):
        """Test with real historical events"""
        caesar_death = HistoricalDate.from_ce_bce(44, Era.BCE, 3, 15)
        augustus_birth = HistoricalDate.from_ce_bce(63, Era.BCE, 9, 23)
        christ_birth = HistoricalDate.from_ce_bce(1, Era.CE, 12, 25)
        
        # Verify chronological order
        self.assertTrue(augustus_birth < caesar_death)
        self.assertTrue(caesar_death < christ_birth)
        
        # Verify time differences
        self.assertEqual(
            augustus_birth.difference_in_years(caesar_death),
            19
        )
        self.assertEqual(
            caesar_death.difference_in_years(christ_birth),
            44
        )
    
    def test_bce_ce_boundary_crossing(self):
        """Test calculations across BCE/CE boundary"""
        bce_date = HistoricalDate(year=-5, month=6, day=15)  # 6 BCE
        ce_date = bce_date.add_years(10)  # Should be 5 CE
        
        self.assertEqual(ce_date.year, 5)
        self.assertEqual(ce_date.era, Era.CE)
        self.assertEqual(ce_date.month, 6)
        self.assertEqual(ce_date.day, 15)
    
    def test_complex_date_arithmetic(self):
        """Test complex date arithmetic scenarios"""
        base_date = HistoricalDate(year=100, month=1, day=1)
        
        # Add various time units
        result = base_date.add_years(5).add_months(6).add_days(15)
        
        self.assertEqual(result.year, 105)
        self.assertEqual(result.month, 7)
        self.assertEqual(result.day, 16)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEra,
        TestHistoricalDate,
        TestHistoricalDateClassMethods,
        TestHistoricalDateProperties,
        TestHistoricalDateFormatting,
        TestHistoricalDateArithmetic,
        TestHistoricalDateComparisons,
        TestHistoricalDateOperators,
        TestHistoricalDateUtilityMethods,
        TestHistoricalDateSerialization,
        TestHistoricalDateEdgeCases,
        TestHistoricalDateIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")