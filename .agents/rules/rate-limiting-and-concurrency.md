# Rule: Multi-Store Rate Limiting, Circuit Breakers & Ingress Invariants

## 1. Directive
All catalog polling, store scrapers, and delta refresh dispatchers **MUST** adhere to store-agnostic rate limiting, cooperative circuit breaking, and strict state invariants (ADR 0005, ADR 0010).

Never fire unpaced outbound requests against retailer storefronts, never use OOP classes for concurrency state, and never stamp verification timestamps on failed requests.

---

## 2. Invariants & Required Protocols

### 2.1 Mandatory Permit Acquisition
- Outbound HTTP requests must call `limiter.acquire()` from `storage/rate_limiter.py` before executing requests.
- Pacing must default to `2.0 req/s` (or store-specific `requests_per_second` configured in `config/delta_config.json`).

### 2.2 Anti-Thundering-Herd Circuit Tripping
- When any thread encounters an HTTP 429:
  1. Parse the `Retry-After` header (default to 30.0s if omitted).
  2. Call `limiter.trip_circuit_breaker(store_name, wait_sec)`.
  3. Cooldown is capped at `MAX_COOLDOWN_SECONDS = 300.0`.
- All sibling worker threads for that store must cooperatively pause during the cooldown window.
- Tripping Store A's circuit breaker MUST NEVER pause Store B (multi-store isolation).

### 2.3 Exponential Jitter Backoff
- On HTTP 429 or 5xx, retries must use full exponential jitter backoff:
  `backoff = wait_sec + random.uniform(0.5, 2.0 * (2 ** attempt))`
- Do not sleep if all retry attempts have been exhausted; release the thread immediately.

### 2.4 Selective Timestamp Stamping Invariant
- `product["last_verified_at"]` MUST ONLY be updated if `delta_result["status"] in ("success", "not_found")`.
- NEVER stamp `last_verified_at` if `status` is `"rate_limited"` or `"error"`.
- Reason: stamping failed checks marks them fresh and skips them for 60 minutes. Leaving timestamps untouched ensures immediate retry on the next cycle.

### 2.5 Delisting (404) Attribute Preservation
- When a product returns HTTP 404 (delisted):
  - Retain `old_availability`, `old_source_price`, and `current_source_price = old_source_price`.
  - Set `availability = "out_of_stock"` and `is_active = False`.
  - NEVER emit `null` fields in delta events or sync queues.

### 2.6 Pure Functional Concurrency & Lock Management (ADR 0005)
- Zero OOP classes for rate limiters, state holders, or clients.
- Concurrency state is managed exclusively via module-level dictionaries and `threading.Lock`.

### 2.7 Top-Level Worker Exception Isolation
- Worker loops in thread pools must wrap single-item execution in top-level `try/except Exception as err` blocks.
- Route exceptions with full tracebacks to `logs/errors.log`. One failing product must never crash sibling workers or the dispatcher.

### 2.8 Anti-Bot Adaptive Challenge Settlement
- Never rely on static sleeps (e.g. `time.sleep(4)`) when resolving client-side anti-bot challenges (e.g., Kasada, Akamai).
- Use an **adaptive polling loop** (up to 12s) checking that anti-bot challenge scripts (e.g., `istlWas`) are cleared and the document title/DOM is fully hydrated before extracting data.
- Recurring hourly sweeps MUST run via local stealth browsers (Camoufox) or HTTP pools with zero external paid scraper API cost.

### 2.9 Stealth Browser Worker Tab Crash Isolation
- When long-running background sweeps reuse a stealth browser tab, transient network glitches can cause `NS_ERROR_UNKNOWN_HOST` or socket drops.
- The worker must catch Firefox protocol exceptions and immediately recreate a fresh tab (`page = browser.new_page()`) so subsequent products are not failed by a poisoned session.

### 2.10 Granular Multi-Variant & Size Availability Invariant
- For shoe and apparel retailers with sizing, catalog-level stock checks are insufficient.
- The delta engine must extract per-size availability from hydrated JSON (`shipQuantity > 0` or proposition availability).
- Stored variants must update their `in_stock` boolean per individual size independently.
- Top-level product `availability` is `in_stock` if and only if `any(v["in_stock"] for v in variants)`.

