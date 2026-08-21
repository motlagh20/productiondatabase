#!/usr/bin/env python3
# Apply the 13 dirty kiln-temp values (non-numeric, e.g. '718/', '9+40', '6+0').
# Owner rule 2026-08-21: strip non-digit characters and concatenate the remaining
# digits. EXCEPTION: '6+0' -> 600 (a dropped trailing zero, confirmed by owner).
# SAFE: raw_value is NEVER overwritten; cleaned_value gains the cleaned number;
# resolved=TRUE; correction_reason='strip_nondigit'. No new readings row inserted
# (the parent push has no valid reading for that zone). Idempotent.
import psycopg2, re
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# known exceptions confirmed by owner
EXCEPTIONS={"6+0":"600"}

def clean(s):
    s=str(s)
    if s in EXCEPTIONS:
        return EXCEPTIONS[s]
    digits="".join(c for c in s if c.isdigit())
    return digits if digits else s

cur.execute("""SELECT id, raw_value FROM review_queue
               WHERE field_name LIKE 'kiln_temp%' AND raw_value ~ '[^0-9.]' AND resolved=FALSE""")
rows=cur.fetchall()
applied=0
for rid, raw in rows:
    cleaned=clean(raw)
    cur.execute("""UPDATE review_queue
                      SET cleaned_value=%s,
                          suggested_fix=%s,
                          correction_reason='strip_nondigit',
                          resolved=TRUE, resolved_by='system'
                    WHERE id=%s""",
                (cleaned, f"{raw} -> {cleaned}", rid))
    applied+=1
conn.commit()

# report
cur.execute("SELECT raw_value, cleaned_value FROM review_queue WHERE correction_reason='strip_nondigit' ORDER BY id")
print(f"applied (flagged+cleaned): {applied}")
for r in cur.fetchall():
    print(f"  {r[0]} -> {r[1]}")
cur.execute("SELECT count(*) FROM review_queue WHERE resolved")
res=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM review_queue")
tot=cur.fetchone()[0]
print(f"review_queue total resolved now: {res} / {tot}")
cur.close(); conn.close()
