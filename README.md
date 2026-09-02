# Manufacturing Analytics & Execution Platform

This project has been **redefined** per the [Master Project Rules](docs/00_MASTER_PROJECT_RULES.md): the goal is a configurable, multi-factory **Manufacturing Analytics & Execution Platform** (Django + DRF, React + TypeScript, PostgreSQL), built documentation-first. The initial roof-tile/ceramic plant is the reference implementation, not the architecture.

## Staging database — historical load status (2026-08-26)

> **Intermediate data-load phase** (not the final app DB). PostgreSQL 16 on `productiondb-data`
> (localhost:5433, db `postgres`). It loads the 4 MES modules from the consolidated Excel
> sources so analysts can validate before the Django/React build. Final app DB is a later milestone.

**Source of truth:** `xls/consolidated/All/*.xlsx` (the owner-declared final reference workbooks). See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for the exact 4 files and what to ignore. **These Excel files are for requirements analysis + history access only** — they must not distort the app's core design (boundary enforced by [ADR-0008](adr/ADR-0008-clean-core-vs-historical-etl.md)); all old data is loadable via the separate ETL layer.
**DDL:** `sql/schema/30_setting.sql` · `31_dryer.sql` · `32_kiln.sql` · `33_packing.sql` · `34_wagon_linking.sql` (wagon master, FIFO-44 kiln_exit) · `35_wagon_trip.sql` (trip spine) · `36_glaze.sql` (glaze dimension master) + `36b_glaze_link.sql` · `37_etl_trip_map.sql` (ETL reconciliation map, empty)
**ETL (batched, idempotent):** `scripts/historical_import/etl_setting.py` · `etl_dryer.py` · `etl_kiln.py` · `etl_packing.py` · `etl_link.py` (wagon linking)

| Module | Tables | Loaded rows | Rejects |
|---|---|---|---|
| Setting | `setting_event` / `setting_wagon` | 20,520 / 67,683 | 11 |
| Dryer | `dryer_cycle` / `dryer_reading` | 18,558 / 18,370 | 3 |
| Kiln | `kiln_push` / `kiln_wagon` / `kiln_reading` / `kiln_sensor` / `kiln_exit` | 38,820 / 38,820 / 698,014 / 18 / 38,710 | — |
| Packing | `packing_header` / `packing_wagon` | 8,543 / 93,381 | — |
| Linking | `wagon` (master) | 89 distinct wagons | 110 null `wagon_no` kept as gaps |

**Wagon linking (2026-08-28):** `etl_link.py` builds the `wagon` master, sets `wagon_id` on the 3 fact tables, and populates `kiln_exit` (awaiting-discharge list). Physical model: `wagon_no` = plate name (not counter); kiln = FIFO conveyor of fixed capacity **44** (wagon entering at `push_seq` P exits at P+43). Push key = `source_row` (not date+time — 33 operator-typo duplicates existed). **Known gaps (kept, not dropped per SAFE-APPLY):** 110 kiln rows with NULL `wagon_no` → `xls/consolidated/kiln_null_wagon_no.csv`; rows 11784/11785 are a date,time duplicate (operator typo) pending paper-ledger review.

**Deviation note (ADR-0001):** this staging build diverged from the pre-build ERD (`docs/M2_5_ERD_SCHEMA.md`)
table names — e.g. `kiln_pushes`+`kiln_temperature_readings` (wide) became `kiln_push`+`kiln_wagon`+`kiln_reading`+`kiln_sensor` (row-oriented, 18 sensors). The staging tables are the working load; the ERD remains the target for the final app schema. Legacy frozen-app tables (`kiln_pushes`, `kiln_temperature_readings`, `kiln_temp_correction`, `wagon_master`, `packing_records`, `v_clean_kiln_temps`) were **dropped 2026-08-27** after a verified staging load; a `pg_dump` backup is kept at `.db_backup_kiln/`.

**Current phase:** **M5 vertical slice + UI redesign complete** (2026-09-02). Django + DRF backend (`backend/`) and React 19 + TypeScript + Tailwind v4 frontend (`frontend/`) implement F1–F7: Dryer load/unload/readings → Setting chamber-centric batch → Kiln push (FIFO-44) → Packing (awaiting-discharge) → Wagon journey trace. The frontend is a 10-page dual-theme (light/dark) Persian RTL shell with Jalali dates, sidebar navigation, and the `ui.tsx` shared component library. The app DB (`mes_app`) is Django-owned; staging remains a read-only historical source. Dimensions seeded from staging via `seed_dimensions`. PR [#1](https://github.com/motlagh20/productiondatabase/pull/1) (`m5-slice-build` → `m0-docs`).

> **Canonical vs deprecated tables:** Django models MUST reference only the canonical tables listed in [M5_PLATFORM_PLAN.md §2](docs/M5_PLATFORM_PLAN.md). Legacy duplicates `operators`, `products`, `setting_wagons`, `dryer_readings` are still present in staging for audit only — do NOT model them. Verification is via `scripts/verify/hermes-verify-staging.py` (row counts + FK + FIFO-44), not a committed CI suite yet.

## Status of the existing app in this repository

The application you see here (Docker/PostgREST stack, `web/` SPA, `server.py`, SQLite files) is **frozen as a read-only reference implementation** — kept runnable for domain discovery, receiving no further development ([ADR-0002](adr/ADR-0002-freeze-legacy-app-as-reference.md), [Master Specification §I.5](docs/MASTER_SPECIFICATION.md)). Do not add features to it or "fix" it. Its known defects are documented, deliberately unfixed, in [Appendix A](docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) — do not expose it outside a trusted network.

## Directory guide

| Path | What it is |
|---|---|
| `docs/` | **The project's governing documents.** Constitution: [00_MASTER_PROJECT_RULES.md](docs/00_MASTER_PROJECT_RULES.md) · Blueprint: [MASTER_SPECIFICATION.md](docs/MASTER_SPECIFICATION.md) · Evidence annexes: [A](docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) · [B](docs/APPENDIX_B_DATA_ASSETS.md) · [C](docs/APPENDIX_C_DATA_VS_SCHEMA.md) (data-vs-schema reconciliation) · Part V addendum: [config-driven import & PMS donor](docs/PART_V_ADDENDUM.md) · **[OVERVIEW.md](docs/OVERVIEW.md)** (one-page project status) · **[M0_SIGNOFF.md](docs/M0_SIGNOFF.md)** (architecture approval gate) · **[M1_PLANT_VALIDATION.md](docs/M1_PLANT_VALIDATION.md)** (P0 resolved) · **[M2_HISTORICAL_IMPORT_SPEC.md](docs/M2_HISTORICAL_IMPORT_SPEC.md)** (import spec) · **[M2.5_ERD_SCHEMA.md](docs/M2_5_ERD_SCHEMA.md)** (database ERD) · **[M3_DATA_CLEANING_REPORT.md](docs/M3_DATA_CLEANING_REPORT.md)** (cleaning audit trail) · **[M4_CLEAN_DATA_LAYER.md](docs/M4_CLEAN_DATA_LAYER.md)** (clean read-layer views) · **[IMPORT_RUNBOOK.md](docs/IMPORT_RUNBOOK.md)** (how to load) |
| `adr/` | Architecture Decision Records — incl. [ADR-0004](adr/ADR-0004-pms-as-design-ux-donor.md) (PMS donor), [ADR-0005](adr/ADR-0005-setting-three-layer-model.md) (Setting 3-layer), [ADR-0006](adr/ADR-0006-dimension-redefinition.md) (dimensions), [ADR-0007](adr/ADR-0007-application-architecture-m5.md) (M5 app stack), [ADR-0008](adr/ADR-0008-clean-core-vs-historical-etl.md) (clean core vs historical ETL boundary) |
| `xls/` | **Protected historical data assets.** `xls/*.csv` = the owner's normalized-design prototype (schema reference, **not** the data source); `xls/real data/` = the **authoritative native Excel workbooks** (~80 MB, 22 files incl. `Packing-All.xlsx`, Jalali 1391–1404). Never modify source. Cataloged in [Appendix B](docs/APPENDIX_B_DATA_ASSETS.md) |
| `sql/`, `web/`, `docker-compose.yml`, `nginx.conf`, `postgrest.conf` | Frozen reference implementation (active stack: PostgreSQL 16 + PostgREST + Nginx) |
| `server.py`, `schema.sql`, `*.db`, root `*.py` scripts | Frozen reference implementation (superseded Flask/SQLite stack) |
| `backend/` | **M5 Django + DRF application** — `config/` (settings/urls/wsgi), `mes/` (models, services, views, serializers, migrations, tests). Two DB aliases: `default` → `mes_app` (Django-owned), `staging` → historical source (read-only). FIFO-44 service layer, replay-safe POSTs, dimension seeding |
| `frontend/` | **M5 React 19 + TypeScript + Vite + Tailwind v4 operator UI** — Persian RTL, Vazirmatn font, Jalali dates. Pages: Login, Setting load, Kiln push (18 sensors), Kiln exit, Packing, Wagon journey trace. Axios + Token auth, dev proxy `/api` → `:8000` |
| `DESIGN_*.md`, `IMPLEMENTATION_GUIDE.md`, `QUICK_REFERENCE.md` | Frozen UI design-system reference (Persian/RTL) |

## Documentation set

1. [Master Project Rules](docs/00_MASTER_PROJECT_RULES.md) — product constitution (permanent source of truth)
2. [Master Product & Architecture Specification v0.1](docs/MASTER_SPECIFICATION.md) — **the single project blueprint**: charter · glossary · domain model · as-is process · historical data architecture · architectural principles · roadmap · AI collaboration protocol ([ADR-0003](adr/ADR-0003-consolidated-master-specification.md))
3. [Appendix A — Current System Inventory](docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) — review findings of the frozen app
4. [Appendix B — Data Assets](docs/APPENDIX_B_DATA_ASSETS.md) — catalog of `xls/` historical data

**Note for AI assistants:** per the specification's Part VIII protocol, load [docs/MASTER_SPECIFICATION.md](docs/MASTER_SPECIFICATION.md) (plus the ADRs) before any work. Never invent business rules; unresolved questions live in the specification's Part II §II.7. Architecture changes require an ADR.

## Running the frozen reference app (for domain discovery only)

```bash
docker-compose up -d
# Web UI: http://localhost  ·  PostgREST: http://localhost:3000  ·  PostgreSQL: localhost:5432
```
