# Shopify Product Schema & Validation Specification

## 1. Overview

This document specifies the exact field requirements, data types, and validation rules for synchronizing products scraped via Firecrawl into a Shopify store using the Shopify Admin API (GraphQL / REST).

---

## 2. Field Classification Matrix

### 2.1 Tier 1: Mandatory Fields (Hard Requirements)
If any of these fields are missing or invalid, Shopify rejects the product creation.

| Field | Shopify API Target | Type | Validation Rule |
| :--- | :--- | :--- | :--- |
| **Product Title** | `title` | String | Must not be empty. Max 255 characters. |
| **Variants Array** | `variants` | List[Object] | Must have at least 1 variant (even if single option). |
| **Variant Price** | `variants[].price` | Decimal string | Non-negative decimal formatted string (e.g. `"14500.00"`). |
| **Variant Options** | `variants[].options` | List[String] | Values must align with product `options` definition. |

### 2.2 Tier 2: E-Commerce Critical Fields (High Priority Warnings)
Missing these fields will not break API submission, but results in a degraded, unmarketable storefront listing.

| Field | Shopify API Target | Type | Warning Triggered If Missing |
| :--- | :--- | :--- | :--- |
| **Product Media** | `images[].src` | HttpUrl | `WARNING_NO_IMAGES`: Store listing will lack photos. |
| **Vendor / Brand** | `vendor` | String | `WARNING_NO_VENDOR`: Falls back to store default vendor. |
| **Variant SKU** | `variants[].sku` | String | `WARNING_NO_SKU`: Inventory sync and fulfillment cannot match. |
| **Compare-At Price** | `variants[].compareAtPrice` | Decimal string | `WARNING_NO_MSRP`: Strike-through discount won't display. Must be >= `price`. |
| **Variant Image** | `variants[].imageSrc` | HttpUrl | `WARNING_VARIANT_IMAGE_UNBOUND`: Swatching colors won't change photo. |

### 2.3 Tier 3: Rich Enrichment Fields (Medium Warnings)
Attributes that provide SEO value, conversion trust, and complete product descriptions.

| Field | Shopify API Target | Type | Warning Triggered If Missing |
| :--- | :--- | :--- | :--- |
| **Description HTML** | `descriptionHtml` | HTML string | `WARNING_NO_DESCRIPTION`: Empty body copy. |
| **Bullet Points** | Appended to `descriptionHtml` | List[String] | `WARNING_LOW_BULLETS`: Fewer than 3 feature bullets. |
| **Material Composition** | Metafield or description block | String | `WARNING_NO_MATERIAL`: Missing fabric/hardware details. |
| **Care Instructions** | Metafield or description block | List[String] | `WARNING_NO_CARE`: Missing washing/cleaning rules. |
| **Country of Origin** | Metafield or description block | String | `WARNING_NO_ORIGIN`: Missing manufacturing origin. |
| **Product Type** | `productType` | String | `WARNING_NO_TYPE`: Harder to filter in smart collections. |
| **Tags** | `tags` | List[String] | `WARNING_NO_TAGS`: Impairs collection rules. |

---

## 3. Product Status Strategy

To protect the live storefront:
- **`ACTIVE`**: Product has all Mandatory fields + at least 1 image + in stock + zero Critical warnings.
- **`DRAFT`**: Product is missing images, is out-of-stock, or has unresolved Critical/High warnings. Allows human review in Shopify Admin before going live.
- **`ARCHIVED`**: Delisted or discontinued supplier products.

---

## 4. Verified Shopify GraphQL Mutation (`productSet`)

Google Search verification confirms that **Shopify's REST API for products is deprecated**. All modern sync operations must use the GraphQL Admin API (`productSet` mutation introduced in 2024–2025):

```graphql
mutation ProductSetSync($input: ProductSetInput!, $identifier: ProductSetIdentifiers) {
  productSet(input: $input, identifier: $identifier, synchronous: true) {
    product {
      id
      title
      handle
      status
      variants(first: 50) {
        nodes {
          id
          sku
          price
          compareAtPrice
          title
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
```

### 4.1 Expected ProductSetInput JSON Payload
Our local JSON database will validate each product against this exact payload contract before saving:

```json
{
  "title": "Tabby Shoulder Bag 26",
  "descriptionHtml": "<p>A modern take on an archival 1970s Coach design...</p><ul><li>Polished pebble leather</li><li>Inside zip and multifunction pockets</li></ul>",
  "vendor": "Coach",
  "productType": "Shoulder Bags",
  "status": "DRAFT",
  "tags": ["Bags", "Leather", "Black", "Sale"],
  "productOptions": [
    {
      "name": "Color",
      "values": [{ "name": "Black" }, { "name": "Chalk" }]
    }
  ],
  "variants": [
    {
      "sku": "CH-CH857-BLK",
      "price": "39500.00",
      "compareAtPrice": "45000.00",
      "optionValues": [{ "optionName": "Color", "name": "Black" }]
    }
  ],
  "files": [
    {
      "originalSource": "https://img.coach.com/is/image/Coach/ch857_b4bk_a0",
      "alt": "Coach Tabby Shoulder Bag 26 in Black",
      "contentType": "IMAGE"
    }
  ]
}
```

---

## 5. Currency Conversion Standards (USD -> INR)

1. **Admin API Currency Rule**:
   - Shopify does **not** automatically convert prices when products are pushed via the Admin API.
   - If your store's base currency is **INR (₹)**, any price pushed is recorded directly in INR. Pushing `18.50` will list the product for `₹18.50`.
2. **Local Conversion Strategy**:
   - Use public zero-cost exchange rate feeds (`https://open.er-api.com/v6/latest/USD` or European Central Bank rates via `api.frankfurter.app`).
   - Rates are cached locally for 24 hours (`storage/forex_cache.json`).
   - Prices are converted to INR and rounded cleanly to whole rupees (e.g. `round(usd * rate)` -> `1549.00`).
3. **Forex Fluctuation Guard**:
   - To prevent exchange rate fluctuations from triggering false price change alerts every 10 minutes, the local delta updater compares the **original supplier price** against the last recorded supplier price (`source_price == old_source_price`).

---

## 6. Size Guide & Variant Architecture

### 6.1 Variant Options Structure (Max 3 Dimensions)
Shopify restricts each product to a maximum of 3 option dimensions:
- **Option 1**: `Color` (e.g. `Black`, `Cognac`, `White`)
- **Option 2**: `Size` (e.g. `US 8 / EU 41`, `US 9 / EU 42` for shoes; `S`, `M`, `L` for apparel; `One Size` for bags)
- **Option 3**: `Width` / `Material` (optional, e.g. `Medium (D)`, `Wide (EE)`)

### 6.2 Size Guide Implementation
Shopify has no native text field for size charts. We adopt a 2-tier delivery:
1. **Universal HTML Accordion (Default)**:
   - Injected into `descriptionHtml`:
   ```html
   <details class="size-guide-accordion">
     <summary><strong>📏 Size & Measurement Guide</strong></summary>
     <table class="size-guide-table">
       <thead><tr><th>US</th><th>EU</th><th>UK</th><th>Inches</th><th>CM</th></tr></thead>
       <tbody><tr><td>8</td><td>41</td><td>7.5</td><td>10.2</td><td>26.0</td></tr></tbody>
     </table>
   </details>
   ```
   - Works immediately on 100% of Shopify themes without requiring custom theme code.
2. **Product Metafield (Theme Native)**:
   - Populates `custom.size_chart` with structured table data for themes that feature dedicated size chart modal pop-ups.
