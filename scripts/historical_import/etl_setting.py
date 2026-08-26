#!/usr/bin/env python3
# ETL: Set_All_1.xlsx (sheet 'Data') -> PostgreSQL setting_event / setting_wagon
# Also seeds shared dimensions: operator, chamber, product.
# Bad rows are logged to etl_reject (never silently dropped).
import openpyxl, psycopg2, re

SRC = r"C:/Projects/ProductionDatabase/xls/consolidated/All/Set_All_1.xlsx"
PG  = dict(host='localhost', port=5433, dbname='postgres', user='postgres', password='test')

NAME_FIX = {'علیپناه':'علی پناه', '140':'ناشناخته'}
def norm_name(s):
    s = str(s).strip() if s else ''
    return NAME_FIX.get(s, s)
def norm_prod(s):
    s = str(s).strip() if s else ''
    return {'اجر':'آجر'}.get(s, s)
def s2time(s):
    if s is None: return None
    s = str(s).strip()
    if s in ('', ':'): return None
    m = re.match(r'^(\d{1,2}):(\d{1,2})$', s)
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59: return None
    return f"{h:02d}:{mi:02d}"

def to_int(s):
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
    try: return int(s)
    except (ValueError, TypeError): return None

def to_float(s):
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
    try: return float(s)
    except (ValueError, TypeError): return None

WAGON_OFF = 11
WAGON_W = 6

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb['Data']
hdr = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
di, shi, supi, opi, pei, chi, pri, fri, dri, coi = (
    hdr.index('date_jalali'), hdr.index('shift'), hdr.index('supervisor_name'),
    hdr.index('Operator_name'), hdr.index('personnel_count'), hdr.index('chamber_no'),
    hdr.index('productName'), hdr.index('fingers_count'), hdr.index('dryer_waste'),
    hdr.index('columns_count'))

c = psycopg2.connect(**PG); cur = c.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS etl_reject (
    id BIGSERIAL PRIMARY KEY, module VARCHAR(20), source_row INTEGER,
    reason TEXT, raw_text TEXT, created_at TIMESTAMPTZ DEFAULT NOW())""")

def reject(srow, reason, raw):
    cur.execute("INSERT INTO etl_reject(module,source_row,reason,raw_text) VALUES('setting',%s,%s,%s)",
                (srow, reason, raw[:500] if raw else None))

# ---- seed dimensions ----
ops=set(); sups=set(); prods=set(); chams=set()
rows=list(ws.iter_rows(min_row=2, values_only=True))
for r in rows:
    if r[opi]: ops.add(norm_name(r[opi]))
    if r[supi]: sups.add(norm_name(r[supi]))
    if r[pri]: prods.add(norm_prod(r[pri]))
    if r[chi] is not None: chams.add(r[chi])

op_map={}
for i,nm in enumerate(sorted(ops|sups), start=1):
    code=f"OP{i:03d}"
    cur.execute("INSERT INTO operator(operator_code,full_name,role) VALUES(%s,%s,'setting') ON CONFLICT(operator_code) DO UPDATE SET full_name=EXCLUDED.full_name RETURNING operator_id",(code,nm))
    op_map[nm]=cur.fetchone()[0]
for nm in sorted(sups):
    if nm in op_map:
        cur.execute("UPDATE operator SET role='supervisor' WHERE operator_id=%s",(op_map[nm],))
cham_map={}
for ch in sorted(chams, key=lambda x:int(x)):
    code=f"CH{int(ch):02d}"
    cur.execute("INSERT INTO chamber(chamber_code,chamber_type,description) VALUES(%s,'SETTING',%s) ON CONFLICT(chamber_code) DO UPDATE SET description=EXCLUDED.description RETURNING chamber_id",(code,f"Chamber {ch}"))
    cham_map[ch]=cur.fetchone()[0]
prod_map={}
for p in sorted(prods):
    cur.execute("INSERT INTO product(product_name_setting) VALUES(%s) ON CONFLICT DO NOTHING RETURNING product_id",(p,))
    if cur.rowcount:
        prod_map[p]=cur.fetchone()[0]
    else:
        cur.execute("SELECT product_id FROM product WHERE product_name_setting=%s",(p,)); prod_map[p]=cur.fetchone()[0]

# ---- load events + wagons ----
nev=0; nwag=0; nrej=0
for r in rows:
    # validate row shape
    try:
        srow = int(r[0]) if r[0] is not None else None
    except (ValueError, TypeError):
        nrej+=1; reject(None, 'ستون ردیف عددی نیست', str(r[:6])); continue
    date_j = str(r[di]).strip() if r[di] else None
    if not date_j or not re.match(r'^\d{4}\.\d{1,2}\.\d{1,2}$', date_j):
        nrej+=1; reject(srow, 'تاریخ نامعتبر در date_jalali', str(r[:6])); continue
    m=re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', date_j)
    date_j="%s.%02d.%02d"%(int(m.group(1)),int(m.group(2)),int(m.group(3)))
    try:
        shift = to_int(r[shi])
    except (ValueError, TypeError):
        nrej+=1; reject(srow, 'شیفت عددی نیست', str(r[:6])); continue
    sup = norm_name(r[supi]); op = norm_name(r[opi])
    sup_id = op_map.get(sup); op_id = op_map.get(op)
    cham = cham_map.get(r[chi]); prod = prod_map.get(norm_prod(r[pri]))
    fingers = to_int(r[fri])
    dwaste = to_float(r[dri])
    cols = to_int(r[coi])
    cur.execute("""INSERT INTO setting_event(date_jalali,shift,chamber_id,product_id,supervisor_id,operator_id,personnel_count,fingers_count,columns_count,dryer_waste,source_row)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING setting_event_id""",
                (date_j,shift,cham,prod,sup_id,op_id,r[pei],fingers,cols,dwaste,srow))
    eid=cur.fetchone()[0]; nev+=1
    for b in range(4):
        base=WAGON_OFF+b*WAGON_W
        if base+5 >= len(r): break
        wno=r[base]; glaze=r[base+1]; st=s2time(r[base+2]); en=s2time(r[base+3]); pk=r[base+4]; kh=r[base+5]
        if wno is None and glaze is None and pk is None: continue
        try: wno=to_int(wno)
        except (ValueError, TypeError): wno=None
        pk=to_int(pk)
        kh=to_int(kh)
        cur.execute("""INSERT INTO setting_wagon(setting_event_id,wagon_no,glaze_type,start_time,end_time,packages,khesht_count,position_in_event)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                     (eid,wno,str(glaze) if glaze is not None else None,st,en,pk,kh,b+1))
        nwag+=1

c.commit()
print("setting_event:",nev,"| setting_wagon:",nwag,"| rejected:",nrej)
cur.execute("SELECT count(*) FROM setting_event"); print("تایید setting_event:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM setting_wagon"); print("تایید setting_wagon:",cur.fetchone()[0])
cur.execute("SELECT count(*) FROM etl_reject WHERE module='setting'"); print("تایید etl_reject(setting):",cur.fetchone()[0])
cur.execute("SELECT source_row,reason FROM etl_reject WHERE module='setting' LIMIT 5"); 
for x in cur.fetchall(): print("  reject ردیف",x[0],"->",x[1])
cur.close(); c.close()
