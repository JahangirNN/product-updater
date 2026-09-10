# ADR 0010: Store-Agnostic Rate Limiting, Circuit Breakers & Browser Fingerprinting

## Status
Accepted

## Date
2026-09-10

## Context
As the dropship catalog expands from JW PEI to multiple international retailers, our systematic delta updater must poll live storefronts concurrently without triggering Web Application Firewall (WAF) blocks or HTTP 429 Too Many Requests errors.

Previously:
1. Pacing was hardcoded with static sleeps inside individual worker threads, leading to race conditions and burst traffic.
2. If a thread received a 429 response, sibling threads continued hammering the retailer storefront, triggering extended IP bans and thundering herds upon retry.
3. HTTP headers used older Chrome 120 identifiers without Client Hints (`Sec-Ch-Ua`, `Sec-Fetch-*`), leaving network requests vulnerable to automated bot-detection heuristics.
4. HTTP 404 delisting responses omitted previous price and availability values, causing `null` fields in queued Shopify delta events.
5. Inconclusive delta attempts (`status == "rate_limited"` or `"error"`) were erroneously stamping `last_verified_at`, causing unverified products to be skipped until the next full interval cycle.
6. All architectural extensions must strictly adhere to ADR 0005 (pure functions only, zero OOP classes).

## Decision

1. **Centralized Functional Rate Limiter & Circuit Breaker ([`storage/rate_limiter.py`](../../storage/rate_limiter.py))**:
   - Implemented thread-safe slot scheduling using module-level state dicts and per-store `threading.Lock` primitives (pure functions, zero classes).
   - Designed sliding window slot scheduling that paces requests smoothly according to per-store `requests_per_second` and `delay_seconds`.
   - When a 429 response occurs, `trip_circuit_breaker()` activates a cooldown period for that store. Sibling threads automatically queue after the cooldown period without thundering herds.
   - Robust `parse_retry_after()` extracts numeric seconds or RFC 1123 HTTP dates from `Retry-After` headers, combined with full exponential jitter backoff (`random.uniform(1.0, 2.0 * 2^attempt)`), capped at `MAX_COOLDOWN_SECONDS = 300.0` for lockout protection.
   - Provided `create_store_limiter(store_name)` pure functional closure handle for clean dependency injection and isolated store dispatching.

2. **Browser-Grade Fingerprinting & Connection Management ([`storage/network.py`](../../storage/network.py))**:
   - Upgraded default headers to modern Chrome 133 with complete Client Hints:
     - `User-Agent`: Chrome 133 on Windows 10
     - `Sec-Ch-Ua`: `"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"`
     - `Sec-Ch-Ua-Mobile`: `?0`
     - `Sec-Ch-Ua-Platform`: `"Windows"`
     - `Sec-Fetch-Dest`: `empty`
     - `Sec-Fetch-Mode`: `cors`
     - `Sec-Fetch-Site`: `same-origin`
   - Configured `httpx.Limits(max_keepalive_connections=5, max_connections=10)` to prevent socket exhaustion during concurrent sweeps.

3. **Multi-Store Declarative Configuration ([`config/delta_config.json`](../../config/delta_config.json))**:
   - Updated global defaults: `default_max_workers: 2`, `default_requests_per_second: 2.0`, `default_delay_seconds: 0.5`, `default_timeout_seconds: 8.0`.
   - Established dedicated per-store pacing profiles (e.g. `jwpei`) with extensible schema for onboarding future retailers.

4. **Hardened Store Delta Engine ([`stores/jwpei/delta.py`](../../stores/jwpei/delta.py) & [`stores/_template/delta.py`](../../stores/_template/delta.py))**:
   - Delisted products (HTTP 404) preserve `old_availability`, `old_source_price`, and `current_source_price` to prevent null values in Shopify delta events.
   - `apply_delta_to_product` strictly stamps `last_verified_at` ONLY if `status in ("success", "not_found")`. Rate-limited and error products remain immediately eligible for subsequent polling.

5. **Global Dispatcher Diagnostics ([`sync_catalog.py`](../../sync_catalog.py))**:
   - The central orchestrator passes the store-specific rate limiter and store name into all delta checks.
   - Explicitly intercepts `status == "rate_limited"` and logs diagnostic warnings into [`logs/errors.log`](../../logs/errors.log).
   - Accurately partitions metrics into `in_stock`, `out_of_stock`, and error/rate-limited totals.

## Consequences

- **Positive**:
  - Eliminates thundering herds and WAF detection across multi-worker delta polling.
  - Delta events for Shopify sync contain 100% complete field data without null regressions.
  - Future stores can be onboarded instantly using `stores/_template/delta.py` with built-in resilience.
  - Clean error isolation in `logs/errors.log`.
- **Negative**:
  - Conservative pacing (0.5s delay, 2.0 req/s) slightly increases full catalog sweep duration, but guarantees long-term IP health and stability.
