# Store Knowledge Base: Michael Kors (SFCC Demandware)

> **Purpose**: Document all website-specific quirks, URL query parameter patterns, DOM structures, API shortcuts, and lessons learned for Michael Kors (`michaelkors.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: Michael Kors
- **Store Slug**: `michaelkors`
- **Primary Domain**: `https://www.michaelkors.com`
- **Platform**: Salesforce Commerce Cloud (SFCC / Demandware, `Sites-mk_us-Site/en_US`)
- **Default Currency**: `USD` (Converted to `INR` via whole-rupee math)
- **Primary Vendors**: `MICHAEL Michael Kors`, `Michael Kors Men's`

---

## 2. URL Filter & Query Patterns
*How does this store handle category filters, price bounds, sorting, and pagination in URLs?*

- **Category / Listing Base**:
  - Women Handbags: `/women/handbags/`
  - Women Wallets: `/women/wallets/`
  - Women Sneakers: `/women/shoes/sneakers/`
  - Women Flats: `/women/shoes/flats/`
  - Women Sandals: `/women/shoes/sandals/`
  - Women Sunglasses: `/women/accessories/sunglasses/`
  - Men Wallets: `/men/wallets/`
  - Men Shoes: `/men/shoes/`
  - Men Belts: `/men/accessories/belts/`
- **Pagination**: SFCC Demandware uses `start` (zero-based item offset) and `sz` (page size).
  - Default: `?start=0&sz=24`
  - Optimization: Escalate to `?start=0&sz=100` to fetch up to 100 items per request, reducing pagination calls by ~75%.
  - Subsequent pages: `?start=100&sz=100`, `?start=200&sz=100`, etc.
- **PDP URL Structure**: `https://www.michaelkors.com/{handle}/{sku}.html`
  - Example: `https://www.michaelkors.com/cherie-leather-sandal/40S6CHMS1L.html`

---

## 3. Ingestion & Firecrawl Notes
*Extraction strategies and scraping parameters for SFCC Demandware:*

- **Critical Geolocation Constraint**:
  - Demandware inspects client IP geolocation. Indian/international IPs receive HTTP 302 redirects to `https://michaelkors.global/in/en/`, presenting localized Indian pricing (₹35,000+) and different product catalogs.
  - **Requirement**: Always set `location: {"country": "US"}` in Firecrawl scrape parameters to reliably land on the US flagship store (`Sites-mk_us-Site/en_US`).
- **Listing Page Markdown Layout**:
  - Products appear as markdown links: `[Title](url)`.
  - Prices follow directly below the link in formats: `$XXX.XX` or `Was $XXX.XX Now $YY.YY`.
- **SKU Format Diversity**:
  - Bags, Footwear, Belts, and Small Goods: Alphanumeric 10-character codes (e.g. `30F6T14C9I`, `40S6CHMS1L`, `36H4LBLY1O`).
  - Sunglasses & Eyewear: Hyphenated style codes (e.g. `MK-1160`, `MK-2275BU`).
  - **Regex Requirement**: Must use `r'[A-Z0-9\-]+'` instead of `r'[A-Z0-9]+'`.
- **High-Resolution CDN Images**:
  - Image host: `michaelkors.scene7.com/is/image/MichaelKors/`.
  - Demandware dynamically resizes Scene7 URLs via query params: `?wid=558&hei=747&op_sharpen=1`.
  - Clean URL regex: `r'https://michaelkors\.scene7\.com/is/image/MichaelKors/[A-Za-z0-9_\-]+'`.
  - Avoid base64 thumbnail placeholders.

---

## 4. Delta Updater Fast Paths (Price & Stock)
*How we check price, overall availability, and per-variant size stock in milliseconds / zero external cost:*

- **Primary Fast-Path**: Native SFCC Demandware AJAX Variation API (`stores/michaelkors/delta.py`).
  - **Endpoint**: `https://www.michaelkors.com/on/demandware.store/Sites-mk_us-Site/en_US/Product-Variation?pid={sku}&format=ajax`
  - **TLS Fingerprint**: `curl_cffi` with `impersonate="chrome120"` completely bypasses Akamai Bot Manager while providing sub-second (~400ms) execution.
  - **Zero Geolocation Trap**: Explicit `Sites-mk_us-Site/en_US` query parameter forces US storefront response, completely eliminating the international 302 redirect to `michaelkors.global/in/en/`.
  - **Per-Variant Size Stock Resolution**:
    - Inspects `variationAttributes` for `displayName == "Size"` (or `"Waist"`, `"Length"`).
    - Checks `selectable: True` (in stock) vs `selectable: False` (sold out) for each size value (e.g. `5`, `6`, `8.5`, `34`).
    - Maps each variant by option values, SKU suffix (`-6`), or title, updating `var["in_stock"]` dynamically.
- **Fallback Engine**: Local Camoufox stealth browser (`stores/michaelkors/camoufox_solver.py`).
  - Runs Firefox C++ stealth rendering if HTTP client fails.
  - Uses the same SFCC variation endpoint or anchors PDP price searches strictly under product headings `# {Title}` to avoid header promotional carousels.

---

## 5. Known Gotchas & Edge Cases
*Specific traps encountered and how they were resolved:*

1. **Header Carousel Markdown Price Trap**:
   - *Trap*: SFCC PDPs render a global header promotional announcement banner (`"Hamilton Moderne ... Now $199.50"`) at the top of the DOM. A naive page-wide regex for `$XXX` matched the promotional carousel item rather than the actual PDP product.
   - *Solution*: Anchor price regex strictly under the primary product heading `# {Title}` in the markdown output.
2. **Carousel Recommendations Leaking into Specific Category Collections**:
   - *Trap*: On category collection pages with few items (e.g. Men's Belts with 13 target items), Demandware injects editorial carousels ("You Might Also Like") containing handbags and boots.
   - *Solution*: Use `resolve_category()` based on title and handle keywords rather than trusting the collection URL's fallback category blindly.
3. **Internal Test Products with Numeric Titles**:
   - *Trap*: Style `30F6T14C9I` was listed on the women's handbags page with title `"0"`.
   - *Solution*: Tier A audit flagged single-character titles. Deep PDP scrape revealed the true title: `Goldie Faux Fur Clutch`.
4. **Demandware URL Query Case Sensitivity**:
   - *Trap*: Query parameters `start` and `sz` must be lowercase. Using uppercase `SZ` or `START` is ignored by SFCC and returns default 24 items.

---

## 6. Elimination of Phantom Transitions & Decoupled Variant Deltas
- **The Phantom Delta Trap**:
  - Previously, `stock_changed = (curr_avail != old_availability) or variant_stock_changed`.
  - When a product stayed in stock at the parent level while 1 size sold out, `stock_changed` was set to `True`, triggering a redundant `in_stock -> in_stock` event in logs and delta queues.
- **Resolution (ADR 0015)**:
  - Decoupled parent stock transitions (`stock_changed = (curr_avail != old_availability)`) from variant transitions (`variant_stock_changed = True`).
  - Implemented granular `changed_variants` tracking with `{sku, old_in_stock, new_in_stock}`.
  - In `apply_delta_to_product()`, mutations are triggered if `price_changed or stock_changed or variant_stock_changed`, ensuring accurate Shopify sync triggers with 0 phantom noise.

