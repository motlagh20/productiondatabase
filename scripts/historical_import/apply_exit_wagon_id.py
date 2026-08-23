#!/usr/bin/env python3
# Materialize kiln_pushes.exit_wagon_id using the SAME ordering the app uses.
# We call kiln_chart.ordered_pushes() (the authoritative timeline) and compute
# exit_wagon_id(P) = incoming_car_id at index (rank(P) - 44). Per the owner model a
# wagon enters at push E (slot 1) and, after 44 pushes, exits at slot 44 (push E+44),
# so the wagon EXITING at push P entered 44 pushes earlier. First 44 pushes -> NULL
# (kiln not yet full). Adds ONE nullable column; natural_key (JOIN key) is NEVER
# touched (owner rule). Idempotent.
import sys
sys.path.insert(0, r"C:/Projects/ProductionDatabase")
import kiln_chart as K
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
c=psycopg2.connect(**CONN); cur=c.cursor()
cur.execute("""SELECT 1 FROM information_schema.columns
               WHERE table_name='kiln_pushes' AND column_name='exit_wagon_id'""")
if not cur.fetchone():
    cur.execute("ALTER TABLE kiln_pushes ADD COLUMN exit_wagon_id TEXT")
    print("  column exit_wagon_id added")
else:
    print("  column exit_wagon_id already exists")

pushes=K.ordered_pushes()   # authoritative order: push_seq = idx+1
cur.execute("UPDATE kiln_pushes SET exit_wagon_id = NULL")
upd=[]
for idx,p in enumerate(pushes):
    exit_w = pushes[idx-44]["incoming_car_id"] if idx>=44 else None
    upd.append((exit_w, p["id"]))
cur.executemany("UPDATE kiln_pushes SET exit_wagon_id=%s WHERE id=%s", upd)
n=len(upd); c.commit()
cur.execute("SELECT count(*) FROM kiln_pushes WHERE exit_wagon_id IS NOT NULL")
filled=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM kiln_pushes WHERE exit_wagon_id IS NULL")
nulls=cur.fetchone()[0]
cur.close(); c.close()
print(f"  updated rows: {n}")
print(f"  exit_wagon_id filled: {filled} | null (first 44 / blank prior): {nulls}")
