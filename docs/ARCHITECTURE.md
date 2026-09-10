# System Architecture Specification

## 1. Architectural Vision

Traditional scrapers combine discovery, deep attribute extraction, anti-bot circumvention, scheduling, and database persistence into a single script. When a website alters its layout or increases bot-detection measures, the entire pipeline collapses.

The **Product Updater** architecture decouples discovery from periodic updates:

```mermaid
flowchart TD
    subgraph Tier1["Tier 1: Ingestion & Discovery (Firecrawl)"]
        A[Target URLs / Search Queries] --> B[Firecrawl API / MCP Server]
        B --> C[Full Product Parser & Normalizer]
        C --> D[Canonical Product Payload]
    end

    subgraph Storage["Managed Storage Room"]
        D --> E[(Product Master Store)]
        E --> F[(Price & Stock History)]
        E --> F[(Delta Events Queue: delta_events.json)]
        E --> G[(Audit & Delta Logs: delta_log.json)]
    end

    subgraph Tier2["Tier 2: Product Updater (Local Delta Engine)"]
        H[Config Loader: config/delta_config.json] --> I[Global Dispatcher: sync_catalog.py]
        E -.->|Eligible Products where elapsed >= interval| I
        I --> J[Store Delta Modules: stores/{store}/delta.py]
        J --> K{Price or Stock Changed?}
        K -- Yes --> L[Update Product JSON, Recalc INR, Enqueue delta_events.json]
        K -- No --> M[Touch heartbeat: last_verified_at]
        L --> E
        L --> F
        M --> E
    end

    subgraph Downstream["Downstream Consumers"]
        F --> N[Shopify Admin API Sync Worker]
        E --> O[Static Exporter: scripts/export_viewer_data.py]
        O --> P[Mobile-First Catalog Viewer: React+Vite on GitHub Pages]
    end
```

---

## 2. Component Specifications

### 2.1 Tier 1: Ingestion Engine (Firecrawl)
- **Role**: Initial product discovery, rich metadata extraction, and catalog baseline establishment.
- **Tools**: Firecrawl API / Hosted MCP (`https://mcp.firecrawl.dev/v2/mcp`).
- **Data Extracted**:
  - Identity: Title, Brand, Category taxonomy, Model/Style SKU, Canonical URL.
  - Media: High-resolution image URLs, thumbnail mappings, color-specific image sets.
  - Variants: Color options, Size matrix, Variant SKUs, UPCs.
  - Detailed Attributes: Fabric/Material composition, Country of Origin, Care instructions bullet list, Technical specifications.
- **Trigger**: On-demand when new collections or targets are introduced.

### 2.2 Managed Storage Room (The Core Repository)
- **Role**: Structured, authoritative persistent store for all catalog products and their operational states.
- **Key Tables / Entities**:
  1. `products`: Canonical entity containing fixed attributes (title, brand, description, category, images, variants, materials).
  2. `product_variants`: Variant-level options (color, size, SKU, current price, stock state).
  3. `price_history`: Time-series ledger recording timestamp, variant ID, old price, new price, and discount percentage.
  4. `stock_history`: Time-series log of availability shifts (`in_stock`, `out_of_stock`, `low_stock`).
  5. `update_jobs`: Ledger of update runs, durations, success/failure counts, and rate metrics.

### 2.3 Tier 2: Product Updater (Local Delta Engine)
- **Role**: Frequent, high-speed polling of existing products to detect price fluctuations and stock depletion.
- **Key Characteristics**:
  - **Lightweight**: Does not download whole pages, heavy media, or re-parse static descriptions.
  - **Targeted**: Focuses strictly on storefront AJAX endpoints (e.g. `/products/{handle}.js` < 150ms) or JSON hydration blobs.
  - **Config-Driven**: Frequencies and rate limits are read from `config/delta_config.json` (default 60m / 1 hour).
  - **Timestamp-Based Scheduling**: Evaluates `last_verified_at` per product. Products checked < 60 minutes ago are automatically skipped with 0 network calls.
  - **Centralized Structured Logging**: Uses `storage/logger.py` (Loguru) with dual sinks (`logs/freshner.log` for operational metrics, `logs/errors.log` for isolated diagnostics). See [`docs/LOGGING_SPEC.md`](./LOGGING_SPEC.md).
  - **Tooling**:
    - Universal Dispatcher (`sync_catalog.py` with dynamic store routing to `stores/{store}/delta.py`).
    - Background Scheduler Daemon (`scripts/run_freshner_daemon.py` with responsive heartbeat sleeping and signal handling).
    - Concurrent ThreadPoolExecutor with polite pacing (80ms delay, exponential backoff on HTTP 429).
    - Shopify Delta Queue (`storage/db/history/delta_events.json`).

---

## 3. Data Contract: Canonical Product Payload

When Firecrawl ingests a product, it normalizes the raw output into a strict schema before persisting to the Storage Room:

```json
{
  "source_site": "brand_slug",
  "source_sku": "SKU-12345",
  "source_url": "https://brand.com/products/example",
  "title": "Clean Product Title",
  "brand": "Standardized Brand Name",
  "category_path": ["Women", "Bags", "Totes"],
  "description": "Full marketing description...",
  "bullet_points": [
    "100% Full-grain leather",
    "Zip-top closure",
    "Interior slip pockets"
  ],
  "material": "Full-grain leather with fabric lining",
  "care_instructions": ["Wipe clean with soft dry cloth"],
  "country_of_origin": "Italy",
  "specifications": {
    "dimensions": "12.5\" W x 10\" H x 4.5\" D",
    "handle_drop": "9\""
  },
  "images": [
    { "url": "https://...", "color": "Black", "position": 1 }
  ],
  "variants": [
    {
      "sku": "SKU-12345-BLK",
      "color": "Black",
      "size": "One Size",
      "price_current": 14500.0,
      "price_original": 18000.0,
      "currency": "INR",
      "is_available": true
    }
  ]
}
```

---

## 4. Systematic Delta Update Workflow

1. **Schedule Trigger**: Operator CLI or scheduled cron triggers `python sync_catalog.py` (reads `config/delta_config.json`, default 120m).
2. **Product-Level Eligibility Filtering**:
   - Compares `now - product.last_verified_at`.
   - If `elapsed < interval_minutes`, product is skipped (0 network calls).
   - If `elapsed >= interval_minutes` (or `--force`), product is queued for verification.
3. **Store Dynamic Dispatch**: Products are partitioned by store and dispatched to `stores/{store}/delta.py`.
4. **Execution & Polite Pacing**: Lightweight storefront AJAX checks (`/products/{handle}.js`) run across worker threads with 80ms polite delays and exponential backoff on 429.
5. **Comparison & Audit**:
   - If price has shifted: Updates `source_price` (USD), recalculates `current_price` (INR) via cached forex rate, sets `shopify_sync_pending = True`, updates `last_verified_at`, and appends an event to `storage/db/history/delta_events.json`.
   - If availability has flipped: Updates `availability` (`in_stock` $\leftrightarrow$ `out_of_stock`), updates variant availability, sets `shopify_sync_pending = True`, updates `last_verified_at`, and appends an event to `delta_events.json`.
   - If unchanged: Touches `last_verified_at` on disk and saves product.
6. **Index & Metrics Refresh**: Rebuilds fast `storage/db/index.json` and logs batch metrics to `storage/db/history/delta_log.json`.

---

## 5. Downstream Consumers

### 5.1 Mobile-First Catalog Viewer (React + Vite + Tailwind)
- **Live Deployment**: Hosted on GitHub Pages at [https://jahangirnn.github.io/product-updater/](https://jahangirnn.github.io/product-updater/).
- **Static In-Memory Model**: Uses `scripts/export_viewer_data.py` to compile `storage/db/` into `frontend/public/data/catalog.json` (1.3 MB) for sub-5ms instant filtering, multi-tier navigation (`Store -> Group -> Subgroup`), responsive Size Guide tables, and Raw JSON copy inspector.
- **Automated CI/CD**: Pushes to `main` trigger GitHub Actions (`.github/workflows/deploy-pages.yml`) which automatically builds and redeploys to GitHub Pages in ~25 seconds.

### 5.2 Shopify Admin API Sync Worker (Future Phase)
- Consumes the append-only queue at `storage/db/history/delta_events.json`.
- Executes GraphQL `productSet` mutations targeting only products flagged with `shopify_sync_pending: true`.
- Flushes the queue upon successful Shopify receipt and resets `shopify_sync_pending: false`.
