import copy,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from purchase_flow import run_purchase,price_states
from goal_storage import GoalStore
from test_purchase_flow import selected
from test_goal_planner import inputs,DAY
class CycleRegression(unittest.TestCase):
 def test_simulated_goal_preview_keeps_sourced_quote_and_does_not_write(self):
  with tempfile.TemporaryDirectory() as t:
   store=GoalStore(Path(t)/'local'/'goals.sqlite3');session=selected();original=copy.deepcopy(session);profile,budget=inputs()
   result=run_purchase(dict(action='simulation_goal',session=session,simulated_price='8125',profile=profile,budget=budget),store,DAY)
   goal=result['goal_view']['goals'][0];self.assertEqual(goal['target_amount'],'8125');self.assertTrue(goal['simulated_price'])
   self.assertEqual(session,original);self.assertEqual(session['selected_product']['quote']['effective'],'320');self.assertFalse(store.path.exists())
 def test_simulation_requires_valid_cycle(self):
  report=dict(available_spending='100',quote={'effective':'20'},decision={'recommendation':'NEED_MORE_INFO'})
  self.assertIsNone(price_states(report,DAY))
 def test_compact_travel_states_keep_all_calculations(self):
  from companion import demo_input
  from shared_state import build_shared
  from companion_engine import travel_report,travel_states
  with tempfile.TemporaryDirectory() as t:
   store=GoalStore(Path(t)/'local'/'goals.sqlite3');data=demo_input(DAY)
   shared=build_shared(data['profile'],data['budget'],store.read(),DAY)
   trip=dict(departure='Start',destination='Destination',travel_date='2028-02-29',days=2,nights=1,travelers=1,costs=[dict(name='One',amount='100',unit='group_total',certainty='estimated',source='test'),dict(name='Two',amount='100',unit='group_total',certainty='estimated',source='test')])
   result=travel_states(shared,trip,DAY);self.assertLess(len(result['totals']),len(result['states']))
   for key,state in result['states'].items():
    indexes=[int(x) for x in key.split(',')];values=[c['values'][i] for c,i in zip(result['controls'],indexes)]
    expected=travel_report(shared,trip,DAY,values);actual=result['totals'][state['total']]
    for field in ('financial_fit','goal_status','required_savings','daily_saving','daily_spending'):self.assertEqual(actual[field],expected[field])
    self.assertEqual(state['distribution'],expected['distribution'])
if __name__=='__main__':unittest.main()
