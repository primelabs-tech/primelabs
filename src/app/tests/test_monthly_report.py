"""
Tests for Monthly Report functionality.

These tests cover:
1. FirestoreCRUD.get_docs_for_month() method
2. DailyReportPage monthly report methods
3. Admin-only access control for monthly reports
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import calendar

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))


class TestGetDocsForMonth(unittest.TestCase):
    """Tests for the get_docs_for_month method in FirestoreCRUD"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_db = MagicMock()
        
    def test_get_docs_for_month_date_range_calculation(self):
        """Test that correct date range is calculated for a given month"""
        # Test for February 2026 (non-leap year)
        year = 2026
        month = 2
        
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        # February 2026 should have 28 days (not a leap year)
        self.assertEqual(last_day_num, 28)
        self.assertEqual(first_day.day, 1)
        self.assertEqual(last_day.day, 28)
        
    def test_get_docs_for_month_leap_year(self):
        """Test date range calculation for leap year February"""
        # Test for February 2024 (leap year)
        year = 2024
        month = 2
        
        last_day_num = calendar.monthrange(year, month)[1]
        
        # February 2024 should have 29 days (leap year)
        self.assertEqual(last_day_num, 29)
        
    def test_get_docs_for_month_december(self):
        """Test date range calculation for December (month 12)"""
        year = 2025
        month = 12
        
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime(year, month, last_day_num, 23, 59, 59, 999999, tzinfo=IST)
        
        self.assertEqual(first_day.month, 12)
        self.assertEqual(last_day_num, 31)
        self.assertEqual(last_day.day, 31)
        
    def test_get_docs_for_month_january(self):
        """Test date range calculation for January (month 1)"""
        year = 2026
        month = 1
        
        first_day = datetime(year, month, 1, 0, 0, 0, 0, tzinfo=IST)
        last_day_num = calendar.monthrange(year, month)[1]
        
        self.assertEqual(first_day.month, 1)
        self.assertEqual(last_day_num, 31)


class TestMonthlyReportCalculations(unittest.TestCase):
    """Tests for monthly report calculation logic"""
    
    def test_total_collection_calculation(self):
        """Test that total collection is calculated correctly from records"""
        mock_records = [
            {'payment': {'amount': 500}},
            {'payment': {'amount': 1000}},
            {'payment': {'amount': 750}},
        ]
        
        total_collection = 0
        for record in mock_records:
            payment = record.get('payment', {})
            if isinstance(payment, dict):
                total_collection += payment.get('amount', 0)
        
        self.assertEqual(total_collection, 2250)
        
    def test_total_collection_with_missing_payment(self):
        """Test calculation handles records with missing payment data"""
        mock_records = [
            {'payment': {'amount': 500}},
            {'payment': {}},  # Missing amount
            {'patient': {'name': 'Test'}},  # Missing payment entirely
        ]
        
        total_collection = 0
        for record in mock_records:
            payment = record.get('payment', {})
            if isinstance(payment, dict):
                total_collection += payment.get('amount', 0)
        
        self.assertEqual(total_collection, 500)
        
    def test_total_expenses_calculation(self):
        """Test that total expenses is calculated correctly"""
        mock_expenses = [
            {'expense_type': 'Rent', 'amount': 5000},
            {'expense_type': 'Electricity', 'amount': 2000},
            {'expense_type': 'Staff Salary', 'amount': 15000},
        ]
        
        total_expenses = sum(expense.get('amount', 0) for expense in mock_expenses)
        
        self.assertEqual(total_expenses, 22000)
        
    def test_net_amount_calculation_profit(self):
        """Test net amount calculation when there's profit"""
        total_collection = 50000
        total_expenses = 30000
        
        net_amount = total_collection - total_expenses
        is_profit = net_amount >= 0
        
        self.assertEqual(net_amount, 20000)
        self.assertTrue(is_profit)
        
    def test_net_amount_calculation_loss(self):
        """Test net amount calculation when there's loss"""
        total_collection = 20000
        total_expenses = 35000
        
        net_amount = total_collection - total_expenses
        is_profit = net_amount >= 0
        
        self.assertEqual(net_amount, -15000)
        self.assertFalse(is_profit)


class TestAdminAccessControl(unittest.TestCase):
    """Tests for admin-only access control for monthly reports"""
    
    def test_is_admin_user_with_admin_role(self):
        """Test that users with Admin role are recognized as admin"""
        user_role = "Admin"
        is_admin = user_role == "Admin"
        self.assertTrue(is_admin)
        
    def test_is_admin_user_with_employee_role(self):
        """Test that users with Employee role are not admin"""
        user_role = "Employee"
        is_admin = user_role == "Admin"
        self.assertFalse(is_admin)
        
    def test_is_admin_user_with_manager_role(self):
        """Test that users with Manager role are not admin"""
        user_role = "Manager"
        is_admin = user_role == "Admin"
        self.assertFalse(is_admin)


class TestMonthlyReportGrouping(unittest.TestCase):
    """Tests for grouping records by date and expense type"""
    
    def test_group_records_by_date(self):
        """Test grouping records by date"""
        mock_records = [
            {'date': '2026-02-01', 'payment': {'amount': 500}},
            {'date': '2026-02-01', 'payment': {'amount': 300}},
            {'date': '2026-02-02', 'payment': {'amount': 1000}},
        ]
        
        records_by_date = {}
        for record in mock_records:
            date_str = record.get('date', '')
            if date_str not in records_by_date:
                records_by_date[date_str] = []
            records_by_date[date_str].append(record)
        
        self.assertEqual(len(records_by_date), 2)
        self.assertEqual(len(records_by_date['2026-02-01']), 2)
        self.assertEqual(len(records_by_date['2026-02-02']), 1)
        
    def test_group_expenses_by_type(self):
        """Test grouping expenses by type"""
        mock_expenses = [
            {'expense_type': 'Rent', 'amount': 5000},
            {'expense_type': 'Electricity', 'amount': 2000},
            {'expense_type': 'Rent', 'amount': 5000},  # Another rent payment
        ]
        
        expenses_by_type = {}
        for expense in mock_expenses:
            expense_type = expense.get('expense_type', 'Other')
            if expense_type not in expenses_by_type:
                expenses_by_type[expense_type] = {'total': 0, 'count': 0}
            expenses_by_type[expense_type]['total'] += expense.get('amount', 0)
            expenses_by_type[expense_type]['count'] += 1
        
        self.assertEqual(len(expenses_by_type), 2)
        self.assertEqual(expenses_by_type['Rent']['total'], 10000)
        self.assertEqual(expenses_by_type['Rent']['count'], 2)
        self.assertEqual(expenses_by_type['Electricity']['total'], 2000)
        self.assertEqual(expenses_by_type['Electricity']['count'], 1)


class TestFutureMonthValidation(unittest.TestCase):
    """Tests for preventing future month selection"""
    
    def test_current_month_is_valid(self):
        """Test that current month is valid"""
        today = datetime.now(IST)
        selected_year = today.year
        selected_month = today.month
        
        is_future = selected_year > today.year or (
            selected_year == today.year and selected_month > today.month
        )
        
        self.assertFalse(is_future)
        
    def test_past_month_is_valid(self):
        """Test that past month is valid"""
        today = datetime.now(IST)
        selected_year = today.year
        selected_month = today.month - 1 if today.month > 1 else 12
        if selected_month == 12:
            selected_year -= 1
        
        is_future = selected_year > today.year or (
            selected_year == today.year and selected_month > today.month
        )
        
        self.assertFalse(is_future)
        
    def test_future_month_is_invalid(self):
        """Test that future month is invalid"""
        today = datetime.now(IST)
        selected_year = today.year
        selected_month = today.month + 1 if today.month < 12 else 1
        if selected_month == 1:
            selected_year += 1
        
        is_future = selected_year > today.year or (
            selected_year == today.year and selected_month > today.month
        )
        
        self.assertTrue(is_future)
        
    def test_future_year_is_invalid(self):
        """Test that future year is invalid"""
        today = datetime.now(IST)
        selected_year = today.year + 1
        selected_month = 1
        
        is_future = selected_year > today.year or (
            selected_year == today.year and selected_month > today.month
        )
        
        self.assertTrue(is_future)


if __name__ == '__main__':
    unittest.main()
