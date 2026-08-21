# M4 — Clean Data Layer (Materialized-Ready Views)

**Status:** ✅ COMPLETE (2026-08-21) · Branch `m0-docs` · Last commit `f902adb`+ (M4 add)
**Purpose:** expose the flag-only-corrected historical data as a clean **read layer**
for the future application (Django/DRF per ADR-0001/0002), without ever mutating raw
source values.

---

## 1. Design principle

- Raw values are **immutable** (Master Rules §32/§44). Every view surfaces
  `COALESCE(corrected_value, value)` so the application always reads the *clean*
  value while the original remains auditable.
- Views live in `sql/schema/20_clean_views.sql` and are `CREATE OR REPLACE` (re-runnable).
- No new tables, no data duplication — pure projection over existing data.

---

## 2. Views delivered

| View | Rows | What it does |
|------|------|--------------|
| `v_clean_packing` | 89,602 | packing records + composite product (`products.mold_type × glaze`) + `COALESCE(corrected_grade1, grade1)` + `wagon_flagged` boolean |
| `v_clean_kiln_temps` | 511,117 | kiln temps with `COALESCE(corrected_value, value)` + `was_corrected` flag + wagon_no |
| `v_clean_dryer_readings` | 36,737 | dryer temp/humidity with `COALESCE(corrected_value, value)` + `was_corrected` |
| `v_open_anomalies` | 907 raw / 27 grouped | ONLY flag-only rows still needing plant ledger review (record date extracted from `natural_key`) |

### `v_open_anomalies` contents (the 27 grouped rows the plant must verify)
- `packing_records.wagon_no` — 757 raw (13 grouped)
- `setting_operations.wagon_no` — 138 raw (5 grouped)
- `kiln_pushes.incoming_car_id` — 5 raw (2 grouped)
- `setting_operations.chamber_no` — 7 raw (7 grouped)

These keep their **original (likely mistyped) value** + a record date, per owner
directive "واگن‌ها رو تغییر نده فعلاً" — the plant decides final values from ledgers.

---

## 3. Verification

`hermes-verify-m4-views2.py` (ad-hoc) confirmed:
- All 4 views exist + non-empty.
- `v_clean_kiln_temps.was_corrected = 381` (matches `kiln_temp_correction`).
- `v_clean_dryer_readings` humidity corrected = 9 (matches `dryer_humidity_correction`).
- `v_open_anomalies` contains ONLY the 4 flag-only types (no already-corrected rows leak).
- `kiln_temp.zone` 82 rows all `resolved` in `review_queue`.
- Export `review_queue_v4.xlsx` shows exactly **27 `نیاز_به_بررسی=بله`** rows.

*(Ad-hoc verification only — no test/lint/build harness exists in repo.)*

---

## 4. Reproduce

```bash
# load the views
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/20_clean_views.sql

# (optional) re-apply corrections if DB rebuilt
python scripts/historical_import/apply_kiln_temp_fix.py
python scripts/historical_import/apply_dryer_humidity_fix.py
python scripts/historical_import/apply_grade1_fix.py
python scripts/historical_import/apply_preheat_textfix.py
python scripts/historical_import/apply_textfix_all.py
python scripts/historical_import/apply_kiln_zone_textfix.py
```

---

## 5. Next phase (M5 → application code)

The clean layer is ready for the platform build:
- A thin read-only API (Django/DRF or FastAPI) can serve `v_clean_*` immediately.
- `v_open_anomalies` feeds a "review queue" UI for the plant to resolve wagon/chamber
  typos against physical ledgers.
- No schema change needed before M5 — the views are the contract.

---

*Generated 2026-08-21. Raw source values untouched; `COALESCE` provides the clean read.*
