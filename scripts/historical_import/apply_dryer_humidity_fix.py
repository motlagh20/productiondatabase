#!/usr/bin/env python3
# Propose + apply mean-of-neighbors correction for out-of-range dryer HUMIDITY values.
# Owner rule 2026-08-21: "دما ها هم مثل رطوبت اگر ایراد دارن بر اساس میانگین اصلاح کن"
# (apply mean to all reported Invalid humidity items).
# These are dryer_readings rows where metric='humidity' AND value>100 (9 rows, incl. 3480).
# Each gets corrected_value = mean of 3 nearest healthy (0-100) humidity in the SAME
# operation_id. SAFE: raw value is NEVER overwritten; corrected_value is added. Idempotent.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# ensure dryer_readings has corrected_value (mirror of kiln_temperature_readings)
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name='dryer_readings' AND column_name='corrected_value'""")
if not cur.fetchone():
    cur.execute("ALTER TABLE dryer_readings ADD COLUMN corrected_value NUMERIC")
    print("ALTER: added dryer_readings.corrected_value")

# ensure correction tracking table
cur.execute("""CREATE TABLE IF NOT EXISTS dryer_humidity_correction (
    id SERIAL PRIMARY KEY,
    reading_id BIGINT REFERENCES dryer_readings(id),
    raw_value NUMERIC,
    neighbor_1 NUMERIC, neighbor_2 NUMERIC, neighbor_3 NUMERIC,
    proposed_value NUMERIC,
    applied BOOLEAN DEFAULT FALSE,
    correction_reason TEXT,
    corrected_by TEXT
)""")
print("TABLE: dryer_humidity_correction ready")

# the bad humidity rows (reported Invalid)
cur.execute("""SELECT id, operation_id, value FROM dryer_readings
               WHERE metric='humidity' AND value > 100 ORDER BY value DESC""")
bad=cur.fetchall()

applied=0
for rid, op, val in bad:
    # 3 nearest healthy (0-100) humidity in same operation
    cur.execute("""SELECT value FROM dryer_readings
                   WHERE operation_id=%s AND metric='humidity'
                     AND value BETWEEN 0 AND 100
                   ORDER BY abs(value - %s) LIMIT 3""", (op, val))
    nbrs=[float(r[0]) for r in cur.fetchall()]
    if len(nbrs) < 3:
        print(f"  skip id={rid} op={op} val={val}: only {len(nbrs)} healthy neighbors")
        continue
    mean=round(sum(nbrs)/3, 2)
    cur.execute("""INSERT INTO dryer_humidity_correction
                       (reading_id, raw_value, neighbor_1, neighbor_2, neighbor_3,
                        proposed_value, applied, correction_reason, corrected_by)
                    VALUES (%s,%s,%s,%s,%s,%s,TRUE,'mean_of_neighbors','system')
                    ON CONFLICT DO NOTHING""",
                (rid, val, nbrs[0], nbrs[1], nbrs[2], mean))
    cur.execute("UPDATE dryer_readings SET corrected_value=%s WHERE id=%s", (mean, rid))
    applied+=1
    print(f"  id={rid} raw={val} -> mean({nbrs}) = {mean}")

conn.commit()
cur.execute("SELECT count(*) FROM dryer_readings WHERE corrected_value IS NOT NULL")
print(f"dryer_readings with corrected_value: {cur.fetchone()[0]}")
cur.close(); conn.close()
print(f"applied: {applied}")
