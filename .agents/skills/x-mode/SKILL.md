---
name: x-mode
description: >-
  Executes the definitive, end-to-end "X Mode" brand onboarding, catalog scraping, quality auditing, delta freshness monitoring, and viewer publishing pipeline for any retailer or product collection URL in the product-updater project. Use whenever the user invokes "X mode", provides a brand collection URL to scrape and integrate, or asks to onboard a new retailer or collection end-to-end.
---

# Definitive "X Mode" Catalog Pipeline (`x-mode`)

"X Mode" is the project's rigorous, brand-agnostic production workflow for ingesting new retailer collections, verifying 100% attribute integrity, integrating products into the 1-hour delta freshner daemon, and publishing updates to the live mobile catalog viewer.

Whenever a user provides a collection URL and activates X Mode, execute the following 6-phase pipeline sequentially.

---

## Phase 1: Brand Discovery & Boundary Analysis

1. **Extract Retailer & Domain**:
   - Determine `brand_slug` (e.g. `jwpei`, `coach`, `polene`, `mansur-gavriel`).
   - Check if `stores/{brand_slug}/` exists.
   - If new store:
     ```bash
     cp -r stores/_template stores/{brand_slug}
     ```
     Initialize `stores/{brand_slug}/LEARNINGS.md`, `inflow.py`, and `delta.py`.
   - Register the store in `config/delta_config.json` with appropriate concurrency (`max_workers`), polite delays (`0.08s`), and endpoint patterns.

2. **Category / Scope Boundary Definition**:
   - Analyze collection URL parameters, swatch filters, and total product count.
   - Enforce strict category filters: if ingesting bags, immediately identify and reject apparel, garments, or unrelated categories.
   - Record newly discovered URL query quirks or swatch Metaobject IDs in `stores/{brand_slug}/LEARNINGS.md`.

---

## Phase 2: Ingestion & Canonical Storage (Tier 1)

1. **Scraping & Discovery**:
   - Scrape all collection pages politely using Firecrawl MCP or direct storefront JSON endpoints.
   - Extract raw product lists, handles, and URLs.

2. **Canonical Normalization (Pure Functions, ADR 0005)**:
   - **Title & Color Separation**: Separate model name from color suffix (e.g. `Title: "Noor Top Handle Bag"`, `Color: "Burgundy"`).
   - **Media Gallery**: Collect all high-resolution CDN images and bind the primary variant image.
   - **Size Guide & Accordion (ADR 0006)**: Extract bag dimensions (W x H x D), handle drop, strap drop, and materials. Generate `<details class="size-guide-accordion">` table inside `descriptionHtml`.
   - **Forex Conversion (ADR 0006)**: Convert source currency (USD/EUR/GBP) to whole INR rupees (`round(source_price * forex_rate)`) using `storage/forex.py`.
   - **Shopify Readiness (ADR 0004)**: Ensure all mandatory Shopify fields are satisfied (`title`, `vendor`, `body_html`, `variants`).

3. **Atomic Persistence & Deduplication**:
   - Primary Key: `SHA256(brand_slug + "::" + sku)[:16]`.
   - Write atomically to `storage/db/{brand_slug}/products/{product_id}.json` using `.tmp` and `os.replace` via `storage/db.py`.

---

## Phase 3: Rigorous Two-Tier Quality Audit

Do NOT skip this phase. Data integrity is the highest project priority.

### Tier A: Full Static Audit (100% of Scraped Items)
Run an automated audit script across all newly scraped items to verify:
- [ ] 100% primary keys match `SHA256(brand + "::" + sku)[:16]`.
- [ ] 100% contain `<details class="size-guide-accordion">` with valid dimension measurements.
- [ ] 100% have valid high-resolution image URLs (no broken or placeholder images).
- [ ] 100% have mathematically sound whole-rupee INR conversions.
- [ ] Exactly 0 category leaks (e.g. 0 clothing items if scraping bags).

### Tier B: Live Store Parity Audit (20 Random Samples via Subagent)
Launch a research subagent or execute a sampling script:
- Sample 20 products at random.
- Query live retailer endpoints (`.js` or storefront JSON).
- Verify 1-to-1 parity for: Title, SKU, Source Price, Current Stock State (`in_stock` vs `out_of_stock`).
- **Success Criteria**: 100.0% accuracy across all 20 samples.

---

## Phase 4: Tier 2 Freshness Integration & Daemon Enrollment

1. **Rebuild Master Index**:
   ```bash
   python -c "from storage.db import build_and_save_index; build_and_save_index()"
   ```
   Verify all newly ingested products appear in `storage/db/index.json`.

2. **Run Systematic Delta Sweep**:
   ```bash
   python sync_catalog.py --store {brand_slug}
   ```
   - Verify polite pacing (0 HTTP 429 drops, 0 errors).
   - Verify all items are stamped with live `last_verified_at` timestamps.
   - Verify immediate subsequent rerun skips 100% of fresh items in <0.1s.

3. **Continuous Monitoring Enrollment**:
   - Confirm the background daemon (`scripts/run_freshner_daemon.py`) automatically monitors the new items on its 1-hour schedule.
   - Inspect `logs/freshner.log` and verify `logs/errors.log` remains clean.

---

## Phase 5: Mobile Viewer Redesign & GitHub Pages Deployment

1. **Update Subcategory Taxonomy**:
   - In `scripts/export_viewer_data.py`, update `classify_subgroup()` with regex patterns to map new product styles into intuitive tabs.

2. **Export Static Database Bundle**:
   - Compile `frontend/public/data/catalog.json` and `meta.json`.

3. **Build & Deploy**:
   ```bash
   python scripts/publish_viewer.py
   ```
   - Rebuilds the Vite bundle.
   - Commits changes and pushes to `main`.
   - Triggers GitHub Actions workflow (`deploy-pages.yml`).
   - Verify deployment at `https://jahangirnn.github.io/product-updater/`.

---

## Phase 6: Document Preservation & Verification

1. **Update Knowledge Base**:
   - Record retailer gotchas, API tricks, rate limits, and selector quirks in `stores/{brand_slug}/LEARNINGS.md`.
2. **Run Doc-Keeper Alignment**:
   ```bash
   python .agents/skills/doc-keeper/scripts/verify_docs_alignment.py
   ```
   - Verify all stores, ADRs, and specs remain 100% aligned.
