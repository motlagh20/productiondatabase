# DATA_SOURCES — Authoritative inputs & what to ignore

> Resolves a documentation gap: several older docs (APPENDIX_B, M2_HISTORICAL_IMPORT_SPEC,
> M0_SIGNOFF) say the source of truth is `xls/real data/`, but the actual ETL
> (`scripts/historical_import/etl_*.py`) reads from `xls/consolidated/All/*.xlsx`.
> This doc states the **current, real** source layout as of 2026-08-29.
>
> **Role of these Excel files (owner directive 2026-08-29):** the historical workbooks are
> used **only** to (a) analyse requirements and (b) access the process history. They must
> **NOT** exert a distorting influence on the main application design. All old data is
> loadable into the new app, but because the sources carry a high volume of operator-typo
> noise, they must never perturb the design flow. The clean/historical boundary is enforced
> by [ADR-0008](adr/ADR-0008-clean-core-vs-historical-etl.md): the app core assumes clean
> system-generated data; scrubbing lives in the separate ETL layer.

## 1. Authoritative final sources (ETL reads THESE)

Path: `xls/consolidated/All/` — **these 4 files are the only inputs to the historical load.**

| File | Module | Used by |
|------|--------|---------|
| `Set_All_1.xlsx` | Setting | `etl_setting.py` |
| `Dryer-All.xlsx` | Dryer | `etl_dryer.py` |
| `Kiln-Merged.xlsx` | Kiln | `etl_kiln.py` |
| `Packing-All.xlsx` | Packing | `etl_packing.py` |

Owner-declared final reference (2026-08-26): "ستون ردیف تو هیچ کدوم از فایلها مرجع نیست"
→ within these files the **Excel `ردیف` column is NOT a key**; ETL uses its own file-wide
`row_seq` instead (see IMPORT_RUNBOOK §1). `Set_All_1.xlsx` contains 7 annual blocks
(1398–1404) concatenated; `ردیف` restarts at 1 per block — never use it as a key.

## 2. IGNORE — not sources

| Path / pattern | Why ignored |
|----------------|-------------|
| `xls/real data/` | Legacy pre-consolidation workbooks (only `Dryer-1404.xls`, `Packing-All.xlsx` remain there). Superseded by `xls/consolidated/All/`. Kept for audit trail only. |
| `xls/consolidated/Set_1398.xlsx` … `Set_1404.xlsx`, `Kiln-1398.xlsx` … `Kiln-1404.xlsx`, `Dryer-1398.xlsx` … `Dryer-1404.xlsx` | Per-year split workbooks. **Superseded** by the `-All`/`Merged` consolidated files. Do NOT load these (would duplicate data). |
| `xls/consolidated/*` `REVIEW_*.txt`, `review_queue_export.*` | Operator-typo / unmapped review logs. Output of analysis, not input. |
| `xls/consolidated/setting_daily_wagons.xlsx`, `setting_typo_wagon_no.csv`, `kiln_*.csv` | Ad-hoc verification reports (agent-generated). Not ETL inputs. |
| `xls/consolidated/*.backup-before-dates.xlsx`, `Kiln-Merged.backup-*` | Pre-fix snapshots. Ignore. |
| `xls/consolidated/~$*.xlsx` | Excel lock files. Ignore. |
| `xls/archive/prototype_csv_20260827.zip` | Early CSV prototype (M0-era sample). Not authoritative. |
| `xls/*.csv` (root) | Normalized design prototype from M0. Sample only, NOT the source. |

## 3. Git handling

- `xls/consolidated/All/*.xlsx` — **git-ignored** (workbooks are owner design references, never committed; per owner rule "نه نمیخواد بره تو گیت").
- `xls/archive/`, `xls/real data/`, `xls/consolidated/*.{csv,xlsx}` (non-All) — git-ignored via `.gitignore`.
- Only the **ETL scripts + SQL + docs** are committed.

## 4. If a source file is missing

The 4 files in §1 MUST exist before running `etl_*.py`. If `xls/consolidated/All/` is
empty, re-export from the owner's master workbooks — do NOT fall back to `xls/real data/`
or the per-year splits (they are partial/legacy and will corrupt counts).
