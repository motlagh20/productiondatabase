#!/usr/bin/env python3
# Export full kiln dataset for owner review. Two CSVs:
#   1) kiln_pushes_full.csv  - push metadata (date/hour/incoming_car/product/shift)
#   2) kiln_readings_full.csv - every sensor reading (push_id, zone_group, zone_reading, value)
# Also prints a small table of malformed dates for quick inspection.
import csv, psycopg2, io, re, os
from pathlib import Path

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()

OUT=Path(r"C:/Users/Mohammad/Desktop")
OUT.mkdir(exist_ok=True)

def valid4(d):
    m=re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$", str(d or ""))
    if not m: return False
    y,mo,dd=int(m.group(1)),int(m.group(2)),int(m.group(3))
    return 1<=mo<=12 and 1<=dd<=31

# 1) pushes
cur.execute("""SELECT id, date_jalali, hour, shift, product_code, input_type,
                      incoming_car_id, pushing_time_min, natural_key
               FROM kiln_pushes ORDER BY id""")
cols=[d[0] for d in cur.description]
pushes=cur.fetchall()
with open(OUT/"kiln_pushes_full.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(cols)
    for r in pushes: w.writerow(r)
print("kiln_pushes_full.csv:", len(pushes), "rows ->", OUT/"kiln_pushes_full.csv")

# 2) readings
cur.execute("""SELECT push_id, zone_group, zone_reading, value, source
               FROM kiln_temperature_readings ORDER BY push_id, zone_group, zone_reading""")
cols=[d[0] for d in cur.description]
reads=cur.fetchall()
with open(OUT/"kiln_readings_full.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(cols)
    for r in reads: w.writerow(r)
print("kiln_readings_full.csv:", len(reads), "rows ->", OUT/"kiln_readings_full.csv")

# 3) malformed dates summary
cur.execute("SELECT date_jalali, count(*) FROM kiln_pushes GROUP BY 1")
dd={}
for d,n in cur.fetchall():
    if not valid4(d): dd[d]=dd.get(d,0)+n
print("\n=== MALFORMED date_jalali values (count) ===")
for d in sorted(dd, key=lambda x:-dd[x]):
    print(f"  {d!r}: {dd[d]}")
print("total malformed push rows:", sum(dd.values()))
cur.close(); c.close()
