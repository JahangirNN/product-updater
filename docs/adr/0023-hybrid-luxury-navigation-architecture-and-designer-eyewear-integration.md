# ADR 0023: Hybrid Luxury Navigation Architecture, Eyewear Gender Taxonomy & Real-Time Sync Bridge

## Status
Accepted

## Date
2026-09-27

## Context
Following the onboarding and ingestion of luxury timepieces (574 Jomashop watches across 5 brands), we brought 46 Michael Kors designer sunglasses onto the live Shopify store (*The Rare Avenue*, `hewmvw-am.myshopify.com`). 

To deliver a high-end luxury shopping experience, the storefront required:
1. Clear departmental and category hierarchy across desktop mega-menus and mobile sidebar drawers.
2. An agreed-upon **Hybrid Navigation Architecture** balancing Category-First discovery (in Gender departments) and Brand-First discovery (in the Brands directory).
3. Zero cross-gender product leakage between exclusive men's frames, exclusive women's frames, and unisex designs.
4. Seamless integration with our continuous background freshner daemon (`scripts/run_freshner_daemon.py`, `sync_catalog.py`) for instantaneous, zero-delay price and stock synchronization to Shopify via `productSet`.

---

## Decisions

### 1. Eyewear Gender Taxonomy & Model Series Partitioning
The 46 Michael Kors sunglasses were systematically partitioned across 3 discrete model series:
- **MK-9000 Series (Men's Exclusive — 6 Products)**:
  - Models: *City, Toledo, Bowery, Forio, Camden, Avenue*.
  - Tags: `Men`, `Men's`, `Gender:Men`, `Sunglasses`, `Type:Sunglasses`.
  - Invariant: Zero `Women` or `Gender:Women` tags.
- **MK-1000 Series (Unisex — 19 Products)**:
  - Models: *Monte Carlo, Suffolk, Biarritz, Melbourne, Gold Coast, Manchester, Patra, Cape Town, Kona, Perledo, Dana Point, Brentwood, Oxford, Key West, Mar Vista, Denver, Andros, Buenos Aires, Sea Island*.
  - Tags: Both `Men` and `Women` taxonomy tags (`Gender:Men`, `Gender:Women`).
  - Available across both Men's and Women's eyewear showrooms.
- **MK-2000 Series (Women's Exclusive — 21 Products)**:
  - Models: *Andermatt, Lucerne, Edgewater, Molokai, Siesta Key, Lake Tahoe, Nagoya, Santo Domingo, Napa Valley, Grand Cayman, Atlanta, Agra, Catalina, Athens, Roanoke, Mumbai, Isle of Palms, Piedmont, Tokyo, Wilmington, Grenada*.
  - Tags: `Women`, `Women's`, `Gender:Women`, `Sunglasses`, `Type:Sunglasses`.
  - Invariant: Zero `Men` or `Gender:Men` tags.

### 2. Smart Collection Hierarchy
Three automated collections were provisioned via Shopify Admin GraphQL (`storage/shopify_collections.py`):
1. **Master Eyewear Collection (`/collections/designer-eyewear`)**:
   - GID: `gid://shopify/Collection/693217951910`
   - Scope: All 46 items (`TYPE == Sunglasses` OR `TAG == Sunglasses`).
   - Interactive Gender Facet Pills: `All Pieces (46)`, `Women's (40)`, `Men's (25)`.
2. **Women's Sunglasses (`/collections/womens-sunglasses`)**:
   - GID: `gid://shopify/Collection/693229584550`
   - Scope: 40 items (21 Women's exclusive + 19 Unisex).
   - Rules: `TYPE == Sunglasses` AND `TAG == Women`.
   - Gender facet suppressed to avoid redundant filtering; Brand, Price, Availability preserved.
3. **Men's Sunglasses (`/collections/mens-sunglasses`)**:
   - GID: `gid://shopify/Collection/693229617318`
   - Scope: 25 items (6 Men's exclusive + 19 Unisex).
   - Rules: `TYPE == Sunglasses` AND `TAG == Men`.
   - Gender facet suppressed; 0 cross-gender pollution from women's cat-eye/butterfly frames.

### 3. Hybrid Luxury Navigation Structure
Deployed to live Prestige theme `#197348655270`:
- **Desktop Mega-Menu (`theme/snippets/luxury-desktop-nav.liquid`)**:
  - *Women*: Added **Designer Eyewear** column with direct routes to `/collections/womens-sunglasses`, Michael Kors Eyewear, and frame style filters (`Cat-Eye & Butterfly`, `Aviator & Pilot`, `Oversized & Geometric`).
  - *Men*: Added **Designer Eyewear** column with direct routes to `/collections/mens-sunglasses`, Michael Kors Eyewear, and masculine frame styles (`Aviator & Pilot`, `Navigator & Square`, `Wireframe & Metal`).
  - *Brands A–Z*: Under `J — M`, expanded **Michael Kors** from a flat link to an authentic Maison entry with sub-links for `Luxury Watches`, `Designer Sunglasses`, and `All MK Showroom →`.
- **Mobile Sidebar Drawer (`theme/snippets/luxury-sidebar-panels.liquid`)**:
  - Distinct collapsible accordions added under Women, Men, and Brands sub-panels with gold luxury accents (`#c9a876`).
- **Facet Dynamic Routing (`theme/snippets/facets.liquid`)**:
  - Gender pills on `/collections/designer-eyewear` route directly to the dedicated smart collections (`/collections/womens-sunglasses` and `/collections/mens-sunglasses`).

### 4. Real-Time Delta Synchronization Contract (Verified)
- The continuous background freshner daemon (`scripts/run_freshner_daemon.py`, PID 25960) invokes `sync_catalog.py` on a systematic schedule.
- When a price change (> $0.01) or availability flip occurs for any product with an active `shopify_product_id`:
  1. `sync_catalog.py` directly executes `sync_delta_to_shopify(updated_product, delta_res, forex_rate)` in `storage/shopify_sync.py`.
  2. `sync_delta_to_shopify()` invokes `upsert_product_to_shopify()`, which immediately dispatches the synchronous Shopify Admin GraphQL `productSet` mutation.
  3. The product's INR price (converted via `storage/forex.py` with 0 fractional paise per ADR 0006) and live status (`ACTIVE` if in stock, `DRAFT` if out of stock) update immediately on the live Shopify storefront.
  4. The event is recorded in `storage/db/history/delta_events.jsonl` with `shopify_sync_pending: False` upon GraphQL confirmation.
  5. If the live network call fails, `shopify_sync_pending: True` is flagged, allowing the offline queue drainer `drain_delta_events_queue()` to reconcile when network connectivity is restored.

---

## Consequences
- **Positive**: 100% verified zero cross-gender leakage across desktop and mobile.
- **Positive**: Automatic live price and stock updates directly on Shopify whenever the daemon sweeps source retailers, requiring zero manual intervention.
- **Positive**: Resilient dual-path sync architecture (instant synchronous GraphQL mutation + offline queued event ledger fallback).
- **Positive**: Full Playwright regression suite (40 Tier 1 tests, 6 Tier 4 user journeys) passing with 100% success on the live storefront.
