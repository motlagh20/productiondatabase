# Manufacturing Analytics & Execution Platform

This project has been **redefined** per the [Master Project Rules](docs/00_MASTER_PROJECT_RULES.md): the goal is a configurable, multi-factory **Manufacturing Analytics & Execution Platform** (Django + DRF, React + TypeScript, PostgreSQL), built documentation-first. The initial roof-tile/ceramic plant is the reference implementation, not the architecture.

**Current phase:** Data profiling & migration blueprints **complete** (see [OVERVIEW.md](docs/OVERVIEW.md)). Master Product & Architecture Specification v0.1 + ADRs 0001–0006 approved for the documentation-first path. No new application code exists yet — see [ADR-0001](adr/ADR-0001-documentation-first-development.md). Ready for M0 architecture sign-off.

## Status of the existing app in this repository

The application you see here (Docker/PostgREST stack, `web/` SPA, `server.py`, SQLite files) is **frozen as a read-only reference implementation** — kept runnable for domain discovery, receiving no further development ([ADR-0002](adr/ADR-0002-freeze-legacy-app-as-reference.md), [Master Specification §I.5](docs/MASTER_SPECIFICATION.md)). Do not add features to it or "fix" it. Its known defects are documented, deliberately unfixed, in [Appendix A](docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) — do not expose it outside a trusted network.

## Directory guide

| Path | What it is |
|---|---|
| `docs/` | **The project's governing documents.** Constitution: [00_MASTER_PROJECT_RULES.md](docs/00_MASTER_PROJECT_RULES.md) · Blueprint: [MASTER_SPECIFICATION.md](docs/MASTER_SPECIFICATION.md) · Evidence annexes: [A](docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) · [B](docs/APPENDIX_B_DATA_ASSETS.md) · [C](docs/APPENDIX_C_DATA_VS_SCHEMA.md) (data-vs-schema reconciliation) · Part V addendum: [config-driven import & PMS donor](docs/PART_V_ADDENDUM.md) · **[OVERVIEW.md](docs/OVERVIEW.md)** (one-page project status) · **[M0_SIGNOFF.md](docs/M0_SIGNOFF.md)** (architecture approval gate) · **[M1_PLANT_VALIDATION.md](docs/M1_PLANT_VALIDATION.md)** (P0 resolved) · **[M2_HISTORICAL_IMPORT_SPEC.md](docs/M2_HISTORICAL_IMPORT_SPEC.md)** (import spec) · **[M2.5_ERD_SCHEMA.md](docs/M2_5_ERD_SCHEMA.md)** (database ERD) · **[M3_DATA_CLEANING_REPORT.md](docs/M3_DATA_CLEANING_REPORT.md)** (cleaning audit trail) · **[M4_CLEAN_DATA_LAYER.md](docs/M4_CLEAN_DATA_LAYER.md)** (clean read-layer views) · **[IMPORT_RUNBOOK.md](docs/IMPORT_RUNBOOK.md)** (how to load) |
| `adr/` | Architecture Decision Records — incl. [ADR-0004](adr/ADR-0004-pms-as-design-ux-donor.md) (PMS donor), [ADR-0005](adr/ADR-0005-setting-three-layer-model.md) (Setting 3-layer), [ADR-0006](adr/ADR-0006-dimension-master-redefinition.md) (composite product + cleaned operators) |
| `xls/` | **Protected historical data assets.** `xls/*.csv` = the owner's normalized-design prototype (schema reference, **not** the data source); `xls/real data/` = the **authoritative native Excel workbooks** (~80 MB, 22 files incl. `Packing-All.xlsx`, Jalali 1391–1404). Never modify source. Cataloged in [Appendix B](docs/APPENDIX_B_DATA_ASSETS.md) |
| `sql/`, `web/`, `docker-compose.yml`, `nginx.conf`, `postgrest.conf` | Frozen reference implementation (active stack: PostgreSQL 16 + PostgREST + Nginx) |
| `server.py`, `schema.sql`, `*.db`, root `*.py` scripts | Frozen reference implementation (superseded Flask/SQLite stack) |
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
