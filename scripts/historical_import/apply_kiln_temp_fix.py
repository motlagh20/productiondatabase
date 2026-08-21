#!/usr/bin/env python3
# Apply kiln-temp corrections to kiln_temperature_readings.corrected_value.
# Owner 2026-08-21: replace each out-of-range value with the MEAN of its 3 nearest
# healthy same-zone values (neighbor_1/2/3). SAFE: raw `value` is NEVER overwritten;
# the mean is written to corrected_value. All 381 flagged rows get a mean (even the
# far-from-neighbor ones, since they still have healthy neighbors). applied=TRUE.
# Idempotent: re-running does not double-apply.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()

# 1. set corrected_value = mean(neighbor_1,2,3) for every flagged reading
cur.execute("""
    UPDATE kiln_temperature_readings r
       SET corrected_value = (
             SELECT (COALESCE(c.neighbor_1,0)+COALESCE(c.neighbor_2,0)+COALESCE(c.neighbor_3,0))
                  / NULLIF(
                      (CASE WHEN c.neighbor_1 IS NOT NULL THEN 1 ELSE 0 END)
                    + (CASE WHEN c.neighbor_2 IS NOT NULL THEN 1 ELSE 0 END)
                    + (CASE WHEN c.neighbor_3 IS NOT NULL THEN 1 ELSE 0 END), 0)
             FROM kiln_temp_correction c
            WHERE c.reading_id = r.id
       )
      FROM kiln_temp_correction c2
     WHERE r.id = c2.reading_id
       AND (r.corrected_value IS NULL OR r.corrected_value <> (
             SELECT (COALESCE(c.neighbor_1,0)+COALESCE(c.neighbor_2,0)+COALESCE(c.neighbor_3,0))
                  / NULLIF(
                      (CASE WHEN c.neighbor_1 IS NOT NULL THEN 1 ELSE 0 END)
                    + (CASE WHEN c.neighbor_2 IS NOT NULL THEN 1 ELSE 0 END)
                    + (CASE WHEN c.neighbor_3 IS NOT NULL THEN 1 ELSE 0 END), 0)
             FROM kiln_temp_correction c WHERE c.reading_id = r.id
       ))
""")
upd=cur.rowcount

# 2. mark all as applied + record structured reason
cur.execute("""UPDATE kiln_temp_correction
                 SET applied = TRUE,
                     correction_reason = 'mean_of_neighbors',
                     corrected_by = 'system'
               WHERE applied = FALSE OR correction_reason IS NULL""")
applied=cur.rowcount
conn.commit()

# 3. report
cur.execute("SELECT count(*) FROM kiln_temperature_readings WHERE corrected_value IS NOT NULL")
n_corrected=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM kiln_temperature_readings WHERE (value>1200 OR value<100) AND corrected_value IS NULL")
still_null=cur.fetchone()[0]
print(f"updated readings with corrected_value (mean of 3 neighbors): {upd}")
print(f"kiln_temp_correction rows marked applied: {applied}")
print(f"total readings now carrying a correction: {n_corrected}")
print(f"out-of-range readings still NULL (no neighbors at all): {still_null}")
# sample
cur.execute("""SELECT r.value, r.corrected_value, c.neighbor_1, c.neighbor_2, c.neighbor_3
               FROM kiln_temperature_readings r JOIN kiln_temp_correction c ON c.reading_id=r.id
               WHERE r.value::text LIKE '935935%' LIMIT 1""")
s=cur.fetchone()
print(f"sample: raw {s[0]} -> mean {s[1]} (neighbors {s[2]},{s[3]},{s[4]})")
cur.close(); conn.close()
