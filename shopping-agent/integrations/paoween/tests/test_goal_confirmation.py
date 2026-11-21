import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'.agents'/'skills'/'shopping-agent'/'scripts'))
import dashboard_server as server
from goal_engine import today_bangkok,target_day
from goal_storage import GoalStore
from reservations import ReservationStore


class GoalConfirmationTests(unittest.TestCase):
    def test_proposal_then_confirm_uses_separate_store_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session={'history':[],'cancel':threading.Event(),'busy':True};job={}
            brief=root/'.agents/skills/shopping-agent/references/chat-brief.md';brief.parent.mkdir(parents=True);brief.write_text('synthetic rules',encoding='utf-8')
            ctx={'transactions':[],'review_tasks':[],'scope':{'year':'all','month':'all'},'totals_thb':{},'expense_categories_thb':{}}
            action={'kind':'create_goal','goal_name':'เที่ยวตัวอย่าง','goal_category':'travel',
                    'target_amount':'6000','target_date':target_day('สิ้นเดือน',today_bangkok()).isoformat()}
            result={'answer':'ตรวจเป้าหมายก่อน','action':action,'view':{'name':'none','year':'','month':''}};seen={}
            def stub(cmd,prompt,temp,session,job):
                seen['prompt']=prompt
                return 0,json.dumps(result)
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),
                  patch.object(server,'snapshot',return_value=(ctx,'fingerprint')),
                  patch.object(server,'fingerprint',return_value='fingerprint'),
                  patch.object(server.shutil,'copytree'),patch.object(server,'execute_codex',side_effect=stub)):
                server.run_chat(session,job,'ตั้งเป้าหมายเที่ยว 6000 สิ้นเดือน จากเงินเดือน','shopping',{'year':'all','month':'all'})
                self.assertEqual(job['status'],'done');self.assertEqual(job['proposal']['action']['kind'],'reserve_budget')
                self.assertNotIn('สำหรับการแนะนำสินค้า:',seen['prompt'])
                store=GoalStore(root/'local/goals.sqlite3');self.assertEqual(store.read()['goals'],[])
                answer=server.commit(job['proposal'],root)
                self.assertIn('บันทึกงบ',answer)
                self.assertEqual(store.read()['goals'],[])
                reserve=ReservationStore((root/'local/budget-reservations.sqlite3').resolve())
                self.assertEqual(len(reserve.read()['reservations']),1)
                self.assertEqual(reserve.read()['reservations'][0]['status'],'ACTIVE')
                self.assertEqual(server.commit(job['proposal'],root),answer)
                self.assertEqual(len(reserve.read()['reservations']),1)

    def test_asks_source_before_goal_proposal_and_accepts_followup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session={'history':[],'cancel':threading.Event(),'busy':True};job={}
            brief=root/'.agents/skills/shopping-agent/references/chat-brief.md';brief.parent.mkdir(parents=True);brief.write_text('synthetic',encoding='utf-8')
            ctx={'transactions':[],'review_tasks':[],'scope':{'year':'all','month':'all'},'totals_thb':{},'expense_categories_thb':{}}
            action={'kind':'create_goal','goal_name':'เที่ยว','goal_category':'travel','target_amount':'6000','target_date':target_day('สิ้นเดือน',today_bangkok()).isoformat()}
            result={'answer':'ตัวอย่าง','action':action,'view':{'name':'none','year':'','month':''}}
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),patch.object(server,'snapshot',return_value=(ctx,'fingerprint')),
                  patch.object(server.shutil,'copytree'),patch.object(server,'execute_codex',return_value=(0,json.dumps(result)))):
                server.run_chat(session,job,'ตั้งเป้าหมายเที่ยว 6000 สิ้นเดือน','shopping',{'year':'all','month':'all'})
                self.assertIsNone(job['proposal']);self.assertIn('รายรับ',job['answer']);self.assertIn('เก็บออมใหม่',job['answer'])
                job={};server.run_chat(session,job,'เก็บออมใหม่','shopping',{'year':'all','month':'all'})
                self.assertEqual(job['proposal']['action']['kind'],'create_goal')
                result['action']={'kind':'none'};result['answer']='รับทราบวันแล้วครับ'
                job={};server.run_chat(session,job,'2 ธันวา','shopping',{'year':'all','month':'all'})
                self.assertNotIn('อยากกันงบจากรายรับ',job['answer'])
                self.assertEqual(session['goal_source_choice'],'new_savings')

    def test_income_button_and_date_keep_choice(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session={'history':[],'cancel':threading.Event(),'busy':True};job={}
            brief=root/'.agents/skills/shopping-agent/references/chat-brief.md';brief.parent.mkdir(parents=True);brief.write_text('synthetic',encoding='utf-8')
            ctx={'transactions':[],'review_tasks':[],'scope':{'year':'all','month':'all'},'totals_thb':{},'expense_categories_thb':{}}
            result={'answer':'รับทราบครับ','action':{'kind':'none'},'view':{'name':'none','year':'','month':''}}
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),patch.object(server,'snapshot',return_value=(ctx,'fingerprint')),
                  patch.object(server.shutil,'copytree'),patch.object(server,'execute_codex',return_value=(0,json.dumps(result)))):
                for message in ('ตั้งเป้าหมายเที่ยว 1000 บาท','รายรับที่มีอยู่แล้ว','ไม่ใช่ กันแยก','2 ธันวา'):
                    job={};server.run_chat(session,job,message,'shopping',{'year':'all','month':'all'})
                self.assertEqual(session['goal_source_choice'],'income')
                self.assertTrue(session['goal_separate'])
                self.assertNotIn('อยากกันงบจากรายรับ',job['answer'])

    def test_declined_or_simulation_never_creates_goal(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session={'history':[],'cancel':threading.Event(),'busy':True};job={}
            brief=root/'.agents/skills/shopping-agent/references/chat-brief.md';brief.parent.mkdir(parents=True);brief.write_text('synthetic rules',encoding='utf-8')
            ctx={'transactions':[],'review_tasks':[],'scope':{'year':'all','month':'all'},'totals_thb':{},'expense_categories_thb':{}}
            action={'kind':'create_goal','goal_name':'เที่ยวตัวอย่าง','goal_category':'travel','target_amount':'6000','target_date':target_day('สิ้นเดือน',today_bangkok()).isoformat()}
            result={'answer':'จำลอง','action':action,'view':{'name':'none','year':'','month':''}}
            with (patch.object(server,'ROOT',root),patch.object(server,'CODEX','stub'),patch.object(server,'snapshot',return_value=(ctx,'fingerprint')),
                  patch.object(server.shutil,'copytree'),patch.object(server,'execute_codex',return_value=(0,json.dumps(result)))):
                server.run_chat(session,job,'แค่จำลองกันงบ 6000 ไม่บันทึก','shopping',{'year':'all','month':'all'})
                self.assertEqual(job['status'],'done');self.assertIsNone(job['proposal']);self.assertFalse((root/'local/goals.sqlite3').exists())


if __name__=='__main__':unittest.main()
