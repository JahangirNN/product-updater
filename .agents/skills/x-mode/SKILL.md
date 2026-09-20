---
name: x-mode
description: >-
  Executes the definitive, end-to-end "X Mode" brand onboarding, catalog scraping, quality auditing, delta freshness monitoring, and viewer publishing pipeline for any retailer or product collection URL in the product-updater project. Use whenever the user invokes "X mode", provides a brand collection URL to scrape and integrate, or asks to onboard a new retailer or collection end-to-end.
---

# Definitive "X Mode" Catalog Pipeline (`x-mode`)

"X Mode" is the project's rigorous, brand-agnostic production engineering workflow for ingesting new retailer collections, verifying 100% attribute integrity, integrating products into the 1-hour delta freshner daemon, and publishing updates to the high-performance catalog viewer.

Whenever a user provides a collection URL and activates X Mode, execute the following 6-phase pipeline sequentially.

---

## Phase 1: Brand Discovery & Boundary Analysis

1. **Extract Retailer & Domain**:
   - Determine `brand_slug` (e.g. `jwpei`, `coach`, `michaelkors`, `nordstrom`, `polene`).
   - Check if `stores/{brand_slug}/` exists.
   - If onboarding a new store:
     ```bash
     cp -r stores/_template stores/{brand_slug}
     ```
     Initialize `stores/{brand_slug}/LEARNINGS.md`, `inflow.py`, and `delta.py`.
   - Register the store profile in `config/delta_config.json` with appropriate concurrency, rate limits, and network architecture:
     ```json
     "store_configs": {
       "{brand_slug}": {
         "check_interval_minutes": 60,
         "max_workers": 2,
         "requests_per_second": 2.0,
         "delay_seconds": 0.5,
         "timeout_seconds": 8.0,
         "endpoint_pattern": "https://www.retailer.com/products/{handle}.js"
       }
     }
     ```

2. **Category / Scope Boundary Definition**:
   - Inspect target collection URL parameters, swatch Metaobject IDs, query filters, and total product counts.
   - **Strict Category Boundaries**:
     - **Handbags & Small Goods**: Explicitly filter out and reject apparel, garments, footwear, or unrelated home accessories.
     - **Footwear**: Explicitly filter out apparel, socks, and accessories.
     - **Adult Sizing Enforcement**: For adult footwear collections, enforce minimum numeric sizing threshold ($\ge 3.5$) to eliminate kids/youth sizing leaks.
   - Record newly discovered retailer query quirks or swatch IDs in `stores/{brand_slug}/LEARNINGS.md`.

---

## Phase 2: Ingestion & Canonical Storage (Tier 1)

1. **Scraping & Discovery**:
   - Crawl/scrape all collection pages politely using Firecrawl MCP, SFCC storefront APIs, or Camoufox stealth browser.
   - Extract raw product handles, canonical URLs, and full metadata.
   - **Cross-Sibling Colorway Discovery (Anti-Omission Standard)**:
     - Retailer collection and search grids often only display 1 or 2 featured colorways per model, hiding up to 10+ sibling colorways behind interactive PDP swatches (`styleVariants` in Foot Locker, StarApps swatches in JW PEI, `colorway` arrays in Nordstrom).
     - Phase 2 ingestion must traverse and reconcile all sibling style SKUs discovered in PDP hydrated states so 100% of colorways are captured, not just the search page subset.

2. **Canonical Normalization (Pure Functions, ADR 0005)**:
   - **Title & Color Separation**: Separate model name from color suffix (e.g. `Title: "Noor Top Handle Bag"`, `Color: "Burgundy"`).
   - **Colorway Title Suffixing Invariant**:
     - When retailers share identical model names across multiple distinct colorways (e.g. 15 products all named `Nike Vomero 18 - Women's`), product titles in canonical storage and viewer feeds MUST be enriched as `{model_name} - {color}` (e.g. `Nike Vomero 18 - Women's - Sweet Beet/Bordeaux`). This eliminates duplicate generic cards and prevents sibling colorway confusion.
   - **Media Gallery**: Collect all high-resolution CDN images and bind the primary variant image.
   - **Size Guide & Accordion (ADR 0006)**:
     - **Handbags / Accessories**: Extract dimensions (W x H x D), handle drop, strap drop, and materials. Generate `<details class="size-guide-accordion">` table inside `descriptionHtml`.
     - **Footwear**: Generate gender-tailored shoe conversion matrices (US $\to$ UK $\to$ EU) inside the accordion.
   - **Forex Conversion (ADR 0006)**: Convert source currency (USD/EUR/GBP) to whole INR rupees (`round(source_price * forex_rate)`) using `storage/forex.py`. Zero fractional paise allowed.
   - **Shopify Readiness (ADR 0004)**: Ensure all mandatory Shopify fields are satisfied (`title`, `vendor`, `body_html`, `variants`).

3. **Variant Matrix Extraction & Clearance Invariants**:
   - **Zero 1-Size Truncation vs Clearance Preservation**:
     - For footwear, clothing, or multi-size goods, never accept a single variant placeholder or top-level summary when multiple sizes exist.
     - **Crucial Distinction**: Differentiate between *scraper defect truncation* (where a multi-size shoe was truncated because of a broken selector) vs *genuine retailer clearance* (where the retailer genuinely only has 1 remaining size in stock, e.g. size 7.0 or 8.0).
     - Legitimate clearance products with 1 size in stock must **never** be dropped or skipped. Build the full size matrix for the model (e.g. US 5.0–12.0) with only the active clearance size marked `in_stock: true`, or canonicalize the clearance item with verified single-size inventory.
   - **Out-of-Stock / Delisted Ingestion Resilience**:
     - If a known or harvested SKU returns HTTP 404 or SSR errors (`@api/FAILED: Product is out of stock`, `code: 20006`), never silently discard it during ingestion or catalog rebuilds. Ingest it canonically as `availability: "out_of_stock"` with all variants `in_stock: false`. This prevents catalog holes and eliminates user confusion where a missing clearance product is mistaken for a color swap or corrupted data.
   - **Dehydrated State Extraction**: Extract the complete variant matrix directly from hydrated client states (`window.footlocker.STATE_FROM_SERVER`, `window.__INITIAL_CONFIG__`, SFCC product objects, or Shopify `.js` items).
   - **Width vs Sizing Separation**: Standalone shoe width codes (`2E`, `4E`, `EE`, `D`, `W`, `M`, `Wide`, `Medium`) must **never** be parsed as numeric sizes. Use regex exclusion rules to isolate true US numeric sizes.
   - **Multi-Price Preservation**: Multi-material or multi-colorway items with different prices (e.g. Coach Scene7 or MK styles) must preserve their respective `source_price`, whole-rupee INR price, and unique SKU on each variant.

4. **Atomic Persistence & Deduplication**:
   - Primary Key: `SHA256(brand_slug + "::" + sku)[:16]`.
   - Write atomically to `storage/db/{brand_slug}/products/{product_id}.json` using `.tmp` and `os.replace` via `storage/db.py`.

---

## Phase 3: Rigorous Five-Part Quality Audit Suite

Data integrity is the highest project priority. Do NOT skip this phase.
Run the automated cross-brand audit suite:
```bash
python scripts/audit_cross_brand_catalog.py
```

The suite validates five critical integrity dimensions across 100% of the catalog:

### Part 1: Sizing Integrity (Zero Truncation vs Clearance Verification)
- Audits 100% of footwear and apparel across all brands.
- **Invariant**: Exactly **0 unverified products with $\le 1$ variant** in multi-size categories.
- Legitimate clearance items with 1 size remaining must have explicit clearance validation metadata recorded in store learnings.
- Guarantees full size runs across all footwear styles (averaging 10–17 sizes per model).

### Part 2: Multi-Price & Unique Variant Attributes
- Audits styles featuring multi-material or multi-colorway pricing differentials (e.g. Coach & Michael Kors).
- **Invariants**:
  - 100% unique SKUs per variant (0 missing).
  - 100% valid CDN images bound to variants (e.g. Coach Scene7 / MK images).
  - 0 invalid, zero, or negative variant prices.

### Part 3: Handbags/Accessories Stock Harmony & Whole-Rupee INR Math
- Audits 100% of products and variants across all partitioned store databases.
- **Invariants**:
  - Exactly **0 fractional INR paise** in parent prices (`current_price.is_integer()`).
  - Exactly **0 fractional INR paise** in variant prices (`variant_price.is_integer()`).
  - **Stock Harmony Invariant**: Exactly **0 parent/variant stock desynchronizations**:
    - If any child variant is `in_stock`, parent `availability` must be `in_stock` (`is_active = True`).
    - If all child variants are out of stock, parent `availability` must be `out_of_stock` (`is_active = False`).

### Part 4: Cross-Sibling Coverage & Sibling Inventory Audit
- Cross-references all sibling style SKUs discovered in PDP hydrated states (`styleVariants`, swatch Metaobjects) against `storage/db/{brand_slug}/products/`.
- **Invariant**: Exactly **0 missing sibling styles**. Every discovered colorway must exist as a canonical record in the database.

### Part 5: Live Retailer PDP Parity Sampling
- Randomly samples products across all onboarded brands against live retailer endpoints.
- Verifies 1-to-1 parity for: Title, SKU, Source Price, Availability, and Granular Variant Stock.
- **Success Criteria**: 100.0% concordance rate with zero unaccounted divergences.
- Outputs structured audit forensics to `scripts/live_audit_report.json`.

---

## Phase 4: Tier 2 Freshness Integration & Daemon Enrollment (In-Depth)

The delta freshner systematically monitors catalog availability and pricing every **1 hour** across multiple stores from a single engine. Understanding and following these architectural rules is mandatory for zero rate limits, zero thread collisions, and complete state integrity.

### 4.1 The Store Delta Contract (`stores/{brand_slug}/delta.py`)
Every store module must implement two pure functions adhering to this exact contract:

```python
def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[httpx.Client] = None,
    limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Poll live price and stock status for an existing product.
    Must acquire rate limiter permits, apply jittered backoff on 429,
    trip the store circuit breaker on rate limits, and preserve state on 404.
    """

def apply_delta_to_product(
    product: Dict[str, Any],
    delta_result: Dict[str, Any],
    forex_rate: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply delta check results to a canonical product dict.
    Updates price, INR recalculation, availability, and variant-level states.
    CRITICAL: ONLY stamp last_verified_at when status in ("success", "not_found").
    Returns (updated_product, has_changed).
    """
```

### 4.2 Centralized Rate Limiting & Anti-Thundering-Herd Circuit Breaker
- **Central Rate Limiter (`storage/rate_limiter.py`)**:
  - Enforces a thread-safe ceiling of `requests_per_second` (default 2.0 req/s = 500 Shopify complexity pts/s).
  - Worker threads must call `limiter.acquire()` before firing outbound requests.
- **Store-Wide Circuit Breaker**:
  - When ANY worker thread receives an HTTP 429, it parses `Retry-After` and calls `limiter.trip_circuit_breaker(wait_sec)`.
  - **Result**: All sibling worker threads for that store pause cooperatively, allowing the remote CDN bucket to refill rather than colliding in a thundering herd.
  - **Multi-Store Isolation**: A circuit breaker tripped on Store A does NOT pause worker threads on Store B.

### 4.3 HTTP 429 Backoff & Retry Standards
In `check_price_and_stock()`:
```python
if resp.status_code == 429:
    wait_sec = parse_retry_after(resp.headers, default_cooldown=30.0)
    if limiter:
        trip_circuit_breaker(store_name, wait_sec)
    
    # Only sleep if we have retries remaining; release thread immediately on final attempt
    if attempt < 2:
        backoff = wait_sec + random.uniform(0.5, 2.0 * (2 ** attempt))
        time.sleep(backoff)
        continue
    break
```

### 4.4 HTTP 404 Delisting & Dehydrated SSR Error Handling
When a product is delisted (HTTP 404) or when a retailer's hydrated server state returns an out-of-stock error (e.g. Foot Locker `@api/FAILED`, `statusCode: 404`, `errors: [{"code": "20006", "message": "Product is out of stock"}]`, or empty data object), the delta engine must handle it gracefully:
- **Preserve Previous Pricing & Attributes**: The return dictionary **must preserve previous values** so delta logs and Shopify events never receive `null` states.
- **Stock Depletion Cascade (ADR 0015)**: Automatically cascade depletion to all child variants (`in_stock: False`) and set parent `availability: "out_of_stock"` (`is_active: False`).
```python
if resp.status_code == 404 or status_code == 404 or errors or get_details.get("status") == "@api/FAILED":
    return {
        "status": "not_found",
        "handle": handle,
        "availability": "out_of_stock",
        "old_availability": old_availability,          # Preserved!
        "current_source_price": old_source_price,      # Preserved!
        "old_source_price": old_source_price,          # Preserved!
        "is_active": False,
        "price_changed": False,
        "stock_changed": old_availability != "out_of_stock",
        "elapsed_ms": elapsed_ms,
        "message": f"Product delisted or out of stock (HTTP {status_code or 404})"
    }
```

### 4.5 Canonical URL Slug Normalization
Apostrophes in model names (e.g. `Women's`, `Men's`, `Girls'`, `Boys'`) must be normalized prior to hyphen replacement:
```python
cleaned_title = re.sub(r"['\u2019]s\b", "s", raw_title.lower())
slug = re.sub(r'[^a-zA-Z0-9]+', '-', cleaned_title).strip('-')
```
This generates the retailer's true canonical slug (e.g. `nike-vomero-18-womens`), preventing unnecessary HTTP 301 redirects to unhydrated `/~/SKU.html` stubs.

### 4.6 Selective Timestamp Stamping Invariant
In `apply_delta_to_product()`:
- **Rule**: ONLY stamp `product["last_verified_at"] = now_iso` if `delta_result.get("status") in ("success", "not_found")`.
- **Reason**: If a product check fails or is rate-limited (`status == "rate_limited"` or `"error"`), stamping `last_verified_at` causes the scheduler to skip it for 60 minutes. Leaving `last_verified_at` untouched ensures it is retried in the next cycle.

### 4.7 Variant Price Differential & Stock Cascade Tracking
- When applying deltas, check both top-level and variant-level pricing:
  ```python
  if abs(new_v_price - old_v_price) > 0.01:
      var["price"] = round(new_v_price * forex_rate)
      var["source_price"] = new_v_price
      has_changed = True
      logger.info(f"[DELTA:PRICE] {handle} variant {var['sku']} -> ${new_v_price}")
  ```
- Granular per-size stock updates must cascade to parent availability:
  ```python
  product["availability"] = "in_stock" if any(v.get("in_stock", False) for v in product["variants"]) else "out_of_stock"
  product["is_active"] = (product["availability"] == "in_stock")
  ```

### 4.8 Stealth Browser & Anti-Bot Optimization (`camoufox_solver.py`)
When a retailer employs client-side bot management (Kasada, Akamai, Imperva):
- **Zero API Fees**: Use local headless stealth engine (`camoufox` + `playwright`).
- **Route-Level Resource Aborting**: Abort images, fonts, media, and third-party trackers before page load to cut sweep latencies by >50%.
- **Safe Navigation Handling**: Wrap `page.content()` and `page.title()` in safe `try/except Error` handlers to gracefully handle client-side SPA navigation redirects after challenge solving.
- **Two-Tier Collection Fast Sweep**: Load collection listings first to harvest hydrated entity state for all items in bulk (<40s for ~100 products), only visiting individual PDPs when price or stock shifts are detected.

### 4.9 Dual-Sink Structured Logging (`storage/logger.py`)
All sync activity routes through Loguru dual sinks:
- `logs/freshner.log`: Operational logs, product statuses, and `[DELTA:PRICE]` / `[DELTA:STOCK]` event tags (`INFO+`, 20 MB rotation, 14 days retention).
- `logs/errors.log`: Error forensic sink strictly capturing `ERROR` and `CRITICAL` events with full diagnostic stack traces (`backtrace=True, diagnose=True`, 10 MB rotation, 30 days retention).
- Delta events are queued into `storage/db/history/delta_events.jsonl` (ready for Shopify sync).

### 4.10 Continuous Background Freshner Daemon (`scripts/run_freshner_daemon.py`)
- The daemon runs persistently in the background (`IsDaemon=true`).
- Calculates dynamic sleep intervals: `sleep_seconds = (interval * 60) - cycle_duration`.
- Sleeps using a 1-second heartbeat loop to respond immediately to `SIGINT` (Ctrl+C) and `SIGTERM`.
- **Operator Monitoring Runbook**:
  ```powershell
  # Monitor real-time operational logs
  Get-Content logs/freshner.log -Tail 50 -Wait

  # Monitor isolated error forensics
  Get-Content logs/errors.log -Tail 30 -Wait
  ```

---

## Phase 5: High-Performance Catalog Viewer Pipeline

1. **Update Subcategory Taxonomy**:
   - In `scripts/export_viewer_data.py`, update `classify_subgroup()` with regex patterns to map new product styles into intuitive tabs.

2. **Lean Static Catalog Export (`scripts/export_viewer_data.py`)**:
   - Compile `frontend/public/data/catalog.json` and `meta.json`.
   - **Colorway Enrichment**: Ensure exported titles append `- {color}` when multiple colorway styles share a base model name.
   - **Payload Lean Pruning**:
     - Strip redundant `description_html` (retain only `descriptionHtml`).
     - Limit `images` array in `catalog.json` to top 5 thumbnail URLs (full galleries load in product modal).
     - Clean redundant null/default variant keys to keep the catalog bundle lean (<15 MB for thousands of products).
   - Sync files: `Copy-Item frontend/public/data/* frontend/dist/data/ -Force`.

3. **High-Speed Frontend Rendering Architecture (`frontend/src/`)**:
   - **Dynamic Variant Swatch Switching (`ProductModal.tsx`)**:
     - When a user selects or clicks a variant (size or sibling colorway swatch), the viewer modal must dynamically switch:
       1. Hero image and thumbnail gallery to match the selected variant's `image_url` or colorway photo set.
       2. Display price and compare-at price to reflect the variant's specific pricing.
       3. Real-time availability badge (`In Stock` vs `Out of Stock`).
   - **Incremental Card Batching & Virtual Scroll (`App.tsx`)**:
     - Never mount thousands of card DOM nodes at once.
     - Render products in initial batches of 40 cards with 40-card increments via an `IntersectionObserver` sentinel.
     - Reduces active DOM nodes from 26,000+ to ~600 (97.7% reduction), eliminating main-thread locking.
   - **Debounced Search Input (`Header.tsx`)**:
     - 150ms debounce on search queries to ensure 60 FPS typing without UI stutter.
   - **Component Memoization & Async Image Decoding (`ProductCard.tsx`)**:
     - Wrap export in `React.memo()`.
     - Set `decoding="async"` on all product card thumbnail images.

4. **Build & Deploy to GitHub Pages**:
   ```bash
   python scripts/publish_viewer.py
   ```
   - Compiles Vite production bundle (`tsc && vite build`).
   - Commits and pushes to `main`.
   - GitHub Actions automatically deploys to GitHub Pages (`deploy-pages.yml`).
   - Verify deployment at `https://jahangirnn.github.io/product-updater/`.

---

## Phase 6: Document Preservation & Full Verification Suite

1. **Update Store Knowledge Base**:
   - Record retailer gotchas, API endpoints, rate limits, and selector quirks in `stores/{brand_slug}/LEARNINGS.md`.

2. **Run Multi-Suite Verification**:
   Execute the four-tier verification check before concluding:
   ```bash
   # 1. Delta engine unit & integration tests
   python test_delta_engine.py

   # 2. Cross-brand catalog quality audit & live PDP sampling
   python scripts/audit_cross_brand_catalog.py

   # 3. Architecture documentation & ADR alignment
   python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py

   # 4. Frontend production build
   cd frontend; npm run build; cd ..
   ```
   Ensure 100% pass across all 4 suites before completing the onboarding run.
