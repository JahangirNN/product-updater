# Store Knowledge Base: [Store Name]

> **Purpose**: Document all website-specific quirks, URL query parameter patterns, DOM structures, API shortcuts, and lessons learned for this retailer. Whenever you discover a new edge case or shortcut, update this document.

---

## 1. Store Overview & Domain Identity
- **Store Name**: `[Store Name]`
- **Store Slug**: `[store_slug]`
- **Primary Domain**: `https://www.[store].com`
- **Default Currency**: `USD` (Converted to `INR`)

---

## 2. URL Filter & Query Patterns
*How does this store handle category filters, price bounds, sorting, and pagination in URLs?*

- **Category / Listing Base**: `https://www.[store].com/category/subcategory`
- **Price Filter**: e.g. `?price_min=10&price_max=50` or `?filter.v.price.gte=10`
- **Color / Option Filters**: e.g. `?color=black` or `?filter.color=Black`
- **Pagination**: e.g. `?page=2` or `?p=2`
- **Items Per Page**: e.g. `?limit=48` or `?sz=48`

---

## 3. Ingestion & Firecrawl Notes
*What prompt recipes and extraction strategies work best for this store?*

- **Listing Page Discovery**:
  - Selector or link pattern for PDPs: e.g. `a[href*="/products/"]` or `a.product-card-link`.
- **Product Page (PDP) Extraction**:
  - Is data available in JSON-LD (`<script type="application/ld+json">`)?
  - Are variants embedded in a JavaScript window object (e.g. `window.__INITIAL_STATE__`)?
  - Sizing quirks (e.g., shoe sizing vs apparel vs bags).
  - Material & Care instruction location (bullet points vs dedicated accordion).

---

## 4. Delta Updater Fast Paths (Price & Stock)
*How do we check price and stock in milliseconds without loading heavy HTML?*

- **Internal Stock / Price API Endpoint**: Does this store have an endpoint like `/api/products/{sku}/stock`?
- **Lightweight Selector**: What is the minimal CSS/XPath selector for live price and in-stock button?
  - Price selector: `span.price`
  - Stock indicator: `button.add-to-cart:not([disabled])`
- **Delisted / 404 Behavior**: If a product is removed, what HTTP status or redirect occurs?

---

## 5. Known Gotchas & Edge Cases
*Specific traps encountered and how they were resolved:*

1. **Trap**: ...
   **Solution**: ...
2. **Trap**: ...
   **Solution**: ...
