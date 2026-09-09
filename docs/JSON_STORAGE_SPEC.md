# Local JSON Database Specification & Deduplication Rules

## 1. Why a Local JSON Database?

- **Catalog Sizing**: Expected volume is in hundreds or low thousands of targeted products (not 100,000s).
- **Portability**: Zero external database daemons (no PostgreSQL or Redis required). Entire storage can be backed up, inspected, or committed to Git.
- **Human-Readable**: Directly inspectable in any text editor or CLI tool like `jq`.
- **High Performance**: In-memory dictionary lookup with atomic file writes ensures microsecond reads and safe writes.

---

## 2. Zero-Duplicate Storage Strategy

### 2.1 The Unique Primary Key (Canonical Handle)
To guarantee that the same product is never duplicated across multiple crawl prompts or filtered URL passes:

```
Unique Key = SHA256(normalized_source_domain + "::" + normalized_sku_or_path)[:16]
```

- **Rule 1: Domain Normalization**: Strip `www.`, protocol, query parameters (unless variant ID is encoded), and trailing slashes.
- **Rule 2: SKU / Model Code Extraction**: If a retailer has an internal style ID (e.g. `43F6JVFP3L`), that forms the unique identity.
- **Rule 3: Upsert Behavior**:
  - If Key exists: Perform **delta merge** (update price, stock, audit log, keep original creation timestamp).
  - If Key does not exist: Append new product record.

---

## 3. Storage Layout Options

### Option A: Partitioned Document Store (Recommended)
```
storage/
├── db/
│   ├── index.json                   # Fast in-memory lookup index { id: { sku, site, file_path, updated_at } }
│   ├── products/
│   │   ├── coach/
│   │   │   ├── prd_a8f9c1.json
│   │   │   └── prd_e4b2d8.json
│   │   └── katespade/
│   │       └── prd_f710a3.json
│   └── history/
│       └── price_delta_log.json     # Append-only time-series ledger
```
- **Pros**: Zero write contention, atomic single-file updates, easily inspect individual products, git diffs remain tiny.

### Option B: Single Unified JSON File
```
storage/
├── db/
│   ├── catalog.json                 # All products in one JSON array/map
│   └── history.json                 # All price/stock transitions
```
- **Pros**: Simplest to read in 1 line of Python.
- **Cons**: Every 10-minute update rewrites the entire file.
