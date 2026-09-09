# Product Updater: Architecture & Execution Blueprint

## 1. Executive Summary

The **Product Updater** is a reimagined, decoupled e-commerce intelligence system designed to solve the challenges of traditional monolithic scrapers. Instead of bundling site navigation, catalog crawling, HTML reverse-engineering, variant extraction, and periodic price/stock polling into one tangled codebase, this architecture separates responsibilities into two distinct tiers:

1. **Tier 1: Product Ingestion & Discovery (Firecrawl Engine)**
   - Utilizes Firecrawl's advanced extraction and search capabilities (via API and Model Context Protocol) to discover new products and extract high-fidelity canonical product data (titles, descriptions, bullet points, image galleries, variants, materials, care instructions).
   - Eliminates fragile anti-bot reverse-engineering and site-specific DOM query maintenance for catalog crawls.

2. **Tier 2: Product Updater (Local Delta Engine)**
   - Operates on a structured, managed "Storage Room" of already-ingested products.
   - Performs lightweight, lightning-fast targeted requests (via Crawlee, Playwright, or direct API/HTTP session pools) focusing strictly on **dynamic attributes**: **current price**, **original price**, and **stock/availability status**.
   - Governed entirely by declarative configuration files defining check intervals, schedules, rate limits, and thresholds.

---

## 2. Core Tenets & Engineering Rules

- **Zero Ad-Hoc Scripting**: No single-file monolithic scripts with mixed responsibilities. Every component has a dedicated module, explicit interface, and type contract.
- **Documentation & Decision Logs First**: Every architectural pivot, schema alteration, and technology choice is documented in structured Architecture Decision Records (ADRs).
- **Declarative Configuration**: Polling frequencies, retry backoffs, retailer endpoints, and field selectors are configured externally in YAML/JSON, never hardcoded in execution loops.
- **Resilience & Idempotency**: All updates are idempotent. If an update run fails or gets interrupted, the storage room retains its last known good state with zero data corruption.
- **Separation of Concerns**: Discovery/Full Scraping != Delta Monitoring.

---

## 3. Documentation Index

| Document | Purpose |
| :--- | :--- |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | High-level system design, data flow diagrams, and component interactions |
| [`docs/FOLDER_STRUCTURE.md`](./docs/FOLDER_STRUCTURE.md) | Proposed repository layout, module boundaries, and file organization |
| [`docs/CONFIGURATION.md`](./docs/CONFIGURATION.md) | Declarative configuration schema (schedules, intervals, site profiles) |
| [`docs/CODING_STANDARDS.md`](./docs/CODING_STANDARDS.md) | Engineering practices, typing, error handling, logging, and test strategy |
| [`docs/adr/`](./docs/adr/) | Architecture Decision Records (ADRs) tracking design choices |

---

## 4. Prerequisites & Environment

- **Python Runtime**: Python 3.10+
- **Tooling**: Crawlee, Playwright, Pydantic, PyYAML
- **Firecrawl MCP Integration**:
  - Global config: `~/.gemini/config/mcp_config.json`
  - Workspace config: `.agents/mcp_config.json`
  - Endpoint: `https://mcp.firecrawl.dev/v2/mcp`
