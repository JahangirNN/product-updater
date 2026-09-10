# Coding Standards & Engineering Practices

## 1. Core Principles

1. **Explicit Over Implicit**: Every function signature must include complete type hints (`from typing import Optional, List, Dict`, or Python 3.10+ native pipe unions `int | None`).
2. **Fail-Fast Configuration**: If a configuration parameter or environment variable is missing or invalid, the process must terminate immediately at startup with an informative message.
3. **Graceful Degradation During Scrapes**: A single failed product check must never crash the update batch. The error is logged with context, the product is flagged, and the batch proceeds.
4. **Immutability of Historical Data**: Price history and stock transition records are strictly append-only. Never update or delete existing audit logs.

---

## 2. Python Standards & Guidelines

### 2.1 Type Annotations
All models must inherit from Pydantic `BaseModel` for automatic validation:
```python
from pydantic import BaseModel, Field, HttpUrl
from decimal import Decimal
from datetime import datetime

class DeltaCheckResult(BaseModel):
    product_id: int
    variant_sku: str
    price_current: Decimal
    price_original: Decimal | None = None
    is_in_stock: bool
    verified_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.2 Error Handling & Resilience
- Never use bare `except:` clauses. Always catch specific exceptions (`httpx.HTTPStatusError`, `playwright.async_api.TimeoutError`).
- Use exponential backoff decorators for network calls:
```python
from utils.retry import with_retry

@with_retry(max_retries=3, backoff_factor=1.5, exceptions=(httpx.RequestError,))
async def fetch_price_data(url: str) -> dict:
    ...
```

### 2.3 Centralized Structured Logging (ADR 0009)
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

## 3. Database Interaction Rules

1. **Connection Pooling**: Use managed connection pools (or context-managed SQLite connections) to prevent handle leaks.
2. **Transactions & Atomic Operations**:
   - Master record update + history append MUST execute within a single transaction block.
   - If history insertion fails, the master record update must roll back.
3. **No String Concatenation in SQL**: Always use parameterized queries (`%s` or `?`) to prevent SQL injection and type casting bugs.

---

## 4. Testing Standards

- **Unit Tests (`tests/unit/`)**: Test parsing logic, schema validation, currency conversions, and delta comparators with mock inputs (no live network calls).
- **Integration Tests (`tests/integration/`)**: Test database persistence, repository queries, and scheduler queues against an in-memory SQLite database.
- **Contract Tests**: Verify that Firecrawl output matches the `CanonicalProduct` schema.
