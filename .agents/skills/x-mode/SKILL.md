---
name: x-mode
description: >-
  Executes the definitive, end-to-end "X Mode" brand onboarding, catalog scraping, quality auditing, delta freshness monitoring, and viewer publishing pipeline for any retailer or product collection URL in the product-updater project. Use whenever the user invokes "X mode", provides a brand collection URL to scrape and integrate, or asks to onboard a new retailer or collection end-to-end.
---

# Definitive "X Mode" Catalog Pipeline (`x-mode`)

"X Mode" is the project's rigorous, brand-agnostic production engineering workflow for ingesting new retailer collections, verifying 100% attribute integrity, integrating products into the 1-hour delta freshner daemon, and publishing updates to the live mobile catalog viewer.

Whenever a user provides a collection URL and activates X Mode, execute the following 6-phase pipeline sequentially.

---

## Phase 1: Brand Discovery & Boundary Analysis

1. **Extract Retailer & Domain**:
   - Determine `brand_slug` (e.g. `jwpei`, `coach`, `polene`, `mansur-gavriel`).
   - Check if `stores/{brand_slug}/` exists.
   - If onboarding a new store:
     ```bash
     cp -r stores/_template stores/{brand_slug}
     ```
     Initialize `stores/{brand_slug}/LEARNINGS.md`, `inflow.py`, and `delta.py`.
   - Register the store profile in `config/delta_config.json` with appropriate concurrency and rate limits:
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
   - Enforce strict category boundaries: if scraping bags, explicitly filter out and reject apparel, garments, shoes, or unrelated accessories.
   - Record newly discovered retailer query quirks or swatch IDs in `stores/{brand_slug}/LEARNINGS.md`.

---

## Phase 2: Ingestion & Canonical Storage (Tier 1)

1. **Scraping & Discovery**:
   - Crawl/scrape all collection pages politely using Firecrawl MCP or direct storefront endpoints.
   - Extract raw product handles, canonical URLs, and full metadata.

2. **Canonical Normalization (Pure Functions, ADR 0005)**:
   - **Title & Color Separation**: Separate model name from color suffix (e.g. `Title: "Noor Top Handle Bag"`, `Color: "Burgundy"`).
   - **Media Gallery**: Collect all high-resolution CDN images and bind the primary variant image.
   - **Size Guide & Accordion (ADR 0006)**: Extract bag dimensions (W x H x D), handle drop, strap drop, and materials. Generate `<details class="size-guide-accordion">` table inside `descriptionHtml`.
   - **Forex Conversion (ADR 0006)**: Convert source currency (USD/EUR/GBP) to whole INR rupees (`round(source_price * forex_rate)`) using `storage/forex.py`.
   - **Shopify Readiness (ADR 0004)**: Ensure all mandatory Shopify fields are satisfied (`title`, `vendor`, `body_html`, `variants`).

3. **Atomic Persistence & Deduplication**:
   - Primary Key: `SHA256(brand_slug + "::" + sku)[:16]`.
   - Write atomically to `storage/db/{brand_slug}/products/{product_id}.json` using `.tmp` and `os.replace` via `storage/db.py`.

---

## Phase 3: Rigorous Two-Tier Quality Audit

Data integrity is the highest project priority. Do NOT skip this phase.

### Tier A: Full Static Audit (100% of Scraped Items)
Run an automated audit script across all newly scraped items to verify:
- [ ] 100% primary keys match `SHA256(brand + "::" + sku)[:16]`.
- [ ] 100% contain `<details class="size-guide-accordion">` with valid dimension measurements.
- [ ] 100% have valid high-resolution image URLs (no broken or placeholder images).
- [ ] 100% have mathematically sound whole-rupee INR conversions.
- [ ] Exactly 0 category leaks (e.g. 0 clothing items if scraping bags).

### Tier B: Live Store Parity Audit (20 Random Samples via Subagent)
Launch a research subagent or execute a sampling script:
- Sample 20 products at random.
- Query live retailer endpoints (`.js`, storefront JSON, or Camoufox stealth browser).
- Verify 1-to-1 parity for: Title, SKU, Source Price, Current Stock State (`in_stock` vs `out_of_stock`), and **Granular Per-Size Availability** (confirming that individual shoe or apparel sizes match live stock).
- **Success Criteria**: 100.0% accuracy across all 20 samples.


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

### 4.4 HTTP 404 Delisting State Preservation
When a product is delisted (HTTP 404), the return dictionary **must preserve previous values** so delta logs and Shopify events never receive `null` states:
```python
if resp.status_code == 404:
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
        "message": "Product delisted (HTTP 404)"
    }
```

### 4.5 Selective Timestamp Stamping Invariant
In `apply_delta_to_product()`:
- **Rule**: ONLY stamp `product["last_verified_at"] = now_iso` if `delta_result.get("status") in ("success", "not_found")`.
- **Reason**: If a product check fails or is rate-limited (`status == "rate_limited"` or `"error"`), stamping `last_verified_at` causes the scheduler to skip it for 60 minutes. Leaving `last_verified_at` untouched ensures it is retried in the next cycle.

### 4.6 Browser-Grade Request Fingerprints (`storage/network.py`)
All outbound requests must use `get_browser_headers()` and `create_client()`:
- Modern Chrome 133 User-Agent.
- Full Client Hints: `Sec-Ch-Ua`, `Sec-Ch-Ua-Mobile: ?0`, `Sec-Ch-Ua-Platform: "Windows"`, `Sec-Fetch-Dest: empty`, `Sec-Fetch-Mode: cors`.
- Appropriate Accept: `text/javascript, application/json;q=0.9, */*;q=0.8`.
- Connection pooling limits: `httpx.Limits(max_keepalive_connections=5, max_connections=10)`.

### 4.7 Dual-Sink Structured Logging (`storage/logger.py`)
All sync activity routes through Loguru dual sinks:
- `logs/freshner.log`: Operational logs, product statuses, and `[DELTA:PRICE]` / `[DELTA:STOCK]` event tags (`INFO+`, 20 MB rotation, 14 days retention).
- `logs/errors.log`: Error forensic sink strictly capturing `ERROR` and `CRITICAL` events with full diagnostic stack traces (`backtrace=True, diagnose=True`, 10 MB rotation, 30 days retention).
- `status == "rate_limited"` events are explicitly logged to `logs/errors.log`.

### 4.8 Zero-Cost Local Stealth Browser for Anti-Bot Stores (`stores/{brand_slug}/camoufox_solver.py`)
When a retailer employs client-side bot management (e.g. Kasada, Akamai):
- **Zero API Fees**: Avoid paid proxy or scraping APIs for recurring hourly sweeps. Use a local headless stealth engine (`camoufox` + `playwright`).
- **Adaptive Challenge Settlement**: Never use static sleeps. Implement an adaptive polling loop (up to 12s) that actively verifies anti-bot challenge scripts (`istlWas`) are cleared and page DOM is hydrated.
- **Worker Tab Crash Recovery**: If a transient network glitch raises `NS_ERROR_UNKNOWN_HOST` or disconnects the tab, wrap the sweep loop to catch protocol errors and respawn `page = browser.new_page()` immediately.

### 4.9 Granular Multi-Variant & Size Availability Invariant
When syncing multi-variant sized goods (shoes, clothing):
- Extract per-size availability maps from hydrated JSON/DOM (e.g., `shipQuantity > 0` per SKU).
- In `apply_delta_to_product()`, iterate through `product["variants"]` and update each variant's `in_stock` boolean individually according to its SKU/size match.
- Top-level `product["availability"]` is set to `"in_stock"` if and only if `any(v.get("in_stock", False) for v in product["variants"])`.

### 4.10 Master Index & Delta Freshner Execution Steps
1. **Rebuild Master Index**:

   ```bash
   python -c "from storage.db import build_and_save_index; build_and_save_index()"
   ```
2. **Run Single Delta Sweep Test**:
   ```bash
   python sync_catalog.py --store {brand_slug} --dry-run --limit 5
   ```
   Verify:
   - 0 HTTP 429 drops.
   - Pacing matches configured `requests_per_second`.
   - Average latency < 1,000ms.
3. **Verify Timestamp Skip Logic**:
   Run `python sync_catalog.py --store {brand_slug}` twice. The second run must skip 100% of products in <0.1 seconds.

### 4.9 Continuous Background Freshner Daemon (`scripts/run_freshner_daemon.py`)
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

## Phase 5: Mobile Viewer Redesign & GitHub Pages Deployment

1. **Update Subcategory Taxonomy**:
   - In `scripts/export_viewer_data.py`, update `classify_subgroup()` with regex patterns to map new product styles into intuitive tabs.

2. **Export Static Database Bundle**:
   - Compile `frontend/public/data/catalog.json` and `meta.json`.

3. **Build & Deploy**:
   ```bash
   python scripts/publish_viewer.py
   ```
   - Rebuilds the Vite bundle.
   - Commits changes and pushes to `main`.
   - Triggers GitHub Actions workflow (`deploy-pages.yml`).
   - Verify deployment at `https://jahangirnn.github.io/product-updater/`.

---

## Phase 6: Document Preservation & Verification

1. **Update Knowledge Base**:
   - Record retailer gotchas, API tricks, rate limits, and selector quirks in `stores/{brand_slug}/LEARNINGS.md`.

2. **Run Full Test Suite & Doc-Keeper Alignment**:
   ```bash
   # 1. Run all 9 delta engine test suites
   python test_delta_engine.py

   # 2. Run doc-keeper alignment verifier
   python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py
   ```
   Ensure 100% pass across all tests and documentation checks before completing the run.
