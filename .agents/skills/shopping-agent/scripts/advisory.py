"""Stateless allocation arithmetic for labeled scenarios; never a cash verdict."""
from decimal import Decimal
from engine import money


def monthly_allocation(request):
    income=money(request.get('income'))
    items=request.get('allocations')
    if not isinstance(items,list) or not items:raise ValueError('allocations_required')
    names=set();result=[];total=Decimal(0)
    for item in items:
        name=item.get('name');status=item.get('status')
        if not isinstance(name,str) or not name.strip() or name.strip().casefold() in names:raise ValueError('unique_allocation_names_required')
        if status not in ('CONFIRMED','ESTIMATED','ASSUMED'):raise ValueError('allocation_status_required')
        value=money(item.get('amount'));total+=value;names.add(name.strip().casefold())
        result.append({'name':name.strip(),'amount':str(value.quantize(Decimal('.01'))),'status':status})
    if total>income:raise ValueError('allocations_exceed_income')
    return {'mode':'ADVISORY','income':str(income.quantize(Decimal('.01'))),'allocations':result,
            'unallocated':str((income-total).quantize(Decimal('.01'))),'current_available_cash':None,
            'assumptions':['Allocations are distinct; confirm overlaps before relying on the plan.','This is a scenario, not a verified cash balance or purchase approval.']}
