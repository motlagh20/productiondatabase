# ADR-0007 — M5 Application Architecture (Django + DRF / React / PostgreSQL)

- **Status:** Accepted — build phase started 2026-08-29. The F2→F7 vertical slice is implemented
  (`backend/` + `frontend/`, PR [#1](https://github.com/motlagh20/productiondatabase/pull/1)).
  Schema-ownership open question resolved: Django owns a fresh `mes_app` schema (migrations);
  staging stays a read-only historical source via a second DB alias.
- **Date:** 2026-08-28
- **Deciders:** Project owner
- **Related:** ADR-0001 (doc-first), ADR-0002 (freeze legacy), ADR-0004 (PMS UX donor),
  ADR-0006 (dimension master), MASTER_SPECIFICATION §45 (target stack), §772 (M5 = docs only),
  M2.5 (staging ERD), M4 (clean data layer)

## Context

M0–M4 completed: the Master Specification + ADRs 0001–0006 are approved, 4 MES modules
(Setting / Dryer / Kiln / Packing) are loaded into PostgreSQL 16 **staging** (port 5433,
db `postgres`), and wagons are linked across modules via `etl_link.py` (wagon master + FIFO-44
`kiln_exit`). Per MASTER_SPEC §772, **M5 is a documentation milestone** — it produces the SRS,
ERD/DB spec, API contract, and UX blueprint, **no application code**.

Open questions that block clean app design:
- 516 Setting wagons have no Kiln match (awaiting-discharge hall? or data gap?).
- 110 Kiln rows have NULL `wagon_no` (source missing) — kept as gaps per SAFE-APPLY.
- Rows 11784/11785 are a (date,time) operator typo — pending paper-ledger review.
- Staging has duplicate/legacy table names (`operator` vs `operators`, `product` vs `products`,
  `setting_wagon` vs `setting_wagons`, `dryer_reading` vs `dryer_readings`) — must be reconciled
  before Django models target them.
- Staging tables are a **historical load**; the final app DB may diverge (M2.5 ERD is canonical
  target). Decision needed: build Django models on staging tables directly, or treat staging as a
  read-only source and let Django own a fresh app schema.

## Decision

**Stack (confirmed by ADR-0002 / MASTER_SPEC §45):** Django + Django REST Framework (backend),
React + TypeScript (frontend), PostgreSQL (engine). The staging DB at port 5433 is the
**development/integration database** for M5; the production app DB is a later milestone.

**Schema ownership:** Django migrations are the single source of truth for the *application*
schema (MASTER_SPEC §P3). The existing staging tables are treated as a **data source** that the
app reads/writes through Django models. Where a staging table name collides with a legacy/duplicate
(e.g. `operator` vs `operators`), the ADR-0006 dimension master (`operator`, `product`) is
authoritative; duplicates are deprecated, not modeled.

**Module boundaries (from M2.5 + staging):**
- `setting_event` / `setting_wagon` — operator loads a wagon (plate name from `wagon`).
- `dryer_cycle` / `dryer_reading` — chamber-centric, no wagon (confirmed 2026-08-26).
- `kiln_push` / `kiln_wagon` / `kiln_reading` / `kiln_sensor` / `kiln_exit` — FIFO-44 conveyor;
  `kiln_exit` = awaiting-discharge list; `wagon_id` joins to `wagon`.
- `packing_header` / `packing_wagon` — discharge from `kiln_exit`, may batch several wagons.
- `wagon` — physical plate master (89 distinct today).

**API contract (initial scope):** read-only + operator write paths.
- Operator entry: `POST /api/setting/`, `/api/kiln/`, `/api/packing/` (mirror Excel capture).
- Manager dashboard reads: kiln capacity (≤44 in tunnel), wagon journey (setting→…→packing),
  per-module daily counts, sensor trends.
- Auth: Django auth (replaces the frozen app's `app.users` concept per §510).

**UX donor:** the `PMS` repo (ADR-0004) supplies the React 19 + Tailwind + RTL + recharts
visual language; harvested, not merged.

## Consequences

- **Positive:** single migration-managed schema lineage (fixes frozen app's 4 divergent copies,
  Appendix A lesson); doc-first keeps M5 compliant with §772; staging data is immediately usable
  for integration tests.
- **Negative / accepted cost:** dual DB reality (staging load vs app schema) requires an explicit
  ETL boundary; reconciling duplicate table names is grunt work before models land.
- **Follow-up:** after ADR-0007 accepted → write M5_SRS.md, M5_API_CONTRACT.md, M5_UX_BLUEPRINT.md,
  then Django models + React scaffold (still doc-gated until M5 docs approved).
- **Open items to resolve with owner (plant staff):** the 516/110/11784 gaps above; whether the
  app writes to staging tables or a fresh schema.
