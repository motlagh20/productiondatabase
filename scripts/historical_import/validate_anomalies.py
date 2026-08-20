#!/usr/bin/env python3
# Post-load validation: scan for cross-field / range anomalies NOT caught by load scripts,
# and append them to review_queue. Read-only on facts, write-only to review_queue.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()
added=0
def add(table,nk,field,val,cls,fix):
    global added
    cur.execute("INSERT INTO review_queue(table_name,natural_key,field_name,raw_value,issue_class,suggested_fix) VALUES(%s,%s,%s,%s,%s,%s)",(table,nk,field,str(val),cls,fix))
    added+=1

# 1. packing: grade1 > total
cur.execute("SELECT natural_key, grade1, total FROM packing_records WHERE grade1 > total")
for nk,g1,tot in cur.fetchall():
    add("packing_records",nk,"grade1",f"{g1}>{tot}","Invalid","grade1 exceeds total; verify")
# 2. dryer humidity > 100
cur.execute("""SELECT dr.operation_id, dr.hour_offset, dr.value FROM dryer_readings dr
               WHERE dr.metric='humidity' AND dr.value > 100""")
for op,h,v in cur.fetchall():
    add("dryer_readings",f"op={op}|h={h}","value",v,"Invalid","humidity % cannot exceed 100; verify")
# 3. kiln temp < 100 (implausibly low for a firing kiln)
cur.execute("""SELECT kt.push_id, kt.zone_group, kt.zone_reading, kt.value FROM kiln_temperature_readings kt
               WHERE kt.value < 100""")
for pid,g,r,v in cur.fetchall():
    add("kiln_temperature_readings",f"push={pid}",f"{g}.{r}",v,"Warning","temp <100 implausible; verify sensor/scale")
conn.commit()
print(f"Added {added} cross-field/range anomalies to review_queue.")
cur.execute("SELECT count(*) FROM review_queue"); print("total review_queue:",cur.fetchone()[0])
cur.close(); conn.close()
