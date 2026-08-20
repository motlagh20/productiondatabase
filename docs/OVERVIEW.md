# Project Overview — Manufacturing Analytics & Execution Platform

> Status: **Documentation & data-profiling phase complete.** No platform code written yet (per ADR-0001: documentation-first). All M0 open items are resolved or non-blocking: items 1 (product conflicts) & 4 (temp vocab) done from the workbooks; items 2 (1397 completion) & 3 (typo correction) are post-build data-completion tasks via idempotent re-import. **Ready for M0 architecture sign-off.**

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

## Migration mapping blueprints (`xls/mapping/`, in git)
`operator_mapping_blueprint.csv`, `product_mapping_blueprint.csv`, `glaze_mapping_blueprint.csv` — the `legacy_code → canonical` maps extracted from the authoritative workbooks (inputs to M2 import spec).

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
