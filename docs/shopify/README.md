# Shopify Integration & Development Guide: The Rare Avenue

**Store Domain**: `hewmvw-am.myshopify.com`  
**Custom Domain**: `therareavenue.com`  
**Store Currency**: INR (₹)  
**API Version**: `2026-04` (GraphQL)  

---

## 1. Quick Start

### Testing Store Connectivity
```bash
python -c "from storage.shopify_auth import execute_shopify_graphql; print(execute_shopify_graphql('{ shop { name currencyCode } }')[0])"
```

### Starting Theme Dev Server
```bash
shopify theme dev --store=hewmvw-am.myshopify.com
```

---

## 2. Directory Structure
- `storage/shopify_auth.py`: Dynamic token resolver & GraphQL execution engine.
- `scripts/shopify_mcp_server.py`: Custom FastMCP server for Shopify operations.
- `docs/shopify/`: Complete technical guides and GraphQL recipes.
