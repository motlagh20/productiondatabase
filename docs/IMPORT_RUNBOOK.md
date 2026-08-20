# Historical Data Import — Runbook

> How to load the 22 authoritative workbooks into PostgreSQL 16. Derived from M2 spec + M2.5 ERD.
> **Principle:** read-only on `xls/real data/`; no fabricated values; config-driven bounds; idempotent.

## Prerequisites
- PostgreSQL 16 (or Docker: `docker run -d --name pd_pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16`)
- Python 3.11+ with `openpyxl`, `xlrd`, `psycopg2-binary`
- Source workbooks at `C:/Users/Mohammad/Nextcloud/Projects/Trae/ProductionDatabase/xls/real data/`

## Steps
1. **Create schema** (idempotent dev reset available):
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

## Validation model
Every row is classified: `Valid | Warning | Invalid | Duplicate | Unmapped | NeedsReview`.
Flagged rows land in `review_queue` (never auto-fixed). Counts observed in first load:
- `Invalid` (temp>1200 ×10 typo, wagon>80 typo): ~151
- chamber>40, wagon>80: ~300 combined
- All resolved post-build per M1/M2 (physical-ledger correction cycle).

## Idempotency
All fact tables use `natural_key UNIQUE` + `ON CONFLICT DO UPDATE`. Re-running merges, never duplicates. 1397 (months 11–12 missing) loads idempotently when completed post-build.

## Notes
- `product_code` = canonical (P-SOFAL-KHODRANG), re-derived from (نوع محصول + شرح محصول) per M1-A1.
- `month`/`day` are TEXT (source mixes numbers and month names).
- `setting_wagons` parses 1–4 repeating wagon blocks (cols 12-19,20-27,28-35,36-43); block count varies per file.
- `glaze` kept as free text (typo-fix only: اخراء→اخرا).
- `grade2` ≡ waste; carried if present, blank if absent (M1-E1).

*First successful load: 2026-08-20 — 893k fact rows + dimensions, 0 FK orphans.*
