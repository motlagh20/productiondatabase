#!/usr/bin/env python3
# ETL: link wagons across Setting -> Kiln -> Packing (staging PostgreSQL).
# Physical model (owner-confirmed 2026-08-27):
#   * wagon_no = physical plate name (not a counter)
#   * kiln is a FIFO conveyor of FIXED capacity 44: a wagon entering at push_seq P
#     exits at push_seq P+43 deterministically.
#   * on exit it waits in kiln_exit (awaiting discharge); Packing takes one/sevaral.
# push_seq is assigned by etl_kiln.py (physical row order = source_row order).
# Idempotent: re-running is safe (upserts on unique keys, no duplicates).
import psycopg2

PG = dict(host='localhost', port=5433, dbname='postgres', user='postgres', password='test')
c = psycopg2.connect(**PG); cur = c.cursor()

# push_seq already populated by etl_kiln.py (sorted by source_row). Verify presence:
cur.execute("SELECT count(*) FROM kiln_push WHERE push_seq IS NULL")
null_seq = cur.fetchone()[0]
if null_seq:
    raise SystemExit(f"ERROR: {null_seq} kiln_push rows have NULL push_seq — run etl_kiln.py first")
cur.execute("SELECT count(*) FROM kiln_push")
print("[1] push_seq verified present on", cur.fetchone()[0], "pushes")

# ---- 2. wagon master: collect every distinct wagon name from the 3 modules ----
cur.execute("SELECT DISTINCT wagon_no FROM setting_wagon WHERE wagon_no IS NOT NULL")
sw = {str(r[0]) for r in cur.fetchall()}
cur.execute("SELECT DISTINCT wagon_no FROM kiln_wagon WHERE wagon_no IS NOT NULL")
kw = {str(r[0]) for r in cur.fetchall()}
cur.execute("SELECT DISTINCT wagon_no FROM packing_wagon WHERE wagon_no IS NOT NULL")
pw = {str(r[0]) for r in cur.fetchall()}
all_names = sw | kw | pw
print("[2] distinct wagon names:", len(all_names))
# insert missing
cur.execute("SELECT wagon_name, wagon_id FROM wagon")
existing = {str(r[0]): r[1] for r in cur.fetchall()}
new = [n for n in all_names if n not in existing]
for n in new:
    cur.execute("INSERT INTO wagon(wagon_name) VALUES(%s) RETURNING wagon_id", (n,))
    existing[n] = cur.fetchone()[0]
c.commit()
print("     wagon table now has", len(existing), "rows (+", len(new), "new)")

# ---- 3. set wagon_id on the 3 fact tables ----
cur.execute("UPDATE setting_wagon SET wagon_id=w.wagon_id FROM wagon w WHERE setting_wagon.wagon_no::text=w.wagon_name AND setting_wagon.wagon_id IS NULL")
n1 = cur.rowcount
cur.execute("UPDATE kiln_wagon SET wagon_id=w.wagon_id FROM wagon w WHERE kiln_wagon.wagon_no::text=w.wagon_name AND kiln_wagon.wagon_id IS NULL")
n2 = cur.rowcount
cur.execute("UPDATE packing_wagon SET wagon_id=w.wagon_id FROM wagon w WHERE packing_wagon.wagon_no::text=w.wagon_name AND packing_wagon.wagon_id IS NULL")
n3 = cur.rowcount
c.commit()
print(f"[3] wagon_id set: setting={n1}, kiln={n2}, packing={n3}")

# ---- 4. kiln_exit: every kiln_wagon exits at push_seq+43 ----
# TRUNCATE first (idempotent: push_seq changed after kiln reload, old rows stale)
cur.execute("TRUNCATE kiln_exit RESTART IDENTITY")
c.commit()
cur.execute("""SELECT kw.wagon_id, kp.push_seq, kp.push_date
               FROM kiln_wagon kw JOIN kiln_push kp ON kw.kiln_push_id=kp.kiln_push_id
               WHERE kw.wagon_id IS NOT NULL""")
rows = cur.fetchall()
ins = 0
for wid, seq, d in rows:
    exit_seq = seq + 43
    cur.execute("""INSERT INTO kiln_exit(wagon_id, entry_push_seq, exit_push_seq, exit_date)
                   VALUES(%s,%s,%s,%s) ON CONFLICT (wagon_id, exit_push_seq) DO NOTHING""",
                (wid, seq, exit_seq, d))
    ins += cur.rowcount
c.commit()
print("[4] kiln_exit rows inserted:", ins)

# ---- 5. validator: kiln always holds <=44 wagons ----
# "inside kiln" at push P = wagons with entry_push_seq <= P < exit_push_seq (not yet discharged-past)
cur.execute("""
SELECT MAX(depth) FROM (
  SELECT kp.push_seq,
         (SELECT count(*) FROM kiln_exit ke
          WHERE ke.entry_push_seq <= kp.push_seq AND ke.exit_push_seq > kp.push_seq) AS depth
  FROM kiln_push kp
) x
""")
maxdepth = cur.fetchone()[0]
print("[5] max concurrent wagons in kiln (should be <=44):", maxdepth)
ok44 = (maxdepth is not None and maxdepth <= 44)

# ---- 6. link report (no destructive action) ----
cur.execute("SELECT count(*) FROM setting_wagon sw WHERE sw.wagon_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kiln_wagon kw WHERE kw.wagon_id=sw.wagon_id)")
setting_no_kiln = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM kiln_wagon kw WHERE kw.wagon_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM setting_wagon sw WHERE sw.wagon_id=kw.wagon_id)")
kiln_no_setting = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM packing_wagon pw WHERE pw.wagon_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM kiln_exit ke WHERE ke.wagon_id=pw.wagon_id)")
packing_no_exit = cur.fetchone()[0]
cur.close(); c.close()
print("[6] link gaps (informational, NOT dropped):")
print("     setting wagons with no kiln match:", setting_no_kiln)
print("     kiln wagons with no setting match:", kiln_no_setting)
print("     packing wagons with no kiln_exit:", packing_no_exit)
print("RESULT:", "PASS (44-capacity OK)" if ok44 else "WARN: kiln depth >44 — review link model")
