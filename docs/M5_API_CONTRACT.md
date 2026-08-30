# M5_API_CONTRACT — v3 (as built)

> Companion to [M5_SRS.md](M5_SRS.md) and [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md).
> Status: **F1–F5 + F7 implemented** (2026-08-29). F6 / F8 / F9 / F10 remain draft (§8).
> This v3 documents the implemented surface (v2 added F1 Dryer; v3 made Setting chamber-centric,
> removed the manual kiln-exit endpoint, added push_time, and full packing grades).

Base URL: `/api/`. Auth: **DRF Token** (`Authorization: Token ***`) — all endpoints require it.
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

## 1. Dryer (F1 — implemented)

### POST /api/dryer/cycles/
Log one dryer chamber load/unload cycle + optional hourly humidity/temp readings (22 readings/day).
Produces the dried body that Setting later loads. `dryer_cycle_id` is system-assigned.
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

## 2. Setting (F2 — implemented, CHAMBER-CENTRIC)

### POST /api/setting/events/
Unload one dryer chamber → register 1–4 wagons fed from THAT chamber in a single batch. Each wagon
opens its own `wagon_trip` at load **start** (system-assigned `trip_id`, never typed).
(v1/v2 draft had a single-wagon `setting/loads/` endpoint — replaced by this chamber batch.)
```json
{
  "chamber_code": "5",                   // the source dryer chamber (1..40, dropdown)
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
Response `201`: `{ "setting_event_id": 5531, "trip_ids": [1042, 1043], "wagon_count": 2 }`

## 3. Kiln (F3, F4 — implemented)

### POST /api/kiln/pushes/
Register one kiln push (1 wagon, up to 18 sensor readings as a list). `push_seq` is server-computed;
the service layer rejects a push when 44 wagons are already in the tunnel (FIFO-44). **On every push,
`kiln_exit` is auto-upserted** (exit_push_seq = entry_push_seq + 43) — there is NO manual exit endpoint.
```json
{
  "trip_id": 1042,
  "push_date": "1405.06.08", "push_time": "08:20",
  "shift": 1, "operator_id": 5, "product_id": 7,
  "readings": [ { "sensor_code": "temp_exhaust", "temperature_c": 120 }, … ],
  "client_token": "9b2f…"
}
```
Response `201`: `{ "kiln_push_id": 2201, "trip_id": 1042, "push_seq": 881, "status": "in_tunnel" }`

> **F4 (auto, no endpoint):** wagon discharge is *derived*, not a form. Each push updates `kiln_exit`
> (exit_push_seq = entry_push_seq + 43). A later "confirm discharge" action may set `discharged=TRUE`
> at physical unload, but the exit sequence number is never client-supplied.

## 4. Packing (F5 — implemented)

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

## 5. Dashboards (F7 — implemented; F6/F8 deferred)

### GET /api/dashboard/wagon-journey/?plate=12
One trip-spine timeline per historical trip of that plate (v1 draft returned a bare array —
the implemented response wraps it):
```json
{ "plate": "12", "trips": [ { "trip_id": 1042, "status": "completed", … } ] }
```

### GET /api/dashboard/awaiting-discharge/
Trips ready to pack — feeds the Packing form's wagon picker.
```json
[ { "trip_id": 1042, "plate": "12" } ]
```

## 6. Dimensions (F9 — GET implemented; CRUD deferred)

Dropdown feeds only (clean-core per ADR-0008 — forms consume these, never free text):
- `GET /api/dimensions/operators/` → `operator_id, operator_code, full_name`
- `GET /api/dimensions/products/` → `product_id, product_name_setting, product_code_kiln, product_code_packing`
- `GET /api/dimensions/glazes/` → `glaze_id, glaze_code, glaze_name`
- `GET /api/dimensions/wagons/` → `wagon_id, wagon_name`
- `GET /api/dimensions/chambers/` → `chamber_id, chamber_code, chamber_type`
- `GET /api/dimensions/sensors/`

`POST/PUT/DELETE` on dimensions is deferred to F9.

## 7. Validation rules (enforced server-side, implemented)

- `wagon_id` (in Setting/Packing) and `chamber_id` (in Dryer/Setting) must exist in their dimensions
  (clean 1..80 / 1..40 sets enforced at the seed boundary) — typos cannot enter.
- `chamber_code` (Setting) must exist in the chamber dimension (1..40).
- Kiln FIFO-44: push rejected when the tunnel is full; `exit_push_seq = entry_push_seq + 43` always.
- Trip state machine validated at every transition (setting→`in_progress`, push→`in_tunnel`, pack→`completed`).
- All writes require a valid token; all service functions run `@transaction.atomic`; packing uses row locking (`select_for_update`).
- Raw values immutable; corrections are flag-only (MASTER_SPEC §32/§44 — F10 deferred).

## 8. Deferred endpoints (v1 draft — not yet built)

- F6: `GET /api/dashboard/kiln-occupancy/` → `{ in_tunnel, capacity: 44, awaiting_discharge }`
- F8: `GET /api/dashboard/daily-counts/?from=&to=`
- F9: dimension CRUD
- F10: `POST /api/entries/{module}/{id}/flag/` — correction workflow
