# ADR 0012: Michael Kors Store Onboarding, SFCC Demandware Ingestion & Multi-Category Pipeline Architecture

## Status
Accepted

## Date
2026-09-12

## Context
As part of expanding the dropship catalog, the project scaled from mono-category stores (JW PEI Handbags, Nordstrom On Footwear) to a major multi-category luxury flagship store: **Michael Kors** (`michaelkors.com`).

The target scope encompassed 9 distinct collection links spanning women's and men's departments (Handbags, Wallets, Sneakers, Flats, Sandals, Sunglasses, Belts) with a cumulative expectation of 565 target items listed across pages.

Onboarding Michael Kors introduced technical requirements unique to Salesforce Commerce Cloud (SFCC / Demandware):
1. **Demandware Geolocation & International Redirects**: Requests originating from non-US IP addresses receive HTTP 302 redirects to localized international storefronts (e.g. `michaelkors.global/in/en/`), presenting inflated local pricing and altered catalogs. Setting Firecrawl scraping location to `{"country": "US"}` reliably pinned sessions to the US flagship store (`Sites-mk_us-Site/en_US`).
2. **Demandware Pagination Optimization**: SFCC collection grids paginate using `start` (offset) and `sz` (page size), defaulting to `sz=24`. By programmatically escalating to `sz=100`, page discovery was compressed from 28 roundtrips to 11 pages, successfully harvesting 657 category occurrences reconciling to 530 unique products (100% discovery rate).
3. **Hyphenated and Alphanumeric Style Codes**: While bags and shoes use alphanumeric SKUs (e.g., `30S3GLSS3L`), accessories such as sunglasses utilize hyphenated codes (e.g., `MK-1160`, `MK-2275BU`). Regex parsers required extension from `[A-Z0-9]+` to `[A-Z0-9\-]+` to prevent SKU truncation.
4. **Header Banner Carousel Price Trap**: Michael Kors PDPs display a top announcement carousel ("Hamilton Moderne ... Now $199.50") preceding the product's primary markdown heading (`# {Title}`). Naive price extraction captured the promotional banner price rather than the PDP product price. Price regex had to be anchored strictly within the markdown section under the `# {Title}` element.
5. **Multi-Category Hierarchy & Size Guide Accordions**: Unlike single-domain catalogs, Michael Kors spans multiple distinct sizing frameworks: shoe conversions (US/UK/EU), belt ranges (S/M/L/XL waist inch spans), sunglasses, wallets, and handbags. Each category requires dedicated Shopify-compatible variants and size guide accordions per ADR 0006.
6. **Zero-Cost Stealth Freshness**: Ongoing delta freshness checks require bypassing Demandware bot mitigation without incurring recurring commercial API costs.

## Decision

1. **Pure Functional Ingestion Architecture ([`stores/michaelkors/inflow.py`](../../stores/michaelkors/inflow.py))**:
   - Strictly followed ADR 0005 with zero OOP classes or object-oriented state.
   - `resolve_category()` resolves true product category (`Handbags`, `Wallets`, `Sneakers`, `Flats`, `Sandals`, `Sunglasses`, `Belts`, `Shoes`) via keyword matching on title and handle.
   - `clean_title()` strips promotional keywords ("wishlist", "buy now", "add to bag").
   - `extract_color_from_title()` cleanly decouples color names from product titles.
   - `generate_size_guide_accordion()` produces Shopify `<details class="size-guide-accordion">` tables tailored for footwear, belts, and luxury goods.
   - `build_variants()` constructs variant arrays with US/UK shoe sizes and belt dimensions.
   - Saved 530 canonical products atomically to `storage/db/michaelkors/products/{id}.json` using deterministic primary key `SHA256("michaelkors::" + sku.lower())[:16]`.

2. **Two-Tier Quality Audit**:
   - **Tier A (100% Static Audit)**: Verified all 530 products for primary key integrity, title sanitization, positive USD pricing, whole-rupee INR conversion (`storage/forex.py`), CDN image galleries, variant SKU consistency, and size guide HTML accordions. Zero anomalies detected.
   - **Tier B (Live Parity Audit on 20 Random Samples)**: Scraped 20 live PDPs via Firecrawl. Detected 6 genuine live shifts (e.g. Braided Belt on sale for $58 vs $248 regular price; 2 items sold out) and synced adjustments atomically to storage.

3. **Autonomous Stealth Delta Freshner ([`stores/michaelkors/delta.py`](../../stores/michaelkors/delta.py), [`stores/michaelkors/camoufox_solver.py`](../../stores/michaelkors/camoufox_solver.py))**:
   - Integrated Camoufox stealth browser session management with geolocation pinning.
   - Extracted live price and stock status in ~14 seconds per PDP with zero external API costs.
   - Integrated into [`config/delta_config.json`](../../config/delta_config.json) (`check_interval_minutes: 60`, `engine: "camoufox"`).
   - Generalized [`sync_catalog.py`](../../sync_catalog.py) to dynamically route multi-store stealth browser workers.

4. **Multi-Store Frontend Viewer Integration ([`scripts/export_viewer_data.py`](../../scripts/export_viewer_data.py))**:
   - Extended Level 1 (Store: "Michael Kors"), Level 2 (Groups: Handbags, Wallets, Sneakers, Flats, Sandals, Sunglasses, Belts, Shoes), and Level 3 (45 Subgroups) taxonomy.
   - Total catalog size expanded to 1,009 products (422 JW PEI, 57 Nordstrom, 530 Michael Kors).

## Consequences

- **Positive**:
  - **Comprehensive Multi-Category Expansion**: Successfully ingested and validated all 530 unique products across 9 Michael Kors collection categories with 100% data integrity.
  - **Zero Commercial API Dependency for Monitoring**: Hourly delta sweeps run locally and autonomously via Camoufox stealth browser.
  - **Granular Taxonomy**: End users can navigate Michael Kors by department, product category, and refined luxury silhouette.
  - **Full Documentation Alignment**: Maintains strict conformity with ADR 0001–0011, JSON Storage Spec, and Shopify integration standards.
- **Negative**:
  - SFCC Demandware pages are asset-heavy; headless browser rendering takes ~14s per item, requiring conservative concurrency (1 worker, 1.5s delay) during sweeps.
