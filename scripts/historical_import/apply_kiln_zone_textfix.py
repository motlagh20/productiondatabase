#!/usr/bin/env python3
# M4 fill: the 82 'kiln_temp.zone' Invalid rows in review_queue were kiln temperatures
# that failed load (odd formats like '9450.0','98502.0','9+40') so they have NO row in
# kiln_temperature_readings. Owner directive: apply mean of 3 nearest healthy (100-1200)
# same-push kiln temps, like the kiln correction method. Store in review_queue.cleaned_value
# (raw preserved). Idempotent.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

cur.execute("""SELECT id, natural_key, raw_value FROM review_queue
               WHERE table_name='kiln_pushes' AND field_name='kiln_temp.zone'
                 AND issue_class='Invalid' AND NOT resolved""")
rows=cur.fetchall()
applied=0; skipped=0
for rqid, nk, raw in rows:
    cur.execute("SELECT id FROM kiln_pushes WHERE natural_key=%s", (nk,))
    pids=[r[0] for r in cur.fetchall()]
    if not pids:
        print(f"  skip rq={rqid}: no push for nk={nk}"); skipped+=1; continue
    pid=pids[0]
    cur.execute("""SELECT value FROM kiln_temperature_readings
                   WHERE push_id=%s AND value BETWEEN 100 AND 1200
                   ORDER BY value LIMIT 3""", (pid,))
    healthy=[float(r[0]) for r in cur.fetchall()]
    if len(healthy) < 3:
        print(f"  skip rq={rqid} push={pid}: only {len(healthy)} healthy neighbors (raw={raw})")
        skipped+=1; continue
    mean=round(sum(healthy)/len(healthy), 2)
    cur.execute("""UPDATE review_queue
                   SET cleaned_value=%s, correction_reason='mean_of_neighbors',
                       resolved=TRUE, resolved_by='system',
                       suggested_fix='non-loaded kiln temp; filled with mean of healthy same-push'
                   WHERE id=%s""", (str(mean), rqid))
    applied+=1
    if applied<=5 or applied%20==0:
        print(f"  rq={rqid} push={pid} raw={raw} healthy={healthy} -> mean={mean}")

conn.commit()
cur.execute("""SELECT count(*) FROM review_queue
               WHERE table_name='kiln_pushes' AND field_name='kiln_temp.zone'
                 AND resolved AND correction_reason='mean_of_neighbors'""")
print(f"resolved kiln_temp.zone rows: {cur.fetchone()[0]}")
cur.close(); conn.close()
print(f"applied: {applied} | skipped: {skipped}")
