import sys
import tempfile
import unittest
import threading
from unittest.mock import patch
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.agents/skills/shopping-agent/scripts'))
from reservations import ReservationStore,planned_budget,planned_after_recorded_expenses,reservation_preview
sys.path.insert(0,str(ROOT))
import dashboard_server as server

class ReservationTests(unittest.TestCase):
    def test_chat_prepares_then_confirms_without_early_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);session={'history':[],'cancel':threading.Event(),'busy':True};job={}
            with patch.object(server,'ROOT',root),patch.object(server,'fingerprint',return_value='same'):
                server.run_chat(session,job,'กันเงิน 1000 บาท','shopping',{'year':'all','month':'all'})
                self.assertEqual(job['proposal']['action']['kind'],'reserve_budget')
                self.assertFalse((root/'local/budget-reservations.sqlite3').exists())
                self.assertIn('บันทึกงบ',server.commit(job['proposal'],root))
                self.assertEqual(len(ReservationStore(root/'local/budget-reservations.sqlite3').read()['reservations']),1)
                server.commit(job['proposal'],root)
                self.assertEqual(len(ReservationStore(root/'local/budget-reservations.sqlite3').read()['reservations']),1)

    def test_create_retry_date_cancel_and_planned_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ReservationStore(Path(tmp)/'local/reservations.sqlite3');today=date(2026,11,18)
            a=store.mutate('create',{'amount':'1000'},revision=0,operation_id='create',today=today)
            self.assertEqual(store.mutate('create',{'amount':'1000'},revision=0,operation_id='create',today=today),a)
            self.assertEqual(planned_budget('15000',store.read()['reservations'])['remaining_before_expenses'],'14000')
            ident=a['reservation']['id']
            b=store.mutate('end_date',{'id':ident,'end_date':'2026-12-02'},revision=1,operation_id='date',today=today)
            self.assertEqual(b['reservation']['end_date'],'2026-12-02')
            with self.assertRaises(ValueError):store.mutate('cancel',{'id':ident},revision=1,operation_id='bad',today=today)
            store.mutate('cancel',{'id':ident},revision=2,operation_id='cancel',today=today)
            self.assertEqual(planned_budget('15000',store.read()['reservations'])['remaining_before_expenses'],'15000')
            self.assertFalse((Path(tmp)/'database.csv').exists())

    def test_over_budget_is_not_cash(self):
        result=planned_budget('100',[{'amount':'200','status':'ACTIVE'}])
        self.assertTrue(result['over_budget']);self.assertEqual(result['remaining_before_expenses'],'-100')

    def test_monthly_expenses_deduct_only_once_in_the_same_month(self):
        rows=[{'transaction_id':'1','date':'2026-11-10','transaction_type':'expense','amount_thb':'1200','data_quality_flag':'needs_review'},
              {'transaction_id':'2','date':'2026-11-11','transaction_type':'transfer','amount_thb':'3000'},
              {'transaction_id':'3','date':'2026-10-10','transaction_type':'expense','amount_thb':'4000'}]
        result=planned_after_recorded_expenses('15000',[{'amount':'3010','status':'ACTIVE'}],rows,date(2026,11,18))
        self.assertEqual(result['recorded_expenses'],'1200');self.assertEqual(result['remaining_after_recorded_expenses'],'10790')
        self.assertTrue(result['unreviewed_expenses'])

    def test_preview_accounts_for_expenses_and_existing_reservation(self):
        rows=[{'transaction_id':'1','date':'2026-11-10','transaction_type':'expense','amount_thb':'5237','data_quality_flag':'review'}]
        plan=reservation_preview('15000',[],rows,date(2026,11,18),'3010')
        self.assertEqual((plan['before'],plan['after']),('9763','6753'))
        plan=reservation_preview('15000',[{'amount':'1000','status':'ACTIVE'}],rows,date(2026,11,18),'10000')
        self.assertEqual(plan['after'],'-1237');self.assertIn('ลดงบ',plan['recommendation'])
        self.assertIn('อาจยังไม่ครบ',plan['limitations'])

    def test_purchase_does_not_deduct_linked_reservation_twice(self):
        rows=[{'transaction_id':'1','date':'2026-11-10','transaction_type':'expense','amount_thb':'5237'}]
        reservations=[{'id':'linked','amount':'2580','status':'ACTIVE'},{'id':'other','amount':'2000','status':'ACTIVE'}]
        plan=reservation_preview('15000',reservations,rows,date(2026,11,18),'2580','linked')
        self.assertEqual(plan['before'],'5183');self.assertEqual(plan['after'],'5183');self.assertEqual(plan['additional_to_reserve'],'0')
        partial=reservation_preview('15000',[{'id':'linked','amount':'1000','status':'ACTIVE'}],rows,date(2026,11,18),'2580','linked')
        self.assertEqual(partial['additional_to_reserve'],'1580');self.assertEqual(partial['after'],'7183')

    def test_dynamic_reservation_name_amount_and_end_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=ReservationStore(Path(tmp)/'local/reservations.sqlite3')
            result=store.mutate('create',{'amount':'2750','name':'ค่าหนังสือ','end_date':'2026-12-05'},revision=0,operation_id='dynamic',today=date(2026,11,18))['reservation']
            self.assertEqual((result['type'],result['name'],result['amount'],result['end_date']),('budget_reservation','ค่าหนังสือ','2750','2026-12-05'))

if __name__=='__main__':unittest.main()
