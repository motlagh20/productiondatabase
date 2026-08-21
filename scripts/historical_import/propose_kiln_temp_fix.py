#!/usr/bin/env python3
# Propose kiln-temp corrections WITHOUT applying them (owner directive 2026-08-21).
# For each out-of-range reading (value>1200 or value<100), find the nearest VALID
# value (100<=v<=1200) of the SAME (zone_group, zone_reading) in OTHER pushes, and
# record it as proposed_value in kiln_temp_correction (applied=FALSE).
import psycopg2
from collections import defaultdict
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
LO,HI=100,1200
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# 1. all valid same-zone values, keyed by (zone_group, zone_reading) -> list of values
cur.execute("SELECT zone_group, zone_reading, value FROM kiln_temperature_readings WHERE value BETWEEN %s AND %s",(LO,HI))
valid=defaultdict(list)
for zg,zr,v in cur.fetchall():
    valid[(zg,zr)].append(float(v))

# 2. flagged readings
cur.execute("SELECT id, push_id, zone_group, zone_reading, value FROM kiln_temperature_readings WHERE value > %s OR value < %s",(HI,LO))
flagged=cur.fetchall()

cur.execute("TRUNCATE kiln_temp_correction RESTART IDENTITY")
ins=0
for rid,pid,zg,zr,v in flagged:
    cands=valid.get((zg,zr),[])
    if not cands:
        prop=None; note="no valid same-zone value found in other pushes"
    else:
        # nearest valid value
        prop=min(cands, key=lambda x: abs(x-float(v)))
        note=f"nearest valid {zg}.{zr} in other pushes = {prop}"
    cur.execute("""INSERT INTO kiln_temp_correction(reading_id,push_id,zone_group,zone_reading,raw_value,proposed_value,applied,note)
                   VALUES(%s,%s,%s,%s,%s,%s,FALSE,%s)""",
                (rid,pid,zg,zr,v,prop,note))
    ins+=1
conn.commit()

# summary
cur.execute("SELECT count(*) FROM kiln_temp_correction")
print(f"Proposed corrections (not applied): {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM kiln_temp_correction WHERE proposed_value IS NOT NULL")
print(f"  with a nearest-valid proposal: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM kiln_temp_correction WHERE proposed_value IS NULL")
print(f"  without proposal (no valid neighbor): {cur.fetchone()[0]}")
cur.close(); conn.close()
