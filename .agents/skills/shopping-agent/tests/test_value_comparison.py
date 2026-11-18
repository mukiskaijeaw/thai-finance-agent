import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import cost_per_use_comparison,compare_product_prices


class ValueComparisonTests(unittest.TestCase):
    def test_price_ranking_and_difference_are_computed(self):
        result=compare_product_prices({'items':[{'name':'A','price':'1750'}, {'name':'B','price':'1359'}]})
        self.assertEqual(result['lower_priced'],'B');self.assertEqual(result['difference'],'391')
        equal=compare_product_prices({'items':[{'name':'A','price':'10'}, {'name':'B','price':'10'}]})
        self.assertIsNone(equal['lower_priced']);self.assertEqual(equal['difference'],'0')
        with self.assertRaises(ValueError):compare_product_prices({'items':[{'name':'A','price':'10'}, {'name':'B','price':None}]})
    def item(self, name, price, **kwargs):
        return dict(name=name,price=price,weekly_usage='7',ownership_years='2',
                    additional_costs='0',usage_basis='ASSUMED',**kwargs)

    def test_two_prices_and_costs(self):
        a=self.item('A','3640');b=self.item('B','7280');b['additional_costs']='1040'
        result=cost_per_use_comparison({'items':[a,b]})['items']
        self.assertEqual(result[0]['expected_total_uses'],'728')
        self.assertEqual(result[0]['cost_per_use'],'5.00')
        self.assertEqual(result[1]['cost_per_use'],'11.43')
        self.assertEqual(result[1]['usage_basis'],'ASSUMED')

    def test_unknown_extra_cost_is_not_zero(self):
        item=self.item('A','3640');item['additional_costs']=None
        result=cost_per_use_comparison({'items':[item]})['items'][0]
        self.assertIsNone(result['total_ownership_cost'])
        self.assertIsNone(result['cost_per_use'])
        self.assertEqual(result['price_only_per_use'],'5.00')

    def test_zero_frequency_and_unknown_basis_rejected(self):
        item=self.item('A','500');item['weekly_usage']='0'
        with self.assertRaises(ValueError):cost_per_use_comparison({'items':[item]})
        item['weekly_usage']='1';item['usage_basis']=''
        with self.assertRaises(ValueError):cost_per_use_comparison({'items':[item]})

    def test_comparison_without_financial_profile(self):
        result=cost_per_use_comparison({'items':[self.item('A','100'),self.item('B','200')]})
        self.assertEqual(len(result['items']),2)


if __name__=='__main__':unittest.main()
