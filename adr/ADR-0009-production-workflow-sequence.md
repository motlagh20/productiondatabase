# ADR-0009 — Production Workflow Sequence (Owner-Confirmed)

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Project owner
- **Related:** MASTER_SPECIFICATION Part IV; [PRODUCTION_FLOW.md](../docs/PRODUCTION_FLOW.md); M5_SRS §2.2; ADR-0005 (Setting model); ADR-0007 (M5 architecture)

## Context

Earlier documentation and review materials sometimes showed an incorrect order (e.g. Setting before
Dryer, or a four-step diagram omitting preparation, glazing, waiting hall, and warehouse). Master
Rules §54 listed "Exact production workflow" as an open question (Part II §II.7 item 1).

The owner confirmed the **complete physical sequence** for the roof-tile / clay roof tile line on
2026-08-31.

## Decision

The canonical production workflow for the reference plant is **nine stages**, in this order:

1. **آماده‌سازی** (Preparation)
2. **فرم‌دهی / پرس** (Forming / Press)
3. **خشک‌کن** (Dryer — 40 chambers)
4. **لعاب‌زنی** (Glazing) — **optional**, product-dependent
5. **ستینگ** (Setting — arrange dried product on wagons)
6. **سالن انتظار** (Waiting hall) — **optional**
7. **کوره** (Kiln — push + temperature profile)
8. **بسته‌بندی** (Packing — grading + waste)
9. **انبار محصول** (Finished-goods warehouse)

Rules:

1. **Dryer (3) always precedes Setting (5).** Setting consumes dried body from dryer chambers; it never precedes drying.
2. Stages **4** and **6** are optional branches, not skipped sequence numbers.
3. The **MES recording modules** in this project cover stages **3, 5, 7, 8** only (Excel + app F1–F5). Stages **1, 2, 9** are real but not yet digitized. Stage **4** appears as glaze dimension on Setting rows when applicable.
4. All docs, diagrams, SRS flow sections, and UI copy must reference [PRODUCTION_FLOW.md](../docs/PRODUCTION_FLOW.md) as the single diagram of record.

## Consequences

- **Positive:** Resolves Master Rules §54 / Part II §II.7 item 1 for the reference plant; prevents future schema/UI ordering mistakes.
- **Documentation:** MASTER_SPEC Part IV, M5_PLATFORM_PLAN, M5_SRS updated to match.
- **App scope unchanged:** M5 vertical slice still implements F1–F5 for recorded stages; prep/press/warehouse remain future modules.
- **Trip spine:** `wagon_trip` may still *start* at Setting for MVP, but journey dashboards (F7) must show Dryer when F1 link exists.

## Validation

Owner-provided sequence (2026-08-31). Consistent with M1 dryer→setting domain rules and M5_SRS §2.2 partial flow already corrected 2026-08-29.
