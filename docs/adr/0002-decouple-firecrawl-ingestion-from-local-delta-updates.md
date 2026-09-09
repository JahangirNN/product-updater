# ADR 0002: Decouple Firecrawl Ingestion from Local Delta Updates

## Status
Accepted

## Date
2026-09-09

## Context
Full web scraping of luxury retail websites requires circumventing anti-bot protections (Cloudflare, Kasada, PerimeterX), handling client-rendered SPA frameworks (Next.js, SFCC, Vue), resolving variant matrices, parsing image carousels, and extracting unstructured bullet points. Building and maintaining custom Playwright scrapers for every site's full catalog discovery leads to high maintenance overhead and brittle pipelines.

Conversely, running heavy full-page extraction every 10 minutes simply to check if a product price or stock status changed is wasteful, expensive, and increases the likelihood of rate limits or IP bans.

## Decision
We will separate product ingestion into a two-tier pipeline:

1. **Discovery & Deep Ingestion**: Handled by **Firecrawl** (via hosted API / MCP).
   - Firecrawl handles JavaScript execution, anti-bot circumvention, clean Markdown/JSON extraction, and LLM-ready structured output.
   - Firecrawl is triggered when new catalog URLs, collections, or sites are onboarded.
2. **Dynamic Delta Polling (Product Updater)**: Handled by **Lightweight Local Python Engine**.
   - Products from Firecrawl are saved to the "Storage Room".
   - The local updater script uses fast headless sessions (Crawlee, Playwright, or direct API/HTTP session pools) to check ONLY price and stock status on a configurable recurring schedule (e.g., every 10–30 minutes).

## Consequences
- **Positive**:
  - Dramatic reduction in custom scraper code and brittle DOM selector maintenance.
  - Efficient resource usage: high-frequency checks only fetch minimal required data (price/stock).
  - Clear separation of concerns between catalog ingestion and delta monitoring.
- **Negative**:
  - Ingestion depends on the Firecrawl API service availability and credit limits.
- **Mitigation**:
  - Store all ingested products in local storage so delta updates never require Firecrawl API calls for ongoing monitoring.
