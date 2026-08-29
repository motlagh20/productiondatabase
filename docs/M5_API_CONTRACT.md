# M5_API_CONTRACT — v1 (draft)

> Companion to [M5_SRS.md](M5_SRS.md) and [M5_PLATFORM_PLAN.md](M5_PLATFORM_PLAN.md).
> Status: Proposed. No code yet (ADR-0001).

Base URL: `/api/`. Auth: **DRF Token** (`Authorization: Token <key>`).
All dates: Jalali `YYYY.MM.DD` in/out; all times `HH:MM`. Persian/RTL UI consumes these.

## 1. Dryer (F1 — first production step)

### POST /api/dryer/cycles/
Log a drying cycle (clay body dried in chamber 1..40).
```json
{
  "chamber_id": 5,
  "load_date": "1403.03.01", "load_time": "08:00",
  "unload_date": "1403.03.01", "unload_time": "16:00",
  "operator_id": 3, "product_id": 7, "finger_count": 4,
  "readings": [ {"hour_offset":0,"humidity_pct":62,"temperature_c":38}, … ]  // up to 22
}
```
Response `201`: `{ "dryer_cycle_id": 881 }`

## 2. Setting (F2 — after dryer)

### POST /api/setting/loads/
Load a dried body onto a wagon → opens a `wagon_trip` (trip_id assigned at start).
```json
{
  "plate_name": "12",
  "product_id": 7,
  "glaze_type": "مات",
  "operator_id": 3,
  "shift": 1,
  "chamber_ref": 5,            // source dryer chamber (1..40)
  "start_time": "14:30",
  "end_time": "16:45",
  "packages": 64,
  "khesht_count": 120,
  "load_date": "1403.03.01"
}
```
Response `201`: `{ "trip_id": 1042, "setting_load_id": 5531, "status": "in_progress" }`

### GET /api/setting/loads/?from=&to=&plate=
List loads (manager/supervisor). Filters by Jalali date range or plate name.

## 3. Kiln (F3, F4)

### POST /api/kiln/pushes/
Register one kiln push (1 wagon, 18 sensors).
```json
{
  "trip_id": 1042,
  "push_date": "1403.03.03", "push_time": "08:20",
  "operator_id": 5, "product_id": 7, "push_duration": "2:10",
  "sensors": { "temp_exhaust": 120, "temp_preheat01": 200, … }   // 18 keys
}
```
Response `201`: `{ "kiln_push_id": 2201, "push_seq": 881 }`

### POST /api/kiln/exits/
Mark a wagon discharged → awaiting-discharge list.
```json
{ "trip_id": 1042, "exit_push_seq": 924 }
```
Response `201`: `{ "kiln_exit_id": 774, "awaiting_discharge": true }`

## 4. Packing (F5)

### POST /api/packing/headers/
Pack 1+ wagons from awaiting-discharge, close the trip.
```json
{
  "pack_date": "1403.03.10", "shift": 2, "controller_id": 9,
  "wagons": [
    { "trip_id": 1042, "grade1_count": 58, "grade2_count": 4,
      "waste_count": 2, "total_count": 64, "efficiency_pct": 96.9 }
  ]
}
```
Response `201`: `{ "packing_header_id": 332, "trip_status": "completed" }`

## 5. Dashboards (F6–F8)

### GET /api/dashboard/kiln-occupancy/
```json
{ "in_tunnel": 41, "capacity": 44, "awaiting_discharge": 12 }
```

### GET /api/dashboard/wagon-journey/?plate=12&from=1403.01.01&to=1403.12.29
```json
[{
  "trip_id": 1042, "plate": "12", "status": "completed",
  "dryer":    {"cycle_id":881,"load":"1403.03.01 08:00","unload":"1403.03.01 16:00"},
  "setting":  {"setting_load_id":5531,"date":"1403.03.01","chamber_ref":5,"packages":64},
  "waiting_hall": {"entered":"1403.03.01 16:45"},
  "kiln":     {"push_seq":881,"entry":"1403.03.03 08:20","exit_push_seq":924},
  "packing":  {"header_id":332,"date":"1403.03.10","grade1":58,"waste":2}
}]
```

### GET /api/dashboard/daily-counts/?from=&to=
```json
[ {"date":"1403.03.01","setting_loads":20,"kiln_pushes":18,"packed":15}, … ]
```

## 6. Dimensions (F9)

- `GET/POST/PUT/DELETE /api/dimensions/operators/`
- `GET/POST/PUT/DELETE /api/dimensions/chambers/`
- `GET/POST/PUT/DELETE /api/dimensions/products/`
- `GET/POST/PUT/DELETE /api/dimensions/glazes/`
  ```json
  { "glaze_code": "AKHRA", "glaze_name": "اخرا", "formula": "…", "description": "لعاب اخرا", "is_combined": false }
  ```

## 7. Correction workflow (F10)

### POST /api/entries/{module}/{id}/flag/
Flag an entry as suspect (typo/date error). Keeps raw value, logs to review table.
```json
{ "reason": "تاریخ اشتباه تایپ شده", "flag_type": "date_error" }
```
Response `202`: `{ "flag_id": 55, "original_value_preserved": true }`

## 8. Validation rules (enforced server-side)
- `plate_name` ∈ 1..80 (dropdown; rejects typos like 81 at form level).
- `chamber_ref` ∈ 1..40 (Dryer chambers).
- Kiln capacity: dashboard caps display at 44; back-end asserts `exit_push_seq = entry_push_seq + 43`.
- All writes require valid token + role permission.
- Raw values immutable; corrections are flag-only (MASTER_SPEC §32/§44).
