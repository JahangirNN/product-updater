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
*How we check price and stock in milliseconds / zero external cost:*

- **Engine**: Local Camoufox stealth browser (`stores/michaelkors/camoufox_solver.py`).
  - Demandware employs Akamai / Cloudflare bot mitigation that blocks standard headless HTTP requests.
  - Camoufox runs Firefox C++ stealth rendering with US geolocation coordinates (`latitude: 40.7128, longitude: -74.0060`, timezone: `America/New_York`).
  - Typical PDP execution latency: ~14.5 seconds.
- **DOM Selectors**:
  - Price: `.price-sales, .sales .value, [data-qa="product-price"], .price, .product-price`
  - Stock / Availability:
    - In Stock: `button[data-qa="add-to-bag"]:not([disabled])`, `button.add-to-cart:not([disabled])`
    - Sold Out: `button[disabled]`, text matching `"Sold Out"`, `"Out of Stock"`
  - Delisted / 404: Page title containing `"Page Not Found"`, `"Product Unavailable"`, or redirection to 404 error page.

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
