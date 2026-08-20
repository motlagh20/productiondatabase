# ADR-0002 — Freeze the Legacy Application as a Read-Only Reference Implementation

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Project owner (option "2.c" — freeze everything; all effort goes to the new platform)
- **Related:** Master Rules §1, §51; [MASTER_SPECIFICATION.md §I.5](../docs/MASTER_SPECIFICATION.md); [Appendix A](../docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md)

## Context

The repository contains a working factory-specific application: a Docker stack (PostgreSQL 16 + PostgREST + Nginx), a Persian/RTL vanilla-JS SPA (`web/`), a superseded Flask/SQLite backend (`server.py`), and assorted utility scripts. The full review ([Appendix A](../docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md)) found it conflicts with the Master Rules on nearly every architectural axis: hardcoded factory constants (§27), Excel-shaped schema (§32), text-based Jalali dates (§20), no import subsystem (§17–19), no analytics (§21–25), no multi-factory support (§29), unenforced security (§42), and a different technology stack (§45).

Options considered:

- **(a) Evolve the current app** toward the platform — rejected: the §27/§32 violations are structural; evolution would preserve the wrong foundation.
- **(b) Keep maintaining it while building the new platform** — rejected: split effort, and every fix invests in throwaway architecture.
- **(c) Freeze it entirely as read-only reference** — **chosen**.

## Decision

The entire existing application is **frozen as a read-only reference implementation**, effective immediately:

1. **Nothing is moved, renamed, or deleted.** The app remains runnable (`docker-compose up`) for domain discovery and UI reference.
2. **No new features, endpoints, tables, or UI screens** are added to it.
3. **Known defects are not fixed** — including the password-less logins and committed secrets — they are documented in Appendix A as lessons. Consequently the frozen app must not be exposed outside a trusted network.
4. **Its schema and UI are evidence, not design.** The future platform's model is derived from the approved domain documents, never from the frozen schema (Master Rules §32).
5. **`xls/` CSVs are protected source data** (Master Rules §44) — read-only inputs for the future migration subsystem.

All development effort goes to the new platform (Django + DRF, React + TypeScript, PostgreSQL — Master Rules §45), which will be built alongside the frozen app in this repository per the documentation-first order (ADR-0001).

## Consequences

- **Positive:** single focus on the correct architecture; the frozen app remains available as a live prototype of the plant's recording practices and Persian/RTL UI conventions; zero risk of destabilizing the historical evidence.
- **Negative / accepted cost:** the plant gains no new tooling until the new platform's MVP; known security defects remain in the frozen code (mitigated by trusted-network-only use).
- **Supersession:** this ADR is revisited only if the plant needs an urgent operational fix before the new platform is usable — such a change would require a new ADR.
