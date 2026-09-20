# ADR 0016: JD Sports Store Onboarding, Multi-Tier Footwear Sizing Architecture, and Cross-Sibling Swatch Ingestion

## Status
Accepted

## Date
2026-09-19

## Context

1. **JD Sports Onboarding & Nike Footwear Scope**:
   To expand the catalog with high-demand athletic footwear, JD Sports US (`jdsports.com`) is being onboarded as the sixth supported retailer partition. The target scope encompasses ~514 products across three iconic Nike collections:
   - Nike Air Max (~254 products)
   - Nike Air Force (~155 products)
   - Nike Dunk Low (~105 products)

2. **The Sizing Collision Trap Across Age Tiers**:
   Unlike adult-only footwear catalogs (e.g. Nordstrom On Running or Foot Locker Nike Vomero), JD Sports footwear spans four distinct age tiers:
   - **Adult** (Men's & Women's, US $\ge 6.0\text{M}$ / $\ge 5.0\text{W}$)
   - **Grade School / Big Kids** (Youth, US 3.5Y – 7.0Y)
   - **Preschool / Little Kids** (Children, US 10.5C – 3.0Y)
   - **Toddler / Infant** (Infant & Toddler, US 2C – 10C)

   In raw JD Sports payloads, Toddler size 7, Grade School size 7, and Adult Men's size 7 are all represented as the unadorned numeric string `"7.0"`. Without explicit age-tier disambiguation, this causes severe collisions:
   - Variant titles and SKUs collide (`US 7.0` vs `US 7.0`).
   - Quick size selectors in the catalog viewer fail to distinguish toddler from adult shoes.
   - Size guide conversion tables misapply Adult conversion math (US 7 Men's = UK 6, EU 40) to Toddler shoes (US 7C = UK 6.5, EU 23.5) or Youth shoes (US 7Y = UK 6, EU 40).

3. **Front-End Architecture & Sibling Colorway Swatches**:
   JD Sports US is built on Next.js App Router with React Server Components (RSC streaming). Every Product Detail Page (PDP) delivers a server-rendered `<script type="application/ld+json">` containing a `ProductGroup` entity. 
   Critically, JD Sports search grids only display 1 or 2 primary colorways per silhouette, hiding up to 15+ sibling colorways behind interactive PDP swatches. Furthermore, some clearance colorways have 0 variants in stock and are completely omitted from search results. A two-pass traversal strategy is required to discover 100% of colorways.

4. **Akamai Bot Protection & Delta Polling Invariants**:
   JD Sports enforces Akamai Bot Manager, returning HTTP 403 Forbidden to direct unauthenticated datacenter requests. Catalog ingestion requires Firecrawl MCP for reliable bypass, while background delta polling (`sync_catalog.py`) requires polite pacing (`requests_per_second: 2.0`, `delay_seconds: 0.5`), circuit breaking on HTTP 403/429, and selective timestamping (ADR 0008).

## Decision

1. **Pure Function Architecture (ADR 0005)**:
   Implement `stores/jdsports/inflow.py` and `stores/jdsports/delta.py` with pure functions and zero class hierarchies:
   - Inflow: `parse_product_payload(raw_data, usd_to_inr_rate, group_name)`
   - Delta: `check_price_and_stock(product, client, store_name, rate_limiter, browser_page)` and `apply_delta_to_product(product, delta_result, forex_rate)`

2. **Deterministic Sizing Category Classification**:
   Implement `classify_sizing_category(title, breadcrumbs, raw_sizes)` to deterministically categorize products into:
   - `Toddler`: Keywords `toddler`, `infant`, `baby`, `crib`, `td`.
   - `Preschool`: Keywords `little kids`, `preschool`, `ps`.
   - `Grade School`: Keywords `big kids`, `grade school`, `gs`, `big boys`, `big girls`.
   - `Adult`: Default tier (Men's / Women's / Unisex).

3. **Size Token Preservation**:
   Variant labels and titles strictly preserve the `C` and `Y` suffixes:
   - Toddler: `US 7C`, `US 10C`
   - Preschool: `US 11.5C` (for sizes $\ge 10$) and `US 1.5Y` (for sizes $< 10$)
   - Grade School: `US 7.0Y`, `US 3.5Y`
   - Adult: `US 7.0`, `US 8.5`
   This completely prevents numerical collisions across age categories.

4. **Multi-Tier Size Conversion Accordions (ADR 0006)**:
   Generate tailored shoe size conversion matrices (US $\to$ UK $\to$ EU) inside `<details class="size-guide-accordion">` in `descriptionHtml` for each specific category and gender:
   - Adult Men's: US 6.0–15.0 $\to$ UK 5.5–14.0 $\to$ EU 38.5–49.5
   - Adult Women's: US 5.0–12.0 $\to$ UK 2.5–9.5 $\to$ EU 35.5–44.5
   - Grade School: US 3.5Y–7.0Y $\to$ UK 3.0–6.0 $\to$ EU 35.5–40.0
   - Preschool: US 10.5C–3.0Y $\to$ UK 10.0–2.5 $\to$ EU 27.5–35.0
   - Toddler: US 2C–10C $\to$ UK 1.5–9.5 $\to$ EU 17.0–27.0

5. **Cross-Sibling Swatch Ingestion (Anti-Omission Standard)**:
   Extract the complete variant matrix from JSON-LD `ProductGroup.hasVariant`, capturing 100% of sibling colorways and style SKUs, including clearance colorways omitted from search listings.

6. **Colorway Title Suffixing Invariant**:
   Format product titles as `{model_name} - {color}` (e.g. `Men's Nike Air Max 90 - Black/Dark Smoke Grey`) to eliminate duplicate cards on the catalog viewer.

7. **Whole-Rupee INR Math (ADR 0006)**:
   Convert USD to INR using `round(source_price * forex_rate)` with zero decimal paise, strictly satisfying `current_price.is_integer() == True`.

8. **Parent-Variant Stock Harmony & Depletion Cascade (ADR 0015)**:
   Derive parent availability strictly from child variants (`in_stock` iff any variant in stock). On HTTP 404 delistings, cascade `in_stock = False` to all child variants while preserving historical pricing and attributes.

9. **Selective Timestamp Stamping (ADR 0008)**:
   ONLY stamp `product["last_verified_at"]` when `status in ("success", "not_found")`. Rate limits (429) and WAF blocks (403) leave `last_verified_at` untouched so the scheduler retries them promptly.

10. **Canonical Slug Normalization**:
    Normalize apostrophes (`re.sub(r"['\u2019]s\b", "s", raw_title.lower())`) before generating URL slugs, preventing HTTP 301 redirects to unhydrated stubs.

## Consequences

- **Positive**:
  - **Zero Sizing Collisions**: Suffixing sizes with `C` and `Y` disambiguates Toddler 7C from Adult 7.0 across database records and frontend filters.
  - **100% Colorway Coverage**: Ingesting PDP hydrated `ProductGroup` state discovers all sibling colorways.
  - **Accurate Conversions**: Category-tailored conversion matrices guarantee correct international size recommendations.
  - **Stock Harmony & Resilience**: Full compliance with ADR 0015 eliminates phantom stock shifts and ghost inventory.
- **Negative / Trade-offs**:
  - Managing five distinct conversion charts increases normalization logic complexity.
  - Akamai Bot Manager prevents naive HTTP polling without rate limiting or Firecrawl.
