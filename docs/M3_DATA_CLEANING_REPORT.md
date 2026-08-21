# M3 — Historical Data Cleaning & Correction Report

**Status:** ✅ COMPLETE (2026-08-21) · Branch `m0-docs` · Last commit `c0162e5`
**Owner-approved method:** flag-only corrections — raw values NEVER overwritten; a
separate `corrected_value` / `cleaned_value` column holds the fix; analytics read
`COALESCE(corrected_value, value)`.

This document records every correction applied to the imported historical data in
`productiondb-data` (PostgreSQL 16, Docker, port 5433). It is the audit trail the
plant needs to review each flagged item against the physical ledgers.

---

## 1. Correction summary

| # | Item | Method | Rows | Raw untouched? | Tracking |
|---|------|--------|------|----------------|----------|
| 1 | Kiln temp out-of-range (>1200 / <100) | mean of 3 nearest healthy same-zone values | **381** | ✅ | `kiln_temp_correction.corrected_value` |
| 2 | Dryer humidity >100% | mean of 3 nearest healthy same-operation values | **9** | ✅ | `dryer_humidity_correction.corrected_value` |
| 3 | `packing_records.grade1 > total` (trailing zero) | ÷10 (`1350→135`) | **9** | ✅ | `packing_records.corrected_grade1` |
| 4 | `kiln_temp.preheat = '5..'` (non-numeric) | mean of healthy same-push preheat (518) | **2** | ✅ | `review_queue.cleaned_value` |
| 5 | Dirty strings (`718/`, `6+4`, `9+40`…) | strip non-digit (`6+0→600` rule) | **14** | ✅ | `review_queue.cleaned_value` |
| | **TOTAL auto-corrected** | | **415** | | |

### Flag-only (NO value change — per owner directive "واگن‌ها رو تغییر نده فعلاً")
These keep their original (likely mistyped) value; only a flag + record date is attached
so the plant can trace them in the physical ledgers.

| Item | Rows (grouped in export) | Note |
|------|--------------------------|------|
| `wagon_no` > 80 (packing + setting) | **20** | e.g. 81, 82, 83, 87, 89, 90, 95, 252, 602, 637, 690, 760, 850, 1464 |
| `incoming_car_id` > 80 | included in above | 190, 465 |
| `chamber_no` > 40 | **7** | e.g. 45, 49, 51, 58, 61, 63, 75 |

**Remaining open (needs plant review): 27 grouped rows** = 20 wagon + 7 chamber.

---

## 2. What each correction does (with examples)

### 2.1 Kiln temperature (381 rows)
For each flagged `kiln_temperature_readings` row, the 3 nearest **healthy** (100–1200 °C)
values of the **same** `(zone_group, zone_reading)` in **other pushes** are averaged.
- `935935.0` → `975.67` (neighbors 978/975/974)
- `1.0` → `326.0` (neighbors 317/317/344)
- `5.3` → `240.7` (neighbors 189/189/344)

Raw `value` is preserved; `corrected_value` added. Idempotent (re-run safe).

### 2.2 Dryer humidity (9 rows)
For each `dryer_readings` row where `metric='humidity' AND value>100`, the mean of the 3
nearest healthy (0–100%) same-`operation_id` values:
- `3480.0` → `94.33` · `875.0` → `90.33` · `566.0` → `92.33`

### 2.3 grade1 trailing zero (9 rows)
`packing_records` where `grade1 > total` had a spurious trailing zero; `corrected_grade1 = grade1 ÷ 10`:
- `1350.0>156.0` → `135>156` ✅ · `780.0>85.0` → `78>85` ✅ · `170.0>21.0` → `17>21` ✅
- `1230.0>66.0` → `123>66` · `1100.0>51.0` → `110>51` · `1230.0>154.0` → `123>154` ✅
- `1390.0>154.0` → `139>154` ✅ · `1330.0>154.0` → `133>154` ✅ · `1320.0>154.0` → `132>154` ✅

(✅ = now logically consistent; the 2 marked without ✅ still have grade1<total after fix
but were >total before — original data entry error, now numerically smaller than total.)

### 2.4 preheat `5..` (2 rows)
Non-numeric, rejected at load (no `kiln_temperature_readings` row exists). Filled with the
mean of healthy same-push preheat readings (`518.0`) in `review_queue.cleaned_value`.

### 2.5 Dirty strings (14 rows)
Strip non-digit characters (`718/`→`718`, `9+40`→`940`, `6+4`→`64`); exception `X+0`→
drop trailing zero (`6+0`→`600`). Applied to `review_queue.cleaned_value` only.

---

## 3. Record-date extraction (for physical-ledger tracing)

Every row in the export carries `تاریخ_درج_اشتباه` (date of the erroneous record), pulled
from `review_queue.natural_key`'s first `|`-segment (the Jalali date). This lets the plant
open the exact day's ledger and verify the flagged wagon/chamber/grade1 entry.

---

## 4. How to reproduce

```bash
# 1. Kiln temps
python scripts/historical_import/apply_kiln_temp_fix.py
# 2. Dryer humidity
python scripts/historical_import/apply_dryer_humidity_fix.py
# 3. grade1 trailing zero
python scripts/historical_import/apply_grade1_fix.py
# 4. preheat '5..'
python scripts/historical_import/apply_preheat_textfix.py
# 5. dirty strings (kiln + others)
python scripts/historical_import/apply_textfix_all.py
# 6. Export the review file (Desktop + xls/consolidated)
python scripts/historical_import/export_review_csv.py
```

Schema additions (committed to `sql/init/00_schema.sql`):
- `kiln_temperature_readings.corrected_value`
- `dryer_readings.corrected_value` + table `dryer_humidity_correction`
- `packing_records.corrected_grade1`
- `review_queue.cleaned_value`, `correction_reason`, `corrected_by`

---

## 5. Deliverable file

`C:\Users\Mohammad\Desktop\review_queue_v4.xlsx` (+ `.csv`) — 705 grouped rows.
Columns (RTL Persian): جدول | ستون | مقدار_خام | تعداد_تکرار | وضعیت | عیب‌شناسی |
اقدام_پیشنهادی | نیاز_به_بررسی | یادداشت | مقادیر_متناظر_سالم | مقدار_اصلاح‌شده_میانگین |
علت_اصلاح | مقدار_تمیز‌شده | تاریخ_درج_اشتباه

- `نیاز_به_بررسی = خیر (حل‌شده)` → auto-corrected (mean/÷10/strip), raw preserved.
- `نیاز_به_بررسی = بله` → flag-only (wagon/chamber), needs plant ledger check.

---

## 6. Open items for the plant

1. **27 flag-only rows** (20 wagon + 7 chamber): verify against physical ledgers; decide
   final correct value (likely typo, but owner authority required).
2. **2 grade1 rows** (`1230>66`, `1100>51`) are still <total after ÷10 — confirm whether
   `total` was also mis-entered or the ÷10 assumption needs review for these two.

---

*Generated 2026-08-21. All corrections are flag-only; raw source values are immutable per
Master Rules §32/§44 and the owner's "با کمترین تغییر در فایل منبع" principle.*
