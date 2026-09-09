# Folder Structure & Modular Architecture (Screaming Functional Edition)

## 1. Directory Tree

The **Product Updater** adopts a **Screaming Functional Architecture**. The directory structure immediately reveals the core domain (stores, product groups, knowledge bases, and storage partitions) with **zero class hierarchies**:

```text
product-updater/
├── .agents/
│   └── mcp_config.json              # Workspace Firecrawl MCP configuration
│
├── config.yaml                      # Declarative global settings (scheduler intervals, batch sizes)
├── config_loader.py                 # Pure function: load_config() -> dict
│
├── docs/                            # Multi-file engineering documentation & decision logs
│   ├── ARCHITECTURE.md              # System design & two-tier flow diagram
│   ├── SHOPIFY_INTEGRATION_SPEC.md  # Shopify GraphQL productSet schema & warning triggers
│   ├── JSON_STORAGE_SPEC.md         # Partitioned JSON DB schema & deduplication logic
│   ├── FOLDER_STRUCTURE.md          # Directory tree & module boundaries (this file)
│   ├── CODING_STANDARDS.md          # Functional guidelines, typing, error handling
│   └── adr/                         # Architecture Decision Records
│       ├── 0001-record-architecture-decisions.md
│       ├── 0002-decouple-firecrawl-ingestion-from-local-delta-updates.md
│       ├── 0003-declarative-configuration-driven-architecture.md
│       ├── 0004-local-json-database-and-shopify-readiness.md
│       └── 0005-functional-screaming-architecture-and-store-knowledge-bases.md
│
├── stores/                          # [SCREAMING ARCHITECTURE] Self-contained store modules
│   ├── _template/                   # Starter template for onboarding any new store
│   │   ├── LEARNINGS.md             # Knowledge base template (gotchas, URL filters, API shortcuts)
│   │   ├── inflow.py                # Pure functions: normalize Firecrawl raw output -> canonical
│   │   └── delta.py                 # Pure function: fetch_latest_price_stock(product) -> delta
│   │
│   ├── xyz_store/                   # Concrete store implementation
│   │   ├── LEARNINGS.md             # Living notes: URL query filters, DOM quirks, fast endpoints
│   │   ├── inflow.py                # Firecrawl normalization functions for xyz_store
│   │   ├── delta.py                 # Fast price/stock updater for xyz_store
│   │   └── groups/                  # Category-specific logic (only if needed)
│   │       ├── sports_shoes.py      # Custom shoe size converter / filter parser
│   │       └── jackets.py           # Apparel sizing logic
│   │
│   ├── coach/                       # Luxury retailer module
│   │   ├── LEARNINGS.md
│   │   ├── inflow.py
│   │   └── delta.py
│   │
│   └── katespade/                   # Luxury retailer module
│       ├── LEARNINGS.md
│       ├── inflow.py
│       └── delta.py
│
├── storage/                         # Managed Local JSON Storage Room (Pure Functions)
│   ├── __init__.py
│   ├── reader.py                    # def get_product(id), def list_products(store, group)
│   ├── writer.py                    # def save_product(p), def record_delta(id, price, stock)
│   ├── deduplicator.py              # def make_unique_id(store, sku) -> SHA256 hash
│   ├── validator.py                 # def validate_shopify(p) -> warnings_list
│   │
│   └── db/                          # The Partitioned JSON Database
│       ├── index.json               # Fast in-memory master index { id: { store, group, sku, path } }
│       ├── history/                 # Append-only price/stock delta ledger
│       │   └── delta_log.json
│       └── products/                # Partitioned product documents
│           ├── xyz_store/
│           │   ├── sports_shoes/    # e.g. prd_a8f9c1.json, prd_e4b2d8.json
│           │   └── jackets/
│           └── coach/
│               └── handbags/
│
├── engine/                          # Functional Orchestrator
│   ├── runner.py                    # def run_updater_loop() -> runs scheduled delta cycles
│   └── dispatcher.py                # def dispatch_delta_check(store_slug, product_dict)
│
├── firecrawl_ingest/                # Firecrawl API Client & Two-Step Workflow
│   ├── client.py                    # def firecrawl_discover(url, filters) -> list[urls]
│   └── scraper.py                   # def firecrawl_deep_scrape(url) -> raw_product_dict
│
├── utils/                           # Shared Stateless Utilities
│   ├── logger.py                    # Structured logging setup
│   ├── currency.py                  # def to_inr(amount, source_curr) -> float
│   └── retry.py                     # def retry_async(fn, retries=3)
│
├── .env.example                     # Sample environment variables
├── .gitignore                       # Ignored virtual envs, temp logs, local databases
├── main.py                          # Unified CLI entry point
└── README.md                        # Project executive summary and quickstart
```

---

## 2. Architectural Boundaries & Rules

1. **Pure Functions Only**:
   - Every file exports top-level functions (`def ...`).
   - No `class Scraper` or inheritance hierarchies. Data flows as pure dictionaries or Pydantic models.
2. **Store Isolation**:
   - `stores/xyz_store/` has zero dependencies on `stores/coach/`. If Coach breaks, XYZ Store is completely unaffected.
3. **Colocated Knowledge (`LEARNINGS.md`)**:
   - Every store folder contains its own `LEARNINGS.md`. Any developer or agent working on that store must read and update this file with newly discovered quirks, query parameter structures, or DOM changes.
4. **Partitioned Storage**:
   - Products are organized by `store_slug/product_group/`. This keeps directory listings small, prevents file system lock contention, and makes Git diffs clean and human-inspectable.
