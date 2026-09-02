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

Production flow order (owner-specified 2026-08-31, [PRODUCTION_FLOW.md](PRODUCTION_FLOW.md) /
[ADR-0009](../adr/ADR-0009-production-workflow-sequence.md)):

**Prep → Forming/Press → Dryer → Glazing *(opt)* → Setting → Waiting hall *(opt)* → Kiln → Packing → Warehouse**

MES app records stages **3, 5, 7, 8** (F1–F5). Prep, press, warehouse not yet in scope; glazing optional.

| ID | Capability | Actor | Source module |
|----|-----------|-------|---------------|
| F1 | Log dryer cycle + 22 hourly readings (clay body dried, chamber 1..40) | Operator | Dryer |
| F2 | Register a **Setting batch** (CHAMBER-CENTRIC): select a dryer chamber (1..40), then record the wagons fed from THAT chamber in one submit — each wagon: plate, glaze, start/end load time, packages, khesht. Batch = (date, shift, chamber, operator). Creates (or reuses) one `wagon_trip` per wagon **at load start**. | Operator | Setting | **After** Dryer; until the chamber is fully emptied its body goes only onto these wagons. If a wagon is partially filled when the chamber runs empty, it stays in the setting area and may receive additional fill from the **next** chamber's unload *before* it leaves for the waiting hall — that subsequent chamber's Setting batch reuses the **same** `wagon_trip` for that wagon (multiple `SettingWagon` rows, one trip). The number of chambers that contribute to one wagon in a single journey is **factory / product dependent, not hardcoded**. The wagon leaves for the waiting hall only when fully filled. After packing the trip completes; a future load for that wagon starts a **new** trip. |
| F3 | Register a kiln push (1 wagon, 18 sensors) — wagon from waiting hall | Operator | Kiln |
| F4 | Mark wagon discharge → awaiting-discharge list | Operator | Kiln exit |
| F5 | Register packing (take 1+ wagons from awaiting-discharge) | Operator | Packing |
| F6 | Dashboard: kiln tunnel occupancy (≤44) + waiting-hall + awaiting-discharge | Manager | all |
| F7 | Dashboard: wagon journey trace (dryer → setting → waiting → kiln → packing) | Manager | `wagon` links |
| F8 | Dashboard: daily counts + sensor trends | Manager | all |

## 3b. Trip lifecycle (one trip per wagon per journey)

A `WagonTrip` starts when a wagon is **first loaded** in the setting area and ends when
that wagon is **packed** (product taken off). The trip is the spine of the wagon's journey
(F7). The lifecycle:

```
[SETTING load starts] → in_progress  (trip_id assigned at first load)
   → waiting_hall  (wagon full, awaiting kiln slot)
   → [KILN push] → in_tunnel
   → [KILN exit] → awaiting_discharge
   → [PACKING] → completed
```

**One trip per wagon per journey.** A wagon moves to the waiting hall only when full.
If a chamber runs empty before the wagon is full, the wagon stays in the setting area and
the **next** chamber's unload can continue filling it — that subsequent Setting batch
reuses the **same trip** (multiple `SettingWagon` rows, one trip). The number of chambers
that contribute to one wagon in a single journey is **factory / product dependent, not
hardcoded** (in the current roof-tile plant it is typically 1, occasionally 2).

After the wagon is packed the trip is completed. Any later load of that same wagon
(weeks later, next shift, next product) starts a **new trip**.

**How the Setting form works:** the operator selects wagons by plate (not trip_id).
`create_setting_batch` checks whether the wagon already has an active trip
(`in_progress` / `body_dried` / `waiting_hall`). If yes → reuse it (multi-chamber
fill within the same journey). If no → create a new trip. Operationally the operator
does not manage trip IDs.

> **Design principle (owner 2026-09-02):** do not hardcode a chamber count into the app
> core. The model is `N` chambers per wagon-journey where `N` is determined by the physical
> process of this factory or any future factory / product. The code must stay flexible.

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

## 9. Implementation status (2026-09-02)

**F1–F7 vertical slice + UI redesign complete.** The full F1 Dryer → F2 Setting → F3/F4 Kiln → 
F5 Packing → F7 Wagon journey trace flow is built with a new dual-theme UI shell. PR
[#1](https://github.com/motlagh20/productiondatabase/pull/1) (`m5-slice-build` → `m0-docs`).

### What was built — backend (`backend/`)
- **Django 6.1 + DRF**, single `mes` app. Two PostgreSQL DB aliases — `default` → `mes_app`
  (Django-owned, migrations) + `staging` → historical source (read-only, DB router prevents
  writes). TokenAuthentication + CORS for Vite.
- **Models:** 6 dimension tables (Operator, Chamber, Product, Glaze, Wagon, KilnSensor) +
  8 spine/fact tables (WagonTrip with 8-state machine, SettingEvent, SettingWagon,
  DryerCycle, DryerReading, KilnPush, KilnReading, KilnExit, PackingHeader, PackingWagon)
  + `ChamberState` control table.
- **Service layer (`mes/services.py`):** `create_dryer_cycle`, `append_dryer_reading`,
  `unload_dryer_chamber`, `create_setting_batch`, `push_wagon`, `register_packing`, plus
  `wagon_journey` for F7. FIFO-44 push ceiling, exit_push_seq = entry_push_seq + 43, packing
  close with `select_for_update()` locking. All functions `@transaction.atomic`. Replay-safe
  via `client_token` UNIQUE on DryerCycle, SettingEvent, KilnPush, PackingHeader.
  **`create_setting_batch` reuses an active trip for a wagon when one exists** (multi-chamber
  fill within the same journey), else creates a new trip — one trip per wagon per journey,
  chamber count not hardcoded.
- **15 endpoints (7 GET + 6 POST + 2 derived):**
  - **Writes (auth required):** POST `dryer/cycles/`, `dryer/readings/`, `dryer/unload/`,
    `setting/events/`, `kiln/pushes/`, `packing/headers/`
  - **Reads (auth required):** GET `dryer/chambers/status/`, `dryer/cycles/list/`,
    `setting/events/list/`, `kiln/pushes/list/`, `dashboard/wagon-journey/`,
    `dashboard/awaiting-discharge/`, `dashboard/active-wagons/`
  - **Dimension dropdowns (public — AllowAny):** GET `dimensions/{operators,products,glazes,
    chambers,wagons,sensors}/`; `chamber_list` supports `?loaded=true|false`, `wagon_list`
    supports `?available=true`.
- **Dimension seeding:** `seed_dimensions` management command reads staging once via raw SQL;
  idempotent `update_or_create`. Wagon filter enforces clean-core 1..80 range.
- **Historical replay (ETL layer, ADR-0008):** `replay_historical` replays all staging
  through real domain services at full historical volume (18,558 dryer cycles; ~20k setting
  events; ~38k pushes; ~93k packing wagons). `EtlReject` quarantines dirty rows.
- **Demo slice (`make_demo_slice`):** copies a 1399 window into the current Jalali year
  (1405.xx.xx), rebased so dashboards show realistic live-edge activity. Trip-per-wagon model:
  no duplicate trips per plate from the same run. **Guarantees exactly K distinct wagons in the
  kiln tunnel** (K = `--wagons` flag, default 44 = full FIFO-44 capacity) with current dates,
  refreshed by re-running daily — the window slides forward so "today" is always live.
  `--clear` removes all demo rows before each build (idempotent).

### What was built — frontend (`frontend/`)
React 19 + TypeScript + Vite + Tailwind v4. Persian RTL layout (`lang="fa" dir="rtl"`).
Dual-theme shell (`ui.tsx` components, light/dark toggle). 10 pages on `App.tsx` lazy routes:

| Page | Module | Key features |
|------|--------|-------------|
| `LoginPage` | Auth | Theme toggle + language switch, gradient brand square |
| `DryerDashboard` | F1 | 3-state chamber card grid (empty/drying/dried), quick-reading modal |
| `DryerLoadForm` | F1 | Empty-chamber select, `postDryerCycle`, recent-loads table |
| `DryerReadingsForm` | F1 | Chamber select, `postDryerReading`, recharts line chart |
| `DryerUnloadForm` | F1 | Unloadable-chamber select, `postDryerUnload`, completed-cycles table |
| `SettingEntryForm` | F2 | Loaded-chamber select, event-level product, 1–4 wagons add/remove |
| `SettingLog` | F2 | Searchable/filterable event table, expandable wagon rows, CSV export |
| `KilnPushForm` | F3 | Active-wagon select, 18-sensor grid, push history table |
| `PackingForm` | F5 | Awaiting-discharge checkbox picker, shift/worker count, per-wagon grades |
| `JourneyPage` | F7 | Plate search → trip cards with 4-stage timeline |

**Design:** `ui.tsx` exports shared primitives (`PageHeader`, `Panel`, `Field`, `TextInput`,
`SelectInput`, `Banner`, `SubmitButton`, `PanelTitle`, table CSS). `Navbar` (sidebar) links
all pages with Arabic numerals. `i18n/` holds 131 FA/EN keys via `useUI().t`.
`JalaliDatePicker` wraps PersianDatePicker for `YYYY.MM.DD` Jalali input. Axios client
attaches `Token` from `localStorage` on every request.

### Deferred (not this slice)
- F8 daily counts + sensor trend charts, F9 dimension CRUD, F10 correction workflow,
  N1 offline queue, per-role route guards, waiting-hall temperature logging.
