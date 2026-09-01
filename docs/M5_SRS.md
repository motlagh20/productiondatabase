# M5_SRS — Software Requirements Specification

> Companion to [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md) and [ADR-0007](adr/ADR-0007-application-architecture-m5.md).
> Status: **Approved + partially implemented.** The F2→F7 vertical slice is built
> (2026-08-29, see [M5_PLATFORM_PLAN §9](M5_PLATFORM_PLAN.md)); F1/F6/F8/F9/F10 remain specified but deferred.

## 1. Introduction

The Manufacturing Analytics & Execution Platform (MES) digitizes the roof-tile / ceramic
factory floor: operators register each **recorded** production stage (Dryer → Setting →
Waiting hall → Kiln → Packing) through structured forms; managers get live dashboards (kiln
tunnel occupancy, wagon journey trace, daily KPIs). The **full physical line** is nine stages
including prep, press, optional glazing, and warehouse — see [PRODUCTION_FLOW.md](PRODUCTION_FLOW.md).
The initial reference plant is a single roof-tile factory; the schema stays multi-factory
configurable (MASTER_SPEC §P3).

### 1.1 Stakeholders
- **Operator** — floor worker who registers loads/pushes/packs at each station.
- **Supervisor** — verifies entries, handles corrections (flag-only).
- **Manager** — reads dashboards, exports reports.
- **System admin** — manages dimensions (operators, chambers, products, glazes).

### 1.2 Definitions
- **Wagon** — physical cart identified by a plate NAME (e.g. `12`), not a sequence number.
- **Trip** — one wagon's journey from dryer body (when linked) → Setting load → waiting hall → Kiln push → Packing unload (`wagon_trip`). Trip_id assigned at Setting load start.
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
The **complete line** follows this order (owner-confirmed 2026-08-31, [PRODUCTION_FLOW.md](PRODUCTION_FLOW.md), ADR-0009):

| # | Stage | In MES app? |
|---|-------|-------------|
| 1 | Preparation (آماده‌سازی) | ❌ future |
| 2 | Forming / Press (فرم‌دهی / پرس) | ❌ future |
| 3 | Dryer (خشک‌کن, 40 chambers) | ✅ **F1** — first recorded step |
| 4 | Glazing (لعاب‌زنی) | ⚠️ optional; glaze on Setting row |
| 5 | Setting (ستینگ) | ✅ **F2** — chamber-centric wagon load |
| 6 | Waiting hall (سالن انتظار) | ⚠️ optional; `waiting_hall` trip state |
| 7 | Kiln (کوره) | ✅ **F3/F4** — FIFO-44 tunnel |
| 8 | Packing (بسته‌بندی) | ✅ **F5** |
| 9 | Finished-goods warehouse (انبار محصول) | ❌ future |

**Setting (5) detail:** when dryer chamber *x* is unloaded, its dried body is loaded onto 1–4
wagons until chamber *x* is fully emptied. Batch = (date, shift, chamber, operator) + wagons with
load times, packages, glaze, khesht.

**Waiting hall (6):** loaded wagons may wait before a kiln push slot; temperature logging
anticipated later (`waiting_hall_reading` placeholder in §5).

> **Binding:** Dryer (3) always precedes Setting (5). Setting `chamber_no` references the
> **source dryer chamber** (1..40), not a separate Setting-owned chamber.

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
| F1 | Log a dryer cycle: chamber (1..40), load/unload datetime, operator, product, finger count, hourly humidity/temp readings | Operator | Dryer | **First** production step; produces the dried body that Setting later loads |
| F2 | Register a **Setting batch** (CHAMBER-CENTRIC): select a dryer chamber (1..40), then record 1–4 wagons fed from THAT chamber in one submit — each wagon: plate, glaze, start/end load time, packages, khesht. Batch = (date, shift, chamber, operator). Creates one `wagon_trip` per wagon at load **start** | Operator | Setting | **After** Dryer; until the chamber is fully emptied its body goes only onto these wagons |
| F3 | Register a kiln push: 1 wagon, 18 sensor readings, operator, **push time (exact HH:MM)**, duration | Operator | Kiln | Wagon enters from waiting hall; push = 1 unique event; push_seq by physical order; **on push, auto-compute & upsert `kiln_exit` (exit_push_seq = entry+43)** |
| F4 | *(auto)* Wagon discharge is **derived**, not a form: each push updates `kiln_exit` (exit_push_seq = entry_push_seq + 43). A separate "confirm discharge" action may mark `discharged=TRUE` at physical unload | System | Kiln exit | FIFO-44; no manual exit_push_seq entry |
| F5 | Register packing: take 1+ wagons from awaiting-discharge; for EACH wagon record **grade1 / grade2 / waste / total counts** (not just operator). Closes the `wagon_trip` | Operator | Packing | Full payload per packing_wagon (grades from staging `packing_wagon`) |
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
- `setting_event` (setting_event_id, date_jalali, shift, chamber_id FK, product_id FK, supervisor_id, operator_id, personnel_count, fingers_count, columns_count, dryer_waste, source_row) — **CHAMBER BATCH header** (mirrors staging `setting_event`)
- `setting_wagon` (setting_wagon_id, setting_event_id FK, wagon_id FK, glaze_id FK, trip_id FK, start_time, end_time, packages, khesht_count, position_in_event) — 1..4 per event
- `dryer_cycle` (dryer_cycle_id, chamber_id FK, load/unload datetime, operator_id, product_id, finger_count, readings…)
- `kiln_push` (kiln_push_id, trip_id FK, wagon_id FK, push_seq UNIQUE, push_date, **push_time TIME**, shift, operator_id, product_id, push_duration) — **push_time captured exactly**
- `kiln_reading` (kiln_reading_id, kiln_push_id FK, sensor_id FK, temperature_c) — 18 per push
- `kiln_exit` (kiln_exit_id, trip_id FK, wagon_id FK, entry_push_seq, exit_push_seq, discharged) — **AUTO-UPDATED on each push** (exit_push_seq = entry+43); no manual form
- `packing_header` (packing_header_id, pack_date, shift, controller_id FK, worker_type, worker_count, …) + `packing_wagon` (packing_wagon_id, packing_header_id FK, trip_id FK, wagon_id FK, product_id, **total_count, grade1_count, grade2_count, waste_count**, efficiency_pct) — **full grade payload**
- `operator`, `chamber`, `product`, `glaze` (dimension masters)
- `waiting_hall_reading` (reading_id, reading_time, temperature_c, sensor_id?, operator_id) — **placeholder, deferred**: ambient temp logging for the waiting hall, anticipated later (owner 2026-08-29). Mirrors `dryer_reading`/`kiln_reading` row-oriented pattern; NOT a column on `wagon_trip` (see M5_PROPOSED_SCHEMA §2.5).
- `etl_trip_map` (map_id, source_module, source_row, trip_id?, wagon_id?, matched_at, note) — **ETL/historical layer only** (ADR-0008), created empty by `37_etl_trip_map.sql`; reconciles historical Excel rows (by `row_seq`) to clean-core `trip_id` post-build. NOT an app model.

> Staging tables (`setting_event`, `kiln_wagon`, etc.) remain the **historical source**; an
> ETL map (`etl_trip_map`) reconciles them to the clean core post-build (ADR-0008).

## 6. API contract (summary — full version in M5_API_CONTRACT.md)

Base `/api/`, DRF, token auth.
- `POST /api/dryer/cycles/` (F1), `POST /api/setting/events/` (F2, chamber batch)
- `POST /api/kiln/pushes/` (F3; kiln exit auto-derived, no F4 endpoint)
- `POST /api/packing/headers/` (F5, full grades)
- `GET /api/dashboard/wagon-journey/?plate=` → `[setting, kiln_entry, kiln_exit, packing]` (F7)
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
