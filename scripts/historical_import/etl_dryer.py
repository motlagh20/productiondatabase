#!/usr/bin/env python3
# ETL: Dryer-All.xlsx -> PostgreSQL dryer_cycle / dryer_reading
# Sources: 'Data Entry' (cycles) + 'Humidity'/'Temp' (time series).
# Reuses shared dimensions (operator, chamber, product) from setting ETL;
# seeds any NEW operators/products found here. Bad rows -> etl_reject.
import openpyxl, psycopg2, re

SRC = r"C:/Projects/ProductionDatabase/xls/consolidated/All/Dryer-All.xlsx"
PG  = dict(host='localhost', port=5433, dbname='postgres', user='postgres', password='test')

def norm_date(s):
    if s is None: return None
    s = str(s).strip()
    m = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', s)
    if not m: return None
    return "%s.%02d.%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def s2time(s):
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
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

def op_upsert(cur, name):
    name = str(name).strip() if name else ''
    if name == '': return None
    cur.execute("SELECT operator_id FROM operator WHERE full_name=%s", (name,))
    r = cur.fetchone()
    if r: return r[0]
    cur.execute("INSERT INTO operator(operator_code,full_name,role) VALUES(%s,%s,'dryer') RETURNING operator_id",
                (f"DR{abs(hash(name))%100000:05d}", name))
    return cur.fetchone()[0]

def prod_upsert(cur, name):
    name = str(name).strip() if name else ''
    if name == '': return None
    cur.execute("SELECT product_id FROM product WHERE product_name_setting=%s", (name,))
    r = cur.fetchone()
    if r: return r[0]
    cur.execute("INSERT INTO product(product_name_setting) VALUES(%s) RETURNING product_id", (name,))
    return cur.fetchone()[0]

def cham_id(cur, code):
    if code is None: return None
    code = f"CH{int(code):02d}" if str(code).strip().isdigit() else str(code).strip()
    cur.execute("SELECT chamber_id FROM chamber WHERE chamber_code=%s", (code,))
    r = cur.fetchone()
    if r: return r[0]
    cur.execute("INSERT INTO chamber(chamber_code,chamber_type,description) VALUES(%s,'DRYER',%s) RETURNING chamber_id",
                (code, f"Chamber {code}"))
    return cur.fetchone()[0]

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
de = wb['Data Entry']
hdr = [c for c in next(de.iter_rows(min_row=1, max_row=1, values_only=True))]
ci, ldi, lti, cni, fci, loi, lopi, pni, udi, uti, uoi, upi = (
    hdr.index('ChamberID'), hdr.index('Loading_date'), hdr.index('Loading_time'),
    hdr.index('ChamberNo'), hdr.index('Finger_Count'), hdr.index('Operator_ID'),
    hdr.index('Loading_Operator'), hdr.index('Product_Name'), hdr.index('Unloading_date'),
    hdr.index('Unloading_Time'), hdr.index('Operator_ID'), hdr.index('Unloading_Operator'))

c = psycopg2.connect(**PG); cur = c.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS etl_reject (
    id BIGSERIAL PRIMARY KEY, module VARCHAR(20), source_row INTEGER,
    reason TEXT, raw_text TEXT, created_at TIMESTAMPTZ DEFAULT NOW())""")
def reject(srow, reason, raw):
    cur.execute("INSERT INTO etl_reject(module,source_row,reason,raw_text) VALUES('dryer',%s,%s,%s)",
                (srow, reason, raw[:500] if raw else None))

# ---- idempotent: clear prior load before re-loading ----
cur.execute("TRUNCATE dryer_reading, dryer_cycle RESTART IDENTITY CASCADE")
cur.execute("DELETE FROM etl_reject WHERE module='dryer'")

# ---- load cycles ----
nc=0; nrej=0
rows=list(de.iter_rows(min_row=2, values_only=True))
row_seq=0
for r in rows:
    row_seq+=1
    # NOTE: Excel column 0 ('ردیف') is NOT a source-of-truth key (restarts each block);
    # we assign our own file-wide row_seq instead.
    srow = row_seq
    ld = norm_date(r[ldi]); ud = norm_date(r[udi])
    if ld is None and ud is None:
        nrej+=1; reject(srow, 'هیچ تاریخی معتبر نیست', str(r[:6])); continue
    ch = cham_id(cur, r[cni])
    lop = op_upsert(cur, r[lopi]); uop = op_upsert(cur, r[upi])
    pr = prod_upsert(cur, r[pni])
    cur.execute("""INSERT INTO dryer_cycle(chamber_id,load_date,load_time,unload_date,unload_time,
                   load_operator_id,unload_operator_id,product_id,finger_count,chamber_no,source_row)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING dryer_cycle_id""",
                (ch, ld, s2time(r[lti]), ud, s2time(r[uti]), lop, uop, pr, to_int(r[fci]), to_int(r[cni]), srow))
    nc+=1
c.commit()

# ---- map ChamberID -> dryer_cycle_id (one cycle per ChamberID row in Data Entry) ----
cur.execute("SELECT dryer_cycle_id, source_row FROM dryer_cycle WHERE source_row IS NOT NULL")
cycle_by_src = {src: cid for cid, src in cur.fetchall()}

# ---- load readings from Humidity + Temp ----
nr=0
for sn, col in (('Humidity','humidity_pct'), ('Temp','temperature_c')):
    ws = wb[sn]
    hh = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    # hour columns: indices 1..22 named 'hour N'
    for r in ws.iter_rows(min_row=2, values_only=True):
        cid_src = to_int(r[0])
        if cid_src is None: continue
        dcid = cycle_by_src.get(cid_src)
        if dcid is None: continue
        for i in range(1, len(hh)):
            hname = hh[i]
            m = re.match(r'hour\s+(\d+)$', str(hname).strip())
            if not m: continue
            val = to_int(r[i]) if sn=='Humidity' else to_int(r[i])
            if val is None: continue
            if abs(val) >= 1000:  # exceeds NUMERIC(5,2) range; bad source value
                reject(cid_src, 'مقدار %s خارج از محدوده (>999)' % sn, str(r[:3])); continue
            off = int(m.group(1))
            cur.execute("INSERT INTO dryer_reading(dryer_cycle_id,hour_offset,%s) VALUES(%%s,%%s,%%s) ON CONFLICT(dryer_cycle_id,hour_offset) DO UPDATE SET %s=EXCLUDED.%s" % (col,col,col),
                        (dcid, off, val))
            nr+=1
c.commit()
print("dryer_cycle:", nc, "| dryer_reading:", nr, "| rejected:", nrej)
cur.execute("SELECT count(*) FROM dryer_cycle"); print("تایید dryer_cycle:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM dryer_reading"); print("تایید dryer_reading:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM etl_reject WHERE module='dryer'"); print("تایید etl_reject(dryer):", cur.fetchone()[0])
cur.close(); c.close()
