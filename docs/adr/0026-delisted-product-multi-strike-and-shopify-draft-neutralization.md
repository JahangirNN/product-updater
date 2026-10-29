# 0026. Delisted Product Multi-Strike Circuit & Automatic Shopify Draft Neutralization

## Status
Accepted

## Date
2026-10-10

## Context
In a live dropshipping catalog spanning 3,189 products across 7 partner retailers, source suppliers frequently retire, discontinue, or unpublish seasonal items.
Historically:
1. When a scraper encountered a 404 or redirect away from a discontinued product page, it frequently classified the result as a generic scraping `error`.
2. This left retired products frozen in an orphaned `in_stock` state on the local database and live on the Shopify storefront, exposing the store to out-of-stock orders and fulfillment failures.
3. Conversely, immediately unpublishing a product upon a single 404 response risked false-positive delistings caused by temporary supplier CDN hiccups, maintenance pages, or WAF blips.

A robust lifecycle management protocol was needed to accurately identify retired products, prevent false-positive churn, neutralize inventory, and hide them from the live Shopify storefront while maintaining a path for automatic restoration should the supplier restock.

## Decision
We implemented an intelligent, multi-strike delisting detection and neutralization pipeline:
1. **Explicit Delisting Classification in Solvers**: All store delta modules (`stores/{store}/delta.py`) explicitly distinguish permanent delistings from transient network/WAF errors:
   - Returning `status: "not_found"` and `availability: "out_of_stock"` on confirmed HTTP 404, soft-404 category redirects, or missing core product schemas.
   - Preserving `status: "rate_limited"` or `status: "error"` for HTTP 429, WAF blocks, or network timeouts without triggering delisting logic.
2. **Resilient Multi-Strike Hysteresis**: In `sync_catalog.py`, a consecutive delisting strike counter (`delist_strikes`) is maintained on the product record:
   - **Strike 1**: Increments `delist_strikes = 1`, logs a warning, and leaves Shopify status untouched to tolerate transient supplier hiccups.
   - **Strike 2+ (or confirmed hard HTTP 404)**: Confirms product delisting and executes automatic Shopify neutralization.
3. **Automated Shopify State Neutralization**:
   - All variant inventories are depleted: `inventoryQuantity: 0`, `inventoryPolicy: DENY`, `in_stock: false`.
   - Shopify product status is flipped from `ACTIVE` to `DRAFT`, immediately hiding the product from storefront navigation, collections, search results, and external feeds.
   - The operational tag `supplier-delisted` is attached.
   - Active fulfillment tags (`Ready to Ship`, `instant-ship`, `manual-instant-ship-active`) are stripped to prevent unauthorized ordering.
4. **Auto-Restock Recovery Loop**: If a subsequent scheduled sweep detects that the supplier has restored the product page:
   - Resets `delist_strikes = 0`.
   - Restores live variant inventory quantities.
   - Flips Shopify product status back to `ACTIVE`.
   - Removes the `supplier-delisted` tag.

## Consequences
### Positive
- **Zero Ghost Orders**: Customers can never purchase products that suppliers have retired.
- **Hysteresis Protection**: 2-strike requirement prevents temporary CDN drops from prematurely unpublishing valid merchandise.
- **Hands-Free Restocking**: Re-published supplier products automatically resume active status on Shopify without manual staff intervention.
- **Clean Storefront Search & Feeds**: Setting delisted items to `DRAFT` prevents dead PDPs from degrading SEO and search relevancy.

### Negative / Trade-Offs
- Catalog active counts decrease as seasonal items are retired, requiring ongoing monitoring via `scratch/analyze_staleness.py` and `docs/shopify/CATALOG_LEDGER.md`.
