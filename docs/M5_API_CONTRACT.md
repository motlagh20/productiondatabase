# M5_API_CONTRACT — v4 (as built, 2026-09-02)

> Companion to [M5_SRS.md](M5_SRS.md) and [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md).
> Status: **F1–F7 implemented + UI redesign complete.** 15 endpoints (6 POST + 7 GET reads
> + 2 POST reads) are live. F6/F8/F9/F10 remain deferred (§8).
> v4: added Dryer reading/unload endpoints, new GET list feeds, corrected Setting payload
> (`chamber_id` not `chamber_code`), dimension dropdowns now public (AllowAny).

Base URL: `/api/`. Auth: **DRF Token** (`Authorization: Token ***`) — writes + manager reads
require it. Dimension dropdowns are public (`AllowAny`) so forms render before login.
All dates: Jalali `YYYY.MM.DD` in/out; all times `HH:MM`. Persian/RTL UI consumes these.

**Replay-safety (implemented):** every write accepts an optional `client_token` (UUID, UNIQUE).
Retrying the same POST with the same token returns the original record instead of duplicating it
(offline-tolerant, N1-ready).

## 1. Auth

### POST /api/token/
```json
{ "username": "…", "password": "…" }
```
Response `200`: `{ "token": "…" }`

## 2. Dryer (F1 — implemented)

### POST /api/dryer/cycles/
Log one dryer chamber load/unload cycle + optional hourly humidity/temp readings (22 readings/day).
`dryer_cycle_id` is system-assigned.
```json
{
  "chamber_id": 3,
  "load_date": "1405.06.05", "load_time": "08:00",
  "unload_date": "1405.06.07", "unload_time": "17:00",
  "load_operator_id": 5, "unload_operator_id": 5,
  "product_id": 7, "finger_count": 8,
  "readings": [ { "hour_offset": 0, "humidity_pct": 85.5, "temperature_c": 40.0 }, … ],
  "client_token": "9b2f…"
}
```
Response `201`: `{ "dryer_cycle_id": 221, "readings": 22 }`

### POST /api/dryer/readings/
Append one hourly reading to the chamber's open (active) dryer cycle.
Auto-increments `hour_offset` based on existing readings; idempotent on (cycle, hour_offset).
```json
{
  "chamber_id": 3,
  "temperature_c": 42.5,
  "humidity_pct": 78.0,
  "hour_offset": 5
}
```
Response `201`: `{ "dryer_reading_id": 10234, "hour_offset": 5 }`

### POST /api/dryer/unload/
Complete the unload side of the chamber's open dryer cycle. Sets `unload_date`, `unload_time`,
`unload_operator_id`, `finger_count` on the existing `DryerCycle` row (does NOT create a new cycle).
```json
{
  "chamber_id": 3,
  "unload_date": "1405.06.07",
  "unload_time": "17:00",
  "unload_operator_id": 5,
  "finger_count": 8
}
```
Response `201`: `{ "dryer_cycle_id": 221, "unload_date": "1405.06.07" }`

## 3. Setting (F2 — implemented, CHAMBER-CENTRIC)

### POST /api/setting/events/
Unload one dryer chamber → register 1–4 wagons fed from THAT chamber in a single batch. Each wagon
opens its own `wagon_trip` at load **start** (system-assigned `trip_id`, never typed).
**Note:** payload uses `chamber_id` (integer FK), NOT `chamber_code`.
```json
{
  "chamber_id": 5,
  "product_id": 7, "operator_id": 3, "shift": 1,
  "date_jalali": "1405.06.07",
  "wagons": [
    { "wagon_id": 12, "glaze_id": 2, "start_time": "14:30", "end_time": "16:45",
      "packages": 64, "khesht_count": 120 },
    { "wagon_id": 13, "glaze_id": 2, "start_time": "14:35", "end_time": "16:50",
      "packages": 60, "khesht_count": 115 }
  ],
  "client_token": "9b2f…"
}
```
Response `201`: `{ "setting_event_id": 5531, "chamber": 5, "trip_ids": [1042, 1043], "wagon_count": 2 }`

## 4. Kiln (F3, F4 — implemented)

### POST /api/kiln/pushes/
Register one kiln push (1 wagon, up to 18 sensor readings as a list). `push_seq` is server-computed;
the service layer rejects a push when 44 wagons are already in the tunnel (FIFO-44). **On every push,
`kiln_exit` is auto-upserted** (exit_push_seq = entry_push_seq + 43) — there is NO manual exit endpoint.
The wagon is resolved from `wagon_id`; the active trip for that wagon is looked up automatically.
```json
{
  "wagon_id": 12,
  "push_date": "1405.06.08", "push_time": "08:20",
  "shift": 1, "operator_id": 5, "product_id": 7,
  "readings": [ { "sensor_code": "temp_exhaust", "temperature_c": 120 }, … ],
  "client_token": "9b2f…"
}
```
Response `201`: `{ "kiln_push_id": 2201, "trip_id": 1042, "push_seq": 881, "exit_push_seq": 924, "status": "in_tunnel" }`

> **F4 (auto, no endpoint):** wagon discharge is *derived*, not a form. Each push updates `kiln_exit`
> (exit_push_seq = entry_push_seq + 43). A later "confirm discharge" action may set `discharged=TRUE`
> at physical unload, but the exit sequence number is never client-supplied.

## 5. Packing (F5 — implemented)

### POST /api/packing/headers/
Pack 1+ wagons from awaiting-discharge; each trip closes → `completed`. At least one wagon required.
```json
{
  "pack_date": "1405.06.15", "shift": 2, "controller_id": 9, "worker_count": 4,
  "wagons": [
    { "trip_id": 1042, "product_id": 7,
      "total_count": 64, "grade1_count": 58, "grade2_count": 4, "waste_count": 2 }
  ],
  "client_token": "9b2f…"
}
```
Response `201`: `{ "packing_header_id": 332 }`

## 6. Dashboard reads (F7 — implemented; F6/F8 deferred)

### GET /api/dashboard/wagon-journey/?plate=12
Full trip timeline for a wagon plate. Returns all historical trips for that plate.
**Auth required (Manager).**
```json
{ "plate": "12", "trips": [ { "trip_id": 1042, "status": "completed", "setting": {…}, "kiln_entry": {…}, "kiln_exit": {…}, "packing": {…} } ] }
```

### GET /api/dashboard/awaiting-discharge/
Trips ready to pack — feeds the Packing form's wagon picker. **Auth required (Manager).**
```json
[ { "trip_id": 1042, "plate": "12" } ]
```

### GET /api/dashboard/active-wagons/
Wagons with an active (Setting/Waiting-hall) trip — feeds the Kiln push form's wagon select.
**Auth required.**
```json
[ { "trip_id": 1042, "wagon_id": 12, "plate": "12" } ]
```

## 7. Read feeds (NEW — added during UI redesign)

### GET /api/dryer/chambers/status/
Per-chamber status for the Dryer dashboard. Returns all DRYER-type chambers with
`derived_status` (`empty`/`drying`/`dried`), `is_loaded`, and the current cycle's latest
reading (if loaded). **Auth required.**
```json
[{
  "chamber_id": 3,
  "chamber_code": "DRYER-03",
  "chamber_type": "DRYER",
  "is_loaded": true,
  "derived_status": "drying",
  "current_cycle": {
    "dryer_cycle_id": 221,
    "load_date": "1405.06.05",
    "load_time": "08:00",
    "product_name": "تک‌پخت",
    "finger_count": 8,
    "unload_date": "",
    "latest_reading": { "hour_offset": 5, "temperature_c": "42.5", "humidity_pct": "78.0" }
  }
}]
```

### GET /api/dryer/cycles/list/?chamber_id=&limit=
Dryer cycles with nested readings, newest first. Optional `chamber_id` filter. Default limit 50.
**Auth required.**

### GET /api/setting/events/list/?limit=
Setting events with nested wagons + resolved product/supervisor/operator names, newest first.
Default limit 50. **Auth required.**

### GET /api/kiln/pushes/list/?limit=
Kiln pushes with nested readings + exit info + product/plate names, newest first.
`exit_push_seq` is a `SerializerMethodField` (= `push_seq + 43`). Default limit 50.
**Auth required.**

## 8. Dimensions (F9 — GET implemented; CRUD deferred)

Dropdown feeds only (clean-core per ADR-0008 — forms consume these, never free text).
**All dimension endpoints are public (`AllowAny`) — no auth required.**
- `GET /api/dimensions/operators/` → `operator_id, operator_code, full_name`
- `GET /api/dimensions/products/` → `product_id, product_name_setting, product_code_kiln, product_code_packing`
- `GET /api/dimensions/glazes/` → `glaze_id, glaze_code, glaze_name`
- `GET /api/dimensions/wagons/` → `wagon_id, wagon_name`; `?available=true` → only free wagons
- `GET /api/dimensions/chambers/` → `chamber_id, chamber_code, chamber_type`; `?loaded=true|false`
- `GET /api/dimensions/sensors/` → `sensor_id, sensor_code, sensor_name`

`POST/PUT/DELETE` on dimensions is deferred to F9.

## 9. Validation rules (enforced server-side, implemented)

- `wagon_id` (in Setting/Kiln/Packing) and `chamber_id` (in Dryer/Setting) must exist in their
  dimensions (clean 1..80 / 1..40 sets enforced at the seed boundary).
- Setting: exactly 1–4 wagons per batch; chamber must be loaded.
- Kiln: FIFO-44 push rejected when tunnel is full; `exit_push_seq = entry_push_seq + 43` always.
- Trip state machine validated at every transition (setting→`in_progress`, push→`in_tunnel`, pack→`completed`).
- All writes require a valid token; all service functions run `@transaction.atomic`; packing uses
  row locking (`select_for_update`).
- Raw values immutable; corrections are flag-only (MASTER_SPEC §32/§44 — F10 deferred).

## 10. Deferred endpoints (not yet built)

- F6: `GET /api/dashboard/kiln-occupancy/` → `{ in_tunnel, capacity: 44, awaiting_discharge }`
- F8: `GET /api/dashboard/daily-counts/?from=&to=`
- F9: dimension CRUD
- F10: `POST /api/entries/{module}/{id}/flag/` — correction workflow
