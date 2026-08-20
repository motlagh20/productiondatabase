#!/usr/bin/env python3
# Ad-hoc verification of loaded data (NOT a test suite). Checks row counts, FK integrity,
# review_queue population, wagon_master consistency. Run after load_*.py.
import psycopg2
CONN=dict(host="localhost",port=5433,dbname="postgres",user="postgres",password="test")
conn=psycopg2.connect(**CONN); cur=conn.cursor()
print("=== ROW COUNTS ===")
for t in ["operators","products","glazes","dryer_operations","dryer_readings",
          "kiln_pushes","kiln_temperature_readings","setting_operations",
          "setting_shift_unloads","setting_wagons","wagon_master","packing_records",
          "review_queue","config_chamber_bounds","config_shift_pattern",
          "config_wagon_bounds","config_temp_bounds","config_drying_cadence"]:
    cur.execute(f"SELECT count(*) FROM {t}")
    print(f"  {t:28} {cur.fetchone()[0]:>10,}")
print("\n=== FK INTEGRITY (orphans should be 0) ===")
checks=[
 ("dryer_operations.product_code -> products.canonical_code",
  "SELECT count(*) FROM dryer_operations d LEFT JOIN products p ON d.product_code=p.canonical_code WHERE d.product_code IS NOT NULL AND p.canonical_code IS NULL"),
 ("kiln_pushes.product_code -> products.canonical_code",
  "SELECT count(*) FROM kiln_pushes k LEFT JOIN products p ON k.product_code=p.canonical_code WHERE k.product_code IS NOT NULL AND p.canonical_code IS NULL"),
 ("setting_operations.product_code -> products.canonical_code",
  "SELECT count(*) FROM setting_operations s LEFT JOIN products p ON s.product_code=p.canonical_code WHERE s.product_code IS NOT NULL AND p.canonical_code IS NULL"),
 ("packing_records.product_code -> products.canonical_code",
  "SELECT count(*) FROM packing_records p LEFT JOIN products pr ON p.product_code=pr.canonical_code WHERE p.product_code IS NOT NULL AND pr.canonical_code IS NULL"),
 ("packing_records.wagon_no -> wagon_master.wagon_no",
  "SELECT count(*) FROM packing_records p LEFT JOIN wagon_master w ON p.wagon_no=w.wagon_no WHERE p.wagon_no IS NOT NULL AND w.wagon_no IS NULL"),
 ("setting_wagons.wagon_no -> wagon_master.wagon_no",
  "SELECT count(*) FROM setting_wagons sw LEFT JOIN wagon_master w ON sw.wagon_no=w.wagon_no WHERE sw.wagon_no IS NOT NULL AND w.wagon_no IS NULL"),
]
for name,q in checks:
    cur.execute(q); n=cur.fetchone()[0]
    print(f"  [{'OK' if n==0 else 'FAIL'}] {name}: {n} orphans")
print("\n=== REVIEW QUEUE by class ===")
cur.execute("SELECT issue_class, count(*) FROM review_queue GROUP BY issue_class ORDER BY 2 DESC")
for cls,n in cur.fetchall(): print(f"  {cls:14} {n:>8,}")
print("\n=== WAGON MASTER consistency ===")
cur.execute("SELECT count(DISTINCT wagon_no) FROM setting_wagons")
sw=cur.fetchone()[0]
cur.execute("SELECT count(*) FROM wagon_master")
wm=cur.fetchone()[0]
print(f"  distinct wagons in setting_wagons={sw}, wagon_master rows={wm}  [{'OK' if sw==wm else 'MISMATCH'}]")
cur.close(); conn.close()
print("\n(ad-hoc verification complete)")
