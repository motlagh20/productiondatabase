#!/usr/bin/env python3
# Fix the 9 packing_records rows where grade1 has a spurious trailing zero (owner
# directive 2026-08-21: "1350.0>156.0" should be "135>156" -> only grade1 is wrong,
# divide grade1 by 10; total stays). SAFE: raw grade1 is NEVER overwritten; a new
# corrected_grade1 column holds the fix. Idempotent.
import psycopg2
CONN=dict(host="localhost",port=5432,dbname="postgres",user="postgres",password="test")
# (port 5433 in this env)
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# add corrected_grade1 column if missing
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name='packing_records' AND column_name='corrected_grade1'""")
if not cur.fetchone():
    cur.execute("ALTER TABLE packing_records ADD COLUMN corrected_grade1 NUMERIC")
    print("ALTER: added packing_records.corrected_grade1")

# the 9 bad rows (grade1 > total) -> corrected_grade1 = grade1/10
cur.execute("SELECT id, grade1, natural_key FROM packing_records WHERE grade1 > total")
bad=cur.fetchall()
applied=0
for rid, g1, nk in bad:
    fixed=round(float(g1)/10, 2)
    cur.execute("UPDATE packing_records SET corrected_grade1=%s WHERE id=%s", (fixed, rid))
    applied+=1
    print(f"  id={rid} grade1={float(g1)} -> corrected_grade1={fixed}")

# mirror into review_queue (resolved, with reason) so export + audit reflect it
cur.execute("SELECT id, raw_value, natural_key FROM review_queue WHERE table_name='packing_records' AND field_name='grade1' AND issue_class='Invalid'")
for rqid, raw, nk in cur.fetchall():
    # parse grade1 from 'g>t'
    g1=float(str(raw).split(">")[0])
    fixed=round(g1/10, 2)
    cur.execute("UPDATE review_queue SET cleaned_value=%s, correction_reason='grade1_div10', resolved=TRUE, resolved_by='system', suggested_fix='grade1 has trailing zero; divided by 10' WHERE id=%s",
                (str(fixed), rqid))

conn.commit()
cur.execute("SELECT count(*) FROM packing_records WHERE corrected_grade1 IS NOT NULL")
print(f"packing_records with corrected_grade1: {cur.fetchone()[0]}")
cur.execute("SELECT count(*) FROM review_queue WHERE correction_reason='grade1_div10' AND resolved")
print(f"review_queue grade1_div10 resolved: {cur.fetchone()[0]}")
cur.close(); conn.close()
print(f"applied: {applied}")
