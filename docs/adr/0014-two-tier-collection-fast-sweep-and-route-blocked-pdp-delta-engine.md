# ADR 0014: Two-Tier Collection Fast-Sweep & Route-Blocked PDP Delta Engine

## Status
Accepted

## Date
2026-09-16

## Context
1. **Headless Browser Serial Polling Bottleneck**:
   Retailers protected by aggressive client-side anti-bot challenges (such as Nordstrom with Kasada cryptographic proof-of-work `istlWasHere`) require real browser JavaScript execution via Camoufox (ADR 0011). Because Camoufox is a full headless browser instance, concurrency was appropriately capped at 1 worker (`max_workers = 1`). Visiting 57 individual Product Display Pages (PDPs) serially took ~15.6 minutes (850–950s) per cycle due to repeated client-side proof-of-work solving and heavy asset loading (images, fonts, stylesheets, trackers).
2. **Recurring Cloud API Cost Avoidance**:
   While cloud proxy scrapers (e.g. Firecrawl) avoid local browser execution, running hourly delta sweeps for dozens of products across 24 hours consumes over 1,300 API credits daily ($100s/month), violating our zero-recurring-cost constraint.
3. **Dehydrated Collection-Level Inventory**:
   Investigation of Nordstrom's search and collection pages (`/sr?origin=keywordsearch&keyword=on shoes...`) revealed that Nordstrom embeds live pricing ranges (`sellingRetailPriceRange`), regular prices (`baseRetailPriceRange`), markdowns, and warehouse stock quantities (`availability.shipQuantity`) for all catalog products inside dehydrated client payloads (`window.__INITIAL_CONFIG__["productResults"]["productsById"]`) across only 2 paginated pages.

## Decision

1. **Tier 1 (Fast Collection Sweep) ([`stores/nordstrom/camoufox_solver.py`](../../stores/nordstrom/camoufox_solver.py))**:
   - Implemented `fetch_collection_catalog(page)` to harvest Page 1 and Page 2 of the target collection.
   - Attached aggressive route blocking (`setup_camoufox_route_blocking`) to abort all heavy non-essential assets (`image`, `media`, `font`, and third-party trackers like `doubleclick`, `google-analytics`, `quantummetric`, `branch.io`).
   - In only 2 page navigations (~40 seconds total), extracts live prices and stock for all 111 products into an in-memory cache keyed by numeric style ID and webPathAlias.
2. **In-Memory Fast-Path Evaluation ([`stores/nordstrom/delta.py`](../../stores/nordstrom/delta.py))**:
   - Cached the collection harvest with a 5-minute TTL (`get_or_refresh_collection_cache`).
   - For any product whose stored price and stock status match the live collection data, `check_price_and_stock()` returns immediately in `< 1 millisecond` without visiting the PDP.
   - Updated dispatcher ([`sync_catalog.py`](../../sync_catalog.py)) to skip idle delay sleeps on in-memory fast-path hits, processing stable products near-instantaneously.
3. **Tier 2 (Targeted Route-Blocked PDP Visit)**:
   - If, and only if, a product indicates a price change, markdown, or stock depletion (`shipQuantity == 0`), or is not found in the collection cache, Camoufox navigates to that specific product's PDP (`solve_and_extract_pdp`).
   - Reuses route blocking on PDP navigations to reduce individual page load times from ~15s down to ~3.5s while extracting full granular per-size variant inventory.

## Consequences

- **Positive**:
  - **Dramatic Speedup**: Reduced the full 57-product Nordstrom catalog sweep duration from **938.47 seconds (15.6 minutes) down to 158.08 seconds (2.6 minutes)** — a **6x speedup**.
  - **Sub-Minute Routine Sweeps**: Routine hourly checks where product prices are stable resolve in **~45 seconds** total.
  - **Zero Cloud API Costs**: Maintains completely local, free execution with zero external scraping bills.
  - **Per-Size Variant Granularity Preserved**: Any product with detected deltas receives an immediate targeted PDP visit to synchronize exact size variants (`shipQuantity > 0`).
  - **Store-Agnostic Reusability**: Establishes a reusable two-tier architectural pattern for any future retailer that provides collection-level inventory or pricing.
- **Negative / Trade-offs**:
  - Requires maintaining the collection search URL parameters in sync with the retailer's catalog scope.
