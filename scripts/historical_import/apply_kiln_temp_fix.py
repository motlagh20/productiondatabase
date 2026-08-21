#!/usr/bin/env python3
# Apply confirmed kiln-temp corrections to kiln_temperature_readings.corrected_value.
# SAFE: raw `value` is NEVER overwritten; proposed_value -> corrected_value; applied=TRUE.
# Only confident proposals (proposed_value IS NOT NULL) are applied; the 10 far-from-
# neighbor rows stay NULL for plant review. Idempotent: re-running does not double-apply.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# 1. apply confident proposals
cur.execute("""
    UPDATE kiln_temperature_readings r
       SET corrected_value = c.proposed_value
      FROM kiln_temp_correction c
     WHERE r.id = c.reading_id
       AND c.proposed_value IS NOT NULL
       AND (r.corrected_value IS NULL OR r.corrected_value <> c.proposed_value)
""")
upd=cur.rowcount

# 2. mark applied
cur.execute("""
    UPDATE kiln_temp_correction
       SET applied = TRUE
     WHERE proposed_value IS NOT NULL
""")
applied=cur.rowcount
conn.commit()

# 3. report
cur.execute("SELECT count(*) FROM kiln_temperature_readings WHERE corrected_value IS NOT NULL")
n_corrected=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM kiln_temperature_readings WHERE corrected_value IS NULL AND value > 1200 OR corrected_value IS NULL AND value < 100")
still_flagged=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM kiln_temp_correction WHERE applied")
n_applied=cur.fetchone()[0]
print(f"updated readings with corrected_value: {upd}")
print(f"kiln_temp_correction rows marked applied: {applied}")
print(f"total readings now carrying a correction: {n_corrected}")
print(f"out-of-range readings still un-corrected (NULL, for plant review): {still_flagged}")
print(f"proposal rows marked applied in audit table: {n_applied}")
cur.close(); conn.close()
