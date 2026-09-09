# Store Knowledge Base: JW PEI

> **Purpose**: Document all website-specific quirks, URL query parameter patterns, DOM structures, API shortcuts, and lessons learned for JW PEI (`jwpei.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: `JW PEI`
- **Store Slug**: `jwpei`
- **Primary Domain**: `https://www.jwpei.com`
- **Default Currency**: `USD` (Converted to `INR` at runtime using daily cached exchange rate)
- **E-Commerce Platform**: Shopify

---

## 2. URL Filter & Query Patterns
How JW PEI handles category filters, price bounds, sorting, and pagination in URLs:

- **Category / Listing Base**: `https://www.jwpei.com/collections/handbags`
- **Price Bound Filter**:
  - `filter.v.price.gte=` (minimum price)
  - `filter.v.price.lte=150.00` (maximum price, e.g. $150.00 USD)
- **Color Filters**:
  - JW PEI uses Shopify Metaobject swatch IDs for color filtering:
    `filter.p.m.custom.color_filter_swatch=gid%3A%2F%2Fshopify%2FMetaobject%2F<ID>`
  - Multiple swatches are combined as repeated query parameters.
- **Sorting**: `sort_by=best-selling` (also supports `manual`, `price-ascending`, `price-descending`, `created-descending`).
- **Pagination**: `page=1`, `page=2`, ... `page=9`.
- **Full Category Filter Pattern**:
  ```
  https://www.jwpei.com/collections/handbags?filter.p.m.custom.color_filter_swatch=gid%3A%2F%2Fshopify%2FMetaobject%2F75222777890&...&filter.v.price.lte=150.00&sort_by=best-selling&page=1
  ```

---

## 3. Product Architecture & Ingestion Notes
- **Colorway / Variant Structure**:
  - JW PEI treats each colorway as its own distinct product handle (e.g. `thea-top-handle-bag-dark-olive`, `thea-top-handle-bag-black`).
  - In each product, there is 1 primary variant (`Default Title`) with a unique SKU (e.g. `2T78-7`).
  - Color name is extracted cleanly from the product title (e.g. `Thea Top Handle Bag - Dark Olive` $\to$ Color: `Dark Olive`).
- **Media & High-Res Images**:
  - The `/products/{handle}.json` endpoint returns the complete `images` array containing all 5–8 high-resolution product photos.
  - Image URLs are on Shopify CDN (`cdn.shopify.com/s/files/...`) with parameters like `?v=...`.
- **Enrichment Details & Specifications**:
  - Specifications are embedded in `body_html` inside `<ul><li>...</li></ul>` tags.
  - Extracted fields:
    - **Major Material**: e.g., `Vegan Leather`, `Polyester`, `Canvas`, `Croc-Embossed`
    - **Lining Material**: e.g., `Polyester`, `PU`
    - **Bag Dimensions**: e.g., `9.84" W x 5.51" H x 2.56" D (25cm x 14cm x 6.5cm)`
    - **Handle Drop**: e.g., `1.18" (3cm)`
    - **Shoulder Strap Drop**: e.g., `19.29" ~ 22.05" (49cm ~ 56cm)`
    - **Hardware**: e.g., `Gold Hardware`, `Silver Hardware`
    - **Closure / Disclosure**: e.g., `Magnetic Snap Closure`
    - **Compartments & Pockets**: e.g., `1 Interior Slit Pocket`, `1 Detachable and Adjustable Strap`
- **Shopify Size Guide Delivery**:
  - Dimensions and strap drop are converted into a responsive `<details><summary>📏 Size & Measurement Guide</summary>...</details>` table injected into `descriptionHtml` for universal theme compatibility.

---

## 4. Delta Updater Fast Paths (Price & Stock)
How we check price and stock in milliseconds without heavy HTML overhead:

- **Storefront AJAX Endpoint**: `https://www.jwpei.com/products/{handle}.js`
  - **Stock Status**: `data["available"]` is a boolean (`true` if in stock, `false` if sold out).
  - **Variant Stock**: `data["variants"][0]["available"]` provides per-variant stock.
  - **Price**: `data["price"]` (in cents USD, e.g. `9900` $\to$ `$99.00`).
  - **Compare-At Price**: `data["compare_at_price"]` (in cents USD).
  - **SKU**: `data["variants"][0]["sku"]`.
  - **Payload Size**: ~4 KB – 7 KB (compared to >1 MB for full PDP HTML).
  - **Latency**: Fast network roundtrip with 0 selector fragility.
- **Fallback Stock Check**:
  - HTML PDP contains Schema.org JSON-LD:
    - `http://schema.org/InStock`
    - `http://schema.org/OutOfStock`
- **Currency Fluctuation Guard**:
  - Compare `source_price` ($) against previous `source_price` to prevent daily forex exchange rate changes from triggering false price change alerts.

---

## 5. Known Gotchas & Edge Cases
1. **Trap**: The `/products/{handle}.json` endpoint omits `inventory_quantity` and sets `available` to None for anonymous requests.
   **Solution**: Use `/products/{handle}.js` which directly exposes `available: true/false` on the root product and on each variant.
2. **Trap**: JW PEI prices in `/products/{handle}.js` are returned in cents (`9900` for `$99.00`).
   **Solution**: Divide by 100.0 before performing forex conversion.
3. **Trap**: JW PEI Shopify HTML uses `<li data-mce-fragment="1">` with embedded `<span>` tags. Simple `<li>` regexes fail to extract specifications.
   **Solution**: Match `<li[^>]*>(.*?)</li>`, strip child HTML tags, unescape HTML entities, and normalize non-breaking spaces (`\xa0`, `&nbsp;`).
4. **Trap**: Windows PowerShell default console encoding (CP1252) crashes with `UnicodeEncodeError` when printing the Indian Rupee symbol (₹).
   **Solution**: Always reconfigure stdout via `sys.stdout.reconfigure(encoding='utf-8')` in CLI entrypoints.
5. **Trap**: Dual-Endpoint Harvest Synergy:
   - Calling `/products/{handle}.json` yields high-resolution image URLs and HTML descriptions with dimensions.
   - Calling `/products/{handle}.js` yields verified real-time stock availability and sub-100ms delta checking.
6. **Trap**: Dimension key variations across JW PEI catalog: 51.4% of products use `<li>Dimension: ...</li>` while others use `<li>Bag Dimensions: ...</li>` or `<li>Dimensions: ...</li>`.
   **Solution**: Check `specs.get("Bag Dimensions") or specs.get("Dimension") or specs.get("Dimensions")` and normalize into `specs["Bag Dimensions"]`.
7. **Trap**: Material key variations: Products with non-leather fabrics (Faux Suede, Canvas, Satin) frequently use `<li>Main Material: ...</li>` rather than `Major Material`.
   **Solution**: Check `specs.get("Material") or specs.get("Major Material") or specs.get("Main Material")`.
8. **Trap**: Loose whitespace before inch quotes (e.g. `1.18 " (3cm)`).
   **Solution**: Sanitize typography using `re.sub(r'\s+"', '"', val.strip())`.
9. **Live Restock & Delta Pacing Benchmark**:
   - During live delta verification, product `mini-abacus-hs` transitioned from `out_of_stock` to `in_stock` (`available: true`, `$139.00 USD`), proving real-time availability shift detection.
   - Pacing benchmark: Running `sync_catalog.py` with 3 worker threads and 80ms polite delays achieves ~250–320ms average request latency with zero HTTP 429 rate limit drops across the entire 288-product catalog.

