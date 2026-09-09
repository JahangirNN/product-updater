---
name: doc-keeper
description: >-
  Maps, explains, and maintains all architectural documentation, specifications, Architecture Decision Records (ADRs), and per-store knowledge bases for the product-updater project. Use this skill whenever navigating existing project architecture, checking documented decisions before making changes, recording new architectural choices in ADRs, or updating retailer quirks and gotchas in LEARNINGS.md files.
---

# Document Keeper & Context Preserver (`doc-keeper`)

This skill acts as the project's **Context Keeper and Architecture Guardian**. It guarantees that institutional knowledge, technical decisions, retailer gotchas, and schema rules are never forgotten or buried deep in the codebase.

---

## 1. Living Documentation Map

When working on any task in `product-updater`, consult the relevant authoritative document:

| Domain / Question | Authoritative File | Key Contents |
| :--- | :--- | :--- |
| **System Overview & Two-Tier Flow** | [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) | Tier 1 (Firecrawl Ingestion) vs Tier 2 (Delta Updater) flow and Mermaid diagrams |
| **Shopify Sync & Warnings** | [`docs/SHOPIFY_INTEGRATION_SPEC.md`](../../docs/SHOPIFY_INTEGRATION_SPEC.md) | GraphQL `productSet` mutation requirements, mandatory vs recommended fields, DRAFT status triggers |
| **Local JSON Database** | [`docs/JSON_STORAGE_SPEC.md`](../../docs/JSON_STORAGE_SPEC.md) | Partitioned file layout (`db/{store}/{group}/{id}.json`), `index.json`, composite key deduplication |
| **Folder Layout & Module Rules** | [`docs/FOLDER_STRUCTURE.md`](../../docs/FOLDER_STRUCTURE.md) | Screaming functional layout, module isolation, zero-class guidelines |
| **Coding & Typing Standards** | [`docs/CODING_STANDARDS.md`](../../docs/CODING_STANDARDS.md) | Pure functions, Pydantic type annotations, error handling, atomic file writes |
| **Architecture Decision Records** | [`docs/adr/`](../../docs/adr/) | Numbered, immutable logs of technical decisions (0001 through 0005) |
| **Store-Specific Quirks & Gotchas** | `stores/{store_slug}/LEARNINGS.md` | URL query filter syntax, Firecrawl prompt recipes, sizing quirks, fast delta endpoints |

---

## 2. The 4 Golden Rules of Project Maintenance

1. **Check Context Before Action**: Before writing or refactoring any code, read the relevant specification and ADRs. Never write code that contradicts an Accepted ADR.
2. **Document Decisions in ADRs**: If a new architectural choice, library addition, or schema migration is proposed, create a new numbered record in `docs/adr/` (e.g. `0006-title.md`) before writing implementation code.
3. **Colocate Store Knowledge**: Any newly discovered retailer quirk (e.g. hidden JSON-LD price, shoe size conversion quirk, internal stock API endpoint) MUST be immediately documented in `stores/{store_slug}/LEARNINGS.md`.
4. **Keep Maps Synchronized**: Whenever a new store module, product group, or tool is added, update `docs/FOLDER_STRUCTURE.md` and the master index.

---

## 3. Standard Workflows

### Workflow A: Consulting Context Before Modifying a Store
1. Open and read `stores/{store_slug}/LEARNINGS.md`.
2. Check `docs/SHOPIFY_INTEGRATION_SPEC.md` to ensure any extracted fields satisfy the Shopify readiness criteria.
3. Confirm that all functions in `inflow.py` and `delta.py` remain pure and functional with zero class definitions (per ADR 0005).

### Workflow B: Recording a New Architecture Decision (ADR)
1. Find the next sequential number in `docs/adr/` (e.g., `0006`).
2. Create `docs/adr/NNNN-<kebab-case-title>.md` using the standard format:
   - **Title & Number**
   - **Status**: `Proposed` | `Accepted` | `Deprecated` | `Superseded`
   - **Date**: YYYY-MM-DD
   - **Context**: The problem, constraints, and alternatives evaluated.
   - **Decision**: The selected course of action and rationale.
   - **Consequences**: Positive, negative, and neutral trade-offs.
3. Update the ADR index table in `README.md` and `docs/FOLDER_STRUCTURE.md`.

### Workflow C: Onboarding a New Store
1. Copy the template folder:
   ```bash
   cp -r stores/_template stores/{new_store_slug}
   ```
2. Fill out `stores/{new_store_slug}/LEARNINGS.md` with known URL filter parameters and domain info.
3. Implement pure functions in `stores/{new_store_slug}/inflow.py` and `delta.py`.
4. Run validation to verify zero-duplicate storage and Shopify readiness.

---

## 4. Verification & Audit

Run the alignment verification script to ensure all store modules have documentation and all ADRs are valid:
```bash
python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py
```
