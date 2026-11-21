import json
import sqlite3
import sys
import tempfile
import unittest
import threading
from contextlib import closing
from datetime import timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.agents'/'skills'/'shopping-agent'/'scripts'))
import dashboard_server as server
from goal_engine import today_bangkok
from unittest.mock import patch


class ShoppingPageTests(unittest.TestCase):
    def test_savings_statement_routes_to_goal_context(self):
        pillar,_=server.route_request('วันนี้ชั้นเก็บ 200 บาท','overview',{'year':'all','month':'all'})
        self.assertEqual(pillar,'shopping')

    def test_structured_prices_are_compared_without_inventing_budget(self):
        result=server.shopping_price_summary([
            {'name':'A','price':'1750','source':'https://example.com/a'},
            {'name':'B','price':'1359','source':'https://example.com/b'}])
        self.assertIn('B ราคาสินค้าต่ำกว่า 391.00',result)
        self.assertIn('ไม่ใช่งบส่วนบุคคล',result)

    def test_structured_prices_require_two_sourced_valid_prices(self):
        self.assertEqual(server.shopping_price_summary([{'name':'A','price':'100','source':''},{'name':'B','price':'50','source':'https://example.com'}]),'')
        self.assertEqual(server.shopping_price_summary([{'name':'A','price':'unknown','source':'https://example.com/a'},{'name':'B','price':'50','source':'https://example.com/b'}]),'')

    def test_shopping_brief_requests_range_and_primary_recommendation(self):
        brief=(ROOT/'.agents/skills/shopping-agent/references/chat-brief.md').read_text(encoding='utf-8')
        self.assertIn('Do not automatically suggest a cheaper product',brief)
        self.assertIn('when the user asks for cheaper options',brief)

    def test_no_store_does_not_create_one(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            self.assertEqual(server.shopping_goals(root)['status'],'no_saved_store')
            self.assertFalse((root/'local').exists())

    def test_goal_progress_reads_local_store_without_mutation(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);local=root/'local';local.mkdir();path=local/'goals.sqlite3'
            goal={'goal_id':'fixture','goal_name':'Example','goal_category':'general',
                  'target_amount':'1000','saved_amount':'250','target_date':(today_bangkok()+timedelta(days=30)).isoformat(),
                  'funding_source':'unallocated','status':'ACTIVE'}
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE goals(data TEXT)');db.execute('INSERT INTO goals VALUES (?)',(json.dumps(goal),));db.commit()
            before=path.read_bytes();result=server.shopping_goals(root)
            self.assertEqual(result['status'],'read_only');self.assertEqual(result['goals'][0]['progress'],'25.00')
            self.assertEqual(path.read_bytes(),before)

    def test_purchase_request_routes_to_shopping_without_changing_scope(self):
        pillar,scope=server.route_request('อยากซื้อรองเท้า', 'overview', {'year':'all','month':'all'})
        self.assertEqual(pillar,'shopping');self.assertEqual(scope,{'year':'all','month':'all'})

    def test_chat_includes_skill_and_goal_snapshot_without_network(self):
        fixture={'transactions':[],'review_tasks':[],'scope':{'year':'all','month':'all'},
                 'totals_thb':{},'expense_categories_thb':{}}
        seen={}
        def fake(cmd,prompt,temp,session,job):
            seen['skill']=(Path(temp)/'.agents/skills/shopping-agent/SKILL.md').is_file()
            seen['goal_context']='active_shopping_goals' in prompt
            return 0,json.dumps({'answer':'fixture','action':{'kind':'none'},'view':{'name':'none','year':'','month':''}})
        session={'history':[],'cancel':threading.Event(),'busy':True};job={}
        with (patch.object(server,'CODEX','fixture'),patch.object(server,'snapshot',return_value=(fixture,'fixture')),
              patch.object(server,'shopping_goals',return_value={'goals':[],'status':'no_saved_store'}),patch.object(server,'execute_codex',side_effect=fake)):
            server.run_chat(session,job,'อยากซื้อสินค้า','overview',{'year':'all','month':'all'})
        self.assertEqual(job['status'],'done');self.assertTrue(seen['skill']);self.assertTrue(seen['goal_context'])

    def test_local_child_process_handles_thai_without_network(self):
        code=("import sys,json; sys.stdin.reconfigure(encoding='utf-8'); "
              "sys.stdout.reconfigure(encoding='utf-8'); text=sys.stdin.read(); "
              "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':text}},ensure_ascii=False))")
        session={'cancel':threading.Event()}
        with tempfile.TemporaryDirectory() as tmp:
            status,answer=server.execute_codex([sys.executable,'-c',code],'ข้อความทดสอบ',tmp,session,{})
        self.assertEqual(status,0);self.assertEqual(answer,'ข้อความทดสอบ')
        self.assertNotIn('process',session)


if __name__=='__main__':unittest.main()
