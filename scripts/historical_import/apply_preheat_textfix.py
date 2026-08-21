#!/usr/bin/env python3
# Fix the 2 remaining 'kiln_temp.preheat' = '5..' Invalid rows in review_queue.
# The raw value is non-numeric (rejected at load, so no kiln_temperature_readings row).
# Owner directive 2026-08-21: apply mean of healthy (100-1200) same-push preheat
# neighbors (like kiln/ humidity corrections). This push (25951) has 2 healthy
# preheat readings, both 518.0 -> mean = 518.
# SAFE: review_queue.cleaned_value holds the fix; raw '5..' is preserved. Idempotent.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# find the 2 '5..' preheat rows + their push_id via natural_key
cur.execute("""SELECT id, natural_key FROM review_queue
               WHERE raw_value::text LIKE '5..%' AND field_name='kiln_temp.preheat'""")
rows=cur.fetchall()
applied=0
for rqid, nk in rows:
    # natural_key format: 'date|time|wagon' -> match kiln_pushes by natural_key
    cur.execute("SELECT id FROM kiln_pushes WHERE natural_key=%s", (nk,))
    pids=[r[0] for r in cur.fetchall()]
    if not pids:
        print(f"  skip rq={rqid}: no matching push for nk={nk}"); continue
    pid=pids[0]
    cur.execute("""SELECT value FROM kiln_temperature_readings
                   WHERE push_id=%s AND zone_group='preheat' AND value BETWEEN 100 AND 1200
                   ORDER BY value""", (pid,))
    healthy=[float(r[0]) for r in cur.fetchall()]
    if len(healthy) < 1:
        print(f"  skip rq={rqid}: no healthy preheat in push {pid}"); continue
    mean=round(sum(healthy)/len(healthy), 2)
    cur.execute("""UPDATE review_queue
                   SET cleaned_value=%s, correction_reason='mean_of_neighbors',
                       resolved=TRUE, resolved_by='system',
                       suggested_fix='non-numeric; filled with mean of healthy same-push preheat'
                   WHERE id=%s""", (str(mean), rqid))
    applied+=1
    print(f"  rq={rqid} push={pid} healthy_preheat={healthy} -> mean={mean}")

conn.commit()
cur.execute("""SELECT count(*) FROM review_queue
               WHERE raw_value::text LIKE '5..%' AND field_name='kiln_temp.preheat' AND resolved""")
print(f"resolved '5..' preheat rows: {cur.fetchone()[0]}")
cur.close(); conn.close()
print(f"applied: {applied}")
