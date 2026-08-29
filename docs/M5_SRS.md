# M5_SRS — Software Requirements Specification

> Companion to [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md) and [ADR-0007](adr/ADR-0007-application-architecture-m5.md).
> Per MASTER_SPEC §772 / ADR-0001: documentation milestone — no code yet.
> Status: Proposed (owner approval pending after review).

## 1. Introduction

The Manufacturing Analytics & Execution Platform (MES) digitizes the roof-tile / ceramic
factory floor: operators register each stage of a wagon's journey (Setting → Dryer → Kiln →
Packing) through structured forms; managers get live dashboards (kiln tunnel occupancy,
wagon journey trace, daily KPIs). The initial reference plant is a single roof-tile factory;
the schema stays multi-factory configurable (MASTER_SPEC §P3).

### 1.1 Stakeholders
- **Operator** — floor worker who registers loads/pushes/packs at each station.
- **Supervisor** — verifies entries, handles corrections (flag-only).
- **Manager** — reads dashboards, exports reports.
- **System admin** — manages dimensions (operators, chambers, products, glazes).

### 1.2 Definitions
- **Wagon** — physical cart identified by a plate NAME (e.g. `12`), not a sequence number.
- **Trip** — one wagon's journey from Setting load → Kiln push → Packing unload (`wagon_trip`).
- **Chamber** — physical dryer chamber (1..40); Setting only *references* the source chamber.
- **Kiln tunnel** — FIFO conveyor, fixed capacity **44** wagons; a wagon exits 43 pushes after entry.

## 2. Overall description

### 2.1 System context
- Web app (Django + DRF backend, React + TS frontend), PostgreSQL 16.
- Integrates with the existing **staging DB** (`localhost:5433`, db `postgres`) which already
  holds the historical load (31 tables). Django migrations own the *application* schema; the
  staging tables are the historical source (ADR-0008: clean core vs ETL boundary).
- Persian (Farsi) UI, RTL, Jalali dates (`jdatetime`).

### 2.2 Production flow order (physical sequence on the floor)
The wagon journey follows this **strict physical order** (owner-specified 2026-08-29):
```
Forming (فرم‌دهی)      — NOT YET IN SCOPE (future module)
   ↓
Dryer (خشک‌کن)         — clay bodies are dried; chamber 1..40
   ↓
Glazing (لعاب‌زنی)     — NOT YET IN SCOPE (future module)
   ↓
Setting (ستینگ)       — dried body is loaded onto a wagon (plate name 1..80)
   ↓
Waiting hall (سالن انتظار) — loaded wagons wait for a kiln push slot
   ↓
Kiln (کوره)           — FIFO tunnel, fixed capacity 44; wagon enters at push k, exits at k+43
   ↓
Packing (پکینگ/بسته‌بندی) — wagon discharged from kiln is unpacked & graded
```
> **Key correction:** Setting does NOT precede Dryer. The dryer produces the dried body that
> Setting then loads onto a wagon. The Setting `chamber_no` column is a *reference* to the
> source dryer chamber (1..40), not a Setting-owned chamber. (ADR-0008 / owner rule 2026-08-29.)

### 2.2 User classes
| Class | Privileges |
|---|---|
| Operator | Create entries for own station; view own submissions |
| Supervisor | All operator perms + flag/correct entries + manage dimensions |
| Manager | All + dashboards + exports |
| Admin | User/role management + dimension master upkeep |

### 2.3 Constraints
- **Data integrity (MASTER_SPEC §32/§44):** raw source values immutable; corrections are
  flag-only, never overwrite.
- **Wagon identity** is a plate name (1..80 valid range); out-of-range names = operator typo,
  flagged for paper-ledger adjudication (not auto-fixed).
- **No Excel-era defect logic in the app core** (ADR-0008): dropdowns, system dates, validation
  prevent typos at source. Historical Excel defects are handled by the separate ETL layer.

## 3. Functional requirements

| ID | Requirement | Actor | Module | Notes |
|----|-------------|-------|--------|-------|
| F1 | Log a dryer cycle: chamber (1..40), load/unload datetime, operator, product, finger count, 22 hourly humidity/temp readings | Operator | Dryer | **First** production step; produces the dried body |
| F2 | Register a wagon load: plate name, product, glaze, operator, shift, chamber (source ref to dryer), start/end time, packages, khesht count | Operator | Setting | **After** Dryer; loads dried body onto wagon; creates `wagon_trip` at load **start** |
| F3 | Register a kiln push: 1 wagon, 18 sensor readings, operator, push time, duration | Operator | Kiln | Wagon enters from waiting hall; push = 1 unique event; push_seq by physical order |
| F4 | Mark wagon discharge: wagon exits kiln → added to awaiting-discharge list (`kiln_exit`) | Operator | Kiln exit | FIFO: exit_push_seq = entry_push_seq + 43 |
| F5 | Register packing: take 1+ wagons from awaiting-discharge, record grade/waste counts | Operator | Packing | Closes the `wagon_trip` |
| F6 | Dashboard: kiln tunnel occupancy (≤44), awaiting-discharge + waiting-hall counts | Manager | All | Real-time |
| F7 | Dashboard: wagon journey trace (dryer → setting → waiting → kiln entry → kiln exit → packing) by plate name or trip_id | Manager | `wagon_trip` links | |
| F8 | Dashboard: daily production counts + sensor trend charts | Manager | All | Date-range filter (Jalali) |
| F9 | Dimension management: operators, chambers, products, glazes (CRUD) | Admin | All | Authoritative names per ADR-0006; glaze master = `glaze` (code/name/formula/desc) |
| F10 | Correction workflow: flag an entry as suspect (typo/date error), keep original, log to review table | Supervisor | All | Never overwrites raw value |

### 3.1 Trip lifecycle (state machine)
```
[DRYER cycle logged] → body_dried
   → [SETTING load starts] → in_progress   (trip_id assigned at Setting load start)
   → waiting_hall (loaded wagon awaiting kiln slot)
   → [KILN push] → in_tunnel
   → [KILN exit] → awaiting_discharge
   → [PACKING] → completed
   (or) abandoned / incomplete (if load never finished)
```

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| N1 | **Offline tolerance:** operator forms queue locally and sync when online (factory floor may lose connectivity) |
| N2 | **Persian/RTL:** all UI Persian, RTL, Jalali dates |
| N3 | **Audit:** every write logs actor + timestamp; raw values immutable |
| N4 | **Performance:** kiln-occupancy dashboard < 500ms; journey trace < 1s for any wagon |
| N5 | **Role-based access:** token auth (DRF), per-role permissions |
| N6 | **Configurable multi-factory:** plant config (chamber count, kiln capacity) externalized |

## 5. Data model (application core — clean)

> **Full 100% schema map** (conceptual names → staging tables + the ETL-heavy 30%):
> see [M5_PROPOSED_SCHEMA.md](M5_PROPOSED_SCHEMA.md). This section is the clean-core summary.

Tables owned by Django migrations (not the staging load):
- `wagon` (wagon_id, plate_name UNIQUE)
- `wagon_trip` (trip_id, wagon_id, started_at, completed_at, status) — spine
- `setting_load` (trip_id FK, chamber_id FK, product_id, operator_id, shift, times, packages…)
- `dryer_cycle` (trip_id FK, chamber_id, load/unload, readings…)
- `kiln_push` (trip_id FK, push_seq, push_time, 18 sensor readings…)
- `kiln_exit` (trip_id FK, entry_push_seq, exit_push_seq, discharged)
- `packing_header` / `packing_wagon` (trip_id FK, grades, waste…)
- `operator`, `chamber`, `product`, `glaze` (dimension masters)

> Staging tables (`setting_event`, `kiln_wagon`, etc.) remain the **historical source**; an
> ETL map (`etl_trip_map`) reconciles them to the clean core post-build (ADR-0008).

## 6. API contract (summary — full version in M5_API_CONTRACT.md)

Base `/api/`, DRF, token auth.
- `POST /api/setting/loads/`, `POST /api/dryer/cycles/`, `POST /api/kiln/pushes/`,
  `POST /api/kiln/exits/`, `POST /api/packing/headers/`
- `GET /api/dashboard/kiln-occupancy/` → `{in_tunnel, capacity, awaiting_discharge}`
- `GET /api/dashboard/wagon-journey/?plate=<name>` → full trip timeline
- `GET /api/dashboard/daily-counts/?from=&to=`

## 7. Out-of-scope (this milestone)
- Multi-factory tenancy internals (config-only for now)
- Analytics / ML (post-M5)
- Production deployment (separate milestone)
- Historical Excel defect repair (owned by ETL layer, not the app)

## 8. Acceptance criteria
1. All F1–F10 implementable against the clean core schema.
2. A wagon loaded in Setting today, pushed to Kiln tomorrow, packed day-after traces as ONE trip.
3. Kiln occupancy never exceeds 44 in the dashboard.
4. Out-of-range wagon plate (e.g. 81) is rejected at form level (dropdown 1..80).
5. No Excel-era typo logic exists anywhere in the app codebase.
