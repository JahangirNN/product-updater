# Local JSON Database Specification & Deduplication Rules

## 1. Why a Local JSON Database?

- **Catalog Sizing**: Expected volume is in hundreds or low thousands of targeted luxury products.
- **Portability**: Zero external database daemons (no PostgreSQL, MongoDB, or Redis required). Entire catalog can be backed up, inspected, or committed to Git.
- **Human-Readable**: Directly inspectable in any text editor, web viewer, or CLI tool like `jq`.
- **High Performance**: In-memory dictionary index with atomic file writes ensures microsecond reads and safe writes (`.tmp` + `os.replace`).

---

## 2. Zero-Duplicate Storage Strategy

### 2.1 The Unique Primary Key
To guarantee that the same product is never duplicated across multiple crawl prompts or filtered URL passes:

```python
raw_key = f"{clean_store}::{clean_sku}".encode("utf-8")
product_id = hashlib.sha256(raw_key).hexdigest()[:16]
```

- **Rule 1: Domain Normalization**: Lowercase store slug (e.g. `jwpei`).
- **Rule 2: SKU / Model Code Extraction**: Clean alphanumeric style SKU (e.g. `2T78-7`).
- **Rule 3: Upsert Behavior**:
  - If Key exists: Perform **atomic delta merge** (preserves `created_at`, merges `groups`, updates prices/stock/specs, updates `updated_at`).
  - If Key does not exist: Save new product document.

---

## 3. Storage Layout & Partitioned Document Store

The database is partitioned by retailer directory:

```text
storage/
└── db/
    ├── index.json                   # Fast in-memory master index
    ├── history/
    │   ├── delta_events.json        # Queued price/stock shifts for Shopify Admin API sync
    │   └── delta_log.json           # Execution batch run audit ledger
    └── jwpei/
        └── products/
            ├── 84d55ef19c5db172.json
            └── a5b2128a9d8ca9c2.json
```

---

## 4. Canonical Schemas

### 4.1 Master Index Record (`storage/db/index.json`)
```json
{
  "a5b2128a9d8ca9c2": {
    "id": "a5b2128a9d8ca9c2",
    "store": "jwpei",
    "sku": "2T78-7",
    "title": "Thea Top Handle Bag - Dark Olive",
    "handle": "thea-top-handle-bag-dark-olive",
    "source_price_usd": 99.0,
    "current_price_inr": 9389.0,
    "availability": "in_stock",
    "status": "DRAFT",
    "groups": ["handbags", "top-handle"],
    "file_path": "jwpei/products/a5b2128a9d8ca9c2.json",
    "updated_at": "2026-09-09T21:40:00Z",
    "last_verified_at": "2026-09-10T00:26:00Z",
    "shopify_sync_pending": false
  }
}
```

### 4.2 Shopify Delta Event Queue (`storage/db/history/delta_events.json`)
Staged shifts queued for consumption by the future Shopify Admin API worker:
```json
[
  {
    "event_id": "evt_1788973000_a5b2128a",
    "timestamp": "2026-09-10T00:26:00Z",
    "store": "jwpei",
    "product_id": "a5b2128a9d8ca9c2",
    "handle": "thea-top-handle-bag-dark-olive",
    "title": "Thea Top Handle Bag - Dark Olive",
    "price_changed": true,
    "old_source_price": 99.0,
    "new_source_price": 89.0,
    "new_current_price_inr": 8441.0,
    "stock_changed": false,
    "old_availability": "in_stock",
    "new_availability": "in_stock",
    "shopify_sync_pending": true
  }
]
```

### 4.3 Execution Batch Log (`storage/db/history/delta_log.json`)
Append-only log of sweep executions:
```json
[
  {
    "action": "global_delta_sync",
    "interval_minutes": 120.0,
    "force": false,
    "products_checked": 268,
    "products_skipped": 20,
    "in_stock": 263,
    "out_of_stock": 5,
    "price_changes": 0,
    "stock_changes": 0,
    "errors": 0,
    "average_latency_ms": 276.83,
    "total_time_seconds": 25.45,
    "timestamp": "2026-09-10T00:30:00Z"
  }
]
```
