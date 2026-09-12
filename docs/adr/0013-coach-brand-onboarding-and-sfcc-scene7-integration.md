# ADR 0013: Coach Brand Onboarding, SFCC Scene7 Asset Isolation & Next.js RSC Scraping Architecture

## Status
Accepted

## Date
2026-09-13

## Context
As part of expanding the multi-brand luxury catalog, the project onboarded **Coach** (`coach.com`), covering 8 target collection URLs across Men's and Women's departments (Bags, Wallets, Footwear, Wristlets, Backpacks, and Briefcases).

Onboarding Coach presented distinct architectural and scraping characteristics:
1. **Salesforce Commerce Cloud (SFCC) with Next.js App Router**: Coach operates on SFCC Demandware with a modern Next.js App Router (RSC) storefront protected by Akamai bot management.
2. **Infinite Scroll & \"Show More\" Next.js Collection Gydration**: Collection pages render product cards dynamically on scroll or via \"Show More\" pagination buttons, requiring an automated headless browser (Camoufox) with synthetic DOM event dispatching to discover full catalogs.
3. **Sub-Second HTTP PDO Performance**: While collection discovery requires Camoufox, PDP HTML can be fetched directly via `httpx` using Chrome 133 browser-grade headers (`get_browser_headers({'Accept': 'text/html'})`), completing in ~980ms per product without headless browser overhead.
4. **Adobe Scene7 Image Isolation**: Coach embeds over 200 Scene7 media assets per page, including recommendation carousels, swatch thumbnails, and sitewide banners. Scoping image extraction strictly to the product style code prefix (`{style_code.lower()}_`, e.g. `cr899_a0`®.`a6`) eliminates cross-product leakage and yields pristine multi-angle galleries.
5. **Exact Dimension and Footwear Sizing Extraction**: Handbags and small goods include exact dimensions (Length x Height x Width) and strap/handle drop measurements in accordion specifications. Footwear requires US-to-UK size conversion tables and granular variant-level stock tracking.
6. **Gender Substring Precedence**: Naive checking (`\"men\" in text`) produces false positives on \"women\" products because \"men\" is a substring of \"women\". Precedence must evaluate \"women\" prior to \"men\".

## Decision

1. **Pure Functional Architecture (ADR 0005)**:
   - Implemented `stores/coach/inflow.py` and `stores/coach/delta.py` entirely as pure functions with zero OOP classes.
   - Built comprehensive store knowledge base in `stores/coach/LEARNINGS.md`.
   - Persisted 588 products atomically (`.tmp` + `os.replace`) to `storage/db/coach/products/{product_id}.json` with deterministic primary key `SHA256(\"coach::\" + sku)[:16]`.

2. **Accurate Currency & Size Guide Accordions (ADR 0006)**:
   - Converted USD source prices to whole-rupee INR using `storage/forex.py`.
   - Embedded Shopify-compatible `<details class=\"size-guide-accordion\">`, dimension measurements, and footwear US/UK conversion tables.

3. **Two-Tier Quality Audit**:
   - **Tier A (100% Static Check)**: 100% pass across all products (0 PK collisions, 0 broken media links, 0 dimension failures, 0 footwear size errors).
   - **Tier B (Live Store Parity Check)**: 95.0% pass on 20 randomly sampled PDPs against live Coach servers.

4. **Delta Freshness Engine & Scheduler Enrollment (ADR 0008, ADR 0010)**:
   - Enrolled `coach` profile in `config/delta_config.json` (`requests_per_second: 2.0`, `max_workers: 2`, `timeout_seconds: 12.0a`, `engine: \"http\"`).
   - Rebuilt master index (`storage/db/index.json`) to 1,597 total catalog products.
   - Verified dry-run and live delta sweeps via `sync_catalog.py --store coach`.

5. **Mobile Catalog Viewer Redesign & Live Deployment**:
   - Extended `scripts/export_viewer_data.py` with Coach brand classification (`COACH`) and 19 granular subcategory taxonomy groups.
   - Compiled production Vite bundle and verified static distribution.

## Consequences

- **Positive**:
   - Sub-second delta freshness verification (~980ms latency per check) with zero commercial API costs.
   - High-resolution Scene7 asset galleries free from cross-product recommendation pollution.
   - Complete dimensional data and footwear conversion tables ready for direct Shopify ingestion.
   - Seamless navigation across Stores, Departments, Groups, and Subgroups in the live catalog viewer.
- **Negative**:
   - Initial collection crawling requires Camoufox to handle dynamic Next.js scrolling and button clicks.
