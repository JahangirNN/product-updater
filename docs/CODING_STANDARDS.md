# Coding Standards & Engineering Practices (Pure Functional Edition)

## 1. Core Principles

1. **Explicit Over Implicit**: Every function signature must include complete type hints (`from typing import Optional, List, Dict, Any, Tuple`).
2. **Pure Functions Only (ADR 0005)**: Zero OOP classes, zero class inheritance hierarchies, and zero Pydantic `BaseModel` inheritance. Data flows as pure dictionaries with microsecond operations.
3. **Fail-Fast Configuration**: If a configuration parameter or environment variable is missing or invalid, the process must terminate immediately at startup with an informative message.
4. **Graceful Degradation During Scrapes**: A single failed product check must never crash the update batch. The error is logged with context, the product is flagged, and the batch proceeds.
5. **Immutability of Historical Data**: Price history and stock transition records are strictly append-only. Never update or delete existing audit logs.

---

## 2. Python Standards & Guidelines

### 2.1 Pure Functional Type Annotations (ADR 0005)
All data contracts are modeled as pure dictionaries and typed with Python's standard `typing` constructs:
```python
from typing import Dict, Any, Optional, Tuple, List

def check_price_and_stock(
    product: Dict[str, Any],
    client: Optional[Any] = None,
    limiter: Optional[Any] = None
) -> Dict[str, Any]:
    """Poll live price and stock status for an existing product."""
    ...
```

### 2.2 Store-Agnostic Rate Limiting & Network Resilience (ADR 0010)
- **Mandatory Permit Acquisition**: Outbound requests must call `limiter.acquire()` from `storage/rate_limiter.py` before executing requests to respect the store's `requests_per_second` ceiling.
- **Anti-Thundering-Herd Circuit Tripping**: When any thread encounters an HTTP 429, it parses `Retry-After` and trips the store circuit breaker (`trip_circuit_breaker(store, wait_sec)`), pausing all sibling threads for that store cooperatively while keeping other stores unaffected.
- **Exponential Jitter Backoff**:
```python
if resp.status_code == 429:
    wait_sec = parse_retry_after(resp.headers, default_cooldown=30.0)
    if limiter:
        trip_circuit_breaker(store_name, wait_sec)
    if attempt < 2:
        backoff = wait_sec + random.uniform(0.5, 2.0 * (2 ** attempt))
        time.sleep(backoff)
        continue
    break
```
- **Modern Browser Fingerprints**: Outbound requests must use `storage/network.py` (`get_browser_headers()` and `create_client()`) with Chrome 133 Client Hints and connection pooling limits (`max_keepalive_connections=5, max_connections=10`).

### 2.3 Delta Checking & State Integrity Invariants
- **Selective Timestamp Stamping**: `product["last_verified_at"]` MUST ONLY be stamped when `status in ("success", "not_found")`. Failed checks (`"rate_limited"` or `"error"`) must NEVER stamp `last_verified_at`, ensuring immediate retry on the next cycle.
- **Delisting (404) Attribute Preservation**: When a product is delisted (HTTP 404), preserve `old_availability`, `old_source_price`, and `current_source_price = old_source_price` to prevent `null` fields from propagating into delta events.

### 2.4 Centralized Structured Logging (ADR 0009)
- Use `storage/logger.py` powered by `loguru` (with graceful standard library fallback).
- Route logs through dual sinks:
  - `logs/freshner.log`: Operational and sync metrics (`INFO+`).
  - `logs/errors.log`: Error isolation with full stack traces (`ERROR+`, `backtrace=True`, `diagnose=True`).
  - Console: Real-time ANSI colorized terminal feedback.
- Pure functional interface:
```python
from storage.logger import log_info, log_error, log_delta

log_info("Sync cycle started")
log_delta("PRICE", "thea-top-handle-bag", "$119.0 -> $99.0 USD")
log_error("HTTP request timed out", exc=err)
```
- Full specification documented in [`docs/LOGGING_SPEC.md`](./LOGGING_SPEC.md).

---

## 3. JSON Storage & Atomic Persistence Rules (ADR 0004)

1. **Atomic File Writing**:
   - Updates to `storage/db/{store}/products/{id}.json` must write to a `.tmp` file and perform an atomic swap via `os.replace` (handled via `storage/db.py`).
2. **Deterministic Primary Keys**:
   - Product IDs must be calculated deterministically as `SHA256(store + "::" + sku)[:16]`.
3. **Append-Only History Ledgers**:
   - `storage/db/history/delta_events.json` is strictly append-only for downstream Shopify sync queue events.
   - `storage/db/history/delta_log.json` logs execution batch summaries.
4. **Master Index Generation**:
   - `storage/db/index.json` is generated purely from individual product JSON files and serves as the fast in-memory index for interval lookups.

---

## 4. Testing Standards

- **Unit & Integration Suite (`test_delta_engine.py`)**:
  - Validates declarative multi-store configuration loading.
  - Validates product-level timestamp interval logic and skip mechanics.
  - Validates price shift and stock transition calculations.
  - Validates pure functional rate limiting and circuit breaking under simulated 429 loads.
  - Validates Chrome 133 network fingerprint headers.
  - Validates 404 attribute preservation and selective timestamp stamping invariants.
  - Validates live store polling latency and polite pacing.
  - Validates multi-store isolation (Store A tripped != Store B blocked).
  - Validates dispatcher top-level exception isolation and signature introspection.
- **Contract Tests**:
  - Run `python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py` to ensure 100% alignment across architecture specs, ADRs, and store modules.
