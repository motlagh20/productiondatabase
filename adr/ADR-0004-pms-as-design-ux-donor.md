# ADR-0004 — PMS Repository as UI/UX & Import-Flow Donor (Harvest, not Merge)

- **Status:** Proposed (for owner approval)
- **Date:** 2026-08-15
- **Deciders:** Project owner (confirmed "برداشت هوشمندانه" / intelligent harvest over code-merge)
- **Related:** Master Rules §27, §32, §45; MASTER_SPECIFICATION I.3, Part V, Part VI P1–P2; ADR-0002 (freeze legacy), ADR-0003 (consolidated spec)

## Context

A second repository, **`github.com/motlagh20/PMS`** (public, created 2026-08-17, TypeScript), exists as a *working* application for the same initial factory. It is a React 19 + Vite + Express + **Google Firestore (NoSQL)** single-factory app, hardcoded to this plant ("Set_1400", 4 fixed wagons, 18 kiln temperature columns). It was reviewed read-only.

The owner directed: the historical data is the project's most valuable asset, so *correct* import matters most; the design must be comprehensive yet re-definable per similar plant; and — before any coding — the documents must be reviewed and revised, harvesting the *good parts* (notably design) from PMS and integrating them with the current project.

Two interpretations of "integrate PMS" were possible:
- (a) **Merge** PMS code into the new platform.
- (b) **Harvest** (برداشت هوشمندانه) only the reusable *design/UX and import-flow* as a reference, while the new platform's architecture follows the spec (Django + DRF + React + PostgreSQL, config-driven).

Option (a) conflicts with ADR-0002/§32/§45 (Firestore/NoSQL and factory-locked model contradict the target stack and the "configuration over code" principle). Option (b) is consistent.

## Decision

1. **PMS is a DESIGN/UX DONOR, not a code-merge target.** Only two artifacts are harvested:
   - **(i) Visual design / theme** — React 19 + Tailwind v4 + RTL + lucide-react + recharts UI language. This supersedes the frozen vanilla-JS `web/` design as the *reference* UI for the new React frontend (ADR-0002 already anticipated a UI reference).
   - **(ii) Import user-flow** — the multi-source import pattern (local Excel/XLSX, CSV, and Google Sheets via Drive picker), automatic Persian/English column-keyword mapping, row preview, import progress, and batch commit. This is the **UX template** for the Cleaning/Mapping Layer ② (Part V), not the implementation.
2. **NOT harvested (explicitly rejected):**
   - The Firestore/NoSQL data layer — contradicts target stack I.3 (PostgreSQL) and P3 (single migration-managed schema).
   - The factory-locked data model (Set_1400, car1–car4 columns, 18 hardcoded temp columns) — violates Master Rules §32 (never copy Excel structure) and P1.
   - The import's **fake fallback values** (e.g. `fingerCount = 450 + i*20`, default temps) — these silently fabricate data and directly violate **P2 (evidence over assumption)** and **P5 (audited corrections, never invent)**. The new import must replace fallbacks with a **staging + validation + review-queue** layer (Part V ②) that flags gaps instead of inventing numbers.
3. **Governance:** PMS code is never copied into this repository. Harvested patterns are recorded here and realized in the spec-driven implementation only. Any PMS-derived UI pattern that implies a factory constant enters the **configuration** model (P1), never code.
4. **Reference pointer added** to Part V (new §V.5) and README, so future AI sessions know PMS is the approved design donor.

## Consequences

- **Positive:** the new platform gets a proven, modern, RTL UI language and a battle-tested import UX without inheriting PMS's architectural debt; "comprehensive yet re-definable per plant" is satisfied because only the *presentation/flow* is borrowed, not the *model*.
- **Negative / accepted cost:** PMS's working import logic is re-implemented on the new stack (not reused), adding effort but preserving the target architecture.
- **Binding:** the harvested import flow must be re-expressed through Part V layer ② (staging, validation classes, review queue) — the fake-fallback behaviour is a hard anti-pattern and must not survive the harvest.
- **Supersession:** none; complements ADR-0002 (which froze the *old* legacy app — PMS is a separate, later, donor repo).
