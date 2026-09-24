# ADR 0020: Shopify Catalog Taxonomy, Field Distribution & Real-Time Sync Bridge

## Status
Accepted

## Date
2026-09-24

## Context
We need a systematic, zero-leakage method to map our local database of 3,189 luxury products into Shopify (*The Rare Avenue*, `hewmvw-am.myshopify.com`), organize products into consumer-facing luxury collections, and establish a live bridge with our 1-hour delta freshner daemon.

## Decisions

### 1. Zero Retailer Leakage Invariant
- Never expose internal supplier store names (`jdsports`, `nordstrom`, `footlocker`, `jomashop`, etc.) in product titles, tags, descriptions, URLs, or metadata.
- `vendor` MUST be set exclusively to the authentic designer brand name (e.g. `Versace`, `Tissot`, `COACH`, `Salomon`, `On Running`, `Michael Kors`, `JW PEI`).

### 2. Standardized Field Distribution (`productSet` Mapping)
Each local product record maps to Shopify GraphQL `ProductSetInput`:
- `title`: Clean, brand-standard product title.
- `vendor`: Authentic luxury designer brand.
- `productType`: Canonical category (`Watches`, `Handbags`, `Shoulder Bags`, `Shoes`, `Sneakers`, `Wallets`).
- `descriptionHtml`: Rich HTML overview + technical specifications table + interactive `<details class="size-guide-accordion">` table.
- `tags`: Standardized taxonomy tags (`Gender:Men`, `Gender:Women`, `Brand:Versace`, `Watches`, `Luxury Watches`).
- `variants`:
  - `sku`: Prefix formatted (e.g. `RARE-{source_sku}`).
  - `price`: Whole-rupee INR price formatted with `.00` (e.g. `"38280.00"`).
  - `compareAtPrice`: Converted from USD MSRP with whole-rupee INR math (e.g. `"95500.00"`).
  - `optionValues`: Exact attribute pairing (e.g. `optionName: "Case Diameter"`, `name: "42 mm"`).
  - `inventoryPolicy`: `DENY` (prevent overselling out-of-stock items).
  - `inventoryItem`: Tracked with Shopify inventory management.
- `files`: High-resolution product images uploaded directly to Shopify CDN.

### 3. Automated Smart Collection Taxonomy
Collections on *The Rare Avenue* are managed via automated GraphQL rules:
1. **Departments**:
   - `Men`: `tag EQUALS Gender:Men` OR `tag EQUALS Gender:Unisex`
   - `Women`: `tag EQUALS Gender:Women` OR `tag EQUALS Gender:Unisex`
2. **Product Categories**:
   - `Luxury Watches`: `product_type EQUALS Watches`
   - `Designer Bags`: `product_type IN (Handbags, Shoulder Bags, Tote Bags, Crossbody)`
   - `Premium Footwear`: `product_type IN (Shoes, Sneakers, Athletic Shoes)`
   - `Wallets & Small Leather Goods`: `product_type IN (Wallets, Cardholders)`
3. **Brand Showrooms**:
   - Automated by `vendor EQUALS {BrandName}` (e.g. `Versace`, `Tissot`, `COACH`, `Salomon`).

### 4. Real-Time Delta Synchronization Contract
- When the 1-hour freshner daemon detects a price shift (> $0.01) or availability flip:
  1. Recalculates whole-rupee INR math.
  2. Dispatches `productSet` / `inventorySetQuantities` mutation to Shopify.
  3. Updates Shopify product status (`ACTIVE` if in stock, `out_of_stock` inventory quantity `0`).
  4. Appends audit record to `storage/db/history/delta_events.jsonl`.

## Consequences
- Clean, luxury customer presentation with zero retailer leakage.
- Automated collection assignment without manual merchandising overhead.
- Deterministic, whole-rupee pricing across all variants.
