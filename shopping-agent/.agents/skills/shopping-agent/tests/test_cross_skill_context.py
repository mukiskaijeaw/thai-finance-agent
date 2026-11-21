import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shared_state import cross_skill_context


class CrossSkillTests(unittest.TestCase):
    def test_mock_multiturn_context(self):
        # Synthetic adapter output: not the schema of any real team source.
        turns = [('income','40000','conversation'),('investments','4000','mock investment'),
                 ('expenses','20000','mock income-expense'),('debt','0','conversation')]
        facts=[dict(name=k,value=v,status='CONFIRMED',source=s) for k,v,s in turns]
        out=cross_skill_context(facts)
        self.assertEqual(out['known_monthly_residual'],'16000.00')
        self.assertIsNone(out['current_available_cash'])
        self.assertEqual(out['missing_for_residual'],[])
        self.assertIn('other_commitments_may_be_missing',out['limitations'])

    def test_conflicts_missing_and_user_classification(self):
        facts=[dict(name='income',value='100',status='CONFIRMED'),dict(name='income',value='200',status='CONFIRMED')]
        out=cross_skill_context(facts,{'Groceries':'ESSENTIAL','Other':'UNCATEGORIZED'})
        self.assertEqual(out['facts']['income']['status'],'MISSING')
        self.assertIsNone(out['known_monthly_residual'])
        self.assertEqual(out['classifications']['Groceries'],'ESSENTIAL')
        self.assertEqual(cross_skill_context([],{'Groceries':'DISCRETIONARY'})['classifications']['Groceries'],'DISCRETIONARY')
        with self.assertRaises(ValueError):cross_skill_context([],{'Groceries':'INVALID'})


if __name__=='__main__':unittest.main()
