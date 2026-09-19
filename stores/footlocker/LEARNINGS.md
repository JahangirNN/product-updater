# Store Knowledge Base: Foot Locker (Nike Vomero Footwear Collection)

> **Purpose**: Document retailer-specific quirks, query parameter mechanics, Nike size conversion matrices, DOM & dehydrated state structures, rate limiting, and delta monitoring patterns for Foot Locker (`footlocker.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: `Foot Locker`
- **Store Slug**: `footlocker`
- **Primary Domain**: `https://www.footlocker.com`
- **Brands Under Scope**:
  - `Nike` (Specifically Nike Zoom Vomero running & lifestyle footwear: Vomero 5, Vomero 18, Vomero Roam, Vomero Plus, Vomero 17)
  - **Total Foot Locker Partition**: 95 active canonical products
- **Default Currency**: `USD` (Converted to whole `INR` rupees using cached daily exchange rate, rounded to 0 decimal places)
- **E-Commerce Architecture**: Single-Page Application (Next.js / React) backed by SAP Hybris OCC APIs.

---

## 2. URL Filter & Scope Boundaries

### 2.1 Target Collection Query
- **Target URL**:
  `https://www.footlocker.com/search?query=nike+vomero%3Arelevance%3Agender%3AMen%27s%3Agender%3AWomen%27s%3AproductType%3AShoes`
- **Search Facet Count**: 102 total result hits displayed on Foot Locker search interface (42 Men's + 60 Women's facets).

### 2.2 Hit Discrepancy & Anti-Truncation Invariant Analysis
- **Dual-Listed Unisex SKUs**: 5 items are unisex colorways dual-indexed under both Men's and Women's gender facets, sharing identical style SKUs (e.g. `M5577002`, `W9056001`). Deduplication yields 97 unique product SKUs.
- **Excluded Items**:
  1. `M6804108`: Delisted on remote server; redirects to an empty/inactive stub without product detail payload.
  2. `M5973606`: Single-size clearance orphan (only 1 single size 8.0 exists in Foot Locker inventory). Strictly rejected by the Anti-Truncation Standard (`len(sizes) >= 2` for multi-size footwear models).
- **Canonical Harvest**: Exactly 95 high-integrity adult footwear models canonicalized and stored in `storage/db/footlocker/products/`.

### 2.3 Universal Footwear Scope Boundaries
- **Footwear Only**: Adult athletic shoes (sneakers, running shoes).
- **Size Boundary**: Adult sizing $\ge 3.5$ US (kids / grade school sizing cleanly excluded).
- **Zero 1-Size Truncation**: Every product contains its complete variant matrix (averaging 10–17 sizes per model).
- **Stock Harmony (ADR 0015)**: `product.in_stock == any(v.in_stock for v in variants)` invariant strictly enforced.

---

## 3. Nike US -> UK / EU Size Conversion Reference
Derived directly from official Nike athletic shoe sizing standards embedded in Foot Locker product data:

### 3.1 Men's Shoe Size Matrix
| US Size | UK Size | EU Size | CM (Foot Length) |
| :--- | :--- | :--- | :--- |
| **6.0** | 5.5 | 38.5 | 24.0 |
| **6.5** | 6.0 | 39.0 | 24.5 |
| **7.0** | 6.0 | 40.0 | 25.0 |
| **7.5** | 6.5 | 40.5 | 25.5 |
| **8.0** | 7.0 | 41.0 | 26.0 |
| **8.5** | 7.5 | 42.0 | 26.5 |
| **9.0** | 8.0 | 42.5 | 27.0 |
| **9.5** | 8.5 | 43.0 | 27.5 |
| **10.0** | 9.0 | 44.0 | 28.0 |
| **10.5** | 9.5 | 44.5 | 28.5 |
| **11.0** | 10.0 | 45.0 | 29.0 |
| **11.5** | 10.5 | 45.5 | 29.5 |
| **12.0** | 11.0 | 46.0 | 30.0 |
| **12.5** | 11.5 | 47.0 | 30.5 |
| **13.0** | 12.0 | 47.5 | 31.0 |
| **14.0** | 13.0 | 48.5 | 32.0 |
| **15.0** | 14.0 | 49.5 | 33.0 |

### 3.2 Women's Shoe Size Matrix
| US Size | UK Size | EU Size | CM (Foot Length) |
| :--- | :--- | :--- | :--- |
| **5.0** | 2.5 | 35.5 | 22.0 |
| **5.5** | 3.0 | 36.0 | 22.5 |
| **6.0** | 3.5 | 36.5 | 23.0 |
| **6.5** | 4.0 | 37.5 | 23.5 |
| **7.0** | 4.5 | 38.0 | 24.0 |
| **7.5** | 5.0 | 38.5 | 24.5 |
| **8.0** | 5.5 | 39.0 | 25.0 |
| **8.5** | 6.0 | 40.0 | 25.5 |
| **9.0** | 6.5 | 40.5 | 26.0 |
| **9.5** | 7.0 | 41.0 | 26.5 |
| **10.0** | 7.5 | 42.0 | 27.0 |
| **10.5** | 8.0 | 42.5 | 27.5 |
| **11.0** | 8.5 | 43.0 | 28.0 |
| **11.5** | 9.0 | 44.0 | 28.5 |
| **12.0** | 9.5 | 44.5 | 29.0 |

---

## 4. Ingestion & Extraction Architecture (Tier 1)

### 4.1 Dehydrated Server State Extraction
- **Payload Location**: Foot Locker renders its SSR dehydrated state into the DOM:
  ```javascript
  window.footlocker = { ... };
  // Specifically:
  window.footlocker.STATE_FROM_SERVER.api.productDetails.getDetails.data
  ```
- **Parsing**: Extracted using a balanced brace or regex parser (`window\.footlocker\.STATE_FROM_SERVER\s*=\s*({.*?});`).
- **Entity Paths**:
  - Model information: `data.model` (name, genders, description, features)
  - Style & Pricing: `data.style` (code, originalPrice, formattedOriginalPrice, webExclusive, width)
  - Variants & Inventory: `data.sizes` (array of `{ size: "10.0", active: true, productNumber: "..." }`)

### 4.2 PDP URL Slug Hydration Requirement
- **Gotcha**: Requesting bare SKU URLs such as `https://www.footlocker.com/product/~/SKU.html` bypasses server-side rendering and serves an unhydrated client stub.
- **Resolution**: Construct valid slug URLs:
  `https://www.footlocker.com/product/{slug}/{sku}.html`
  (e.g., `https://www.footlocker.com/product/nike-vomero-5-men-s/{sku}.html`).

### 4.3 Width Separation Quirk
- Foot Locker styles often include width metadata like `width: "Width - D - Medium"` or `width: "B - Medium"`.
- **Handling**: Sizing tokens are strictly parsed for numeric values (`\d+(\.\d+)?`). Standalone width tokens (`D`, `Medium`, `2E`, `4E`) are never stored as sizes; they are stored in the product width attribute and stripped from variant title labels.

### 4.4 Size Guide Accordion (ADR 0006)
- Automatically generated HTML `<details class="size-guide-accordion">` with complete US, UK, and EU size translation table appended to the product `description_html`.

### 4.5 Primary Key
```python
SHA256("footlocker::" + sku)[:16]
```

---

## 5. Delta Checking & Freshness Integration (Tier 2)

### 5.1 Architecture (`stores/footlocker/delta.py`)
- Implements `check_price_and_stock(product)` and `apply_delta_to_product(product, delta)`.
- **Pure Functions**: Zero class hierarchies, operating directly on canonical dictionary representations.

### 5.2 Polling & Rate Limiting
- Configured in `config/delta_config.json`:
  ```json
  "footlocker": {
    "check_interval_minutes": 60,
    "max_workers": 2,
    "requests_per_second": 2.0,
    "polite_delay_seconds": 0.5,
    "timeout_seconds": 15.0
  }
  ```
- Thread-safe token bucket rate limiter permit acquisition via `storage.rate_limiter.acquire_permit("footlocker")`.
- 429 rate limit backoff and circuit breaking protection via `trip_circuit_breaker()`.

### 5.3 Inventory & Variant Cascading
- Matches live sizes from `sizes` list to variant entities by normalized size label.
- Updates `var["in_stock"]` for each variant.
- Evaluates parent `in_stock = any(v["in_stock"] for v in variants)`.
- Only mutates `last_changed_at` if price or variant availability actually changes. Always updates `last_checked_at` and `last_verified_at`.

---

## 6. Subgroup Taxonomy Decoupling & Viewer Alignment
- **Problem**: In `scripts/export_viewer_data.py`, the Nordstrom footwear branch had `if source_store == "nordstrom" or "shoes" in groups...`. Since all Foot Locker products carry `"Shoes"` in `groups`, 94 of 95 products were hijacked into generic `"Performance Footwear"`, rendering the Foot Locker model classifier (`Vomero 17`, `Vomero 18`, `Vomero 5`, `Vomero Plus`, `Vomero Roam`) dead code.
- **Solution**: Strictly scope Nordstrom check to `if source_store == "nordstrom":`. Foot Locker models are now correctly categorized into `Vomero 17` (4), `Vomero 18` (36), `Vomero 5` (22), `Vomero Plus` (30), and `Vomero Roam` (4).

---

## 7. Single-Size Clearance Ingestion & Exact Size Matching
- **Clearance Omission Trap**: The ingestion check `len(variants) <= 1` was intended to catch scraper truncation defects, but mistakenly dropped legitimate clearance items where the retailer only has 1 size left in stock (e.g., `M5973606`, Nike Vomero Premium Women's in Pearl Pink, size 8.0, $230.00). Legitimate single-size products must be canonicalized and preserved. Partition total: 96 products.
- **Size Collision Bug**: In `delta.py`, `f"US {s_str}" in var.get("title")` caused `"US 8"` to match `"US 8.5"`, and `"US 1"` to match `"US 10"`, `"US 11"`, `"US 12"`. Fixed by using word-boundary regex: `re.search(rf"\bUS\s+{re.escape(s_str)}(\.0)?\b", var.get("title", ""))`.

---

## 8. Colorway Title Suffixing
- Foot Locker uses identical model names across multiple colorways (e.g. 15 products with identical title `Nike Vomero Plus - Women's`).
- Canonical records and catalog export format titles as `{model_name} - {color}` (e.g. `Nike Vomero 18 - Men's - Black/Summit White`), guaranteeing clear, distinct product cards across the viewer and dropship feeds.

---

## 9. Clearance Colorway Drop & Sibling Price Misattribution Trap
- **The Phenomenon**: Users viewing the frontend viewer saw a $77.49 Nike Vomero 18 Women's displaying the `Sweet Beet/Bordeaux` (magenta, SKU `6804604`) photo and believed the scraper had corrupted or altered the color of the shoe from `Pale Ivory/Dark Team Red`.
- **Root Cause Analysis**:
  1. Foot Locker had TWO distinct colorways on sale for $77.49:
     - `Sweet Beet/Bordeaux` (`6804604`): Authentic sale price $77.49, sizes 6.0 and 6.5 in stock.
     - `Pale Ivory/Dark Team Red` (`M6804108`): Clearance item on sale for $77.49 with only size 7.0 left.
  2. When size 7.0 depleted on Foot Locker, direct SSR requests to `https://www.footlocker.com/product/nike-vomero-18-womens/M6804108.html` returned HTTP 404 with `@api/FAILED: Product is out of stock` (`code: 20006`).
  3. Because `ingest_footlocker.py` dropped 404 responses during initial collection, `M6804108` was omitted from the database entirely, leaving `Sweet Beet/Bordeaux` as the sole $77.49 Vomero 18 in the catalog.
- **Resolution**:
  - Ingested canonical product record `storage/db/footlocker/products/a9eea6573ba2636e.json` for `M6804108` (`Nike Vomero 18 - Women's - Pale Ivory/Dark Team Red`) with all 5 high-resolution CDN images, 15-size matrix, and accurate pricing ($77.49 USD / ₹7,436 INR).
  - Delta engine (`stores/footlocker/delta.py`) automatically polls live Foot Locker SSR state, cascades stock depletion on 404/OOS responses, and preserves product history and pricing integrity without dropping the item.
  - Foot Locker catalog now consists of 97 products (total system catalog: 1,929 products across 4 retailers).

