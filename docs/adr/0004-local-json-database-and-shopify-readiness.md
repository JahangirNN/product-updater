# ADR 0004: Local JSON Database & Shopify Readiness Validation

## Status
Accepted

## Date
2026-09-09

## Context
The project operates with targeted product catalogs (hundreds to low thousands of curated products) rather than vast tens-of-thousands scraped catalogs. Running a full relational database server (like PostgreSQL) introduces external daemon dependencies, port conflicts, and backup complexity.

Additionally, scraped products are intended for Shopify synchronization. Attempting to push incomplete scraped data to Shopify causes API rejection or degraded storefront listings.

## Decision
1. **Local JSON Database**:
   - We will implement a file-based JSON storage room with an in-memory index for fast lookup and deduplication.
   - Products are uniquely identified by a composite hash of `(normalized_domain, normalized_sku)`.
2. **Shopify Readiness Validator**:
   - Every product ingested via Firecrawl will pass through a strict Shopify Readiness Validator.
   - The validator outputs a warning score and flag list (`missing_material`, `missing_images`, `invalid_compare_price`).
   - Products with critical errors will be marked as `status: DRAFT` to protect the Shopify store.

## Consequences
- **Positive**: Lightweight, zero daemon setup, fully portable, transparent Git-friendly storage, pre-validates data before hitting Shopify.
- **Negative**: File I/O must be written atomically to prevent file corruption during sudden interruptions.
