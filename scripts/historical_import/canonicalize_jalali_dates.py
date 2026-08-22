#!/usr/bin/env python3
# M5: Canonicalize Jalali dates in the historical DB.
# Owner rule: years before 1400 are stored 2-digit (91,96,98...) and must become
# 4-digit (1391,1396,1398...). All separators unified to '.' and month/day zero-padded
# to 2 digits -> canonical format 'YYYY.MM.DD'. Stored as TEXT so it can NEVER be
# misread as Gregorian ISO ('-') or US ('/').
# Raw source files are NOT touched (Master Rules); only our DB text columns.
import psycopg2, re
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")

def canon(d):
    """Return canonical 'YYYY.MM.DD' (dot-sep, 4-digit yr, zero-padded) or None if unparseable."""
    if not d:
        return None
    s=d.strip()
    # 4-digit year already -> normalize separators + zero-pad
    m=re.match(r"^\s*(\d{4})([./\-])(\d{1,2})\2(\d{1,2})\s*$", s)
    if m:
        return f"{m.group(1)}.{int(m.group(3)):02d}.{int(m.group(4)):02d}" if False else f"{m.group(1)}.{int(m.group(3)):02d}.{int(m.group(4)):02d}"
    # 2-digit year -> pad to 13xx + zero-pad
    m=re.match(r"^\s*(\d{2})([./\-])(\d{1,2})\2(\d{1,2})\s*$", s)
    if m:
        y=int(m.group(1))
        return f"13{y:02d}.{int(m.group(3)):02d}.{int(m.group(4)):02d}"
    # malformed (e.g. '8.4', '14.3.2.24', 'push=...') -> leave as-is (flagged elsewhere)
    return None

TABLES=["packing_records","kiln_pushes","setting_operations","dryer_operations"]
conn=psycopg2.connect(**CONN); cur=conn.cursor()
total=0; skipped=0
for t in TABLES:
    cur.execute(f"SELECT id, date_jalali FROM {t} WHERE date_jalali IS NOT NULL")
    rows=cur.fetchall()
    for rid, d in rows:
        c=canon(d)
        if c is None:
            skipped+=1
            continue
        if c!=d:
            cur.execute(f"UPDATE {t} SET date_jalali=%s WHERE id=%s", (c, rid))
            total+=1
    conn.commit()
    print(f"{t}: committed (cumulative updated {total})")
cur.close(); conn.close()
print(f"TOTAL updated: {total} | skipped (malformed): {skipped}")
