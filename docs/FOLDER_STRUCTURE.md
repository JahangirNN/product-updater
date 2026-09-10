# Folder Structure & Modular Architecture (Screaming Functional Edition)

## 1. Directory Tree

The **Product Updater** adopts a **Screaming Functional Architecture**. The directory structure immediately reveals the core domain (stores, product groups, knowledge bases, and storage partitions) with **zero class hierarchies (ADR 0005)**:

```text
product-updater/
├── .agents/
│   └── skills/
│       ├── doc-keeper/              # Architectural guardian and alignment verifier
│       └── x-mode/                  # Definitive 6-phase brand onboarding & ingestion pipeline
│
├── .github/
│   └── workflows/
│       └── deploy-pages.yml         # CI/CD: Automated GitHub Pages deployment on push
│
├── config/
│   └── delta_config.json            # Centralized settings (60m check interval, concurrency, logging)
│
├── docs/                            # Multi-file engineering documentation & decision logs
│   ├── ARCHITECTURE.md              # System design & two-tier flow diagram
│   ├── LOGGING_SPEC.md              # Structured logging architecture, dual sinks, runbooks
│   ├── SHOPIFY_INTEGRATION_SPEC.md  # Shopify GraphQL productSet schema & warning triggers
│   ├── JSON_STORAGE_SPEC.md         # Partitioned JSON DB schema & deduplication logic
│   ├── FOLDER_STRUCTURE.md          # Directory tree & module boundaries (this file)
│   ├── CODING_STANDARDS.md          # Functional guidelines, typing, error handling
│   └── adr/                         # Architecture Decision Records
│       ├── 0001-record-architecture-decisions.md
│       ├── 0002-decouple-firecrawl-ingestion-from-local-delta-updates.md
│       ├── 0003-declarative-configuration-driven-architecture.md
│       ├── 0004-local-json-database-and-shopify-readiness.md
│       ├── 0005-functional-screaming-architecture-and-store-knowledge-bases.md
│       ├── 0006-currency-conversion-and-shopify-variants-size-guide.md
│       ├── 0007-mobile-first-catalog-viewer-and-github-pages-deployment.md
│       ├── 0008-systematic-2-hour-delta-freshner-and-timestamp-scheduling.md
│       └── 0009-centralized-logging-and-background-scheduler-daemon.md
│
├── frontend/                        # Mobile-First Catalog Data Viewer (React + Vite + Tailwind)
│   ├── public/data/
│   │   ├── catalog.json             # Consolidated static catalog (422 items)
│   │   └── meta.json                # Summary statistics & export timestamp
│   ├── src/
│   │   ├── components/              # Header, NavigationHierarchy, ProductCard, ProductDetailModal
│   │   ├── services/catalogService  # Sub-5ms instant in-memory search and multi-tier filtering
│   │   └── types/                   # Canonical TypeScript data contracts
│   ├── vite.config.ts               # base: './' for universal GitHub Pages subpath compatibility
│   └── tailwind.config.js           # Luxury Dark & Glassmorphism design tokens
│
├── logs/                            # Centralized Structured Runtime Logs (gitignored)
│   ├── freshner.log                 # General operational & cycle metrics (INFO+)
│   └── errors.log                   # Isolated error diagnostics & stack traces (ERROR+)
│
├── scripts/                         # Automation & Export CLI Scripts
│   ├── run_freshner_daemon.py       # 1-hour background scheduler daemon with heartbeat sleep
│   ├── export_viewer_data.py        # Compiles storage/db/ into frontend/public/data/catalog.json
│   ├── publish_viewer.py            # 1-command export, Vite build, git commit & push
│   └── reprocess_catalog.py         # Batch migration script to fix dimension formatting
│
├── storage/                         # Managed Local JSON Storage Room (Pure Functions)
│   ├── db.py                        # def save_product(), load_product(), append_delta_event()
│   ├── forex.py                     # def get_usd_to_inr_rate(), convert_usd_to_inr()
│   ├── logger.py                    # def init_logger(), log_info(), log_error(), log_delta()
│   ├── validator.py                 # def validate_product() against Shopify rules
│   │
│   └── db/                          # Partitioned JSON Database
│       ├── index.json               # Fast in-memory master index { id: { sku, price, last_verified_at } }
│       ├── history/                 # Append-only price/stock delta ledgers
│       │   ├── delta_events.json    # Queued shift events for Shopify Admin API sync
│       │   └── delta_log.json       # Historical batch execution audit logs
│       └── jwpei/                   # Retailer partition
│           └── products/            # Individual JSON documents (e.g. 84d55ef19c5db172.json)
│
├── stores/                          # [SCREAMING ARCHITECTURE] Self-contained store modules
│   ├── _template/                   # Starter template for onboarding any new store
│   │   ├── LEARNINGS.md             # Knowledge base template (gotchas, URL filters, API shortcuts)
│   │   ├── inflow.py                # Pure functions: normalize raw payload -> canonical
│   │   └── delta.py                 # Pure function: check_price_and_stock(), apply_delta_to_product()
│   │
│   └── jwpei/                       # Concrete JW PEI implementation
│       ├── LEARNINGS.md             # Living notes: swatch IDs, dimensions parsing, restock findings
│       ├── inflow.py                # Ingestion normalizer with responsive Size Guide generator
│       └── delta.py                 # Fast AJAX checker & pure delta mutation functions
│
├── sync_catalog.py                  # Universal multi-store delta engine & systematic scheduler
├── test_delta_engine.py             # Automated unit & integration test suite for delta engine
├── run_inflow_jwpei.py              # Store-specific full ingestion runner for JW PEI
├── .env.example                     # Sample environment variables
├── .gitignore                       # Ignored build artifacts, node_modules, temp logs
└── README.md                        # Executive blueprint, quickstart, and live deployment links
```

---

## 2. Architectural Boundaries & Rules

1. **Pure Functions Only (ADR 0005)**:
   - Every module exports top-level pure functions (`def ...`).
   - Zero classes or OOP inheritance hierarchies. Data flows as pure dictionaries with microsecond operations.
2. **Store Isolation**:
   - `stores/jwpei/` has zero dependencies on other store modules. If JW PEI DOM or endpoints change, other stores remain unaffected.
3. **Colocated Knowledge (`LEARNINGS.md`)**:
   - Every retailer partition maintains a living `LEARNINGS.md`. Any developer or subagent working on that store must read and record newly uncovered retailer quirks.
4. **Partitioned Storage**:
   - Products are organized by `storage/db/{store}/products/{id}.json`. This keeps directory listings small, prevents file locks, and makes Git diffs clean and human-inspectable.
5. **Decoupled Downstream Consumption**:
   - Viewer consumes static exports compiled from `storage/db/`.
   - Shopify sync worker consumes append-only queue events from `storage/db/history/delta_events.json`.
