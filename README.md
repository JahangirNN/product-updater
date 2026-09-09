# Product Updater: Decoupled Dropshipping Intelligence Engine

A modular, screaming-architecture e-commerce catalog ingestion, delta monitoring, and visual audit platform.

🌐 **Live Catalog Viewer**: [https://jahangirnn.github.io/product-updater/](https://jahangirnn.github.io/product-updater/)  
📦 **GitHub Repository**: [https://github.com/JahangirNN/product-updater](https://github.com/JahangirNN/product-updater)

---

## 1. System Architecture

The **Product Updater** decouples heavy catalog discovery from high-speed delta monitoring:

```mermaid
flowchart TD
    subgraph Ingestion["Tier 1: Ingestion Engine"]
        A[Retailer Collections / PDPs] --> B[Firecrawl API / Store Inflow Normalizer]
        B --> C[Canonical Product JSON: storage/db/{store}/products/{id}.json]
    end

    subgraph Storage["Managed Storage Room"]
        C --> D[(Partitioned JSON DB)]
        D --> E[(Fast Master Index: storage/db/index.json)]
        D --> F[(Shopify Shift Queue: storage/db/history/delta_events.json)]
        D --> G[(Execution Audit Logs: storage/db/history/delta_log.json)]
    end

    subgraph DeltaEngine["Tier 2: Systematic Delta Freshner"]
        H[config/delta_config.json: 120m interval] --> I[sync_catalog.py Dispatcher]
        E -.->|Elapsed >= 120m| I
        I --> J[stores/{store}/delta.py]
        J --> K{Price or Stock Changed?}
        K -- Yes --> L[Update JSON, Recalculate INR, Queue delta_events.json]
        K -- No --> M[Touch last_verified_at]
        L --> D
        M --> D
    end

    subgraph Showcase["Downstream Presentation & Sync"]
        D --> N[scripts/export_viewer_data.py]
        N --> O[React 18 + Vite 6 + Tailwind Mobile Viewer on GitHub Pages]
        F --> P[Shopify Admin API GraphQL Sync Worker]
    end
```

---

## 2. Quickstart & CLI Commands

### 2.1 Run the Systematic Delta Freshner
```powershell
# 1. Normal production check (reads config/delta_config.json, 120m interval):
python sync_catalog.py

# 2. Test mode with short interval (e.g. 2 minutes, first 10 products):
python sync_catalog.py --interval 2 --limit 10

# 3. Force check all products immediately (bypasses timestamps):
python sync_catalog.py --force

# 4. Dry run (probes live endpoints without writing mutations to disk):
python sync_catalog.py --dry-run
```

### 2.2 Run Automated Test Suite
```powershell
# Executes full unit and live integration suite (config, timestamps, synthetic shifts, live JW PEI connectivity):
python test_delta_engine.py
```

### 2.3 Publish to GitHub Pages
```powershell
# Exports latest database snapshot, builds Vite bundle, commits, and pushes to GitHub Pages:
python scripts/publish_viewer.py
```

---

## 3. Architecture Decision Records (ADRs)

All engineering decisions are recorded and immutably numbered in [`docs/adr/`](./docs/adr/):

| ADR | Title | Status |
| :--- | :--- | :--- |
| **[0001](./docs/adr/0001-record-architecture-decisions.md)** | Record Architecture Decisions | Accepted |
| **[0002](./docs/adr/0002-decouple-firecrawl-ingestion-from-local-delta-updates.md)** | Decouple Firecrawl Ingestion from Local Delta Updates | Accepted |
| **[0003](./docs/adr/0003-declarative-configuration-driven-architecture.md)** | Declarative Configuration-Driven Architecture | Accepted |
| **[0004](./docs/adr/0004-local-json-database-and-shopify-readiness.md)** | Local JSON Database & Shopify Readiness | Accepted |
| **[0005](./docs/adr/0005-functional-screaming-architecture-and-store-knowledge-bases.md)** | Functional Screaming Architecture & Store Knowledge Bases | Accepted |
| **[0006](./docs/adr/0006-currency-conversion-and-shopify-variants-size-guide.md)** | Currency Conversion & Shopify Variants Size Guide | Accepted |
| **[0007](./docs/adr/0007-mobile-first-catalog-viewer-and-github-pages-deployment.md)** | Mobile-First Catalog Viewer & Automated GitHub Pages Deployment | Accepted |
| **[0008](./docs/adr/0008-systematic-2-hour-delta-freshner-and-timestamp-scheduling.md)** | Systematic 2-Hour Delta Freshner & Timestamp-Based Scheduling | Accepted |

---

## 4. Documentation Index

- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md): Full system architecture, two-tier workflows, and downstreams.
- [`docs/FOLDER_STRUCTURE.md`](./docs/FOLDER_STRUCTURE.md): Screaming functional directory tree and module boundaries.
- [`docs/JSON_STORAGE_SPEC.md`](./docs/JSON_STORAGE_SPEC.md): Database partitioning, primary key hashing, and JSON schemas.
- [`docs/SHOPIFY_INTEGRATION_SPEC.md`](./docs/SHOPIFY_INTEGRATION_SPEC.md): GraphQL `productSet` mutation contracts and Size Guide tables.
- [`docs/CODING_STANDARDS.md`](./docs/CODING_STANDARDS.md): Pure functions, typing standards, and atomic file writes.
- `stores/jwpei/LEARNINGS.md`: Living retailer knowledge base for JW PEI (query filters, swatch IDs, fast endpoints).
