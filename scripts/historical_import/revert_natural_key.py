#!/usr/bin/env python3
# REVERT the natural_key changes made by apply_date_fixes.py.
# We must NOT touch natural_key (it's the JOIN key). date_jalali stays fixed;
# natural_key is restored to its ORIGINAL form (old malformed date + |hour|car).
# The original date segment is recovered from the preview CSV (old_date_jalali).
import csv, psycopg2
from pathlib import Path

CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")

# map push_id -> original (old) date segment from preview CSV
prev=Path(r"C:/Users/Mohammad/Desktop/kiln_date_fixes_preview.csv")
revert={}
for r in csv.DictReader(open(prev,encoding="utf-8-sig")):
    if r["confidence"] in ("HIGH","CHECK") and r["proposed_date_jalali"] not in ("","???"):
        revert[int(r["push_id"])]=r["old_date_jalali"]

c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("SELECT id, natural_key FROM kiln_pushes WHERE id = ANY(%s)", (list(revert),))
restored=0
for pid, nk in cur.fetchall():
    old=revert[pid]
    rest=nk.split("|",1)[1] if "|" in nk else ""   # keep |hour|car verbatim
    new_nk=f"{old}|{rest}"
    cur2=psycopg2.connect(**CONN); cu=cur2.cursor()
    cu.execute("UPDATE kiln_pushes SET natural_key=%s WHERE id=%s", (new_nk, pid))
    cur2.commit(); cu.close(); cur2.close()
    restored+=1
cur.close(); c.close()
print(f"natural_key restored for {restored} rows (date_jalali kept fixed).")
