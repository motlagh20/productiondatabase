#!/usr/bin/env python3
# ETL: Packing-All.xlsx (sheet 'Sheet1') -> PostgreSQL packing_header / packing_wagon
# FIXED: workbook rows are materialized FIRST (no DB calls during iteration),
# then all DB lookups/inserts happen after. Avoids openpyxl read_only + psycopg2
# cursor interleaving that was silently truncating the load.
import openpyxl, psycopg2, psycopg2.extras, re, io

SRC = r"C:/Projects/ProductionDatabase/xls/consolidated/All/Packing-All.xlsx"
PG  = dict(host='localhost', port=5433, dbname='postgres', user='postgres', password='test')

def norm_date_slash(s):
    if s is None: return None
    s = str(s).strip()
    m = re.match(r'^(\d{4})/(\d{1,2})/(\d{1,2})$', s)
    if not m: return None
    return "%s.%02d.%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))

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

# ---- PASS 1: read ALL rows from excel into memory (no DB calls) ----
wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb['Sheet1']
hdr = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
di = hdr.index('تاریخ بسته بندی'); shi = hdr.index('شیفت'); ci = hdr.index('کنترلر')
wti = hdr.index('نوع کارگران'); wci = hdr.index('تعداد کارگران')
mi = hdr.index('ماه'); dai = hdr.index('روز')
pti = hdr.index('نوع محصول'); pci = hdr.index('کد محصول'); pdi = hdr.index('شرح مجصول')
wni = hdr.index('شماره واگن')
tci = hdr.index('تعداد کل محصول'); g1i = hdr.index('تعداد درجه 1')
g2i = hdr.index('تعداد درجه 2'); wsi = hdr.index('تعداد ضایعات'); efi = hdr.index('راندمان')

raw = []
for r in ws.iter_rows(min_row=2, values_only=True):
    raw.append(r)

# ---- group in memory ----
headers = {}
for r in raw:
    d = norm_date_slash(r[di])
    if d is None: continue
    sh = to_int(r[shi])
    ctrl = str(r[ci]).strip() if r[ci] else None
    key = "%s|%s|%s" % (d, sh, ctrl)
    if key not in headers:
        headers[key] = dict(date=d, shift=sh, ctrl_name=ctrl, wt=str(r[wti]).strip() if r[wti] else None,
                            wc=to_int(r[wci]), month=str(r[mi]).strip() if r[mi] else None,
                            day=str(r[dai]).strip() if r[dai] else None, src=to_int(r[0]), wagons=[])
    h = headers[key]
    h['wagons'].append((to_int(r[wni]), str(r[pci]).strip() if r[pci] else None,
                        str(r[pdi]).strip() if r[pdi] else None, to_int(r[tci]),
                        to_int(r[g1i]), to_int(r[g2i]), to_int(r[wsi]), to_float(r[efi])))

# ---- PASS 2: DB lookups/caches (workbook fully read, no interleaving) ----
c = psycopg2.connect(**PG); cur = c.cursor()
cur.execute("SELECT operator_code, operator_id, full_name FROM operator")
op_by_code = {}; op_by_name = {}
for code, oid, name in cur.fetchall():
    op_by_code[code] = oid
    if name: op_by_name[name] = oid
def op_get(name):
    if name is None: return None
    name = str(name).strip()
    if name in op_by_name: return op_by_name[name]
    code = "PK%d" % (len(op_by_code)+1)
    cur.execute("INSERT INTO operator(operator_code,full_name,role) VALUES(%s,%s,'packing') RETURNING operator_id", (code, name))
    oid = cur.fetchone()[0]; op_by_code[code]=oid; op_by_name[name]=oid
    return oid

cur.execute("SELECT product_code_packing, product_id FROM product")
prod_by_code = {r[0]: r[1] for r in cur.fetchall() if r[0]}
def prod_get(code, desc):
    if code is None: return None
    code = str(code).strip()
    if code in prod_by_code: return prod_by_code[code]
    cur.execute("INSERT INTO product(product_code_packing,product_name_setting) VALUES(%s,%s) RETURNING product_id", (code, str(desc).strip() if desc else None))
    pid = cur.fetchone()[0]; prod_by_code[code]=pid
    return pid

# resolve controller ids + product ids for each header/wagon
for h in headers.values():
    h['ctrl_id'] = op_get(h['ctrl_name'])
    new_w = []
    for w in h['wagons']:
        new_w.append((w[0], prod_get(w[1], w[2]), w[2], w[3], w[4], w[5], w[6], w[7]))
    h['wagons'] = new_w

header_data = list(headers.values())
# insert headers one-by-one so returned IDs are guaranteed in input order
# (execute_values + RETURNING + page_size is NOT order-safe across batches)
ids = []
for h in header_data:
    cur.execute("""INSERT INTO packing_header(pack_date,shift,controller_id,worker_type,worker_count,month_name,day_name,source_row)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING packing_header_id""",
                (h['date'],h['shift'],h['ctrl_id'],h['wt'],h['wc'],h['month'],h['day'],h['src']))
    ids.append(cur.fetchone()[0])
key_list = list(headers.keys())

wagon_rows = []
for i, hid in enumerate(ids):
    h = headers[key_list[i]]
    for pos, w in enumerate(h['wagons'], start=1):
        wagon_rows.append((hid, w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7], pos))

buf = io.StringIO()
for row in wagon_rows:
    vals = [str(v) if v is not None else '\\N' for v in row]
    buf.write("\t".join(vals) + "\n")
buf.seek(0)
cur.copy_from(buf, 'packing_wagon', columns=('packing_header_id','wagon_no','product_id','product_desc','total_count','grade1_count','grade2_count','waste_count','efficiency_pct','position_index'))
c.commit()
print("packing_header:", len(header_data), "| packing_wagon:", len(wagon_rows))
cur.execute("SELECT count(*) FROM packing_header"); print("تایید packing_header:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM packing_wagon"); print("تایید packing_wagon:", cur.fetchone()[0])
cur.close(); c.close()
