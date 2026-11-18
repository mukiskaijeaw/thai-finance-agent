import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from purchase_flow import new_session,candidates,select,reject,run_purchase
from purchase_renderer import render_purchase
from goal_storage import GoalStore
from test_goal_planner import inputs,goal,DAY


def listing(model='Model A',price='300'):
    source='https://example.org/'+model.replace(' ','-')
    return dict(name=model,url=source,price=price,shipping='20',discount='0',
                verified=True,shipping_verified=True,checked=DAY.isoformat(),
                stock='available',stock_verified=True,evidence={'model':{'value':model,'source':source}})


def selected():
    state=candidates(new_session(),[listing()],{'model':'Model A'},DAY,exact=True)
    return select(state,state['candidates'][0]['id'],True)


def context():
    return {k:dict(value=v,source='user-confirmed test fixture') for k,v in
            dict(purpose='ใช้เรียน',necessity='required',value_suitable=True,offer_ready=True,planned=True).items()}


class PurchaseFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=GoalStore(Path(self.tmp.name)/'local/goals.sqlite3')
        self.p,self.b=inputs()

    def tearDown(self):self.tmp.cleanup()

    def request(self,action='evaluate',**extra):
        return dict(action=action,session=selected(),profile=self.p,budget=self.b,context=context(),precompute_dates=False,**extra)

    def test_empty_entry_and_supplied_input_skip_form(self):
        self.assertEqual(new_session()['stage'],'INTENT')
        self.assertIsNone(new_session()['selected_product'])
        self.assertEqual(new_session({'product':'ชื่อที่ผู้ใช้ระบุ'})['stage'],'SEARCH_REQUIRED')
        self.assertEqual(new_session({'image_attached':True})['stage'],'SEARCH_REQUIRED')

    def test_broad_input_limited_to_four_exact_only_one(self):
        offers=[listing('Model '+str(i)) for i in range(8)]
        self.assertEqual(len(candidates(new_session(),offers,{},DAY)['candidates']),4)
        self.assertEqual(len(candidates(new_session(),offers,{'model':'Model 3'},DAY,exact=True)['candidates']),1)

    def test_confirmation_required_and_rejection_clears_state(self):
        state=candidates(new_session(),[listing()],{},DAY)
        with self.assertRaises(ValueError):run_purchase(dict(action='evaluate',session=state),self.store,DAY)
        chosen=select(state,state['candidates'][0]['id'],True)
        self.assertIsNone(reject(chosen)['selected_product'])
        self.assertEqual(reject(chosen,True)['stage'],'SEARCH_REQUIRED')

    def test_select_second_existing_candidate_without_search(self):
        state=candidates(new_session(),[listing('Model A'),listing('Model B')],{},DAY)
        chosen=select(state,state['candidates'][1]['id'],True)
        self.assertEqual(chosen['selected_product']['name'],'Model B')
        result=run_purchase(dict(action='evaluate',session=chosen,precompute_dates=False),self.store,DAY)
        self.assertEqual(result['report']['product']['name'],'Model B')
        self.assertEqual(result['report']['financial']['status'],'INSUFFICIENT_DATA')

    def test_advisory_budget_is_visible_when_current_cash_is_missing(self):
        rows=[{'transaction_id':'i','date':'2028-02-01','year_month':'2028-02','transaction_type':'income','amount_thb':'10000','category':'Salary'},
              {'transaction_id':'e','date':'2028-02-02','year_month':'2028-02','transaction_type':'expense','amount_thb':'2000','category':'Other'}]
        financial_context={'cycle':{'start':'2028-02-01','start_confirmed':True,'expenses_complete':True,
                                    'commitments':[],'commitments_complete':True}}
        result=run_purchase(dict(action='evaluate',session=selected(),precompute_dates=False,
                                 transactions=rows,financial_context=financial_context),self.store,DAY)
        self.assertEqual(result['report']['advisory_context']['estimated_budget'],'8000')
        self.assertEqual(result['report']['financial']['status'],'INSUFFICIENT_DATA')
        self.assertEqual(result['report']['decision']['follow_up_questions'],[])
        from purchase_renderer import render_purchase_markdown
        text=render_purchase_markdown(result)
        self.assertIn('8000',text);self.assertIn('ไม่ใช่ยอดเงินสด',text)

    def test_financial_assessment_reads_synthetic_provider_history_without_balance(self):
        from engine import SCHEMA
        from goal_engine import today_bangkok
        day=today_bangkok();root=Path(self.tmp.name)/'provider';root.mkdir()
        (root/'AGENTS.md').write_text('synthetic provider',encoding='utf-8')
        (root/'financial_profile.json').write_text(json.dumps({'schema_version':1,'profile':{'income':'15000'}}),encoding='utf-8')
        rows=[]
        for ident,kind,value in [('i','income','15000'),('e','expense','4000')]:
            r=dict.fromkeys(SCHEMA,'');r.update(transaction_id=ident,date=day.isoformat(),year_month=day.strftime('%Y-%m'),transaction_type=kind,amount_thb=value,category='Other');rows.append(r)
        with (root/'database.csv').open('w',encoding='utf-8',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=SCHEMA);writer.writeheader();writer.writerows(rows)
        before=(root/'database.csv').read_bytes()
        request=dict(action='evaluate',session=selected(),precompute_dates=False)
        script=Path(__file__).resolve().parents[1]/'scripts'/'shopping.py'
        proc=subprocess.run([sys.executable,str(script),'purchase','--finance-dir',str(root),'--store',str(self.store.path)],input=json.dumps(request),text=True,encoding='utf-8',capture_output=True,check=True)
        result=json.loads(proc.stdout)['report']
        self.assertEqual(result['advisory_context']['level'],'HISTORICAL_CONTEXT')
        observed=result['advisory_context']['history']['monthly_observed'][day.strftime('%Y-%m')]
        self.assertEqual(observed['income'],'15000.00');self.assertEqual(observed['expense'],'4000.00')
        self.assertIsNone(result['advisory_context']['current_available_cash'])
        self.assertEqual(result['financial']['status'],'INSUFFICIENT_DATA')
        self.assertEqual((root/'database.csv').read_bytes(),before)
        self.assertFalse(self.store.path.exists())

    def test_default_month_end_affordable_no_goal_created(self):
        r=run_purchase(self.request(),self.store,DAY)['report']
        self.assertEqual(r['target_date'],'2028-02-29')
        self.assertEqual(r['financial']['status'],'AFFORDABLE')
        self.assertEqual(r['remaining_after_purchase'],'2680')
        self.assertEqual(r['decision']['recommendation'],'BUY_NOW')
        self.assertFalse(self.store.path.exists())

    def test_created_goal_does_not_allocate_but_saved_money_is_protected(self):
        from goal_planner import run
        run(dict(action='create',goal=goal(target_amount='600',saved_amount='100'),profile=self.p,budget=self.b,
                 operation_id='existing',expected_revision=0),self.store,DAY,True)
        r=run_purchase(self.request(),self.store,DAY)['report']
        self.assertEqual(r['available_spending'],'2900')
        self.assertEqual(r['remaining_after_purchase'],'2580')

    def test_missing_shipping_not_affordable_and_price_refresh(self):
        request=self.request();request['session']['selected_product']['listing']['shipping']=None
        r=run_purchase(request,self.store,DAY)['report']
        self.assertEqual(r['decision']['recommendation'],'NEED_MORE_INFO')
        request=self.request();request['session']['selected_product']['listing']['checked']='2020-01-01'
        self.assertIsNone(run_purchase(request,self.store,DAY)['report']['quote']['effective'])

    def test_user_budget_is_respected(self):
        request=self.request();request['session']['intent']['budget']='100'
        r=run_purchase(request,self.store,DAY)['report']
        self.assertEqual(r['financial']['status'],'SAVE_FIRST')
        self.assertEqual(r['available_spending'],'100')

    def test_local_date_precomputation_and_cross_month_forecast(self):
        request=self.request();request['precompute_dates']=True
        r=run_purchase(request,self.store,DAY)
        self.assertEqual(len(r['date_reports']),3)
        self.assertEqual(r['date_reports'][DAY.isoformat()]['daily_saving'],'320.00')
        request=self.request('change_date',target_date='2028-03-02')
        self.assertEqual(run_purchase(request,self.store,DAY)['report']['goal_plan']['status'],'INSUFFICIENT_DATA')
        request['forecast']=dict(complete=True,through='2028-03-02',events=[dict(date='2028-03-01',income='1000',outflow='100',confirmed=True)])
        self.assertEqual(run_purchase(request,self.store,DAY)['report']['goal_plan']['status'],'FEASIBLE')

    def test_start_preview_then_review_consent_and_calendar(self):
        request=self.request('start_goal',purchase_saved_amount='0')
        preview=run_purchase(request,self.store,DAY)
        self.assertFalse(self.store.path.exists())
        confirm=dict(request,action='confirm_goal',review_token=preview['report']['review_token'],
                     funding_source_confirmed=True,expected_revision=0,operation_id='start')
        with self.assertRaises(ValueError):run_purchase(confirm,self.store,DAY)
        saved=run_purchase(confirm,self.store,DAY,True)
        self.assertEqual(saved['stage'],'GOAL_ACTIVE')
        self.assertEqual(len(saved['goal_view']['calendar'][saved['goal_saved']['goal']['goal_id']]),29)
        self.assertEqual(len(self.store.read()['goals']),1)

    def test_revised_budget_invalidates_confirmation(self):
        request=self.request('start_goal',purchase_saved_amount='0')
        preview=run_purchase(request,self.store,DAY)
        request.update(action='confirm_goal',review_token=preview['report']['review_token'],funding_source_confirmed=True,expected_revision=0,operation_id='start')
        request['profile']=dict(self.p,cash='6000')
        with self.assertRaisesRegex(ValueError,'review_updated'):run_purchase(request,self.store,DAY,True)

    def test_confirm_goal_without_financial_profile_or_saved_balance(self):
        request=dict(action='start_goal',session=selected(),precompute_dates=False)
        preview=run_purchase(request,self.store,DAY)
        self.assertEqual(preview['report']['goal_plan']['status'],'INSUFFICIENT_DATA')
        confirm=dict(request,action='confirm_goal',review_token=preview['report']['review_token'],
                     expected_revision=0,operation_id='unknown-finances')
        saved=run_purchase(confirm,self.store,DAY,True)['goal_saved']
        self.assertEqual(saved['goal']['feasibility'],'UNKNOWN')
        self.assertIsNone(saved['goal']['saved_amount'])
        self.assertTrue(saved['goal']['allocation_enabled'])
        self.assertEqual(saved['goal']['funding_source'],'unallocated')
        self.assertFalse(saved['funds_allocated'])
        with self.assertRaises(ValueError):run_purchase(confirm,self.store,DAY,True)

    def test_confirm_goal_with_insufficient_money(self):
        request=self.request('start_goal',purchase_saved_amount='0')
        request['profile']=dict(self.p,cash='0')
        preview=run_purchase(request,self.store,DAY)
        confirm=dict(request,action='confirm_goal',review_token=preview['report']['review_token'],
                     expected_revision=0,operation_id='low-cash')
        saved=run_purchase(confirm,self.store,DAY,True)['goal_saved']
        self.assertTrue(saved['goal']['allocation_enabled'])
        self.assertNotEqual(saved['feasibility'],'FEASIBLE')

    def test_monthly_advice_is_a_scenario_not_cash(self):
        from advisory import monthly_allocation
        result=monthly_allocation({'income':'40000','allocations':[
            {'name':'essential','amount':'20000','status':'CONFIRMED'},
            {'name':'travel','amount':'3000','status':'ASSUMED'}]})
        self.assertEqual(result['unallocated'],'17000.00')
        self.assertIsNone(result['current_available_cash'])
        self.assertEqual(result['allocations'][1]['status'],'ASSUMED')
        self.assertFalse(self.store.path.exists())

    def test_skip_does_not_write_and_ui_source_is_reused(self):
        r=run_purchase(dict(action='skip',session=selected()),self.store,DAY)
        self.assertEqual(r['recommendation'],'SKIP_PURCHASE')
        self.assertFalse(self.store.path.exists())
        raw=render_purchase(new_session())
        self.assertNotIn('Model A',raw)
        self.assertNotIn('__PURCHASE_PAYLOAD__',raw)
        self.assertIn('ช่วยดูให้หน่อยว่าควรซื้อไหม',raw)

    def test_zero_total_does_not_force_a_savings_goal(self):
        request=self.request()
        request['session']['selected_product']['listing'].update(price='0',shipping='0')
        r=run_purchase(request,self.store,DAY)['report']
        self.assertEqual(r['financial']['status'],'AFFORDABLE')
        self.assertEqual(r['goal_status'],'NOT_REQUIRED')
        self.assertFalse(self.store.path.exists())


if __name__=='__main__':unittest.main()
