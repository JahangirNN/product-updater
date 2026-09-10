# Product Updater: Workspace Constitutional Rules

## 1. Zero Class Architecture (ADR 0005)
- All scrapers, updaters, and storage handlers must be written as **pure, composable Python functions** (`def ...`).
- No OOP class inheritance trees, no `BaseScraper`, no abstract base classes.
- Store logic is completely independent in `stores/{store_slug}/`.

## 2. Mandatory Library Research via Context7 MCP
- Whenever introducing or using third-party libraries (`pydantic`, `crawlee`, `playwright`, `httpx`, `vite`, `tailwindcss`), **Context7 MUST be used** to fetch the latest official documentation and best practices before writing code.
- Workflow: `resolve-library-id` -> `query-docs` -> implement using verified patterns.
- Never guess method signatures or rely on potentially outdated training data.

## 3. Living Documentation & Decision Integrity (Skill: doc-keeper)
- Before modifying or adding code, consult `docs/ARCHITECTURE.md`, `docs/SHOPIFY_INTEGRATION_SPEC.md`, `docs/JSON_STORAGE_SPEC.md`, and `docs/adr/`.
- Every store module MUST maintain its own `stores/{store_slug}/LEARNINGS.md` documenting URL filter query parameters, Firecrawl prompt recipes, and fast delta checking endpoints.
- Any architectural pivot or schema modification must be recorded as a new ADR in `docs/adr/`.

## 4. Zero Code Until Explicitly Authorized
- Maintain strict discipline: never write implementation code or scrape live websites until the user gives explicit green-light approval.

## 5. Frontend & GitHub Pages Invariants (ADR 0007)
- **Relative Base Resolution**: Any Vite web application deployed to GitHub Pages must set `base: './'` in `vite.config.ts` to prevent asset 404 and MIME-type errors when served from repository subpaths (`https://<username>.github.io/<repo>/`).
- **Relative Static Assets**: Client-side data fetching for static bundles must use relative paths (e.g., `./data/catalog.json`) rather than root-relative paths (`/data/catalog.json`).

## 6. Systematic Delta Engine & Freshness Invariants (ADR 0008)
- **Non-Destructive Delta Checkers**: Delta polling modules (`delta.py`) must strictly poll dynamic fields (price, availability, variant status) via fast endpoints (`/products/{handle}.js`) and must never re-parse static descriptions or overwrite `created_at`.
- **Timestamp-Based Scheduling**: Products must track `last_verified_at`. Checkers must evaluate `now - last_verified_at` against configured intervals to prevent redundant network requests and avoid CDN rate limits.
- **Dedicated Shift Queue**: Price and stock shifts must be staged in `storage/db/history/delta_events.json` with `shopify_sync_pending: true` to decouple monitoring from downstream consumers.

## 7. Strategic Project Priority: Data Collection & Freshness First
- **Core Directive**: The primary focus of this project is discovering catalog collections, accurately extracting rich product attributes, size guides, and high-res media, and maintaining high-frequency, reliable freshness updates across brands.
- **Shopify Sync Phasing**: Downstream Shopify Admin API synchronization workflows are explicitly deferred to future phases. All data staging (`shopify_sync_pending: true`, `delta_events.json`) is designed for non-blocking downstream consumption without complicating our immediate ingestion and freshness priorities.
