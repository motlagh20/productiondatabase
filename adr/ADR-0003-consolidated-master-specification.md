# ADR-0003: Consolidated Master Specification and revised roadmap

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decider:** Project owner
- **Related:** ADR-0001 (documentation-first), ADR-0002 (legacy freeze)

## Context

The documentation foundation was initially delivered as separate files (`docs/01_PROJECT_CHARTER.md`, `02_GLOSSARY.md`, `03_BUSINESS_DOMAIN_MODEL.md`, `04_BUSINESS_PROCESS_SPECIFICATION.md`). The project owner identified two risks:

1. **Fragmentation drift** — isolated documents may eventually contradict each other, and AI-assisted sessions need one authoritative artifact to load ("the project remembers itself, the AI does not need to").
2. **Missing phases** — the Master Rules §48 phase order did not make Historical Data Architecture, the Configuration Model, and the Workflow Engine explicit, standalone phases before platform architecture, despite 15+ years of historical plant data being a core asset.

Options considered for the document structure:
- (a) **Merge and retire** — one consolidated specification; standalone 01–04 deleted.
- (b) Merge but keep superseded copies with banners — duplicated content would drift.
- (c) Umbrella spec binding the standalone files by reference — "give the AI one file" becomes eight files.

## Decision

1. Create **`docs/MASTER_SPECIFICATION.md` — Master Product & Architecture Specification v0.1**, consolidating the charter, glossary, domain model, and process specification, and adding four new normative parts: Historical Data Architecture (Part V), Architectural Principles (Part VI), revised Roadmap (Part VII), and AI Collaboration Protocol (Part VIII).
2. **Option (a): merge and retire.** The standalone `docs/01–04` files are deleted; their full content lives on in the specification. `docs/00_MASTER_PROJECT_RULES.md` (constitution), Appendices A/B (evidence annexes), and the ADRs remain separate files.
3. The roadmap refines Master Rules §48 by inserting **Historical Data Model → Configuration Model → Workflow Engine** between the domain model and platform architecture (milestones M2–M4 in Part VII). The historical Excel structure is never forced into the new application; data flows Raw → Cleaning/Mapping → Canonical Manufacturing Model → Analytics Model.
4. **AI Collaboration Protocol adopted** (Part VIII): every AI session receives the current specification first; AIs implement approved spec sections only and never make architectural decisions; open-ended prompts ("build me a manufacturing management system") are forbidden.

## Consequences

- Single point of product truth; zero duplicated normative content; one file to hand to any AI or contributor.
- Version history of the retired standalone files is lost at the filesystem level (accepted; content preserved verbatim in the specification).
- Future phase documents (SRS, ERD, API contract, UX blueprint) are *derived from* and must cite the specification; they do not replace it.
- Any future architectural change requires a specification version bump plus a new ADR.
