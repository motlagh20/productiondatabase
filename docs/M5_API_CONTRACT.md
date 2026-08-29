# M5_API_CONTRACT — v2 (as built)

> Companion to [M5_SRS.md](M5_SRS.md) and [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md).
> Status: **F2–F5 + F7 implemented** (2026-08-29, PR [#1](https://github.com/motlagh20/productiondatabase/pull/1)).
> F1 / F6 / F8 / F9 / F10 remain draft (§8). This v2 documents the implemented surface;
> v1 draft shapes that differ are called out inline.

Base URL: `/api/`. Auth: **DRF Token** (`Authorization: Token <key>`) — all endpoints require it.
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

## 2. Setting (F2 — implemented)

### POST /api/setting/loads/
Load a dried body onto a wagon → opens a `wagon_trip`. `trip_id` is **system-assigned**, never typed
(v1 draft had `plate_name`/`glaze_type` free-text — replaced by FK ids + dropdown validation).
```json
{
  "plate": "12",                       // must exist in wagon dimension (dropdown 1..80)
  "chamber_code": "5",                 // optional; must exist in chamber dimension (1..40)
  "product_id": 7, "glaze_id": 2, "operator_id": 3,
  "shift": 1,
  "date_jalali": "1405.06.07",
  "start_time": "14:30", "end_time": "16:45",
  "packages": 64, "khesht_count": 120,
  "client_token": "9b2f…"
}
```
Response `201`: `{ "trip_id": 1042, "setting_load_id": 5531, "status": "in_progress" }`

## 3. Kiln (F3, F4 — implemented)

### POST /api/kiln/pushes/
Register one kiln push (1 wagon, up to 18 sensor readings as a list — v1 draft's wide 18-key
`sensors` map became `readings[]`). `push_seq` is server-computed; the service layer rejects a push
when 44 wagons are already in the tunnel (FIFO-44).
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

### POST /api/kiln/exits/
Mark a wagon discharged → awaiting-discharge list. `exit_push_seq = entry_push_seq + 43` is
**server-computed** (v1 draft had the client supply it — now rejected by design).
```json
{ "trip_id": 1042, "exit_date": "1405.06.10" }
```
Response `201`: `{ "kiln_exit_id": 774, "trip_id": 1042, "entry_push_seq": 881, "exit_push_seq": 924, "status": "awaiting_discharge" }`

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

- `plate` must exist in the wagon dimension (clean 1..80 set enforced at the seed boundary) — typos like 81 cannot enter.
- `chamber_code` must exist in the chamber dimension (1..40).
- Kiln FIFO-44: push rejected when the tunnel is full; `exit_push_seq = entry_push_seq + 43` always.
- Trip state machine validated at every transition (load→`in_progress`, push→`in_tunnel`, exit→`awaiting_discharge`, pack→`completed`).
- All writes require a valid token; all service functions run `@transaction.atomic`; packing uses row locking (`select_for_update`).
- Raw values immutable; corrections are flag-only (MASTER_SPEC §32/§44 — F10 deferred).

## 8. Deferred endpoints (v1 draft — not yet built)

- F1: `POST /api/dryer/cycles/` + 22 hourly readings (chamber 1..40)
- F6: `GET /api/dashboard/kiln-occupancy/` → `{ in_tunnel, capacity: 44, awaiting_discharge }`
- F8: `GET /api/dashboard/daily-counts/?from=&to=`
- F9: dimension CRUD
- F10: `POST /api/entries/{module}/{id}/flag/` — correction workflow
