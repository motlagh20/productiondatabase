# M5 — Platform Architecture & Build Plan (Documentation Milestone)

> **Per MASTER_SPEC §772, M5 produces documents only — no application code.**
> Companion: [ADR-0007](adr/ADR-0007-application-architecture-m5.md) (architecture decision).

## 1. Scope

Build the Manufacturing Analytics & Execution Platform on the approved stack
(Django + DRF / React + TypeScript / PostgreSQL). The initial roof-tile/ceramic plant is the
reference implementation; the architecture must stay multi-factory configurable (MASTER_SPEC §P3).

## 2. Staging DB as integration source

- Dev/integration DB = PostgreSQL 16 at `localhost:5433`, db `postgres` (the existing staging load).
- Authoritative **canonical** tables (Django models MUST reference ONLY these):
  `operator`, `product`, `chamber`, `glaze`, `wagon`, `wagon_trip`,
  `setting_event`, `setting_wagon`, `dryer_cycle`, `dryer_reading`,
  `kiln_push`, `kiln_wagon`, `kiln_reading`, `kiln_sensor`, `kiln_exit`,
  `packing_header`, `packing_wagon`, `etl_reject`, `etl_trip_map`.
- **Deprecated legacy duplicates** (still present in staging, NOT modeled by Django — kept for audit only):
  `operators` (19 rows → use `operator`), `products` (9 → use `product`),
  `setting_wagons` (45,911 → use `setting_wagon`), `dryer_readings` (36,737 → use `dryer_reading`),
  `glazes` (dropped 2026-08-29 → use `glaze`). Do NOT reference these in app code.
- Staging is the historical-data source; Django migrations own the *application* schema. M5 leaves
  the staging load in place and defines the read/write boundary.
- **Excel files are analysis/history artifacts only (owner 2026-08-29).** The 4 `xls/consolidated/All/*.xlsx`
  workbooks are used to *derive requirements* and *access process history* — they must **never** shape
  the app's core schema or business logic. All old data is loadable (via the ETL layer, ADR-0008), but
  because the sources are typo-heavy, they are deliberately kept outside the design loop. The app core
  assumes clean system-generated data; scrubbing/flagging stays in `scripts/historical_import/` only.

## 3. Functional requirements (initial)

Production flow order (owner-specified): **Dryer → Setting → Waiting hall → Kiln → Packing**
(Forming & Glazing not yet in scope).

| ID | Capability | Actor | Source module |
|----|-----------|-------|---------------|
| F1 | Log dryer cycle + 22 hourly readings (clay body dried, chamber 1..40) | Operator | Dryer |
| F2 | Register a wagon load (plate, product, operator, shift) — loads dried body from dryer | Operator | Setting |
| F3 | Register a kiln push (1 wagon, 18 sensors) — wagon from waiting hall | Operator | Kiln |
| F4 | Mark wagon discharge → awaiting-discharge list | Operator | Kiln exit |
| F5 | Register packing (take 1+ wagons from awaiting-discharge) | Operator | Packing |
| F6 | Dashboard: kiln tunnel occupancy (≤44) + waiting-hall + awaiting-discharge | Manager | all |
| F7 | Dashboard: wagon journey trace (dryer → setting → waiting → kiln → packing) | Manager | `wagon` links |
| F8 | Dashboard: daily counts + sensor trends | Manager | all |

## 4. API contract (v1, draft)

Base `/api/`. Django REST Framework, token auth.

- `POST /api/setting/events/` · `POST /api/setting/wagons/`
- `POST /api/dryer/cycles/` · `POST /api/dryer/readings/`
- `POST /api/kiln/pushes/` · `POST /api/kiln/wagons/` · `POST /api/kiln/exits/`
- `POST /api/packing/headers/` · `POST /api/packing/wagons/`
- `GET /api/dashboard/kiln-occupancy/` → `{in_tunnel, capacity:44, awaiting_discharge}`
- `GET /api/dashboard/wagon-journey/?wagon=<name>` → `[setting, kiln_entry, kiln_exit, packing]`
- `GET /api/dashboard/daily-counts/?from=&to=`

## 5. UX blueprint

- **Donor:** `PMS` repo (ADR-0004) — React 19 + Tailwind v4 + RTL + lucide-react + recharts.
- **Screens:** Operator entry (4 module forms, offline-tolerant) · Manager dashboard
  (kiln tunnel view, wagon journey timeline, trend charts) · Login/roles (Django auth).
- **Language:** Persian (Jalali dates via `jdatetime`), RTL.

## 6. Data-integrity rules (carried from staging)

- `wagon_no` = physical plate NAME, never a sequence counter.
- Kiln = FIFO conveyor, fixed capacity **44**; `exit_push_seq = entry_push_seq + 43`.
- Raw source values immutable (MASTER_SPEC §32/§44); corrections are flag-only, never overwrite.
- Known gaps kept, not dropped: 110 NULL `wagon_no` kiln rows; 516 unmatched Setting wagons
  (awaiting-discharge hall hypothesis — confirm with plant staff); 11784/11785 typo (paper-ledger).

## 7. Out-of-scope for M5 docs

- Multi-factory tenancy internals (config only).
- Analytics/ML (post-M5).
- Production deployment (separate milestone).

## 8. Gate to implementation

M5 docs (this file + ADR-0007) are **approved by owner** (2026-08-28). Next: `M5_SRS.md` (expand §3),
`M5_API_CONTRACT.md` (expand §4), then Django models + React scaffold.
