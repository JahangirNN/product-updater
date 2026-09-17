# Store Knowledge Base: COACH

> **Purpose**: Document all website-specific quirks, URL query parameter patterns, DOM structures, API shortcuts, and lessons learned for Coach (`coach.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: COACH
- **Store Slug**: `coach`
- **Primary Domain**: `https://www.coach.com`
- **Default Currency**: `USD` (Converted to `INR` whole rupees via `storage/forex.py`)
- **Vendor Name**: `COACH`

---

## 2. URL Filter & Query Patterns
- **Outlet Listing Base**: `https://www.coach.com/shop/outlet/{gender}/{category}`
- **Price Bounds Filter**: e.g. `?pmin=58&pmax=225`
- **Search URL**: `https://www.coach.com/search?q={query}&page={page}`
- **Style Group Filter**: e.g. `?styleGroup=Backpacks|Briefcases|Crossbody+Bags|Totes+and+Carryalls&index=0`
- **Pagination Mechanics**:
  - Initial server-side static HTML renders 16 products.
  - Clicking "Show More" or scrolling in a browser triggers client-side hydration fetching subsequent product batches.
  - In Camoufox headless browser, automated scrolling and clicking `button` with text "show more" effortlessly loads all items to match target counts.

---

## 3. PDP Data Extraction & Architecture
- **Platform**: Salesforce Commerce Cloud (SFCC Demandware) with Next.js hydration.
- **Bot Mitigation**: Akamai. Requires modern Chrome 133 headers (`get_browser_headers({'Accept': 'text/html'})`) with `follow_redirects=True`. Executes with HTTP 200 in sub-second to <9s without blocking.
- **Structured JSON-LD**:
  - Every PDP contains multiple `<script type="application/ld+json">` blocks.
  - `@type: "ProductGroup"` contains `hasVariant` array with individual style/color/size variants, each with `sku`, `name`, `color`, `size`, and `offers.availability` (`https://schema.org/InStock` vs `OutOfStock`).
  - `@type: "Product"` contains `description` with dimensions (e.g. `9 1/2" (L) x 6" (H) x 3" (W)`), materials, and primary offer.
  - Structured Quantitative values: `height`, `width`, `depth` in inches (`INH`), and `additionalProperty` containing `handleDrop` (e.g. `Detachable handle with 8.5" drop`).
- **Media CDN**:
  - Adobe Scene7: `https://coach.scene7.com/is/image/Coach/{style}_{color}_a0`
  - Multi-angle views: `a0` (front), `a3` (angle), `a5` (back), `a6` (interior/top), `a8`, `a91`, `a92`.
- **Shoe Sizing & Variants**:
  - Shoes contain size buttons `<button class="variation-size" data-qa="cm_link_size_swatch_enbld">7</button>` vs `cm_link_size_swatch_dsbld`.
  - US shoe sizes map to UK sizes using official charts:
    - Men: US 7 -> UK 6.5, US 8 -> UK 7.5, US 9 -> UK 8.5, US 10 -> UK 9.5, US 11 -> UK 10.5, US 12 -> UK 11.5, US 13 -> UK 12.5.
    - Women: US 5 -> UK 3, US 6 -> UK 4, US 7 -> UK 5, US 8 -> UK 6, US 9 -> UK 7, US 10 -> UK 8, US 11 -> UK 9.

---

## 4. Delta Updater Fast Paths (Price & Stock)
- **Fast Path**: `httpx.get(pdp_url, headers=get_browser_headers({'Accept': 'text/html'}), follow_redirects=True)`.
- **Parsing**: Parse embedded JSON-LD `@type: "Product"` / `"ProductGroup"` for:
  - `offers.price`: Current USD price.
  - `offers.availability`: Overall stock (`InStock` vs `OutOfStock`).
  - Variant-level availability for individual shoe sizes and color options.
- **Delisted / 404 Behavior**: If delisted (HTTP 404 or redirect to category), preserve previous prices and stock state (ADR 0010).

---

## 5. Known Gotchas & Edge Cases
1. **Gotcha**: Combining multi-word queries in Coach search (e.g. `q=Nolita+teri`) without preceding session cookies can result in "0 Results".
   **Solution**: Crawl via Camoufox browser session, which establishes valid cookies and yields the exact 19 Nolita and Teri bag results.
2. **Gotcha**: Plain requests without modern Chrome user agent / client hints trip Akamai 403.
   **Solution**: Always use `storage.network.get_browser_headers()` or Camoufox.
3. **Gotcha**: Windows CP1252 stdout encoding error on fancy characters (e.g. smart quotes or bullet points).
   **Solution**: Ensure UTF-8 file encoding for all writes (`encoding="utf-8"`).

---

## 6. Multi-Color Variant Ingestion, Sizing Extraction & Filename Rules
- **Accessories & Bags (Colorway Ingestion)**:
  - Ingest multi-color variants directly from JSON-LD `ProductGroup.hasVariant`.
  - Bind individual Scene7 hero images (`a0`) per colorway.
  - Set option name strictly to `"Color"` (Shopify Option 1).
  - Map individual variant SKUs and distinct prices per colorway (capturing sale discounts per color).
- **Footwear (Sizing Ingestion)**:
  - Ingest size variants from HTML buttons (`variation-size` enabled/disabled).
  - Set option name strictly to `"Size"`.
  - Map US shoe sizes to official UK counterparts (e.g. `US 7 / UK 6.5`).
- **Structured Dimension Separation**:
  - Extract fractional inch dimensions (e.g. `4 1/2" (L) x 3 3/4" (H) x 1" (W)`) into dedicated `dimensions`.
  - Extract structured key-value measurements (e.g. `Length: 11.0"`, `Handle Drop: 8.5"`) into `measurements`.
- **Media Hygiene**:
  - Automatically filter out thumbnail swatches (`*_swatch*` and `swatch_*`) from the media gallery to preserve viewer visual quality.
- **ADR 0004 Filename Alignment**:
  - All files in `storage/db/coach/products/` must be named strictly `{product_id}.json` (`SHA256("coach::" + sku)[:16]`) to match the primary key and enable instant resolution by `load_product("coach", p_id)`.
- **Variant Delta Synchronization**:
  - In `stores/coach/delta.py`, synchronize both variant-level stock (`in_stock`) and variant-level pricing (`source_price` / `price`) when live Coach PDPs return `ProductGroup.hasVariant`.

