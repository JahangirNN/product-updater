---
name: doc-keeper
description: Maps, explains, and maintains all architectural documentation, specifications, Architecture Decision Records (ADRs), and per-store knowledge bases for the product-updater project. Use this skill whenever navigating existing project architecture, checking documented decisions before making changes, recording new architectural choices in ADRs, or updating retailer quirks and gotchas in LEARNINGS.md files.
---

# Document Keeper & Context Preserver (`doc-keeper`)

This skill acts as the project's **Context Keeper and Architecture Guardian**. It guarantees that institutional knowledge, technical decisions, retailer gotchas, schema rules, and **Shopify onboarding milestones** are never forgotten or buried deep in the codebase.

---

## 1. Living Documentation Map

When working on any task in `product-updater`, consult the relevant authoritative document:

| Domain / Question | Authoritative File | Key Contents |
| :--- | :--- | :--- |
| **System Overview & Multi-Store Flow** | [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) | Multi-tier architecture, delta engine, and Shopify synchronization pipeline |
| **Shopify Progress & Ingestion Ledger** | [`docs/shopify/PROGRESS_TRACKER.md`](../../docs/shopify/PROGRESS_TRACKER.md) | Living milestone tracker, product upload ledger per store, and collection statuses |
| **Shopify Integration & API Specs** | [`docs/shopify/README.md`](../../docs/shopify/README.md) | GraphQL 2026-04 recipes, `productSet`, bulk staged uploads, and CLI session auth |
| **Centralized Delta Configuration** | [`config/delta_config.json`](../../config/delta_config.json) | 60m check interval, concurrency, polite delays, and per-store profiles |
| **Universal Delta Engine & Scheduler** | [`sync_catalog.py`](../../sync_catalog.py) | Dynamic multi-store dispatcher, timestamp-based polling, and shift queueing |
| **Mobile Catalog Viewer** | [`frontend/`](../../frontend/) | React 18 + Vite 6 + Tailwind mobile-first auditing dashboard hosted on GitHub Pages |
| **Local JSON Database** | [`docs/JSON_STORAGE_SPEC.md`](../../docs/JSON_STORAGE_SPEC.md) | Partitioned file layout (`db/{store}/products/{id}.json`), `index.json`, `delta_events.jsonl` |
| **Folder Layout & Module Rules** | [`docs/FOLDER_STRUCTURE.md`](../../docs/FOLDER_STRUCTURE.md) | Screaming functional layout, module isolation, zero-class guidelines |
| **Coding & Typing Standards** | [`docs/CODING_STANDARDS.md`](../../docs/CODING_STANDARDS.md) | Pure functions, Pydantic type annotations, error handling, atomic file writes |
| **Architecture Decision Records** | [`docs/adr/`](../../docs/adr/) | Numbered, immutable logs of technical decisions (0001 through 0020) |
| **Store-Specific Quirks & Gotchas** | `stores/{store_slug}/LEARNINGS.md` | URL query filter syntax, sizing quirks, fast delta endpoints, and bot bypasses |

---

## 2. The 6 Golden Rules of Project Maintenance

1. **Check Context Before Action**: Before writing or refactoring any code, read the relevant specification and ADRs. Never write code that contradicts an Accepted ADR.
2. **Document Decisions in ADRs**: If a new architectural choice, library addition, or schema migration is proposed, create a new numbered record in `docs/adr/` (e.g. `0020-title.md`) before writing implementation code.
3. **Keep Shopify Progress Ledger Updated**: After every coding milestone (collection creation, product batch upload, delta bridge connection, theme build), update [`docs/shopify/PROGRESS_TRACKER.md`](../../docs/shopify/PROGRESS_TRACKER.md) with exact counts, timestamps, and test results.
4. **Colocate Store Knowledge**: Any newly discovered retailer quirk (e.g. hidden GraphQL bot challenge, shoe size conversion quirk, internal stock API endpoint) MUST be immediately documented in `stores/{store_slug}/LEARNINGS.md`.
5. **Keep Maps Synchronized**: Whenever a new store module, product group, or tool is added, update `docs/FOLDER_STRUCTURE.md` and the master index.
6. **Prioritize Ingestion & Freshness First**: Maintain laser focus on rich catalog attribute collection and systematic delta freshness with zero fractional paise.

---

## 3. Standard Workflows

### Workflow A: Consulting Context Before Modifying a Store
1. Open and read `stores/{store_slug}/LEARNINGS.md`.
2. Check `docs/SHOPIFY_INTEGRATION_SPEC.md` and `docs/shopify/README.md` to ensure any extracted fields satisfy the Shopify readiness criteria.
3. Confirm that all functions in `inflow.py` and `delta.py` remain pure and functional with zero class definitions (per ADR 0005).

### Workflow B: Recording a New Architecture Decision (ADR)
1. Find the next sequential number in `docs/adr/` (e.g., `0020`).
2. Create `docs/adr/NNNN-<kebab-case-title>.md` using the standard format:
   - **# Title & Number**
   - **## Status**: `Proposed` | `Accepted` | `Deprecated` | `Superseded`
   - **## Date**: YYYY-MM-DD
   - **## Context**: The problem, constraints, and alternatives evaluated.
   - **## Decision**: The selected course of action and rationale.
   - **## Consequences**: Positive, negative, and neutral trade-offs.
3. Update the ADR index table in `README.md` and `docs/FOLDER_STRUCTURE.md`.

### Workflow C: Updating Shopify Ingestion & Delta Progress
1. Open [`docs/shopify/PROGRESS_TRACKER.md`](../../docs/shopify/PROGRESS_TRACKER.md).
2. Update the Store Catalog Ingestion Ledger with new ingested counts and timestamps.
3. Update the Collections Ledger with newly provisioned Shopify collection GIDs.
4. Record the verification test result in the Audit Trail table.

---

## 4. Verification & Audit

Run the alignment verification script to ensure all store modules, documentation, and ADRs are valid:
```bash
python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py
```
