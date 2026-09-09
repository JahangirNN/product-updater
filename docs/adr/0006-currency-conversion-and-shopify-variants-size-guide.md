# ADR 0006: Currency Conversion & Shopify Variants / Size Guide Standards

## Status
Accepted

## Date
2026-09-09

## Context
1. **Currency**: Scraped supplier websites predominantly list prices in foreign currencies (USD, EUR, GBP), whereas our target Shopify store operates in Indian Rupees (INR). We need a strategy to convert prices without relying on expensive paid APIs, and verify if Shopify automatically converts API prices.
2. **Variants & Size Guides**: Shopify has strict structural requirements for product options and variants, and lacks a native size guide field on the base Product object. We must determine how to format and store size guides so they integrate seamlessly into Shopify.

## Decision

### 1. Currency Conversion
- **Shopify Admin API Constraint**: The Shopify Admin API strictly expects prices in the **Store Base Currency** (INR). Passing USD values results in 1:1 numerical interpretation in INR (e.g. $18.50 becomes ₹18.50).
- **Conversion Strategy**:
  - Convert all supplier prices to INR locally before storing and syncing.
  - Use free, high-uptime public exchange rate APIs (`open.er-api.com` or `api.frankfurter.app`).
  - Cache the exchange rate locally for 24 hours to prevent redundant network calls.
  - Store both `source_price` (in original currency) and `current_price` (in INR rounded to whole rupees).
  - Delta updates compare source currency against source currency to prevent daily forex fluctuations from triggering false price change alerts.

### 2. Variants Format
- Follow Shopify GraphQL `productOptions` and `optionValues` hierarchy:
  - Product defines up to 3 options (e.g. `Color`, `Size`).
  - Each variant maps to exact `optionValues`.
  - Bind color-specific image URLs directly to the variant.

### 3. Size Guide Strategy
- Store extracted size guides as structured tables in `product.size_guide`.
- Sync to Shopify using a dual approach:
  1. Primary: Inject a clean HTML collapsible `<details><summary>Size Guide</summary>...</details>` table at the end of `descriptionHtml` (renders across all themes).
  2. Secondary: Populate the `custom.size_chart` metafield for modern themes with native pop-up blocks.

## Consequences
- **Positive**: Zero cost for currency conversion, avoids false price alert storms, guaranteed rendering of size guides on any Shopify storefront.
- **Negative**: Daily forex rate changes require periodic re-evaluation if margin thresholds shift.
