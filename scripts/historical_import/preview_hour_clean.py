#!/usr/bin/env python3
# PREVIEW ONLY (no DB write): show hour values that will be cleaned.
# Rule (owner): drop the spurious date prefix, keep the HH:MM:SS time.
import psycopg2, re
from pathlib import Path
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("SELECT id, hour FROM kiln_pushes ORDER BY id")
tm=re.compile(r'(\d{1,2}):(\d{2}):(\d{2})')
will_fix=0; already_ok=0; nullish=0; samples=[]
for pid,h in cur.fetchall():
    s=str(h or "")
    m=tm.search(s)
    if m:
        new=m.group(0)
        if new==s.strip():
            already_ok+=1
        else:
            will_fix+=1
            if len(samples)<8: samples.append((pid, s, new))
    else:
        nullish+=1
cur.close(); c.close()
print(f"will-fix (date-prefixed -> time only): {will_fix}")
print(f"already OK (HH:MM:SS):                {already_ok}")
print(f"nullish/parse-fail:                   {nullish}")
print("samples (id, old, new):")
for s in samples: print("  ", s)
