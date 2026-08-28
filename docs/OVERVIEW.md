# Project Overview — Manufacturing Analytics & Execution Platform

> Status: **Historical data load complete & verified** (4 MES modules + wagon linking on PostgreSQL 16 staging; see IMPORT_RUNBOOK). M0–M4 documents approved (ADRs 0001–0006). **M5 (platform architecture) in documentation phase** — ADR-0007 + M5_PLATFORM_PLAN written, pending owner approval. No platform code written yet (per ADR-0001). **Ready for M5 doc approval → Django/React build.**

## What we did (read-only analysis + migration blueprints)

We profiled the **authoritative source workbooks** (`xls/real data/`, 22 files, 15 years 1391–1404) and the owner's normalized `xls/*.csv` prototype, then froze the findings as ADRs + Appendix C. All analysis was read-only; **no source data was modified**.

### Verified operational facts (owner-confirmed)
| Dimension | Verified rule | Out-of-range handling |
|---|---|---|
| Chamber (چمبر) | **1–40** (40 chambers) | `>40` → flag (user typo) |
| Shift (شیفت) | **1–3** = صبح / عصر / شب | outside {1,2,3} → flag |
| Wagon (واگن) | **1–80** (serial) | `>80` → flag, correct from physical ledgers |
| Date | **Jalali is canonical**; Gregorian only for cross-validation | 2-digit years → normalize to **13xx**; 1397 missing 2 months (complete later) |
| Time | **HH:MM** (no seconds) | `1900-01-03` Excel-time cast trap → strip; `20` (hour-only) tolerated |
| Product | **composite** (type × glaze), redefined — not legacy opaque codes | legacy codes (Packing 1–28, Dryer/Kiln A–E+91xxxx) → review queue |

### Key findings
- The `xls/*.csv` files are a **normalized design prototype (sample)**, NOT the data source. Source of truth = `xls/real data/`.
- Operator codes are **per-file partitioned** (Kiln-1404 reversed 4↔5); cleaned to global 1–5, **names untouched**.
- Product codes are **internally inconsistent** (8 codes map to multiple names) → drives ADR-0006 redefinition.
- Kiln temperature columns **grew over time** (1 in 1398 → 18 in 1404) → row-oriented schema required.
- Packing (`Packing-All.xlsx`, 93k rows) is the richest transaction set; its legacy product/wagon codes feed review queues.

## Architecture Decisions (ADRs)
| ADR | Title | One-line |
|---|---|---|
| 0001 | Documentation-first development | No code until M0 + glossary approved |
| 0002 | Freeze legacy app as reference | Frozen app = evidence only, holds 0 rows |
| 0003 | Consolidated Master Specification | Single spec of record |
| 0004 | PMS repo as design/UX donor | Harvest UI/UX & import flow, never merge code |
| 0005 | Setting 3-layer model | operation → shift-unload → wagon (repeated ID = batch key) |
| 0006 | Dimension master redefinition | Composite product; clean operators; old→new mapping with review queue |

## Supporting docs
- `docs/APPENDIX_C_DATA_VS_SCHEMA.md` — §1–12: constraint conflicts, packing source, operational columns, date/time, temperatures. **The canonical data-profile reference.**
- `docs/APPENDIX_B_DATA_ASSETS.md` — data asset catalog (corrected counts + unmapped-code list).
- `docs/PART_V_ADDENDUM.md` — config-driven import model.

## Cleaned workbooks (local, NOT in git)
`xls/consolidated/` holds operator/product/glaze-normalized copies for detailed review (git-ignored per owner: workbooks are design references, never committed). `REVIEW_*.txt` files log flagged rows (typos, unmapped) for owner decision.

## M3 — Historical data cleaning (COMPLETE 2026-08-21)

All import-time review-queue anomalies were resolved with **flag-only corrections**
(raw preserved; `corrected_value`/`cleaned_value` added). Audit trail:
[`docs/M3_DATA_CLEANING_REPORT.md`](docs/M3_DATA_CLEANING_REPORT.md).

| Correction | Rows | Method |
|---|---|---|
| Kiln temp out-of-range | 381 | mean of 3 nearest healthy same-zone values |
| Dryer humidity >100% | 9 | mean of 3 nearest healthy same-operation values |
| grade1 trailing zero | 9 | ÷10 (`1350→135`) |
| preheat `5..` non-numeric | 2 | mean of healthy same-push preheat (518) |
| Dirty strings (`718/`,`6+4`…) | 14 | strip non-digit (`6+0→600` rule) |
| **Flag-only (no change)** wagon/chamber | 27 | original value kept + record date for ledger check |

Deliverable: `C:\Users\Mohammad\Desktop\review_queue_v4.xlsx` (705 grouped rows).
**27 rows remain `نیاز_به_بررسی=بله`** = 20 wagon + 7 chamber — plant must verify against
physical ledgers (owner authority required for final values).

## M4 — Clean data layer (COMPLETE 2026-08-21)

Four `COALESCE(corrected, raw)` **views** expose the corrected data for the app without
touching raw: [`docs/M4_CLEAN_DATA_LAYER.md`](docs/M4_CLEAN_DATA_LAYER.md).
`v_clean_packing` / `v_clean_kiln_temps` / `v_clean_dryer_readings` / `v_open_anomalies`.
The last isolates the **27 flag-only** rows (wagon/chamber) needing ledger review.

`operator_mapping_blueprint.csv`, `product_mapping_blueprint.csv`, `glaze_mapping_blueprint.csv` — the `legacy_code → canonical` maps extracted from the authoritative workbooks (inputs to M2 import spec).

## Staging database — historical load (2026-08-26, status: loaded + verified)

PostgreSQL 16 (`productiondb-data`, localhost:5433) now holds the 4 MES modules as a
**working staging load** (not the final app DB — see README). Built from the owner-declared
final sources `xls/consolidated/All/*.xlsx` via `sql/schema/30–33_*.sql` + `scripts/historical_import/etl_*.py`.

| Module | Tables | Loaded rows | Rejects | ETL verified |
|---|---|---|---|---|
| Setting | `setting_event` / `setting_wagon` | 20,520 / 67,683 | 11 | yes (ad-hoc) |
| Dryer | `dryer_cycle` / `dryer_reading` | 18,558 / 18,370 | 3 | yes (ad-hoc) |
| Kiln | `kiln_push` / `kiln_wagon` / `kiln_reading` / `kiln_sensor` | 38,781 / 38,818 / 697,312 / 18 | — | yes (ad-hoc, live) |
| Packing | `packing_header` / `packing_wagon` | 8,543 / 93,381 | — | yes (ad-hoc, live) |

**Notes / honest caveats:**
- Verification was **ad-hoc** (fresh inline SQL counts + FK-orphan checks), *not* a committed test suite. No CI/test harness exists yet.
- Kiln: 83 of 38,781 pushes carry <18 sensor readings — these are **genuine source gaps** (the Excel has null/blank sensors for those pushes), not load defects. The ETL recovers any sensor present in *any* row of a push (merge-first-valid logic).
- Packing: date source format `YYYY/MM/DD` normalized to `YYYY.MM.DD`; grouped by (date, shift, controller).
- Legacy frozen-app tables (`kiln_pushes`, `kiln_temperature_readings`, `wagon_master`, `packing_records`) still coexist and are **superseded but not yet dropped** (pending owner confirmation).
- Staging tables use row-oriented schemas that differ from the pre-build ERD names (see README deviation note). The ERD remains the target for the final app schema.

## Open items before M0 sign-off
| # | Item | Status | Who |
|---|---|---|---|
| 1 | Resolve the 8 conflicting Packing product codes | **DONE** (§11.1; blueprint updated; code 20 still REVIEW) | — |
| 2 | 1397 missing 2 months | **NOT blocking** — import after DB build (idempotent re-import from physical ledgers; year/month not hard-coded) | Owner (post-build) |
| 3 | Correct flagged wagon/operator typos | **NOT blocking** — flagged in `REVIEW_*.txt`; correct from physical ledgers post-build | Owner (post-build) |
| 4 | Confirm zone/reading vocabulary + plausibility bound for kiln temperatures | **DONE** (§12.1; vocab + 1200°C max, ×10-typo pattern) | — |
| 5 | Setting continuous-wagon model + final column audit | **DONE** (§14 header+wagon; §15 audit: all operational cols covered, analytic cols excluded) | — |

Items 2 & 3 are **not M0 blockers**: the import is append/idempotent, so once the owner supplies the missing 1397 months or typo corrections from physical ledgers, a re-run of the same import adds them without duplicating existing rows (upsert on the natural key). Items 1, 4, 5 are resolved from the workbooks alone.

**Analytic columns EXCLUDED from migration** (owner decision): `راندمان` rollups, `Rand_Tize`/`Rand_sofal`, `Analyse`/`Analyse1`, `Tabarestan`, `Note`, etc. — derived/summary views, re-designed later from migrated facts.

## Next phase (only after M0)
Write the platform code (Django+DRF / React / PostgreSQL) per the frozen specs + ADRs. Until then: **documents-first, no app code.**
