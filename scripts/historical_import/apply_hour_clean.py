#!/usr/bin/env python3
# APPLY: clean kiln_pushes.hour where a spurious date prefix was stored.
# '1900-01-01 18:20:00' -> '18:20:00' via single SQL regexp_replace.
# ONLY the hour column changes. natural_key untouched (owner rule). Idempotent.
import psycopg2, time
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
t=time.time()
cur.execute("""
  UPDATE kiln_pushes
  SET hour = regexp_replace(hour, '.*?(\\d{1,2}:\\d{2}:\\d{2}).*', '\\1')
  WHERE hour ~ '\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}\\s'   -- date-prefixed rows only
""")
n=cur.rowcount
c.commit(); cur.close(); c.close()
print(f"FIXED hour rows: {n}  ({time.time()-t:.1f}s)")
