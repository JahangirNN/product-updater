# ADR 0021: Distributed Shopify Connector & Real-Time Sync Architecture

## Status
Accepted

## Date
2026-09-25

## Context
Following the successful ingestion of all 574 luxury watches, the catalog required a robust, distributed connector architecture to ingest and synchronize the remaining ~90% of products (2,615 products across JW PEI, COACH, Michael Kors, Nordstrom, Foot Locker, and JD Sports) into Shopify (*The Rare Avenue*, `hewmvw-am.myshopify.com`).

Key architectural challenges included:
1. Multi-store brand name resolution without exposing upstream retailer scraper identities (Zero Retailer Leakage).
2. Heterogeneous product variant structures across shoes (numerical sizes), bags (colors / one size), and watches (case diameters), including handling scraped duplicates.
3. Declarative, idempotent Shopify smart collection provisioning across master departments, categories, and brand showrooms.
4. Seamless integration with the 1-hour background delta freshner daemon for instant price and stock shift propagation, paired with an offline queue drainer for network resilience.

## Decisions

### 1. Unified Taxonomy & Schema Normalizer (`storage/shopify_taxonomy.py`)
- Standardizes all 7 dropship stores into compliant Shopify GraphQL `ProductSetInput` payloads.
- **Zero Retailer Leakage**: Resolves authentic luxury designer brands (`JW PEI`, `COACH`, `MICHAEL Michael Kors`, `Salomon`, `On`, `HOKA`, `Nike`, `adidas`, `ASICS`, `Jordan`, `Tissot`, `Citizen`, `Movado`, `Seiko`, `Versace`, `Ferragamo`). All upstream supplier names (`jomashop`, `nordstrom`, `footlocker`, `finishline`, `jdsports`) are scrubbed from vendor, tags, and HTML.
- **Tri-Field Whole-Rupee INR Math**: Strictly enforces 0 fractional paise (`round(usd * rate)`) ending in `.00`.
- **Variant De-duplication**: De-duplicates raw variants sharing identical option values (e.g. duplicate scraped color names), prioritizing in-stock variants to satisfy Shopify's uniqueness requirement.

### 2. Declarative Smart Collection Provisioner (`storage/shopify_collections.py`)
- Manifest-driven collection provisioning with automated ruleSets:
  - **Master Categories**: `Luxury Watches` (`/collections/luxury-watches`), `Designer Bags` (`/collections/designer-bags`), `Premium Footwear` (`/collections/premium-footwear`), `Wallets & Accessories` (`/collections/wallets-accessories`).
  - **Gender Sub-Categories**: `Men's Watches`, `Women's Watches`, `Women's Handbags`, `Men's Bags`, `Men's Shoes`, `Women's Shoes`.
  - **Brand Showrooms**: 17 dedicated designer collections across all catalog brands.
- Idempotent execution: Queries existing store collections by handle, creating only missing collections via `collectionCreate`.

### 3. High-Throughput Bulk Catalog Ingestor (`scripts/shopify_bulk_uploader.py`)
- High-throughput CLI uploader supporting `--store`, `--category`, `--limit`, `--dry-run`, and `--delay` pacing (0.3s inter-request delay).
- Stamping mechanism: Writes `shopify_product_id`, `shopify_handle`, and `shopify_synced_at` back to partitioned product files on disk and rebuilds `storage/db/index.json`.

### 4. Real-Time Delta Bridge & Queue Drainer (`storage/shopify_sync.py`)
- `sync_delta_to_shopify`: Called by `sync_catalog.py` on any detected price or availability shift to mutate Shopify Admin GraphQL instantly.
- `drain_delta_events_queue`: Offline recovery function that sweeps `storage/db/history/delta_events.jsonl` for events with `shopify_sync_pending = True` and synchronizes them to Shopify.

## Consequences
- **Modular & Distributed**: Any new store or category can be onboarded immediately by adding its mapping to `shopify_taxonomy.py` and `shopify_collections.py`.
- **Zero Retailer Leaks**: Upstream scrapers operate invisibly behind the authentic luxury brand identity.
- **Resilient Delta Synchronization**: Both live daemon execution and offline queue recovery are supported without dropped price or stock shifts.
