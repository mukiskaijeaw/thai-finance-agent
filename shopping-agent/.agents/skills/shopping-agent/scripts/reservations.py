"""Shopping-owned logical reservations; never modifies a ledger or bank balance."""
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from engine import money


class ReservationStore:
    def __init__(self,path):
        self.path=Path(path)

    def read(self):
        if not self.path.exists():return {'revision':0,'reservations':[]}
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)) as db:
            revision=db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()
            return {'revision':int(revision[0]),'reservations':[json.loads(x[0]) for x in db.execute('SELECT data FROM reservations ORDER BY rowid')]}

    def mutate(self,action,data,*,revision,operation_id,today):
        if action not in ('create','end_date','cancel') or type(revision) is not int or not operation_id:
            raise ValueError('invalid_reservation_operation')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(self.path,timeout=10,isolation_level=None)) as db:
            try:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                db.execute("INSERT OR IGNORE INTO meta VALUES('revision','0')")
                db.execute('CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY,data TEXT NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,response TEXT NOT NULL)')
                digest=hashlib.sha256(json.dumps([action,data],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                previous=db.execute('SELECT request_hash,response FROM operations WHERE id=?',(operation_id,)).fetchone()
                if previous:
                    if previous[0]!=digest:raise ValueError('operation_id_conflict')
                    db.execute('ROLLBACK');return json.loads(previous[1])
                current=int(db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])
                if current!=revision:raise ValueError('stale_revision')
                if action=='create':
                    value=money(data.get('amount'))
                    if value<=0:raise ValueError('positive_amount_required')
                    name=data.get('name') or 'เงินกันแยก'
                    if not isinstance(name,str) or not name.strip() or len(name)>200:raise ValueError('invalid_name')
                    end=data.get('end_date')
                    if end and date.fromisoformat(end)<today:raise ValueError('date_in_past')
                    item={'id':str(uuid4()),'type':'budget_reservation','name':name.strip(),'amount':str(value),'created':today.isoformat(),'end_date':end,'status':'ACTIVE'}
                else:
                    row=db.execute('SELECT data FROM reservations WHERE id=?',(data.get('id'),)).fetchone()
                    if not row:raise ValueError('reservation_not_found')
                    item=json.loads(row[0])
                    if item['status']!='ACTIVE':raise ValueError('reservation_not_active')
                    if action=='cancel':item['status']='CANCELLED'
                    else:
                        day=date.fromisoformat(data.get('end_date',''))
                        if day<today:raise ValueError('date_in_past')
                        item['end_date']=day.isoformat()
                db.execute('INSERT OR REPLACE INTO reservations VALUES (?,?)',(item['id'],json.dumps(item,ensure_ascii=False)))
                current+=1;db.execute("UPDATE meta SET value=? WHERE key='revision'",(str(current),))
                result={'revision':current,'reservation':item}
                db.execute('INSERT INTO operations VALUES (?,?,?)',(operation_id,digest,json.dumps(result,ensure_ascii=False)))
                db.execute('COMMIT');return result
            except Exception:
                if db.in_transaction:db.execute('ROLLBACK')
                raise


def planned_budget(income,reservations):
    """Reservation amounts only; other cash flows and overlaps must be reconciled elsewhere."""
    total=sum((money(r['amount']) for r in reservations if r.get('status')=='ACTIVE'),Decimal(0))
    base=money(income)
    return {'income':str(base),'reserved':str(total),'remaining_before_expenses':str(base-total),'over_budget':total>base}

def planned_after_recorded_expenses(income,reservations,rows,current):
    """Illustrative monthly plan; transaction completeness and reservation overlap are unknown."""
    plan=planned_budget(income,reservations)
    expenses=Decimal(0);unreviewed=False;ids=set()
    for row in rows:
        when=date.fromisoformat(row['date'])
        if when.year!=current.year or when.month!=current.month or when>current:continue
        ident=row['transaction_id']
        if not ident or ident in ids:raise ValueError('duplicate_or_missing_transaction_id')
        ids.add(ident)
        if row.get('transaction_type')=='expense':
            expenses+=money(row['amount_thb'])
            unreviewed=unreviewed or bool(row.get('data_quality_flag'))
    plan.update(recorded_expenses=str(expenses),remaining_after_recorded_expenses=str(Decimal(plan['remaining_before_expenses'])-expenses),
                period=current.strftime('%Y-%m'),unreviewed_expenses=unreviewed,
                assumption='Recorded expenses may be incomplete and must not overlap the reserved amounts; this is not a cash balance.')
    return plan

def reservation_preview(income,reservations,rows,current,new_amount,linked_reservation_id=None):
    """Estimated calendar-month plan; incomplete and potentially overlapping inputs stay explicit."""
    before=planned_after_recorded_expenses(income,reservations,rows,current)
    amount=money(new_amount)
    linked=[r for r in reservations if r.get('id')==linked_reservation_id and r.get('status')=='ACTIVE'] if linked_reservation_id else []
    if linked_reservation_id and len(linked)!=1:raise ValueError('linked_reservation_missing')
    covered=min(amount,money(linked[0]['amount'])) if linked else Decimal(0)
    additional=amount-covered
    after=Decimal(before['remaining_after_recorded_expenses'])-additional
    recommendation='ยังไม่แนะนำให้ซื้อ ควรลดงบหรือเลื่อนวันซื้อครับ' if after<0 else 'แนะนำให้เผื่อค่าใช้จ่ายจำเป็นที่เหลือก่อนตัดสินใจซื้อครับ'
    return {'income':before['income'],'recorded_expenses':before['recorded_expenses'],
            'existing_reservations':before['reserved'],'before':before['remaining_after_recorded_expenses'],
            'after':str(after),'period':before['period'],'recommendation':recommendation,
            'already_reserved_for_item':str(covered),'additional_to_reserve':str(additional),
            'limitations':'รายจ่ายและภาระที่เหลืออาจยังไม่ครบ; หากนำเงินที่กันไว้ไปใช้แล้ว ต้องปรับยอดที่กันไม่ให้หักซ้ำ',
            'other_commitments':None}
