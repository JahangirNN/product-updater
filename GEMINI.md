# Product Updater: Workspace Constitutional Rules

## 1. Zero Class Architecture (ADR 0005)
- All scrapers, updaters, and storage handlers must be written as **pure, composable Python functions** (`def ...`).
- No OOP class inheritance trees, no `BaseScraper`, no abstract base classes.
- Store logic is completely independent in `stores/{store_slug}/`.

## 2. Mandatory Library Research via Context7 MCP
- Whenever introducing or using third-party libraries (`pydantic`, `crawlee`, `playwright`, `httpx`, `pyyaml`, `requests`), **Context7 MUST be used** to fetch the latest official documentation and best practices before writing code.
- Workflow: `resolve-library-id` -> `get-library-docs` -> implement using verified patterns.
- Never guess method signatures or rely on potentially outdated training data.

## 3. Living Documentation & Decision Integrity (Skill: doc-keeper)
- Before modifying or adding code, consult `docs/ARCHITECTURE.md`, `docs/SHOPIFY_INTEGRATION_SPEC.md`, `docs/JSON_STORAGE_SPEC.md`, and `docs/adr/`.
- Every store module MUST maintain its own `stores/{store_slug}/LEARNINGS.md` documenting URL filter query parameters, Firecrawl prompt recipes, and fast delta checking endpoints.
- Any architectural pivot or schema modification must be recorded as a new ADR in `docs/adr/`.

## 4. Zero Code Until Explicitly Authorized
- Maintain strict discipline: never write implementation code or scrape live websites until the user gives explicit green-light approval.
