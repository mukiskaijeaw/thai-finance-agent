"""Host routing and skill packaging checks with synthetic context and stubbed model."""
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

APP=Path(__file__).resolve().parents[4]
SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
sys.path.insert(0,str(SKILL/'scripts'))
try:
    import dashboard_server as server
except ModuleNotFoundError as exc:
    if exc.name != 'dashboard_server':
        raise
    raise unittest.SkipTest('Paoween host is not included in the standalone Shopping checkout')
import shared_state
from goal_engine import today_bangkok


class RuntimeRoutingTests(unittest.TestCase):
    def test_bare_product_and_completed_transaction_route_separately(self):
        scope={'year':'all','month':'all'}
        for msg in ('รองเท้าวิ่ง','หูฟัง','รองเท้ารุ่นไหนดี'):
            self.assertEqual(server.route_request(msg,'overview',scope)[0],'shopping')
        self.assertNotEqual(server.route_request('บันทึกรายจ่ายซื้อรองเท้าแล้ว','overview',scope)[0],'shopping')

    def test_natural_language_purchase_routes_and_packages_current_skill(self):
        scope={'year':'all','month':'all'}
        self.assertEqual(server.route_request('อยากซื้อรองเท้าวิ่ง','overview',scope)[0],'shopping')
        context={'scope':scope,'transactions':[],'review_tasks':[],'totals_thb':{},'expense_categories_thb':{}}
        session={'history':[],'cancel':threading.Event(),'busy':True};job={};observed={}
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);destination=root/'.agents'/'skills'/'shopping-agent'
            shutil.copytree(SKILL,destination,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            def stub(cmd,prompt,temp,session,job):
                file=Path(temp)/'.agents'/'skills'/'shopping-agent'/'SKILL.md'
                observed['skill']=file.read_text(encoding='utf-8')
                observed['prompt']=prompt
                return 0,json.dumps({'answer':'synthetic fixture','action':{'kind':'none'},'view':{'name':'none','year':'','month':''}})
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),
                  patch.object(server,'snapshot',return_value=(context,'fixture')),
                  patch.object(server,'shopping_goals',return_value={'goals':[],'status':'no_saved_store'}),
                  patch.object(server,'execute_codex',side_effect=stub)):
                server.run_chat(session,job,'อยากซื้อรองเท้าวิ่ง','overview',scope)
        self.assertEqual(job['status'],'done')
        self.assertEqual(observed['skill'],(SKILL/'SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('financial_profile',observed['prompt'])
        self.assertIn('อยากซื้อรองเท้าวิ่ง',observed['prompt'])

    def test_price_only_never_reads_financial_snapshot_or_goals(self):
        scope={'year':'all','month':'all'};session={'history':[],'cancel':threading.Event(),'busy':True};job={};seen={}
        def stub(cmd,prompt,temp,session,job):
            context=json.loads((Path(temp)/'context.json').read_text(encoding='utf-8'))
            seen['context']=context
            return 0,json.dumps({'answer':'synthetic price','action':{'kind':'none'},'view':{'name':'none','year':'','month':''}})
        with (patch.object(server,'CODEX','stub'),patch.object(server,'snapshot',side_effect=AssertionError('financial read')),
              patch.object(server,'shopping_goals',side_effect=AssertionError('goal read')),
              patch.object(server,'execute_codex',side_effect=stub)):
            server.run_chat(session,job,'รองเท้าวิ่ง ราคาอย่างเดียว','overview',scope)
        self.assertEqual(job['status'],'done');self.assertEqual(seen['context']['financial_profile_status'],'not_requested')
        self.assertNotIn('financial_profile',seen['context'])

    def test_product_request_gets_local_historical_aggregate(self):
        scope={'year':'all','month':'all'};day=today_bangkok();stamp=day.replace(day=1).isoformat()
        context={'scope':scope,'transactions':[],'review_tasks':[],'totals_thb':{},'expense_categories_thb':{}}
        records=[{'transaction_id':'fixture','date':stamp,'year_month':stamp[:7],
                  'transaction_type':'expense','amount_thb':'1200','category':'Other','description':'private merchant'}]
        session={'history':[],'cancel':threading.Event(),'busy':True};job={};seen={}
        def stub(cmd,prompt,temp,session,job):
            seen['prompt']=prompt
            return 0,json.dumps({'answer':'synthetic','action':{'kind':'none'},'view':{'name':'none','year':'','month':''}})
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);shutil.copytree(SKILL,root/'.agents'/'skills'/'shopping-agent',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),patch.object(server,'snapshot',return_value=(context,'fixture')),
                  patch.object(server,'shopping_goals',return_value={'goals':[],'status':'no_saved_store'}),
                  patch.object(shared_state,'load_transactions',return_value=records),patch.object(server,'execute_codex',side_effect=stub)):
                server.run_chat(session,job,'รองเท้าวิ่ง','overview',scope)
        self.assertEqual(job['status'],'done');self.assertIn('monthly_observed',seen['prompt'])
        self.assertIn('1200.00',seen['prompt']);self.assertNotIn('private merchant',seen['prompt'])


if __name__=='__main__':unittest.main()
