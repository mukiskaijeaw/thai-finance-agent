import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from companion_engine import cycle_spending_alert


class CycleAlertTests(unittest.TestCase):
    def test_warns_when_spending_ahead_of_pace(self):
        request={'cycle_start':'2026-11-01','next_income_date':'2026-12-01',
                 'spending_budget':'9000','spent_to_date':'6000','spending_complete':True}
        result=cycle_spending_alert(request,date(2026,11,10))
        self.assertEqual(result['status'],'AT_RISK')
        self.assertEqual(result['remaining'],'3000')
        self.assertEqual(result['daily_remaining'],'142.85')

    def test_no_complete_data_no_verdict(self):
        self.assertEqual(cycle_spending_alert({},date(2026,11,10))['status'],'INSUFFICIENT_DATA')

    def test_budget_exhausted(self):
        request={'cycle_start':'2026-11-01','next_income_date':'2026-12-01',
                 'spending_budget':'9000','spent_to_date':'9000','spending_complete':True}
        self.assertEqual(cycle_spending_alert(request,date(2026,11,10))['status'],'EXHAUSTED')
