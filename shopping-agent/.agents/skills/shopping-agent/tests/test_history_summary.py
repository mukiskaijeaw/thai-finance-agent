import sys
import tempfile
import unittest
import csv
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from shared_state import historical_summary, load_transactions, monthly_shopping_budget
from engine import SCHEMA


def row(i, month, kind, amount, category='', action=''):
    return dict(zip(SCHEMA, [str(i), month+'-01', kind, '', amount, category, action, month, '', '', '', '', '', '']))


class HistoryTests(unittest.TestCase):
    def test_confirmed_months_only_and_no_transfer_double_count(self):
        rows=[row(1,'2026-09','income','1000'),row(2,'2026-09','expense','100','Food'),row(3,'2026-09','transfer','200'),row(4,'2026-10','expense','300','Food'),row(5,'2026-10','investment','50','Fund','Buy')]
        out=historical_summary(rows,date(2026,11,15),['2026-09','2026-10'])
        self.assertEqual(out['monthly_averages']['categories']['Food'],'200.00')
        self.assertEqual(out['monthly_averages']['investment_buy'],'25.00')
        self.assertIsNone(out['current_available_cash'])

    def test_incomplete_and_duplicate_do_not_claim_average(self):
        r=row(1,'2026-10','expense','100','Food')
        self.assertIsNone(historical_summary([r],date(2026,11,15))['monthly_averages'])
        out=historical_summary([r,r],date(2026,11,15),['2026-10'])
        self.assertIsNone(out['monthly_averages'])
        self.assertIn('invalid_or_duplicate_transaction',out['issues'])

    def test_adapter_schema_and_time_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'database.csv'
            with path.open('w',encoding='utf-8',newline='') as f:
                w=csv.DictWriter(f,fieldnames=SCHEMA);w.writeheader();w.writerows([row(1,'2026-07','expense','9'),row(2,'2026-10','expense','8')])
            self.assertEqual(len(load_transactions(tmp,'2026-11',3)),1)
            path.write_text('wrong,header\n',encoding='utf-8')
            with self.assertRaises(ValueError):load_transactions(tmp,'2026-11',3)

    def test_current_month_cannot_be_claimed_complete(self):
        with self.assertRaises(ValueError):historical_summary([],date(2026,11,15),['2026-11'])

    def test_budget_requires_complete_non_overlapping_components(self):
        p=dict(income='30000',essential='12000',other_planned='3000',savings='2000',investments='1000',goals='1000',shopping_spent='500',complete=True,non_overlapping=True)
        result=monthly_shopping_budget(p)
        self.assertEqual(result['monthly_shopping_budget'],'11000.00')
        self.assertEqual(result['remaining_shopping_budget'],'10500.00')
        self.assertIsNone(result['current_available_cash'])
        p['non_overlapping']=False
        self.assertIsNone(monthly_shopping_budget(p)['monthly_shopping_budget'])


if __name__=='__main__': unittest.main()
