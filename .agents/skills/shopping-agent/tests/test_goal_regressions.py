import sys
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from goal_storage import GoalStore
from goal_planner import run
from goal_engine import plan_goals
from purchase_flow import run_purchase
from test_goal_planner import DAY,goal,inputs
from test_purchase_flow import selected,context


class GoalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=GoalStore(Path(self.tmp.name)/'local/goals.sqlite3');self.p,self.b=inputs()

    def mutate(self,action,g,rev,**extra):
        return run(dict(action=action,goal=g,expected_revision=rev,operation_id='op-'+str(rev),
                        profile=self.p,budget=self.b,**extra),self.store,DAY,True)

    def test_create_without_profile_and_unaffordable(self):
        r=run(dict(action='create',goal=goal(saved_amount=None),expected_revision=0,operation_id='x'),self.store,DAY,True)
        self.assertEqual(r['feasibility'],'UNKNOWN');self.assertFalse(r['goal']['allocation_enabled'])
        edited=self.mutate('edit',dict(goal_id=r['goal']['goal_id'],target_amount='999999'),1)
        self.assertEqual(edited['feasibility'],'UNKNOWN')
        costly=self.mutate('create',goal(goal_name='Costly',target_amount='999999'),2)
        self.assertEqual(costly['feasibility'],'NOT_FEASIBLE')

    def test_activation_reserves_cycle_and_cancel_releases_plan(self):
        created=self.mutate('create',goal(),0);ident=created['goal']['goal_id']
        before=run(dict(action='view',profile=self.p,budget=self.b),self.store,DAY)
        self.mutate('activate',{'goal_id':ident},1)
        active=run(dict(action='view',profile=self.p,budget=self.b),self.store,DAY)
        self.assertEqual(Decimal(before['remaining_spending_budget'])-Decimal(active['remaining_spending_budget']),Decimal('300'))
        self.assertLess(Decimal(active['daily_spending']),Decimal(before['daily_spending']))
        self.mutate('delete',{'goal_id':ident},2)
        after=run(dict(action='view',profile=self.p,budget=self.b),self.store,DAY)
        self.assertEqual(after['remaining_spending_budget'],before['remaining_spending_budget'])

    def test_incomplete_activation_is_unknown_and_keeps_savings_unknown(self):
        r=run(dict(action='create',goal=goal(saved_amount=None,activate_on_create=True),expected_revision=0,operation_id='x'),self.store,DAY,True)
        self.assertEqual(r['goal']['status'],'ACTIVE');self.assertEqual(r['feasibility'],'UNKNOWN')
        self.assertIsNone(r['goal']['saved_amount']);self.assertFalse(r['funds_allocated'])

    def test_cross_cycle_only_current_contributions_are_reserved(self):
        g=goal(target_amount='600',target_date='2028-03-02')
        f=dict(complete=True,through='2028-03-02',events=[dict(date='2028-03-01',income='1000',outflow='0',confirmed=True)])
        result=plan_goals([g],self.p,self.b,DAY,forecast=f)
        self.assertEqual(result['status'],'FEASIBLE')
        self.assertEqual(Decimal(result['total_goal_allocation']),Decimal('600'))
        self.assertEqual(Decimal(result['remaining_spending_budget']),Decimal('2640'))

    def test_actual_savings_once_and_multiple_goals(self):
        one=self.mutate('create',goal(activate_on_create=True),0)['goal']['goal_id']
        self.mutate('create',goal(goal_name='Second',target_amount='600',activate_on_create=True),1)
        before=run(dict(action='view',profile=self.p,budget=self.b),self.store,DAY)
        self.mutate('record_savings',dict(goal_id=one,amount='100'),2)
        after=run(dict(action='view',profile=self.p,budget=self.b),self.store,DAY)
        metric=next(g for g in after['goals'] if g['goal_id']==one)
        self.assertEqual(metric['saved_amount'],'100');self.assertEqual(metric['remaining_target_amount'],'200')
        self.assertEqual(after['remaining_spending_budget'],before['remaining_spending_budget'])
        with self.assertRaisesRegex(ValueError,'duplicate_savings_day'):
            self.mutate('record_savings',dict(goal_id=one,amount='10'),3)

    def test_saved_money_outside_current_cash_is_not_deducted_twice(self):
        g=goal(status='PAUSED',saved_amount='100')
        included=plan_goals([g],self.p,self.b,DAY)
        outside_profile=dict(self.p,cash='4900')
        outside_budget=dict(self.b,cash_excluded_goal_savings={'a':'100'})
        excluded=plan_goals([g],outside_profile,outside_budget,DAY)
        self.assertEqual(included['remaining_spending_budget'],excluded['remaining_spending_budget'])
        with self.assertRaisesRegex(ValueError,'overlapping_goal_savings_coverage'):
            plan_goals([g],outside_profile,outside_budget,DAY,coverage={'a':'1'})

    def test_buy_linked_goal_releases_only_its_savings(self):
        session=selected();ident=session['selected_product']['id']
        self.mutate('create',goal(goal_name='Product',target_amount='320',saved_amount='100',product_ref=ident,activate_on_create=True),0)
        base=dict(session=session,action='evaluate',profile=self.p,budget=self.b,context=context(),precompute_dates=False)
        regular=run_purchase(base,self.store,DAY)['report']
        used=run_purchase(dict(base,use_linked_goal_savings=True,goal_savings_in_current_cash=True),self.store,DAY)['report']
        self.assertEqual(used['linked_goal_savings_used'],'100')
        self.assertGreater(Decimal(used['remaining_after_purchase']),Decimal(regular['remaining_after_purchase']))
        with self.assertRaisesRegex(ValueError,'confirm_linked_goal_savings'):
            run_purchase(dict(base,use_linked_goal_savings=True),self.store,DAY)


if __name__=='__main__':unittest.main()
