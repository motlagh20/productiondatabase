#!/usr/bin/env python3
# Apply owner's strip-nondigit cleaning rule to ALL non-numeric dirty values in
# review_queue (kiln temps like '718/', '9+40', AND humidity '6+4', etc.).
# Owner rule 2026-08-21: strip non-digit characters and concatenate remaining digits.
# EXCEPTION: '6+0' -> 600 (dropped trailing zero, confirmed by owner).
# SAFE: raw_value is NEVER overwritten; cleaned_value gains the cleaned number;
# resolved=TRUE; correction_reason='strip_nondigit'. Idempotent.
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

# all unresolved, non-numeric (contain a char that is not a digit or dot) raw values,
# EXCLUDING 'x>y' grade comparisons (e.g. '1350.0>156.0') which are real Invalid
# values, not dirty strings to strip.
cur.execute("""SELECT id, raw_value FROM review_queue
               WHERE raw_value::text ~ '[^0-9.]' AND raw_value::text NOT LIKE '%>%' AND resolved=FALSE""")
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
