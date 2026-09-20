# Store Knowledge Base: JD Sports US (Nike Footwear Collections)

> **Purpose**: Authoritative engineering documentation for JD Sports US (`jdsports.com`). Details retailer architecture, Akamai WAF mitigation, JSON-LD hydrated state extraction, multi-tier footwear sizing taxonomy, sibling swatch reconciliation, and Tier 2 delta freshness integration.

---

## 1. Store Overview & Domain Identity

- **Store Name**: `JD Sports US` (The King of Trainers)
- **Store Slug**: `jdsports`
- **Primary Domain**: `https://www.jdsports.com`
- **Brands Under Scope**:
  - `Nike` (Nike Air Max, Nike Air Force, Nike Dunk Low)
  - **Scope Target**: ~514 products across Adult, Grade School (GS), Preschool (PS), and Toddler (TD) sizing tiers.
- **Default Currency**: `USD` (Converted to whole `INR` rupees using cached daily exchange rate with 0 decimal paise, per ADR 0006).
- **Front-End Architecture**: Next.js App Router with React Server Components (RSC streaming), delivering high-fidelity JSON-LD `ProductGroup` and `BreadcrumbList` schemas in the server-rendered HTML.

---

## 2. Target Collections & Scope Breakdown

Scraped live search queries reveal the inventory distribution:
1. **Nike Air Max**: `https://www.jdsports.com/search?query=nike+air+max` (254 products across 3 pages: 100 + 100 + 54)
2. **Nike Air Force**: `https://www.jdsports.com/search?query=nike%20air%20force` (155 products across 2 pages: 100 + 55)
3. **Nike Dunk Low**: `https://www.jdsports.com/search?query=nike%20dunk%20low` (105 products across 2 pages: 100 + 5)
- **Total Combined Scope**: $254 + 155 + 105 = 514$ products.

---

## 3. Bot Protection & Akamai WAF Shield Handling

- **WAF Engine**: Akamai Bot Manager (`server-timing: cdn-cache; desc=HIT, edge; dur=1, ak_p; ...`).
- **Behavior**: Direct unauthenticated HTTP requests (`curl`, `httpx`) from local datacenter IPs return HTTP 403 Forbidden with Finish Line / JD Sports access denial HTML. Local headless `Camoufox` without residential proxies encounters the same IP-level challenge.
- **Mitigation Strategy**:
  1. **Catalog Ingestion & Sweeps (Tier 1)**: Use Firecrawl MCP (`firecrawl_scrape`), which reliably bypasses Akamai Bot Manager and delivers complete SSR HTML with hydrated JSON-LD.
  2. **Delta Polling (Tier 2)**: For fast HTTP checks in `stores/jdsports/delta.py`, use Chrome 133 Client Hints headers and cooperative rate limiting (`requests_per_second: 2.0`, `delay_seconds: 0.5`). On HTTP 403 or 429, trip the store circuit breaker (`trip_circuit_breaker`) and return `status: "rate_limited"`.
  3. **Selective Timestamp Invariant (ADR 0008)**: Never stamp `last_verified_at` on HTTP 403 or 429, allowing the background daemon to retry on the next sweep cycle without waiting 60 minutes.

---

## 4. Front-End Hydration & Structured Data Sources

Every JD Sports PDP delivers structured payloads embedded directly in the server-rendered HTML:

### 4.1 JSON-LD Schema (`<script type="application/ld+json">`)
This is the **primary source of truth**:
- **`BreadcrumbList`**:
  Contains taxonomy hierarchy: `Home > Kids' > Boys' Shoes > Big Boys' Shoes (Sizes 3.5-7)`.
  Essential for disambiguating youth/toddler footwear from adult models.
- **`ProductGroup`**:
  Contains:
  - `name`: Base model name (e.g. `Men's Nike Air Max 95 Big Bubble Realtree Camo Casual Shoes`)
  - `productGroupID`: Master model ID (e.g. `prod2876897`)
  - `variesBy`: `["size", "color"]`
  - `hasVariant`: Complete array of child `Product` objects covering all sizes and sibling colorways.
  - Each variant contains:
    - `sku`: Variant SKU (e.g. `3284880`)
    - `size`: Size string (e.g. `"8.0"`, `"7.0"`)
    - `color`: Color description (e.g. `"Black/Dark Smoke Grey"`)
    - `offers`: Pricing in USD (`"200.00"`), availability (`"https://schema.org/InStock"`), and canonical PDP URL.

### 4.2 Next.js RSC Chunks (`self.__next_f.push`)
Contains `productData` with media galleries:
- Image URL pattern: `https://media.jdsports.com/i/finishline/{styleCode}_{colorCode}_P{1..6}?bg=rgb%28237%2C237%2C237%29&fmt=auto&w=1200&h=1200`.

---

## 5. Multi-Tier Footwear Sizing Taxonomy & Collision Prevention

### 5.1 The Size Collision Trap
In raw JD Sports data, Toddler sizes (`7.0`), Big Kids sizes (`7.0`), and Adult Men's sizes (`7.0`) are all represented as the unadorned string `"7.0"`. Ingesting these without age-tier disambiguation results in catastrophic variant title collisions, broken Quick Size selectors on the frontend, and incorrect size conversions.

### 5.2 Deterministic Sizing Classification
Classification inspects title keywords, breadcrumbs, and raw size sets in order of priority:
1. **Toddler / Infant (TD)**: Keywords `toddler`, `infant`, `baby`, `crib`, `td`. Sizes `US 2C` – `10C`.
2. **Preschool / Little Kids (PS)**: Keywords `little kids`, `preschool`, `ps`. Sizes `US 10.5C` – `3.0Y`.
3. **Grade School / Big Kids (GS)**: Keywords `big kids`, `grade school`, `gs`, `big boys`, `big girls`. Sizes `US 3.5Y` – `7.0Y`.
4. **Adult**: Default tier. Men's (US $\ge 6.0\text{M}$) and Women's (US $\ge 5.0\text{W}$).

### 5.3 Token Preservation Standard
Variant labels and titles strictly preserve `C` and `Y` suffixes:
- **Toddler**: `US 7C`, `US 10C` (never `US 7.0`)
- **Preschool**: `US 11.5C` (for $\ge 10$) / `US 1.5Y` (for $< 10$)
- **Grade School**: `US 7.0Y`, `US 3.5Y`
- **Adult**: `US 7.0`, `US 8.5`

### 5.4 Size Conversion Reference (US -> UK / EU)

#### Men's Adult Footwear
| US Size | UK Size | EU Size |
| :--- | :--- | :--- |
| **6.0** | 5.5 | 38.5 |
| **7.0** | 6.0 | 40.0 |
| **8.0** | 7.0 | 41.0 |
| **9.0** | 8.0 | 42.5 |
| **10.0** | 9.0 | 44.0 |
| **11.0** | 10.0 | 45.0 |
| **12.0** | 11.0 | 46.0 |
| **13.0** | 12.0 | 47.5 |

#### Women's Adult Footwear
| US Size | UK Size | EU Size |
| :--- | :--- | :--- |
| **5.0** | 2.5 | 35.5 |
| **6.0** | 3.5 | 36.5 |
| **7.0** | 4.5 | 38.0 |
| **8.0** | 5.5 | 39.0 |
| **9.0** | 6.5 | 40.5 |
| **10.0** | 7.5 | 42.0 |
| **11.0** | 8.5 | 43.0 |

#### Grade School / Big Kids (Youth 3.5Y – 7.0Y)
| US Size | UK Size | EU Size |
| :--- | :--- | :--- |
| **3.5Y** | 3.0 | 35.5 |
| **4.0Y** | 3.5 | 36.0 |
| **5.0Y** | 4.5 | 37.5 |
| **6.0Y** | 5.5 | 38.5 |
| **7.0Y** | 6.0 | 40.0 |

#### Preschool / Little Kids (10.5C – 3.0Y)
| US Size | UK Size | EU Size |
| :--- | :--- | :--- |
| **10.5C** | 10.0 | 27.5 |
| **11.0C** | 10.5 | 28.0 |
| **12.0C** | 11.5 | 29.5 |
| **13.0C** | 12.5 | 31.0 |
| **1.0Y** | 13.5 | 32.0 |
| **2.0Y** | 1.5 | 33.5 |
| **3.0Y** | 2.5 | 35.0 |

#### Toddler / Infant (1C – 10C)
| US Size | UK Size | EU Size |
| :--- | :--- | :--- |
| **2C** | 1.5 | 17.0 |
| **4C** | 3.5 | 19.5 |
| **6C** | 5.5 | 22.0 |
| **7C** | 6.5 | 23.5 |
| **8C** | 7.5 | 25.0 |
| **10C** | 9.5 | 27.0 |

---

## 6. Cross-Sibling Swatch Discovery (Anti-Omission Standard)

- **The Problem**: Search and collection grids only display 1 or 2 primary colorways per silhouette. Up to 15+ sibling colorways are concealed behind interactive color swatches on the PDP.
- **The Solution**: In JD Sports, `ProductGroup.hasVariant` contains variants for **all sibling colorways** belonging to that model group. Traversing `v["offers"]["url"]` discovers 100% of colorways—including clearance colorways with 0 variants in stock that never appear in search listings.

---

## 7. Colorway Title Suffixing Invariant

- When multiple colorway styles share a base model name (e.g. 17 colorways named `Men's Nike Air Max 95 Big Bubble Casual Shoes`), product titles must be suffixed as:
  `{model_name} - {color}`
  (e.g. `Men's Nike Air Max 95 Big Bubble Casual Shoes - Black/Dark Smoke Grey`).
- Eliminates duplicate generic cards on the catalog viewer.

---

## 8. Tier 2 Delta Freshness Contracts & Quirks

### 8.1 Universal Delta Contract
`stores/jdsports/delta.py` implements:
- `check_price_and_stock(product, client=None, store_name="jdsports", rate_limiter=None, browser_page=None) -> Dict[str, Any]`
- `apply_delta_to_product(product, delta_result, forex_rate) -> Tuple[Dict[str, Any], bool]`

### 8.2 Invariants Enforced
1. **Selective Timestamp Stamping (ADR 0008)**: ONLY stamp `product["last_verified_at"]` when `status in ("success", "not_found")`.
2. **Parent-Child Stock Harmony (ADR 0015)**: Parent `availability` is strictly derived from child variants (`in_stock` iff any variant is available).
3. **404 Delisting Cascade**: When a PDP returns HTTP 404, cascade `in_stock = False` to all child variants while preserving historical pricing.
4. **Canonical URL Slug Normalization**: Strip apostrophes (`re.sub(r"['\u2019]s\b", "s", raw_title.lower())`) before replacing punctuation with hyphens. This produces clean URLs (e.g. `mens-nike-air-max-90`) and eliminates HTTP 301 redirects.
5. **Whole-Rupee INR Math**: All parent and variant INR prices are rounded via `round(source_price * forex_rate)` with zero fractional paise (`price.is_integer() == True`).

---

## 9. Clearance Preservation vs Scraper Truncation

- **Scraper Truncation Defect**: A multi-size shoe where extraction prematurely stopped after 1 variant due to a broken CSS selector or timeout. This is an integrity defect and must be rejected.
- **Genuine Clearance Orphan**: A shoe where the retailer genuinely has only 1 remaining size in stock (e.g. size 8.0) because all other sizes have sold out.
- **Rule**: Genuine clearance items must be preserved, not dropped. The product record maintains its true clearance inventory and is marked `availability: "in_stock"` with the active clearance size, satisfying both completeness and catalog availability.
