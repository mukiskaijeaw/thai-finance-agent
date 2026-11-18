import sys
import unittest
import json
import subprocess
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shared_state import financial_context_fallback
from test_goal_planner import inputs,DAY


TODAY=date(2026,11,18)
def row(ident,day,kind,value,category='Other',flag=''):
    return dict(transaction_id=ident,date=day,year_month=day[:7],transaction_type=kind,
                amount_thb=value,category=category,data_quality_flag=flag)


class FinancialFallbackTests(unittest.TestCase):
    def cycle(self,**extra):
        return dict(start='2026-11-01',start_confirmed=True,expenses_complete=True,
                    commitments=[],commitments_complete=True,**extra)

    def test_cycle_income_expenses_without_cash_or_next_payday(self):
        rows=[row('i','2026-11-01','income','15000','Salary'),row('e','2026-11-05','expense','4000'),
              row('r','2026-11-06','income','500','Refund'),row('t','2026-11-07','transfer','1000')]
        result=financial_context_fallback(rows,TODAY,{'cycle':self.cycle()})
        self.assertEqual(result['level'],'ESTIMATED_BUDGET')
        self.assertEqual(result['estimated_budget'],'11500')
        self.assertEqual(result['net_recorded_expenses'],'3500')
        self.assertIsNone(result['current_available_cash'])
        self.assertEqual(result['strict_status'],'INSUFFICIENT_DATA')

    def test_no_cycle_historical_only_never_claims_current_balance(self):
        rows=[row('i','2026-10-01','income','15000'),row('e','2026-10-02','expense','5000')]
        result=financial_context_fallback(rows,TODAY,{'complete_months':['2026-10']})
        self.assertEqual(result['level'],'HISTORICAL_CONTEXT')
        self.assertIsNone(result['estimated_budget']);self.assertIsNone(result['current_available_cash'])
        self.assertEqual(result['history']['monthly_averages']['expense'],'5000.00')

    def test_explicit_receipt_replaces_recorded_income_and_commitments_count_once(self):
        rows=[row('i','2026-11-01','income','15000'),row('e','2026-11-05','expense','4000')]
        cycle=self.cycle(income_received='15000',income_received_confirmed=True)
        cycle['commitments']=[{'id':'paid','amount':'500','confirmed':True,'already_in_expenses':True},
                              {'id':'goal','amount':'1000','confirmed':True,'already_in_expenses':False}]
        result=financial_context_fallback(rows,TODAY,{'cycle':cycle})
        self.assertEqual(result['estimated_budget'],'10000')

    def test_incomplete_or_unreviewed_never_becomes_confirmed_cash(self):
        rows=[row('i','2026-11-01','income','15000'),row('e','2026-11-05','expense','4000',flag='needs_review')]
        result=financial_context_fallback(rows,TODAY,{'cycle':self.cycle()})
        self.assertIsNone(result['estimated_budget']);self.assertIn('cycle_records_need_review',result['issues'])
        rows[1]['data_quality_flag']='';cycle=self.cycle();cycle.pop('commitments')
        result=financial_context_fallback(rows,TODAY,{'cycle':cycle})
        self.assertEqual(result['unadjusted_recorded_remainder'],'11000')
        self.assertIsNone(result['estimated_budget']);self.assertIsNone(result['current_available_cash'])

    def test_salary_profile_is_not_receipt_or_current_cash(self):
        rows=[row('e','2026-11-05','expense','4000')]
        result=financial_context_fallback(rows,TODAY,{'profile':{'income':'15000'},'cycle':self.cycle()})
        self.assertEqual(result['level'],'HISTORICAL_CONTEXT')
        self.assertIn('income_received_not_recorded',result['issues'])

    def test_active_goal_must_be_explicitly_covered(self):
        rows=[row('i','2026-11-01','income','15000'),row('e','2026-11-05','expense','4000')]
        goal={'goal_id':'trip','goal_name':'Trip','goal_category':'travel','target_amount':'6000',
              'saved_amount':'0','target_date':'2026-11-30','funding_source':'unallocated','status':'ACTIVE','allocation_enabled':True}
        cycle=self.cycle()
        result=financial_context_fallback(rows,TODAY,{'cycle':cycle,'goals':[goal]})
        self.assertIsNone(result['estimated_budget']);self.assertIn('active_goal_commitment_missing',result['issues'])
        cycle['commitments']=[{'id':'trip','amount':'1500','confirmed':True,'already_in_expenses':False}]
        result=financial_context_fallback(rows,TODAY,{'cycle':cycle,'goals':[goal]})
        self.assertEqual(result['estimated_budget'],'9500')

    def test_investments_require_overlap_confirmation(self):
        invest=row('fund','2026-11-05','investment','1000');invest['action']='Buy'
        rows=[row('i','2026-11-01','income','15000'),row('e','2026-11-05','expense','4000'),invest]
        cycle=self.cycle();result=financial_context_fallback(rows,TODAY,{'cycle':cycle})
        self.assertIsNone(result['estimated_budget']);self.assertIn('investment_overlap_requires_confirmation',result['issues'])
        cycle['investment_separate_from_expenses']=True
        result=financial_context_fallback(rows,TODAY,{'cycle':cycle})
        self.assertEqual(result['estimated_budget'],'10000')

    def test_confirmed_strict_context_takes_precedence(self):
        p,b=inputs();result=financial_context_fallback([],DAY,{'profile':p,'budget':b})
        self.assertEqual(result['level'],'CONFIRMED_BALANCE')
        self.assertEqual(result['current_available_cash'],'5000')

    def test_context_command_emits_read_only_advisory(self):
        from goal_engine import today_bangkok
        today=today_bangkok();start=today.replace(day=1).isoformat()
        rows=[row('i',start,'income','15000'),row('e',start,'expense','4000')]
        request={'transactions':rows,'financial_context':{'cycle':dict(start=start,start_confirmed=True,
                 expenses_complete=True,commitments=[],commitments_complete=True)}}
        script=Path(__file__).resolve().parents[1]/'scripts'/'shopping.py'
        proc=subprocess.run([sys.executable,str(script),'context'],input=json.dumps(request),capture_output=True,text=True,encoding='utf-8',check=True)
        data=json.loads(proc.stdout)['financial_context']
        self.assertEqual(data['estimated_budget'],'11000');self.assertIsNone(data['current_available_cash'])


if __name__=='__main__':unittest.main()
