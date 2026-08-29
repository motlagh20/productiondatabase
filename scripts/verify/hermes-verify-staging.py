#!/usr/bin/env python3
"""
hermes-verify-staging.py — minimal staging smoke test (ad-hoc, not CI).
Run: python scripts/verify/hermes-verify-staging.py
Checks: row counts match the last verified load + key FK integrity + FIFO-44 depth.
Exits non-zero on any mismatch (so a rebuild is caught immediately).
"""
import psycopg2, sys

CONN = dict(host="localhost", port=5433, dbname="postgres", user="postgres", password="test")

# (table, column, expected_count) — last verified 2026-08-29
EXPECTED = {
    "setting_event": 20522,
    "setting_wagon": 67694,
    "dryer_cycle": 18558,
    "dryer_reading": 18370,
    "kiln_push": 38820,
    "kiln_wagon": 38820,
    "kiln_reading": 698014,
    "kiln_sensor": 18,
    "kiln_exit": 38710,
    "packing_header": 8543,
    "packing_wagon": 93381,
    "glaze": 7,
    "wagon_trip": 0,
    "etl_trip_map": 0,
}

def main():
    c = psycopg2.connect(**CONN); cur = c.cursor()
    fails = 0
    for t, exp in EXPECTED.items():
        cur.execute(f"SELECT count(*) FROM {t}")
        got = cur.fetchone()[0]
        ok = "OK " if got == exp else "FAIL"
        if got != exp: fails += 1
        print(f"  [{ok}] {t}: {got} (expected {exp})")
    # FK integrity: every kiln_wagon.kiln_push_id must exist in kiln_push
    cur.execute("""SELECT count(*) FROM kiln_wagon kw 
                    LEFT JOIN kiln_push kp ON kp.kiln_push_id=kw.kiln_push_id 
                    WHERE kp.kiln_push_id IS NULL""")
    orphan = cur.fetchone()[0]
    print(f"  [{'OK ' if orphan==0 else 'FAIL'}] kiln_wagon orphan kiln_push_id: {orphan}")
    if orphan: fails += 1
    # FIFO-44 depth: max(exit_push_seq - entry_push_seq) == 43
    cur.execute("SELECT max(exit_push_seq - entry_push_seq) FROM kiln_exit")
    depth = cur.fetchone()[0]
    print(f"  [{'OK ' if depth==43 else 'FAIL'}] FIFO depth: {depth} (expected 43)")
    if depth != 43: fails += 1
    cur.close(); c.close()
    if fails:
        print(f"\n{fails} CHECK(S) FAILED"); sys.exit(1)
    print("\nALL STAGING CHECKS PASSED")

if __name__ == "__main__":
    main()
