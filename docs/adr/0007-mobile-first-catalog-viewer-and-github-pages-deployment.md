# ADR 0007: Mobile-First Catalog Viewer & Automated GitHub Pages Deployment

## Status
Accepted

## Date
2026-09-09

## Context
As our ingestion engine and delta updaters populate the partitioned local JSON database (`storage/db/`), developers, operators, and stakeholders need a rapid, visual, and intuitive way to audit the catalog without querying JSON files via terminal commands. The viewer must:
1. Showcase products on mobile viewports as a primary priority (touch-friendly, luxury card aesthetic, slide-up modal sheets).
2. Display multi-tier hierarchy navigation: **Level 1 (Retailer)** $\to$ **Level 2 (Group)** $\to$ **Level 3 (Carrying Style / Subcategory)** with item counts and headings.
3. Feature dual pricing (primary whole-rupee INR alongside source USD), color swatches, interactive Size & Measurement Guide tables, and a collapsible Raw JSON Inspector for auditing.
4. Be hosted on GitHub Pages for zero-cost, serverless internal viewing.
5. Provide sub-5ms instant in-memory search and filtering across the entire catalog.

## Decision
1. **Frontend Stack**: Built using **React 18 + Vite 6 + Tailwind CSS v3 + TypeScript + Lucide-React** located in `frontend/`.
2. **Relative Base Path for GitHub Pages**:
   - Configured `base: './'` in `frontend/vite.config.ts` to eliminate root subpath 404 and MIME-type mismatch errors when hosted under `https://<username>.github.io/<repo-name>/`.
3. **Consolidated Static In-Memory Data Model**:
   - A dedicated export script (`scripts/export_viewer_data.py`) scans `storage/db/` and generates a single static JSON bundle (`frontend/public/data/catalog.json`) and summary metadata (`meta.json`).
   - The React client loads this bundle once into memory on mount, enabling sub-5ms instantaneous client-side filtering, multi-field search, and sorting.
4. **Automated CI/CD & Deployment**:
   - **GitHub Actions Workflow** (`.github/workflows/deploy-pages.yml`): Automatically exports fresh data, installs dependencies, builds Vite production assets, and deploys to GitHub Pages on every push to `main` affecting `frontend/`, `storage/db/`, or export scripts.
   - **CLI Publisher** (`scripts/publish_viewer.py`): A one-command Python CLI that automates exporting DB snapshot $\to$ building Vite $\to$ staging $\to$ committing $\to$ pushing to GitHub.

## Consequences
- **Positive**: Operators can verify product titles, dual currency pricing, sizing accordions, and images directly on mobile devices or desktop browsers with zero operational server maintenance.
- **Negative**: When catalog grows past 5,000+ products, a single static JSON bundle may exceed 10 MB. At that scale, pagination or chunked static JSON partitions will be adopted.
