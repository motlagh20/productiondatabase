# M5 — Platform Architecture & Build Plan

> **Status: build in progress.** The M5 docs were approved 2026-08-28 (gate passed per §8);
> the first thin vertical slice (F2→F7) is implemented — see §9.
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

## 2b. App DB separation — DONE (dev)

- **App DB = dedicated container** `productiondb-app` (Docker, `docker-compose.app.yml`):
  PostgreSQL 16 on **port 5434**, database `mes_app`, user `mes`. Volume `pgdata_app`
  is separate from staging's `pgdata_hist`. A staging reload/incident cannot touch app data.
- **Staging** stays on `productiondb-data` (port 5433, db `postgres`) as read-only historical source
  for dimension seeding only (alias `staging`).
- Wired via `backend/.env` (`DB_PORT=5434` for `default`; `STAGING_DB_PORT=5433` for `staging`).
  `.env` is git-ignored — never commit credentials.
- Port `5432` = the FROZEN reference app (PostgREST/SQLite). Never touch (ADR-0002).
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

- `POST /api/dryer/cycles/`
- `POST /api/setting/events/`
- `POST /api/kiln/pushes/`  (kiln exit is auto-derived on push — no exit endpoint)
- `POST /api/packing/headers/`
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

M5 docs (this file + ADR-0007) are **approved by owner** (2026-08-28). `M5_SRS.md` (expand §3),
`M5_API_CONTRACT.md` (expand §4) drafted; Django models + React scaffold built (2026-08-29).

## 9. Implementation status (2026-08-29)

The first **thin vertical slice** is built: F2 Setting load → F3 Kiln push → F4 Kiln exit →
F5 Packing → F7 Wagon journey trace. 50 files, +5622 lines in `backend/` and `frontend/`.
PR [#1](https://github.com/motlagh20/productiondatabase/pull/1) (`m5-slice-build` → `m0-docs`).

### What was built
- **Backend (`backend/`):** Django 6.1 + DRF project, single `mes` app. Two PostgreSQL DB
  aliases — `default` → `mes_app` (Django-owned, migrations) + `staging` → historical
  source (read-only, DB router prevents writes). TokenAuthentication + CORS for Vite.
- **Models:** 6 dimension tables (Operator, Chamber, Product, Glaze, Wagon, KilnSensor) +
  7 spine/fact tables (WagonTrip with 8-state machine, SettingLoad, KilnPush, KilnReading,
  KilnExit, PackingHeader, PackingWagon).
- **Service layer (`mes/services.py`):** trip assignment, FIFO-44 push ceiling, exit_push_seq
  = entry_push_seq + 43, packing close with `select_for_update()` locking. All functions
  `@transaction.atomic`. Replay-safe via `client_token` UNIQUE on SettingLoad, KilnPush,
  PackingHeader.
- **Endpoints:** 5 write (setting loads, kiln pushes/exits, packing headers) + 1 journey read
  + 6 dimension dropdowns + 1 awaiting-discharge list + 1 auth token obtain. All behind
  `IsAuthenticated`.
- **Dimension seeding:** `seed_dimensions` management command reads staging once via raw SQL;
  idempotent `update_or_create`. Wagon filter enforces clean-core 1..80 range at the seed
  boundary.
- **Historical replay (ETL layer, ADR-0008):** `replay_historical` management command reads
  staging (`dryer_cycle`+`dryer_reading` → `setting_event`+`setting_wagon` → `kiln_push`+`kiln_wagon`
  → `packing_header`+`packing_wagon`) and re-creates the full trip spine in the app via the
  **real domain services** (`create_dryer_cycle` / `create_setting_batch` / `push_wagon` /
  `register_packing`) — so F1→F5, FIFO-44, the 44-capacity ceiling, and the journey state
  machine are exercised at real volume (18,558 dryer cycles; ~20k setting events; ~38k pushes;
  ~93k packing wagons). Dirty history is **not** admitted: any row whose `wagon_no` is NULL or
  outside 1..80, or whose chamber/operator FK is missing, is written to the app's `EtlReject`
  table (module, source_row, reason, raw) for human adjudication against the paper ledgers.
  Replay is idempotent via deterministic UUID `client_token`s derived from staging source keys.
  This is the missing "hard 30%": the app is now load-tested against real historical shape,
  not just synthetic single-trip tests.
- **Demo slice (`make_demo_slice`):** because the historical snapshot stops at ~1404, every trip
  is `completed` and the live dashboards (in-tunnel wagons, awaiting-discharge, occupancy) are
  empty. This command copies a genuinely-populated historical window (1399.03.08..1399.06.08,
  which has data in ALL modules) and rebases it to **1405.03.08..1405.06.08** (near "today"
  1405.06.08), leaving the tail in a live (`in_progress` / `in_tunnel` / `awaiting_discharge`)
  state so management dashboards show realistic near-current activity. Replay-safe via
  `demo:`-namespaced client_tokens; `--clear` removes the slice. Original archive untouched.
- **ETL verified result (full replay of all historical staging):**
  - setting: **11,120** events loaded, 13,245 rejected (dirty `wagon_no` NULL/>80 — expected).
  - kiln: **31,301** pushes loaded, 7,525 rejected (orphan pushes for wagons whose setting
    batch was dirty → no trip existed; correctly quarantined).
  - packing: **3,181** headers loaded, 55,324 wagon-rows rejected (orphans whose upstream trip
    was rejected, plus a few duplicate historical packing rows caught by `register_packing`'s
    completed-trip guard).
  - Spine outcome: **31,301 WagonTrip**, all `completed`; 31,301 KilnExit (all discharged);
    0 wagons stuck in tunnel / awaiting-discharge. **Peak tunnel occupancy = 43** (never
    exceeds the 44-wagon physical ceiling — FIFO-44 confirmed against real data; the apparent
    "153" at the tail of the sequence is purely the 110 unexited end-of-file wagons still in
    the tunnel when the ledger was snapped, not a capacity violation).
  - Lesson learned: pushes and exits MUST be interleaved on one sequence-ordered timeline;
    running all pushes before any exit fills the 44-wagon tunnel and jams (false "tunnel full"
    rejects). Fixed in `replay_historical` stage 2.
- **Tests:** 12 acceptance tests covering FIFO-44 ceiling + slot freeing, exit=entry+43,
  one-trip-across-days spine, replay idempotency, out-of-range plate rejection, plate dropdown
  range, packing state guard, unauthenticated rejection, service-layer rule violation.
- **Frontend (`frontend/`):** React 19 + TypeScript + Vite + Tailwind v4. Persian RTL layout
  (Vazirmatn font, `lang="fa" dir="rtl"`). Pages: Login, SettingLoadForm, KilnPushForm (18
  sensors), KilnExitForm, PackingForm (multi-wagon from awaiting-discharge), JourneyPage
  (per-plate timeline). Axios + Token auth, Jalali date helpers, clean-core dropdowns.

### Deferred (not this slice)
- F1 Dryer cycle, F6 occupancy dashboard, F8 daily counts, F9 dimension CRUD, F10 correction
  workflow, N1 offline queue, per-role route guards, waiting-hall temperature logging.
