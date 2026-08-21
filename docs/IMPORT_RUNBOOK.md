# Historical Data Import — Runbook

> How to load the 22 authoritative workbooks into PostgreSQL 16. Derived from M2 spec + M2.5 ERD.
> **Principle:** read-only on `xls/real data/`; no fabricated values; config-driven bounds; idempotent.

## Prerequisites
- Docker (for persistent DB) OR local PostgreSQL 16.
- Python 3.11+ with `openpyxl`, `xlrd`, `psycopg2-binary`.
- Source workbooks at `C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data/`.

## 0. Start the persistent warehouse DB
```bash
docker compose -f docker-compose.data.yml up -d   # postgres:16, port 5433, volume pgdata_hist (survives restart)
# connection: host=localhost port=5433 user=postgres password=test db=postgres
# stop later:  docker compose -f docker-compose.data.yml down   (data preserved in volume)
# full wipe:   docker compose -f docker-compose.data.yml down -v  (DESTROYS loaded data)
```

## 1. Create schema (dev reset available)
   ```bash
   psql -f sql/init/00_schema.sql          # creates 18 tables + seeds config
   # dev only: psql -f sql/init/99_reset.sql  # DROP SCHEMA public CASCADE first
   ```
2. **Load dimension masters** (operators/products/glazes):
   ```bash
   python load_dimensions.py
   ```
3. **Load fact tables** (order: dryer, kiln, setting, packing):
   ```bash
   python load_dryer.py
   python load_kiln.py
   python load_setting.py
   python load_packing.py
   ```
4. **Verify** (row counts, FK integrity, review_queue, wagon_master):
   ```bash
   python verify_load.py
   ```

## 5. Export review_queue for plant handoff
```bash
python export_review_csv.py
# -> xls/consolidated/review_queue_export.xlsx  (Farsi, RTL, grouped by value + occurrence count)
# -> xls/consolidated/review_queue_export.csv   (UTF-8 BOM, for tooling)
```
Outputs a QA worksheet with columns: جدول | ستون | مقدار_خام | تعداد_تکرار | وضعیت |
عیب‌شناسی | اقدام_پیشنهادی | نیاز_به_بررسی | یادداشت. Rows are grouped by (table, field,
value, class) with an occurrence count, and each row carries a Farsi diagnosis + proposed
action. Use the **.xlsx** for plant staff (guaranteed Persian/RTL, no glyph loss); CSV for pipelines.
No auto-correction is applied — flagged rows stay in `review_queue` per owner directive.

## Validation model
Every row is classified: `Valid | Warning | Invalid | Duplicate | Unmapped | NeedsReview`.
Flagged rows land in `review_queue`. Kiln-temp `Invalid` rows are corrected via the
neighbor method into `kiln_temperature_readings.corrected_value` (raw `value` preserved);
the other flagged classes (wagon>80, chamber>40, grade1>total, humidity) remain OPEN
per owner directive ("واگنها رو هم تغییر نده"). Counts after first load + kiln fix:
- `Invalid`: 134 resolved (kiln temp ×10/×100 typo, neighbor-corrected), 35 still open
- `Warning`: 1153 open (wagon>80, chamber>40, low-temp, etc.)

## Idempotency
All fact tables use `natural_key UNIQUE` + `ON CONFLICT DO UPDATE`. Re-running merges, never duplicates. 1397 (months 11–12 missing) loads idempotently when completed post-build.

## Notes
- `product_code` = canonical (P-SOFAL-KHODRANG), re-derived from (نوع محصول + شرح محصول) per M1-A1.
- `month`/`day` are TEXT (source mixes numbers and month names).
- `setting_wagons` parses 1–4 repeating wagon blocks (cols 12-19,20-27,28-35,36-43); block count varies per file.
- `glaze` kept as free text (typo-fix only: اخراء→اخرا).
- `grade2` ≡ waste; carried if present, blank if absent (M1-E1).

*First successful load: 2026-08-20 — 893k fact rows + dimensions, 0 FK orphans.*
