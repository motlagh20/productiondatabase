# Historical Data Import — Runbook

> How to (re)load the 4 MES modules into PostgreSQL 16 staging from `xls/consolidated/All/*.xlsx`.
> **Authoritative sources:** see [DATA_SOURCES.md](DATA_SOURCES.md) — only the 4 `-All`/`Merged` files are inputs;
> `xls/real data/` and per-year splits are legacy/ignored.
> **Principle:** read-only on sources; no fabricated values; batched + idempotent.
> This runbook reflects the **current staging build** (2026-08-26), which diverged from the
> pre-build ERD — table names below are the staging tables, not the ERD's.

## Prerequisites
- Docker (for persistent DB) OR local PostgreSQL 16.
- Python 3.11+ with `openpyxl`, `psycopg2-binary`, `jdatetime`.
- Source workbooks at `xls/consolidated/All/` (`Set_All_1.xlsx`, `Dryer-All.xlsx`, `Kiln-Merged.xlsx`, `Packing-All.xlsx`).

## 0. Start the staging DB
```bash
# container productiondb-data — postgres:16, port 5433
# connection: host=localhost port=5433 user=postgres password=test db=postgres
docker start productiondb-data      # or: docker compose -f docker-compose.data.yml up -d
```

## 1. Create schema (idempotent — IF NOT EXISTS)
```bash
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/30_setting.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/31_dryer.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/32_kiln.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/33_packing.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/34_wagon_linking.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/35_wagon_trip.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/36_glaze.sql
psql -h localhost -p 5433 -U postgres -d postgres -f sql/schema/36b_glaze_link.sql

## 2. Load dimensions (operators / chambers / products)
```bash
python scripts/historical_import/extract_dimensions.py
python scripts/historical_import/load_dimensions.py
```

## 3. Load fact modules (batched, idempotent ETL)
Each script clears only its own module tables first (TRUNCATE inside), so re-running
is safe and never doubles rows.
```bash
python scripts/historical_import/etl_setting.py
python scripts/historical_import/etl_dryer.py
python scripts/historical_import/etl_kiln.py
python scripts/historical_import/etl_packing.py
```

## 3b. Link wagons across modules (run AFTER step 3)
Builds the `wagon` master, sets `wagon_id` on the 3 fact tables, and populates
`kiln_exit` (the awaiting-discharge list). Idempotent.
```bash
python scripts/historical_import/etl_link.py
```
Physical model (owner-confirmed 2026-08-27):
- `wagon_no` is a physical plate NAME (e.g. '12'), not a sequence counter.
- A push = one Excel row, keyed by `source_row` (NOT date+time — 33 operator-typo
  (date,time) collisions existed; the old key merged multiple wagons into one push).
- The kiln is a FIFO conveyor of FIXED capacity 44: a wagon entering at `push_seq` P
  exits at `push_seq` P+43 deterministically. On exit it waits in `kiln_exit`
  (awaiting discharge); Packing later takes one or several.

## 4. Verify (ad-hoc row counts + FK integrity)
```bash
python -c "import psycopg2; c=psycopg2.connect(host='localhost',port=5433,user='postgres',password='test',dbname='postgres'); cur=c.cursor()
for t in ['setting_event','setting_wagon','dryer_cycle','dryer_reading','kiln_push','kiln_wagon','kiln_reading','kiln_sensor','kiln_exit','wagon','packing_header','packing_wagon']:
    cur.execute('SELECT count(*) FROM '+t); print(t, cur.fetchone()[0])"
```
Expected: setting_event 20520 · setting_wagon 67683 · dryer_cycle 18558 · dryer_reading 18370 ·
kiln_push 38820 · kiln_wagon 38820 · kiln_reading 698014 · kiln_sensor 18 · kiln_exit 38710 ·
wagon 89 · packing_header 8543 · packing_wagon 93381.

## 5. Review queue (legacy frozen-app path — superseded)
The frozen-app `review_queue` export (`export_review_csv.py` → `xls/consolidated/review_queue_export.xlsx`)
is preserved for plant handoff of the 27 flag-only wagon/chamber rows. The new staging ETLs log
structural rejects into per-module reject handling instead.

## Validation model (staging ETL)
- Each row classification: `Valid | Warning | Invalid | Unmapped`. Malformed dates / out-of-range
  temps / `HH:MM:SS` time casts are skipped-and-counted, never fabricated.
- Kiln: 83 pushes have <18 sensor readings — genuine Excel gaps, recovered where any row of the
  push carries the value (merge-first-valid logic).
- Setting: 11 source rows rejected (row-shift anomalies) and logged.
- Dryer: 3 source rows rejected and logged.

## Idempotency
Each `etl_*.py` TRUNCATEs its own module tables at start, then re-inserts — re-running yields the
same counts, never duplicates. 1397 (months 11–12 missing) loads idempotently when completed.

## Notes
- `product` dimension is shared across modules (`product_code_kiln` / `product_code_packing`).
- `kiln_wagon.setting_wagon_id` is a nullable link to `setting_wagon` (matched downstream).
- Date format normalized to `YYYY.MM.DD`; Packing source uses `YYYY/MM/DD` (slashes) → normalized.

*Staging load first completed: 2026-08-26. Pre-build load (legacy `load_*.py` / wide tables) is
superseded — see README deviation note + `docs/M2_5_ERD_SCHEMA.md` for the target ERD.*
