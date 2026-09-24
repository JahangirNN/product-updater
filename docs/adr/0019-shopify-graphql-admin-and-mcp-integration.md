# ADR 0019: Shopify Admin GraphQL 2026 Integration, Dynamic CLI Authentication & Dual MCP Server Architecture

## Status
Accepted

## Context
We need to bridge our catalog of 3,189 normalized luxury/designer products (40,021 variants across 7 retailers) into Shopify (*The Rare Avenue*, `hewmvw-am.myshopify.com`), keep prices and inventory live via the 1-hour delta freshner daemon, and build a custom-coded Liquid OS 2.0 storefront with Vite and Tailwind CSS.

## Decisions
1. **Dynamic CLI Session Token Resolution**:
   - `storage/shopify_auth.py` dynamically resolves the active authenticated token from Shopify CLI session storage (`%APPDATA%\shopify-cli-kit-nodejs\Config\config.json`), with fallback to `config/shopify_config.json`.
   - Enables zero-friction, auto-refreshed GraphQL authentication against `hewmvw-am.myshopify.com`.

2. **100% Modern GraphQL API (Version 2026-04)**:
   - Use `productSet` for atomic full-tree product upserts.
   - Use `bulkOperationRunMutation` for initial bulk catalog ingestion.
   - Enforce pure functional execution with zero classes.

3. **Dual MCP Server Architecture**:
   - Official `@shopify/dev-mcp@latest` for schema introspection and Liquid validation.
   - Custom `scripts/shopify_mcp_server.py` for project-specific operations (`test_connection`, `upload_product`, `sync_deltas`).

4. **Code-Driven Storefront UI**:
   - Liquid Online Store 2.0 + Vite (`vite-plugin-shopify`) + Tailwind CSS v4.
   - Seamless local development via Shopify CLI 4.x.

## Consequences
- Single-point authentication and automated token resolution.
- Zero manual token refreshes needed.
- Full parity with Shopify's 2026 developer ecosystem.
