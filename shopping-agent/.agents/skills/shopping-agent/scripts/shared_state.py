"""Read-only financial companion state. All features protect the same goal store."""
import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from pathlib import Path
from goal_engine import plan_goals
from engine import SCHEMA
from engine import money


def build_shared(profile, options, snapshot, current, forecast=None, coverage=None):
    from purchase_flow import relevant_forecast
    recorded={e['goal_id'] for e in snapshot.get('entries',[]) if e['date']==current.isoformat()}
    report=plan_goals(snapshot.get('goals',[]),profile,options,current,relevant_forecast(snapshot.get('goals',[]),options,current,forecast),coverage,recorded)
    return dict(profile=profile,budget_options=options,portfolio=report,
                revision=snapshot.get('revision',0),snapshot=snapshot,
                forecast=forecast,coverage=coverage)


def load_transactions(finance_dir, month, history_months=1):
    """Read only requested month range; never infer balances or contact a network."""
    if type(history_months) is not int or not 1<=history_months<=3:raise ValueError('history_limit_three_months')
    year,number=map(int,month.split('-'));ordinal=year*12+number-1
    months={f'{(ordinal-i)//12:04d}-{(ordinal-i)%12+1:02d}' for i in range(history_months)}
    path=Path(finance_dir).resolve()/'database.csv'
    rows=[]
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames not in (SCHEMA,SCHEMA[:11]):raise ValueError('schema_mismatch')
        for row in reader:
            if row.get('year_month') in months:rows.append(row)
    return rows


def historical_summary(rows, current, complete_months=()):
    """Aggregate observed records; completeness is explicitly supplied, never inferred."""
    monthly = {}
    seen = set()
    issues = set()
    for row in rows:
        try:
            day = date.fromisoformat(row['date'])
            ident = row['transaction_id']
            if not ident or ident in seen or day > current or row['year_month'] != day.strftime('%Y-%m'):
                raise ValueError('invalid record')
            kind = row['transaction_type']
            if kind not in ('income', 'expense', 'transfer', 'investment'):
                raise ValueError('unknown transaction type')
            if kind == 'investment' and row.get('action') not in ('Buy', 'Sell'):
                raise ValueError('unknown investment action')
            value = money(row['amount_thb'])
            seen.add(ident)
            if row.get('data_quality_flag'):
                issues.add('records_need_review')
            bucket = monthly.setdefault(row['year_month'], {'income': Decimal(0), 'expense': Decimal(0), 'investment_buy': Decimal(0), 'categories': {}})
            if kind in ('income', 'expense'):
                bucket[kind] += value
            if kind == 'expense':
                category = (row.get('category') or '').strip() or 'unknown'
                bucket['categories'][category] = bucket['categories'].get(category, Decimal(0)) + value
            if kind == 'investment' and row.get('action') == 'Buy':
                bucket['investment_buy'] += value
        except (ValueError, TypeError, KeyError):
            issues.add('invalid_or_duplicate_transaction')
    eligible = sorted(set(complete_months))
    if any(not isinstance(m, str) or not __import__('re').fullmatch(r'\d{4}-(0[1-9]|1[0-2])', m) or m >= current.strftime('%Y-%m') for m in eligible):
        raise ValueError('complete_months_must_be_past_calendar_months')
    if not eligible:
        issues.add('history_completeness_unconfirmed')
    if any(m not in monthly for m in eligible):
        issues.add('complete_month_without_records')
    def fmt(value):
        return str(value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    averages = None
    if eligible and not issues.intersection({'invalid_or_duplicate_transaction', 'records_need_review', 'complete_month_without_records'}):
        cats = set().union(*(monthly[m]['categories'] for m in eligible))
        averages = {'income': fmt(sum((monthly[m]['income'] for m in eligible), Decimal(0))/len(eligible)),
                    'expense': fmt(sum((monthly[m]['expense'] for m in eligible), Decimal(0))/len(eligible)),
                    'investment_buy': fmt(sum((monthly[m]['investment_buy'] for m in eligible), Decimal(0))/len(eligible)),
                    'categories': {c: fmt(sum((monthly[m]['categories'].get(c, Decimal(0)) for m in eligible), Decimal(0))/len(eligible)) for c in sorted(cats)}}
    serialized = {m: {k: ({c: fmt(v) for c, v in b['categories'].items()} if k == 'categories' else fmt(b[k])) for k in b} for m,b in sorted(monthly.items())}
    return {'monthly_observed': serialized, 'complete_months': eligible, 'monthly_averages': averages,
            'issues': sorted(issues), 'current_available_cash': None,
            'note': 'Recorded transactions only; transfers excluded, balances and future obligations are not inferred.'}


def monthly_shopping_budget(inputs):
    """Use only explicitly confirmed, non-overlapping planned amounts."""
    keys = ('income', 'essential', 'other_planned', 'savings', 'investments', 'goals', 'shopping_spent')
    result = {'monthly_shopping_budget': None, 'remaining_shopping_budget': None,
              'current_available_cash': None, 'issues': []}
    if inputs.get('complete') is not True or inputs.get('non_overlapping') is not True:
        result['issues'].append('confirm_complete_non_overlapping_plan')
    values = {}
    for key in keys:
        try: values[key] = money(inputs.get(key))
        except ValueError: result['issues'].append(key+'_missing_or_invalid')
    if not result['issues']:
        budget = values['income'] - sum((values[k] for k in keys[1:-1]), Decimal(0))
        result['monthly_shopping_budget'] = str(budget.quantize(Decimal('.01')))
        result['remaining_shopping_budget'] = str((budget-values['shopping_spent']).quantize(Decimal('.01')))
    return result


def financial_context_fallback(rows, current, request):
    """Read-only advisory tiers. Estimates never become cash or a buy verdict."""
    ordinal=current.year*12+current.month-1-2
    loaded_since=date(ordinal//12,ordinal%12+1,1)
    relevant=[];invalid_dates=False
    for row in rows:
        try:
            when=date.fromisoformat(row['date'])
            if loaded_since<=when<=current:relevant.append(row)
        except (KeyError,TypeError,ValueError):invalid_dates=True
    rows=relevant
    result={'level':'HISTORICAL_CONTEXT','current_available_cash':None,
            'estimated_budget':None,'unadjusted_recorded_remainder':None,
            'strict_status':'INSUFFICIENT_DATA','issues':[],
            'history':historical_summary(rows,current,request.get('complete_months',[]))}
    profile=request.get('profile') or {};budget_options=request.get('budget') or {}
    strict=plan_goals(request.get('goals') or [],profile,budget_options,current,
                      request.get('forecast'),request.get('coverage'))
    result['strict_status']=strict['status']
    if strict['status']=='FEASIBLE':
        result.update(level='CONFIRMED_BALANCE',current_available_cash=strict['budget']['current_balance'],
                      confirmed_available_spending=strict['remaining_spending_budget'])
        return result
    if invalid_dates:
        result['issues'].append('invalid_transaction_date');return result
    cycle=request.get('cycle') or {}
    try:
        if cycle.get('start_confirmed') is not True:raise ValueError('cycle_start_unconfirmed')
        start=date.fromisoformat(cycle['start'])
        if start>current or (current-start).days>93:raise ValueError('cycle_start_invalid')
        if start<loaded_since:raise ValueError('cycle_predates_loaded_history')
        if cycle.get('loaded_since') and start<date.fromisoformat(cycle['loaded_since']):raise ValueError('cycle_predates_loaded_history')
        if cycle.get('end') and not current<=date.fromisoformat(cycle['end']):raise ValueError('cycle_end_invalid')
    except (KeyError,TypeError,ValueError):
        result['issues'].append('current_income_cycle_start_not_confirmed');return result
    seen=set();income=Decimal(0);expense=Decimal(0);refund=Decimal(0);investment=Decimal(0);expense_rows=0;income_rows=0;investment_rows=0
    for row in rows:
        try:
            when=date.fromisoformat(row['date'])
            if not start<=when<=current:continue
            ident=row['transaction_id']
            if not ident or ident in seen or row['year_month']!=when.strftime('%Y-%m'):raise ValueError('invalid_or_duplicate')
            seen.add(ident);kind=row['transaction_type']
            if kind not in ('income','expense','transfer','investment'):raise ValueError('invalid_type')
            value=money(row['amount_thb'])
            if row.get('data_quality_flag'):raise ValueError('unreviewed_record')
            if kind=='expense':expense+=value;expense_rows+=1
            elif kind=='investment':
                if row.get('action') not in ('Buy','Sell'):raise ValueError('unknown_investment_action')
                if row['action']=='Buy':investment+=value;investment_rows+=1
                else:
                    result['issues'].append('investment_sale_cashflow_needs_review');return result
            elif kind=='income':
                if str(row.get('category','')).strip().casefold() in ('refund','เงินคืน'):
                    refund+=value
                else:income+=value;income_rows+=1
        except (KeyError,TypeError,ValueError):
            result['issues'].append('cycle_records_need_review');return result
    received=cycle.get('income_received')
    if received is not None:
        if cycle.get('income_received_confirmed') is not True:
            result['issues'].append('income_received_not_confirmed');return result
        # Explicit total replaces transaction income; do not add the two.
        try:income=money(received)
        except ValueError:result['issues'].append('invalid_income_received');return result
    elif not income_rows:
        result['issues'].append('income_received_not_recorded');return result
    if not expense_rows and cycle.get('expenses_complete') is not True:
        result['issues'].append('expenses_not_recorded_or_confirmed');return result
    if refund>expense:
        result['issues'].append('refund_exceeds_cycle_expenses');return result
    net_expense=expense-refund;remaining=income-net_expense
    result.update(level='ESTIMATED_BUDGET',cycle_start=start.isoformat(),cycle_end=cycle.get('end'),
                  income_received=str(income),net_recorded_expenses=str(net_expense),
                  unadjusted_recorded_remainder=str(remaining))
    if investment_rows:
        result['recorded_investment_purchases']=str(investment)
        if cycle.get('investment_separate_from_expenses') is not True:
            result['issues'].append('investment_overlap_requires_confirmation');return result
        remaining-=investment
    if cycle.get('expenses_complete') is not True:result['issues'].append('recorded_expenses_may_be_incomplete')
    commitments=cycle.get('commitments')
    if commitments is None:
        result['issues'].append('upcoming_commitments_not_confirmed');return result
    if not isinstance(commitments,list):raise ValueError('commitments_must_be_list')
    total=Decimal(0);ids=set()
    for item in commitments:
        ident=item.get('id') if isinstance(item,dict) else None
        if not ident or ident in ids or item.get('confirmed') is not True or type(item.get('already_in_expenses')) is not bool:
            result['issues'].append('commitment_requires_confirmation_and_overlap_review');return result
        ids.add(ident)
        try:value=money(item.get('amount'))
        except ValueError:result['issues'].append('invalid_commitment');return result
        if not item['already_in_expenses']:total+=value
    for goal in request.get('goals') or []:
        if goal.get('status')=='ACTIVE' and goal.get('allocation_enabled',True) and goal.get('goal_id') not in ids:
            result['issues'].append('active_goal_commitment_missing');return result
    result['known_unpaid_commitments']=str(total)
    if cycle.get('commitments_complete') is not True:
        result['issues'].append('upcoming_commitments_may_be_incomplete')
    result['estimated_budget']=str(remaining-total)
    return result


def cross_skill_context(facts, classifications=None):
    """Normalize caller-supplied facts; never infer external provider schemas."""
    allowed_status = {'CONFIRMED', 'ESTIMATED', 'MISSING'}
    allowed_classes = {'ESSENTIAL', 'DISCRETIONARY', 'FINANCIAL_COMMITMENT', 'UNCATEGORIZED'}
    output = {}
    conflicts = []
    for fact in facts:
        name = fact.get('name')
        status = fact.get('status')
        if not isinstance(name, str) or not name or status not in allowed_status:
            raise ValueError('invalid_context_fact')
        value = None if status == 'MISSING' else str(money(fact.get('value')))
        item = {'status': status, 'value': value, 'source': str(fact.get('source') or '')}
        prior = output.get(name)
        if prior and prior['status'] == 'CONFIRMED' and status == 'CONFIRMED' and money(prior['value']) != money(value):
            conflicts.append(name)
            output[name] = {'status': 'MISSING', 'value': None, 'source': 'conflicting_confirmations'}
        elif name not in conflicts and (not prior or (status == 'CONFIRMED' and prior['status'] != 'CONFIRMED') or (status == 'ESTIMATED' and prior['status'] == 'MISSING')):
            output[name] = item
    classes = {}
    for category, classification in (classifications or {}).items():
        if not isinstance(category, str) or not category or classification not in allowed_classes:
            raise ValueError('invalid_expense_classification')
        classes[category] = classification
    needed = ('income', 'investments', 'expenses', 'debt')
    missing = [key for key in needed if output.get(key, {}).get('status') != 'CONFIRMED']
    residual = None
    if not missing:
        values = {key: money(output[key]['value']) for key in needed}
        residual = str((values['income']-values['investments']-values['expenses']-values['debt']).quantize(Decimal('.01')))
    return {'facts': output, 'classifications': classes, 'conflicts': sorted(set(conflicts)),
            'known_monthly_residual': residual, 'current_available_cash': None,
            'missing_for_residual': missing,
            'limitations': ['residual_is_not_cash_or_shopping_budget', 'other_commitments_may_be_missing']}
