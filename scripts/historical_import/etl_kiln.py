#!/usr/bin/env python3
# ETL: Kiln-Merged.xlsx (sheet 'Kiln-All') -> PostgreSQL kiln_push / kiln_wagon / kiln_reading
# Batched with psycopg2.extras.execute_values for speed.
# Each Excel row = one wagon inside a push. A push = unique (date_jalali, PushingTime_min).
# 18 thermal sensors unpivoted into kiln_reading (long format), once per push.
import openpyxl, psycopg2, psycopg2.extras, re

SRC = r"C:/Projects/ProductionDatabase/xls/consolidated/All/Kiln-Merged.xlsx"
PG  = dict(host='localhost', port=5433, dbname='postgres', user='postgres', password='test')

SENSORS = ["temp_exhaust","temp_preheat01","temp_preheat02","temp_termostat",
    "temp_Zone00","temp_Zone01","temp_Zone02","temp_Zone03","temp_Zone04","temp_Zone05",
    "temp_Zone06","temp_Zone07","temp_rapid01","temp_Rapid02","temp_bottomA","temp_bottom01",
    "temp_bottomB","temp_bottom02"]

def s2time(s):
    if s is None: return None
    s = str(s).strip()
    if s in ('', ':'): return None
    m = re.match(r'^(\d{1,2}):(\d{1,2})(:\d{1,2})?$', s)  # accept HH:MM or HH:MM:SS
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59: return None
    return f"{h:02d}:{mi:02d}"

def norm_date(s):
    if s is None: return None
    s = str(s).strip()
    m = re.match(r'^(\d{4})\.(\d{1,2})\.(\d{1,2})$', s)
    if not m: return None
    return "%s.%02d.%02d" % (int(m.group(1)), int(m.group(2)), int(m.group(3)))

def s2interval(s):
    if s is None: return None
    s = str(s).strip()
    m = re.match(r'^(\d{1,2}):(\d{1,2})$', s)
    if not m: return None
    return f"{int(m.group(1))} hours {int(m.group(2))} minutes"

def to_int(s):
    if s is None: return None
    s = str(s).strip()
    if s == '': return None
    try: return int(s)
    except (ValueError, TypeError): return None

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb['Kiln-All']
hdr = [c for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
di = hdr.index('date_jalali'); ti = hdr.index('PushingTime_min')
oci = hdr.index('OperatorCode_FK'); oni = hdr.index('OperatorName')
pi = hdr.index('ProductCode_FK')
wni = hdr.index('WagonNo'); dci = hdr.index('date_control')
dchi = hdr.index('date_changed?'); fi = hdr.index('flag')
sensor_idx = {s: hdr.index(s) for s in SENSORS}

c = psycopg2.connect(**PG); cur = c.cursor()

# idempotent: clear only this module's tables before reload (self-correcting, no external TRUNCATE needed)
cur.execute("TRUNCATE kiln_reading, kiln_wagon, kiln_push RESTART IDENTITY CASCADE")
c.commit()

# seed sensors
sensor_map = {}
for order, code in enumerate(SENSORS, start=1):
    nm = code.replace('temp_', '').replace('_', ' ').title()
    cur.execute("INSERT INTO kiln_sensor(sensor_code,sensor_name,position_order) VALUES(%s,%s,%s) ON CONFLICT(sensor_code) DO UPDATE SET position_order=EXCLUDED.position_order RETURNING sensor_id", (code, nm, order))
    sensor_map[code] = cur.fetchone()[0]

# operator / product caches
cur.execute("SELECT operator_code, operator_id, full_name FROM operator")
op_by_code = {}; op_by_name = {}
for code, oid, name in cur.fetchall():
    op_by_code[code] = oid
    if name: op_by_name[name] = oid
cur.execute("SELECT product_code_kiln, product_id FROM product")
prod_by_code = {r[0]: r[1] for r in cur.fetchall() if r[0]}

def op_get(code, name):
    if code is not None:
        code = str(code).strip()
        if code in op_by_code: return op_by_code[code]
    if name is not None:
        name = str(name).strip()
        if name in op_by_name: return op_by_name[name]
    code = code if code else "KI%d" % (len(op_by_code)+1)
    cur.execute("INSERT INTO operator(operator_code,full_name,role) VALUES(%s,%s,'kiln') RETURNING operator_id", (code, name))
    oid = cur.fetchone()[0]; op_by_code[code]=oid
    if name: op_by_name[name]=oid
    return oid

def prod_get(code):
    if code is None: return None
    code = str(code).strip()
    if code in prod_by_code: return prod_by_code[code]
    cur.execute("INSERT INTO product(product_code_kiln) VALUES(%s) RETURNING product_id", (code,))
    pid = cur.fetchone()[0]; prod_by_code[code]=pid
    return pid

# group rows by (date,time)
pushes = {}            # key -> dict(push tuple, wagons list, readings list)
order = 0
for r in ws.iter_rows(min_row=2, values_only=True):
    order += 1
    date_j = norm_date(r[di])
    if date_j is None:  # malformed source date -> skip this row (kept traceable via source_row elsewhere)
        continue
    t = s2time(r[ti])
    key = "%s|%s" % (date_j, t)
    if key not in pushes:
        pushes[key] = dict(date=date_j, time=t, op=op_get(r[oci], r[oni]), prod=prod_get(r[pi]),
                           dur=s2interval(r[6]) if len(r)>6 else None, src=to_int(r[0]),
                           dc=str(r[dci]).strip() if r[dci] else None,
                           dch=str(r[dchi]).strip() if r[dchi] else None,
                           fl=str(r[fi]).strip() if r[fi] else None,
                           wagons=[], readings={})  # readings: sensor_id -> first valid value
    p = pushes[key]
    wno = to_int(r[wni])
    p['wagons'].append(wno)
    # merge: keep first VALID (non-None, in-range) value per sensor across all rows of this push
    for s in SENSORS:
        sid = sensor_map[s]
        if sid in p['readings']:
            continue  # already have a valid value for this sensor
        v = to_int(r[sensor_idx[s]])
        if v is not None and abs(v) < 10000:
            p['readings'][sid] = v

# build push list and insert one-by-one so RETURNING ids are in input order
# (execute_values + page_size is NOT order-safe for RETURNING across batches)
push_data = list(pushes.values())
ids = []
wagon_rows = []
reading_rows = []
for p in push_data:
    cur.execute("""INSERT INTO kiln_push(push_date,push_time,operator_id,product_id,push_duration,source_row,date_control,date_changed,flag)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING kiln_push_id""",
                (p['date'], p['time'], p['op'], p['prod'], p['dur'], p['src'], p['dc'], p['dch'], p['fl']))
    ids.append(cur.fetchone()[0])
key_list = list(pushes.keys())
for i, pid in enumerate(ids):
    p = pushes[key_list[i]]
    for pos, wno in enumerate(p['wagons'], start=1):
        wagon_rows.append((pid, wno, pos))
    if p['readings']:
        for sid, val in p['readings'].items():
            if val is not None and abs(val) < 10000:
                reading_rows.append((pid, sid, val))

psycopg2.extras.execute_values(cur, "INSERT INTO kiln_wagon(kiln_push_id,wagon_no,position_index) VALUES %s",
                               wagon_rows, page_size=2000)
psycopg2.extras.execute_values(cur, "INSERT INTO kiln_reading(kiln_push_id,sensor_id,temperature_c) VALUES %s",
                               reading_rows, page_size=5000)
c.commit()
print("kiln_push:", len(push_data), "| kiln_wagon:", len(wagon_rows), "| kiln_reading:", len(reading_rows))
cur.execute("SELECT count(*) FROM kiln_push"); print("تایید kiln_push:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM kiln_wagon"); print("تایید kiln_wagon:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM kiln_reading"); print("تایید kiln_reading:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM kiln_sensor"); print("تایید kiln_sensor:", cur.fetchone()[0])
cur.close(); c.close()
