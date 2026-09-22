# Store Knowledge Base: Jomashop (Luxury & Designer Watches)

> **Purpose**: Authoritative engineering documentation for Jomashop (`jomashop.com`). Details Magento 2 headless backend architecture, Apollo GraphQL data extraction, Cloudflare Turnstile mitigation, category boundary enforcement, watch specification parsing, case diameter variant sizing, whole-rupee INR conversion, and Tier 2 delta freshness integration.

---

## 1. Store Overview & Domain Identity

- **Store Name**: `Jomashop`
- **Store Slug**: `jomashop`
- **Primary Domain**: `https://www.jomashop.com`
- **GraphQL Endpoint**: `POST https://www.jomashop.com/graphql`
- **Category Root ID**: `871` (Watches, `url_key: "watches"`)
- **Brands Under Scope**:
  - `Versace` (11 series, 46 products)
  - `Tissot` (13 series, 157 products)
  - `Seiko` (8 series, 67 products)
  - `Citizen` (13 series, strictly $100–$500 USD, 119 products)
  - `Michael Kors` (8 series, 67 products)
  - **Total Scope Target**: Exactly **456 products**.
- **Default Currency**: `USD` (Converted to whole `INR` rupees using cached daily exchange rate with 0 decimal paise, per ADR 0006).
- **Front-End Architecture**: Headless Magento 2 backend paired with a client-side React Single Page Application (SPA) powered by Apollo GraphQL.

---

## 2. Target Collections & Scope Breakdown

The 5 target brand query filter URLs map directly to Magento 2 GraphQL category filter inputs:

| Collection | Target Brand | Filter Query Parameters | Target Series Scope | Price Boundary | Verified Count |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Versace Watches** | `Versace` | `category_id: 871`, `manufacturer: Versace` | Chrono, Chrono Master, Greca Fortuna, Greca Jewel, Sport Chrono, V-Chrono, V-Contempo, Hellenyium, Greca Flourish, Greek, Greca Sphere | None | **46** |
| **Tissot Watches** | `Tissot` | `category_id: 871`, `manufacturer: Tissot` | PRX, Seastar, Seastar 1000, Seastar 1001, Seastar 2000, PR516, Carson, Le Locle, Powermatic 80, T-Classic, Chemin Des Tourelles, Carson Premium, Lady Heart | None | **157** |
| **Seiko Watches** | `Seiko` | `category_id: 871`, `manufacturer: Seiko` | 5 Sports, Chronograph, Essentials, Presage, Prospex, Prospex Sea, Quartz, Sport | None | **67** |
| **Citizen Watches** | `Citizen` | `category_id: 871`, `manufacturer: Citizen`, `price: {from: 100, to: 500}` | Promaster Dive, Promaster Diver, Promaster Navihawk, Promaster Sky Navihawk, Promaster Sea, Sports, Sport Luxury, Sport Automatic, Promaster Marine, Promaster Skyhawk, Tsuyosa, Promaster Dive Automatic, Promaster Skyhawk U830 | **$100.00 to $500.00 USD** | **119** |
| **Michael Kors Watches** | `Michael Kors` | `category_id: 871`, `manufacturer: Michael Kors` | Lexington, Billie, Petite Lexington, Runway, Slim Runway, Bradshaw, Parker, Corey | None | **67** |
| **Total Ingestion Scope** | — | — | — | — | **456 products** |

---

## 3. Bot Protection & Zero-Token GraphQL Architecture

- **WAF Engine**: Cloudflare (`server: cloudflare`, Turnstile on HTML routes).
- **Behavior**:
  - Direct HTTP GET requests to HTML category pages (`/filters/watches?...`) return HTTP 403 Forbidden with Turnstile challenge stubs to standard TLS fingerprints.
  - **Crucial Ingestion & Delta Advantage**: The Apollo GraphQL endpoint (`POST https://www.jomashop.com/graphql`) is **NOT** challenge-gated. Standard `httpx.post` and `curl_cffi` execute queries with sub-400ms latency, zero challenge pages, and zero token costs ($0.00).
- **Zero-Token Local Execution**:
  - Ingestion and recurring delta checks use direct GraphQL requests via `httpx.post`, avoiding heavy headless browser overhead.
  - Fallback: Local headless Camoufox (per ADR 0017) is available if Cloudflare policies change.

---

## 4. Category Boundary & Isolation Invariants

1. **Watch-Only Boundary (`category_id: 871`)**:
   - Every GraphQL query explicitly includes `"category_id": {"eq": "871"}`.
   - Any product belonging to sunglasses/eyewear, fragrances/beauty, apparel, handbags/leather goods, jewelry, watch winders, or standalone straps/bands is immediately rejected.
2. **Citizen Price Boundary**:
   - Citizen watch products with USD source price `< 100.0` or `> 500.0` are strictly rejected.
3. **Footwear Audit Isolation Invariant**:
   - Watches are physical luxury accessories where the primary physical dimension is **Case Diameter** (e.g. `40 mm`). They are not footwear or apparel.
   - To prevent false 1-size truncation failures in `scripts/audit_cross_brand_catalog.py` (Part 1: Footwear Sizing Integrity), watch records MUST:
     - Set `product_type = "Watches"`.
     - Set `groups = ["watches", brand_slug, f"{brand_slug}-{series_slug}"]`.
     - **NEVER** include footwear or apparel keywords (`shoes`, `footwear`, `sneaker`, `apparel`, `clothing`) in `groups` or `product_type`.

---

## 5. Technical Specifications & Variant Sizing Architecture

### 5.1 Case Diameter Sizing Option
- Option Name: `"Case Diameter"` (e.g. `"40 mm"`, `"42 mm"`).
- Variant Title Format: `{Case Diameter} - {Dial Color} / {Band Type}` (e.g. `40 mm - Blue Dial / Stainless Steel`).
- Never use generic placeholder strings like `"Default Title"` or `"One Size"`.

### 5.2 Attribute Extraction (`moredetails.more_details`)
Extracted from PDP GraphQL response:
- `Case Diameter` (`Case` -> `case_diameter_text`)
- `Case Thickness` (`Case` -> `case_thickness`)
- `Case Material` (`Case` -> `case_material`)
- `Case Back` (`Case` -> `case_back`)
- `Movement` (`Information` -> `movement`)
- `Engine` (`Information` -> `engine`)
- `Power Reserve` (`Information` -> `power_reserve`)
- `Dial Color` (`Dial` -> `dial_color`)
- `Crystal` (`Dial` -> `crystal`)
- `Hands` (`Dial` -> `hands`)
- `Dial Markers` (`Dial` -> `dial_markets`)
- `Band Material` (`Band` -> `bracelet_material`)
- `Band Color` (`Band` -> `band_color_text`)
- `Clasp` (`Band` -> `clasp`)
- `Water Resistance` (`Features` -> `water_resistant`)
- `Calendar` (`Features` -> `calendar`)
- `Functions` (`Features` -> `functions`)
- `Warranty` (`Additional Info` -> `warranty`)
- `UPC Code` (`Additional Info` -> `upc_code`)

### 5.3 Technical Specifications & Size Guide Accordion (`descriptionHtml`)
Assembled into three styled HTML blocks:
1. Product overview text.
2. Technical specifications table (`<div class="product-specifications">`).
3. Interactive wrist sizing guide accordion (`<details class="size-guide-accordion">`) with wrist circumference matching matrix.

---

## 6. Whole-Rupee INR Math & Stock Harmony (ADR 0006 & ADR 0015)

1. **Whole-Rupee Math**:
   - USD converted to INR via `storage/forex.py`: `round(source_price * forex_rate)`.
   - Exactly **0 fractional paise** across parent and variant prices (`is_integer() == True`).
   - String prices formatted as `f"{round(...):.2f}"` (e.g. `"37916.00"`).
2. **Parent-Variant Stock Harmony**:
   - `availability = "in_stock"` and `is_active = True` if and only if any child variant is `in_stock`.
   - If all variants out of stock, parent `availability = "out_of_stock"` and `is_active = False`.
3. **404 Delisting Depletion Cascade**:
   - On delisting (HTTP 404 or empty items), cascade `in_stock = False` to all variants, set parent to `"out_of_stock"`, and preserve previous USD pricing.
4. **Selective Timestamp Stamping (ADR 0008)**:
   - ONLY stamp `last_verified_at` on `"success"` or `"not_found"`. Never on `"rate_limited"` or `"error"`.

---

## 7. Rate Limits & Concurrency Configuration

Configured in `config/delta_config.json`:
```json
"jomashop": {
  "check_interval_minutes": 60,
  "engine": "http",
  "max_workers": 2,
  "requests_per_second": 2.0,
  "delay_seconds": 0.5,
  "timeout_seconds": 10.0,
  "endpoint_pattern": "https://www.jomashop.com/{handle}.html"
}
```
Worker threads acquire permits via `storage/rate_limiter.py` and cooperatively pause on HTTP 429 via `trip_circuit_breaker()`.
