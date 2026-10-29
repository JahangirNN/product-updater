# Store Knowledge Base: KATE SPADE OUTLET

> **Purpose**: Document all website-specific quirks, URL query parameter patterns, DOM structures, API shortcuts, and lessons learned for Kate Spade Outlet (`katespadeoutlet.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: Kate Spade Outlet
- **Store Slug**: `katespade`
- **Primary Domain**: `https://www.katespadeoutlet.com`
- **Default Currency**: `USD` (Converted to `INR` whole rupees via `storage/forex.py`)
- **Vendor Name**: `Kate Spade`
- **Parent Company**: Tapestry, Inc. (Shares architecture with Coach)

---

## 2. URL Filter & Query Patterns
- **Search Base**: `https://www.katespadeoutlet.com/search?q={query}`
- **Price Bounds Filter**: e.g. `&pmin=58&pmax=200`
- **Category Base**: `https://www.katespadeoutlet.com/handbags/{category}`
- **Pagination Mechanics**:
  - Initial server-side static SSR HTML renders the first 8-16 products.
  - Page is a Next.js App Router (RSC) client-side application.
  - In Camoufox stealth browser, automated scrolling and triggering "Show More" buttons dynamically hydronates subsequent product tiles to match exact catalog counts (429 items for Handbags under $200).

---

## 3. PDP Data Extraction & Architecture
- **Platform**: Salesforce Commerce Cloud (SFCC Demandware) with Next.js App Router.
- **Bot Mitigation**: Akamai. Requires modern Chrome browser-grade headers (`Accept: text/html...`, `impersonate='chrome124'`). Executes with HTTP 200 in sub-second latency (~600–900ms) without headless browser overhead.
- **Structured JSON-LD**:
  - Every PDP contains multiple `<script type="application/ld+json">` blocks.
  - `@type: "ProductGroup"` contains `hasVariant` array with individual colorway variants, each with:
    - `sku`: Variant SKU (e.g. `KP079 BLK`, `KP079 VKS`, `KP079 UVD`).
    - `name`: Variant title.
    - `color`: Exact colorway name (e.g. `Black`, `Meringue`, `Hot Fudge`).
    - `image`: Array of Adobe Scene7 images specific to that colorway (`KP079_001`, `KP079_001_1`, `KP079_001_3`).
    - `offers.price`: USD price (supporting colorway-specific discount pricing).
    - `offers.availability`: Overall stock (`https://schema.org/InStock` vs `OutOfStock`).
  - `@type: "Product"` contains `description`, base style code, and product material.
- **Specifications & Measurements**:
  - Rendered in `.product-props__details` sections:
    - `Style Number`: e.g. `KP079`
    - `Measurements`: `Length: 6.5"`, `Height: 4.5"`, `Width: 2.5"`
    - `Strap / Handle`: `Adjustible, removable crossbody strap with 22" drop`
    - `Materials`: `Coated Canvas`, `Saffiano leather`, `Gold hardware`, `Lining: fabric`
    - `Features`: `Exterior: 2 zip pockets`, `Interior: 2 card slots`, `Zip closure`, `Fits most large phones, most small wallets`
- **Media CDN**:
  - Adobe Scene7: `https://katespade.scene7.com/is/image/KateSpade/{style}_{color_code}`
  - High-res multi-angle views: standard, `_1`, `_2`, `_3`.
  - Strictly filter out swatches (`_swatch`, `swatch_`).

---

## 4. Delta Updater Fast Paths (Price & Stock)
- **Fast Path**: `curl_cffi` / `httpx.get(pdp_url, headers=DEFAULT_HEADERS, timeout=15.0)`.
- **Parsing**: Parse embedded JSON-LD `@type: "ProductGroup"` / `"Product"`:
  - `offers.price`: Current USD price.
  - `offers.availability`: Overall stock (`InStock` vs `OutOfStock`).
  - Variant-level availability and pricing for each colorway.
- **Delisted / 404 Behavior**: If delisted (HTTP 404 or redirect), preserve previous prices and stock state (ADR 0010, ADR 0026).

---

## 5. Multi-Color Variant Ingestion Rules
- **Colorway Ingestion**:
  - Ingest multi-color variants directly from JSON-LD `ProductGroup.hasVariant`.
  - Bind individual Scene7 hero images (`KP079_001`) per colorway.
  - Set option name strictly to `"Color"` (Shopify Option 1).
  - Map individual variant SKUs and distinct prices per colorway.
- **Structured Dimension Separation**:
  - Extract fractional inch dimensions (e.g. `6.5" (L) x 4.5" (H) x 2.5" (W)`) into dedicated `dimensions`.
  - Extract structured key-value measurements (e.g. `Handle Drop: 5.0"`, `Strap Drop: 22.0"`) into `measurements`.
- **Media Hygiene**:
  - Automatically filter out thumbnail swatches (`*_swatch*` and `swatch_*`) from the media gallery.
- **ADR 0004 Filename Alignment**:
  - All files in `storage/db/katespade/products/` must be named strictly `{product_id}.json` (`SHA256("katespade::" + sku)[:16]`) to match the primary key and enable instant resolution by `load_product("katespade", p_id)`.
- **Variant Delta Synchronization**:
  - In `stores/katespade/delta.py`, synchronize both variant-level stock (`in_stock`) and variant-level pricing (`source_price` / `price`).
