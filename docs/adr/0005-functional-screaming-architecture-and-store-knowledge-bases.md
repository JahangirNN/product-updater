# ADR 0005: Functional Screaming Architecture & Per-Store Knowledge Bases

## Status
Accepted

## Date
2026-09-09

## Context
Traditional scrapers often rely on deep object-oriented inheritance hierarchies (`BaseScraper`, `PlaywrightScraper(BaseScraper)`, `RetailerScraper(PlaywrightScraper)`). In practice, this creates brittle coupling where changes to base classes break unrelated retailer scrapers. Furthermore, e-commerce retailers vary drastically in how they render HTML, handle variant options (e.g. shoe sizing vs handbag dimensions), and encode filter parameters in URLs.

Additionally, scraping lessons, site-specific gotchas, and anti-bot behavior are rarely documented next to the code, leading to lost institutional knowledge when revisiting or adding product groups for the same retailer.

## Decision

1. **Screaming Architecture (Store-Centric)**:
   - The primary organizational unit is the **Store** (`stores/{store_slug}/`).
   - The directory tree screams the business domain rather than technical framework layers.
2. **Pure Functional Style (Zero Classes)**:
   - Scraper, updater, and storage logic will be written exclusively using pure, composable Python functions (`def function_name(data: dict) -> dict`).
   - No OOP class inheritance trees, no metaclasses, no stateful object instances.
   - Pydantic models or plain dictionaries will be used strictly as typed data transfer objects (DTOs).
3. **Per-Store Living Knowledge Base (`LEARNINGS.md`)**:
   - Every store folder MUST contain a `LEARNINGS.md` documenting:
     - Filter URL structure (how price, color, category, sorting are passed in query params).
     - Firecrawl prompt recipes that produce the highest-fidelity extraction.
     - DOM vs JSON-LD quirks and currency handling.
     - Fast delta endpoints (e.g. internal stock/price JSON APIs) to bypass full HTML loading during periodic updates.
4. **Category Group Partitioning**:
   - Products are organized in storage by store and category group (`storage/db/{store_slug}/{product_group}/{product_id}.json`).
   - Category-specific variations within a store (e.g. shoe size mapping vs handbag dimensions) reside in `stores/{store_slug}/groups/{group_name}.py`.

## Consequences
- **Positive**:
  - Independent store modules: Changes to Store A can never break Store B.
  - Zero cognitive overhead from OOP boilerplate.
  - Onboarding a new store or product group is as simple as copying `stores/_template/` and filling in functions.
  - Knowledge and gotchas are colocated directly with the code.
- **Negative**:
  - Requires maintaining the per-store `LEARNINGS.md` disciplined updates whenever site quirks are discovered.
