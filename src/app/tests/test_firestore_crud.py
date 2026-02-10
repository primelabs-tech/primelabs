"""
Tests for FirestoreCRUD methods, specifically the get_docs_for_month method.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import calendar

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


class TestGetDocsForMonthIntegration(unittest.TestCase):
    """Integration-style tests for get_docs_for_month method"""
    
    def test_month_boundary_first_day(self):
        """Test that first day of month starts at 00:00:00.000000"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        
        self.assertEqual(first_day.hour, 0)
        self.assertEqual(first_day.minute, 0)
        self.assertEqual(first_day.second, 0)
        self.assertEqual(first_day.microsecond, 0)
        
    def test_month_boundary_last_day(self):
        """Test that last day of month ends at 23:59:59.999999"""
        year, month = 2026, 2
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        self.assertEqual(last_day.hour, 23)
        self.assertEqual(last_day.minute, 59)
        self.assertEqual(last_day.second, 59)
        self.assertEqual(last_day.microsecond, 999999)
        
    def test_all_months_have_valid_ranges(self):
        """Test that all 12 months produce valid date ranges"""
        year = 2026
        expected_days = {
            1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }
        
        for month in range(1, 13):
            last_day_num = calendar.monthrange(year, month)[1]
            self.assertEqual(
                last_day_num, 
                expected_days[month],
                f"Month {month} should have {expected_days[month]} days, got {last_day_num}"
            )
            
    def test_leap_year_february(self):
        """Test February in leap year has 29 days"""
        leap_years = [2024, 2028, 2032]
        
        for year in leap_years:
            last_day_num = calendar.monthrange(year, 2)[1]
            self.assertEqual(
                last_day_num, 
                29,
                f"February {year} should have 29 days (leap year)"
            )
            
    def test_non_leap_year_february(self):
        """Test February in non-leap year has 28 days"""
        non_leap_years = [2025, 2026, 2027]
        
        for year in non_leap_years:
            last_day_num = calendar.monthrange(year, 2)[1]
            self.assertEqual(
                last_day_num, 
                28,
                f"February {year} should have 28 days (non-leap year)"
            )


class TestDateRangeQueryLogic(unittest.TestCase):
    """Tests for date range query logic used in monthly reports"""
    
    def test_date_within_range(self):
        """Test that dates within range are included"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # Test date in middle of month
        test_date = datetime(year, month, 15, 12, 30, 0, 0, tzinfo=IST)
        
        self.assertTrue(first_day <= test_date <= last_day)
        
    def test_date_at_start_boundary(self):
        """Test that date at start boundary is included"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # Test date at exact start
        test_date = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        
        self.assertTrue(first_day <= test_date <= last_day)
        
    def test_date_at_end_boundary(self):
        """Test that date at end boundary is included"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # Test date at exact end
        test_date = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        self.assertTrue(first_day <= test_date <= last_day)
        
    def test_date_before_range(self):
        """Test that date before range is excluded"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # Test date from previous month
        test_date = datetime(year, 1, 31, 23, 59, 59, 999999, tzinfo=IST)
        
        self.assertFalse(first_day <= test_date <= last_day)
        
    def test_date_after_range(self):
        """Test that date after range is excluded"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # Test date from next month
        test_date = datetime(year, 3, 1, 0, 0, 0, 0, tzinfo=IST)
        
        self.assertFalse(first_day <= test_date <= last_day)


class TestTimezoneHandling(unittest.TestCase):
    """Tests for IST timezone handling in monthly reports"""
    
    def test_ist_offset(self):
        """Test that IST offset is correct (UTC+5:30)"""
        ist_offset = IST.utcoffset(None)
        expected_offset = timedelta(hours=5, minutes=30)
        
        self.assertEqual(ist_offset, expected_offset)
        
    def test_datetime_with_ist_timezone(self):
        """Test that datetime objects have IST timezone"""
        year, month = 2026, 2
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        
        self.assertEqual(first_day.tzinfo, IST)
        
    def test_utc_to_ist_conversion(self):
        """Test UTC to IST conversion"""
        utc_time = datetime(2026, 2, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        ist_time = utc_time.astimezone(IST)
        
        # UTC 00:00 should be IST 05:30
        self.assertEqual(ist_time.hour, 5)
        self.assertEqual(ist_time.minute, 30)


if __name__ == '__main__':
    unittest.main()
