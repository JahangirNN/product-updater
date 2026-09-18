# Store Knowledge Base: Nordstrom (On, HOKA & Salomon Footwear Collections)

> **Purpose**: Document retailer-specific quirks, query parameter mechanics, size conversion matrices, DOM structures, bot mitigation handling, and delta monitoring patterns for Nordstrom (`nordstrom.com`).

---

## 1. Store Overview & Domain Identity
- **Store Name**: `Nordstrom`
- **Store Slug**: `nordstrom`
- **Primary Domain**: `https://www.nordstrom.com`
- **Brands Under Scope**:
  - `On` (On Running athletic footwear: 93 styles)
  - `HOKA` (Hoka maximum-cushioned footwear: 89 styles)
  - `Salomon` (Salomon technical trail and outdoor footwear: 56 styles)
  - **Total Nordstrom Partition**: 238 styles
- **Default Currency**: `USD` (Converted to whole `INR` rupees using cached daily exchange rate)
- **E-Commerce Architecture**: Single-Page App (React / Next.js) protected by Imperva / Incapsula / Kasada bot mitigation.

---

## 2. URL Filter & Scope Boundaries

### 2.1 On Running Shoes Collection
- **Target URL**:
  `https://www.nordstrom.com/sr?origin=keywordsearch&keyword=on%20shoes&filterByBrand=on&filterByGenderAge=men&filterByGenderAge=unisex&filterByGenderAge=women`
- **Catalog Size**: 93 adult footwear products.

### 2.2 HOKA Footwear Collection
- **Target URL**:
  `https://www.nordstrom.com/sr?origin=keywordsearch&keyword=hoka%20shoes&filterByGenderAge=men&filterByGenderAge=unisex&filterByGenderAge=women&filterByProductType=shoes_boots&filterByProductType=shoes_sandals&filterByProductType=shoes_sneakers`
- **Catalog Size**: 89 adult footwear products (13 kids styles cleanly excluded).

### 2.3 Salomon Footwear Collection
- **Target URL**:
  `https://www.nordstrom.com/sr?origin=keywordsearch&keyword=salomon%20shoes`
- **Catalog Size**: 56 adult footwear products.

### 2.4 Universal Footwear Scope Boundaries
- Footwear only (strictly reject any apparel, socks, accessories, or clothing; reject kids/youth category leaks).
- Accepts all adult footwear products offering valid size variants (`len(size_variants) >= 1`).
- All available sizes are stored with granular per-variant US, UK, and EU size mappings.

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

## 5. Delta Checking & Polling (Tier 2: Zero-Cost Camoufox & Per-Size Sizing)

### 5.1 Kasada Client-Side Proof-of-Work Bypass (`stores/nordstrom/camoufox_solver.py`)
- **Challenge Identification**: Nordstrom renders Kasada JavaScript client-side proof-of-work challenges identified by `window['istlWas']` or `istlWasHere`.
- **Zero-Cost Local Solver**: Rather than paying for Firecrawl or proxy scraper APIs, we use `camoufox` (open-source C++ stealth Firefox fork) and Playwright.
- **Event Pump Handling**: In synchronous Camoufox, calling `time.sleep()` freezes the browser event pump and prevents Kasada from solving. Always use `page.wait_for_timeout(4000)` instead.
- **Strict Anti-False-Positive Guardrail**: If `istlWas` remains unresolved in the HTML after adaptive waiting, the solver returns `status: "blocked"`. It never falsifies success.

### 5.2 Granular Per-Size Shoe Inventory Tracking
- **Dehydrated Entity Location**: Nordstrom embeds complete hydrated entity JSON inside `window.__INITIAL_CONFIG__` (~420KB JSON payload).
- **Extraction Mechanism**: Parsed via `json.JSONDecoder().raw_decode()`.
- **Schema Path**:
  `__INITIAL_CONFIG__["products"][style_id]["coreChoices"][color_id]["items"][sku_id]["propositions"][0]["availability"]["shipQuantity"]`
- **Stock Mapping**:
  - If `shipQuantity > 0`: `in_stock = True`
  - If `shipQuantity == 0`: `in_stock = False` (sold out)
- **Variant Stock Mutation (`stores/nordstrom/delta.py`)**:
  - When even a single size sells out or restocks, `variant_stock_changed` is set to `True`.
  - `apply_delta_to_product` updates `var["in_stock"]` on each variant model, sets `has_changed = True`, and queues the event into `storage/db/history/delta_events.json` for Shopify sync.

### 5.3 Two-Tier Collection Fast Sweep & Route Blocking Optimization
- **Bottleneck Discovered**: Visiting 57 individual PDPs serially via Camoufox took ~15.6 minutes (850s–950s) due to Kasada proof-of-work solving and heavy asset downloading on each page.
- **Two-Tier Architecture**:
  1. **Tier 1 (Fast Collection Sweep)**: Camoufox loads Page 1 and Page 2 of the On Shoes collection (`/sr?origin=keywordsearch&keyword=on shoes...`) with aggressive route blocking (aborting images, media, fonts, and third-party trackers). Extracts `productsById` from `window.__INITIAL_CONFIG__` covering all 111 products in ~40 seconds.
  2. **In-Memory Cache & Fast-Path**: Products whose stored price and stock status match the live collection data resolve in `< 1ms` in memory.
  3. **Tier 2 (Targeted PDP Visit)**: If, and only if, a product indicates a price change, markdown, or goes out of stock (`shipQuantity == 0`), Camoufox visits only that specific product's PDP to synchronize granular per-size variants.
- **Performance Impact**: Reduced full 57-product Nordstrom sweep duration from **~15.6 minutes down to ~2.6 minutes (158s)** with zero API cost and 100% accuracy.

### 5.4 Salomon Footwear Onboarding & Single-Width LLM Fallback Quirk
- **Catalog Size**: 56 adult footwear models (XT-6, XT-4, Speedcross, ACS Pro, RX Moc/Slide, X-Alp, Snowclog).
- **Brand Handling**: Vendor is dynamically set to `Salomon` with SKU prefix `SALOMON-{styleId}-{size}`, EnergyCell / Contagrip cushioning specifications, and Salomon size guide accordion.
- **Single-Width Extractor Quirk**:
  - For footwear with single-width options, LLM extractors can mistakenly parse the width ("M" or "W") instead of the numeric shoe sizes.
  - **Resolution**: Seamless Camoufox hydration directly queries Nordstrom's `window.__INITIAL_CONFIG__["productDisplay"]["productDisplaysById"]["entities"]` `items` where `concatenatedDisplaySize` and `sizeDimension1.label` provide true US numeric sizes (e.g. US 5 through 15) and per-variant stock (`shipQuantity > 0`).
- **Parity Verification**: 100% Tier A static schema compliance and 100% live Tier B parity achieved across sample PDPs.

### 5.5 Full-Catalog Variant Rehydration & Numeric Adult Shoe Sizing Matrix
- **Problem**: 89 of 238 Nordstrom footwear products had truncated variants ($\le 6$ sizes, with 22 having only 1 variant) due to LLM extraction bounds during initial onboarding.
- **Camoufox Rehydration Pipeline**:
  - Leveraged Camoufox headless browsing to load PDPs and parse dehydrated entity structures:
    `__INITIAL_CONFIG__["productDisplay"]["productDisplaysById"]["entities"][style_id]["coreProducts"][0]["coreChoices"][color_idx]["items"]`
  - Rehydrated the entire 238-product catalog from **2,258 up to 3,040 verified sizes** (+34.6% expansion; averaging 12.77 sizes/shoe).
  - Only 3 products remain with $\le 6$ sizes, confirmed on live Nordstrom PDPs to be genuine limited-run specialty releases.
- **Numeric Adult Sizing Filter (`stores/nordstrom/inflow.py`)**:
  - Must enforce `parse_numeric_size(display_size) >= 3.5` to eliminate apparel sizes, kids sizing leaks, and raw width tokens.
  - Width indicators (`2E`, `4E`, `EE`, `D`, `W`, `M`) must be filtered out so variants reflect clean US/UK/EU numeric matrices.

### 5.6 Camoufox In-Flight Page Navigation Resilience (`stores/nordstrom/camoufox_solver.py`)
- **Quirk**: Playwright throws `Page.content: Unable to retrieve content because the page is navigating and changing the content` when Nordstrom's SPA executes internal client-side redirects after solving Kasada.
- **Remediation**:
  - Wrapped `page.content()` and `page.title()` in safe `try/except Error` handlers.
  - Extended Kasada wait polling from 10 to 20 ticks.
  - Pre-captured `page_title` in a local variable before evaluating blocked heuristics, completely eliminating in-flight navigation exceptions during background freshener cycles.

