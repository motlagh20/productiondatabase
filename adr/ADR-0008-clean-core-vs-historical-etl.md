# ADR-0008 — Clean App Core vs. Historical ETL Boundary

- **Status:** Proposed
- **Date:** 2026-08-29
- **Deciders:** Project owner
- **Related:** ADR-0001 (doc-first), ADR-0007 (M5 app architecture), ADR-0002 (freeze legacy)

## Context

The historical Excel sources (`xls/consolidated/All/*.xlsx`) contain substantial operator-typo
noise: wagon names outside the valid 1–80 range (516 Setting rows with names 81/82/83/141/444/585),
duplicate push times (Kiln-Merged rows 11784/11785), reversed dates flagged by the `Date Chaned`
control column, and package counts like 900. These defects are **characteristic of the paper-ledger
data-entry era** and are expected to **never recur** in the web application, where:

- wagon selection is a constrained dropdown (1–80) → name typos impossible;
- dates/times are system-generated, not hand-typed → date errors impossible;
- form validation + unique constraints → duplicate/orphan rows impossible.

We observed that trying to make the **application core** resilient to these Excel-era defects pulls
the schema and business logic in the wrong direction (e.g. over-engineering trip codes to "catch"
typos). The historical data is a **one-time migration burden**, not a recurring app concern.

## Decision

1. **Two-layer separation.**
   - **App Core (clean):** All Django/DRF models, API contracts, and business logic assume
     *clean, system-generated data*. Wagon identity is a FK to `wagon(wagon_id)`; trips are
     system-assigned sequential `trip_id`s; no defensive code for "wagon name > 80" etc.
   - **Historical ETL layer (separate):** A standalone, non-application ETL pipeline
     (`scripts/historical_import/`) is responsible for cleaning/scrubbing the Excel sources and
     mapping them into the clean core schema. Defect handling (flagging, manual-review CSVs,
     operator adjudication) lives ONLY here, never in the app.

2. **Trip identity model (clean core).**
   - A `wagon_trip` (or `trip`) table is the spine: `trip_id BIGSERIAL PK`, `wagon_id FK`,
     `started_at`, `status`. Each Setting load, Kiln push, and Packing unload references a
     `trip_id`. The system assigns `trip_id` on trip start — operators never type it.
   - A human-readable `trip_code` (e.g. `S-<date>-<wagon>`) MAY exist for logs/debug but is
     **derived**, never a validation input. It is NOT designed to "catch" typos.

3. **Historical data loaded via ETL map.** Old Excel rows are reconciled to the clean core through
   an `etl_trip_map` (source_row → trip_id) produced by the ETL layer. Suspect rows are flagged to
   `etl_reject` / review CSVs for **owner adjudication from the paper ledger** — the app never
   auto-corrects source truth (SAFE-APPLY rule retained for the migration only).

4. **Boundary rule:** No application model, serializer, or view shall contain logic whose purpose is
   to tolerate Excel-era data defects. If such a need appears, it is added to the ETL layer instead.

## Consequences

- **Good:** App core stays simple, fast, and correct for the 99% case (clean web input). Historical
  defects are isolated to a throwaway pipeline that will be discarded after migration.
- **Good:** Future web data needs zero scrubbing; the same core serves live operation.
- **Cost:** The ETL layer must own all the messy reconciliation (trip matching by wagon name +
  1–10 day window, typo flagging, manual review). This is accepted as a finite, one-time cost.
- **Cost:** Historical trips may remain partially unlinked (e.g. the 516 typo wagons) until the
  owner adjudicates from paper — they stay in review tables, never block the app.
- **Risk mitigated:** We will not over-build the schema around legacy noise (e.g. we will NOT add
  "wagon name > 80" validators to the app, nor encode typo-recovery into trip codes).
