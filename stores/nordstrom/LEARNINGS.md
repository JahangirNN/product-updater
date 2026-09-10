# Store Knowledge Base: Nordstrom (On Shoes Collection)

> **Purpose**: Document retailer-specific quirks, query parameter mechanics, size conversion matrices, DOM structures, bot mitigation handling, and delta monitoring patterns for Nordstrom (`nordstrom.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: `Nordstrom`
- **Store Slug**: `nordstrom`
- **Primary Domain**: `https://www.nordstrom.com`
- **Brand Under Scope**: `On` (On Running athletic footwear)
- **Default Currency**: `USD` (Converted to whole `INR` rupees using cached daily exchange rate)
- **E-Commerce Architecture**: Single-Page App (React / Next.js) protected by Imperva / Incapsula anti-bot challenge.

---

## 2. URL Filter & Scope Boundaries
- **Target Collection URL**:
  `https://www.nordstrom.com/sr?origin=keywordsearch&keyword=on%20shoes&filterByBrand=on&filterByGenderAge=men&filterByGenderAge=unisex&filterByGenderAge=women`
- **Query Filters**:
  - `keyword=on shoes`
  - `filterByBrand=on`
  - `filterByGenderAge=men`
  - `filterByGenderAge=unisex`
  - `filterByGenderAge=women`
- **Pagination**:
  - Page 1: `...&page=1` (or omitted) yields ~70 items
  - Page 2: `...&page=2` yields remaining ~40 items
  - Total Catalog: 110 items (~108 unique product styles)
- **Scope Boundary**:
  - Footwear only (reject any apparel, socks, accessories, or clothing).
  - Size boundary: Strict requirement that products must offer **at least 7 distinct size variants** (`len(size_variants) >= 7`).
  - Products with fewer than 7 size variants (e.g. low-stock remnants with only 1 to 6 sizes left) are excluded.
  - For accepted products, all available sizes are stored, mapping each US size to its official UK and EU counterpart using the On shoe size conversion matrix.

---

## 3. On Shoes US -> UK / EU Size Conversion Reference
Derived directly from the official Nordstrom On shoe conversion guides:

### Women's Shoe Size Matrix
| US Size | UK Size | EU Size | BR Size | Japanese (CM) | Foot Length (Inches) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **5.0** | 3.0 | 36.0 | 33 | 22.0 | 8 5/8 |
| **5.5** | 3.5 | 36.5 | 34 | 22.5 | 8 3/4 |
| **6.0** | 4.0 | 37.0 | n/a | 23.0 | 9 |
| **6.5** | 4.5 | 37.5 | 35 | 23.5 | 9 1/8 |
| **7.0** | **5.0** | 38.0 | 36 | 24.0 | 9 1/4 |
| **7.5** | **5.5** | 38.5 | 37 | 24.5 | 9 1/2 |
| **8.0** | **6.0** | 39.0 | 38 | 25.0 | 9 5/8 |
| **8.5** | **6.5** | 40.0 | 39 | 25.5 | 9 3/4 |
| **9.0** | **7.0** | 40.5 | n/a | 26.0 | 10 |
| **9.5** | **7.5** | 41.0 | 40 | 26.5 | 10 1/8 |
| **10.0** | **8.0** | 42.0 | 41 | 27.0 | 10 1/4 |
| **10.5** | **8.5** | 42.5 | n/a | 27.5 | 10 1/2 |
| **11.0** | **9.0** | 43.0 | 42 | 28.0 | 10 5/8 |
| **11.5** | **9.5** | 44.0 | n/a | 28.5 | 10 3/4 |
| **12.0** | **10.0** | 44.5 | 43 | 29.0 | 11 |
| **12.5** | **10.5** | 45.0 | 44 | 29.5 | 11 1/8 |
| **13.0** | **11.0** | 46.0 | 45 | 30.0 | 11 1/4 |
| **14.0** | **11.5** | 47.0 | 46 | 30.5 | 11 1/2 |

### Men's Shoe Size Matrix
| US Size | UK Size | EU Size | BR Size | Japanese (CM) | Foot Length (Inches) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **7.0** | **6.5** | 40.0 | 37 | 25.0 | 9 5/8 |
| **7.5** | **7.0** | 40.5 | 38 | 25.5 | 9 3/4 |
| **8.0** | **7.5** | 41.0 | 39 | 26.0 | 10 |
| **8.5** | **8.0** | 42.0 | n/a | 26.5 | 10 1/8 |
| **9.0** | **8.5** | 42.5 | 40 | 27.0 | 10 1/4 |
| **9.5** | **9.0** | 43.0 | 41 | 27.5 | 10 1/2 |
| **10.0** | **9.5** | 44.0 | n/a | 28.0 | 10 5/8 |
| **10.5** | **10.0** | 44.5 | 42 | 28.5 | 10 3/4 |
| **11.0** | **10.5** | 45.0 | n/a | 29.0 | 11 |
| **11.5** | **11.0** | 46.0 | 43 | 29.5 | 11 1/8 |
| **12.0** | **11.5** | 47.0 | 44 | 30.0 | 11 1/4 |
| **12.5** | **12.0** | 47.5 | 45 | 30.5 | 11 1/2 |
| **13.0** | **12.5** | 48.0 | 46 | 31.0 | 11 5/8 |
| **14.0** | **13.5** | 49.0 | 43 | 31.5 | 12 |

---

## 4. Ingestion & Extraction Architecture (Tier 1)
- **Anti-Bot Circumvention**: Nordstrom serves an Imperva JavaScript challenge (`istlWasHere`) on headless non-browser connections. Firecrawl executes the JavaScript runtime and extracts the rendered DOM.
- **Firecrawl Extraction**:
  - Uses `jsonOptions` with structured schema to extract product title, brand, gender, current price, regular price, available colors, available sizes, materials, and media galleries.
- **Size Guide Accordion (ADR 0006)**:
  - Formats `<details class="size-guide-accordion">` with custom shoe conversion table (US $\to$ UK $\to$ EU) tailored to the shoe gender.
- **Primary Key**:
  `SHA256("nordstrom::" + source_sku)[:16]`

---

## 5. Delta Checking & Polling (Tier 2)
- **Monitoring Strategy**:
  - Outbound requests acquire per-store rate permits (2.0 req/s, 0.5s delay).
  - Trips circuit breaker on HTTP 429.
  - On HTTP 404 delisting, previous prices and availability are preserved.
  - Selective stamping: `last_verified_at` stamped strictly on `success` or `not_found`.
