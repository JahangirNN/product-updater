# 0025. Footwear Sizing Consolidation & Canonical UK Size Option

## Status
Accepted

## Date
2026-10-07

## Context
During catalog ingestion across our three athletic footwear supplier stores (**JD Sports**, **Foot Locker**, and **Nordstrom**), footwear products were initially modeled with two distinct size option dimensions on Shopify:
- `Size (US)` (e.g., `US 8.5`, `US 9.0`)
- `Size (UK)` (e.g., `UK 8`, `UK 8.5`)

On the Shopify storefront (Prestige Theme), having two independent size options created a **combinatorial Cartesian dilemma**:
1. Shopify's variant selector renders independent pill/dropdown blocks for every option.
2. If a customer selected `Size (US): 8.5` and `Size (UK): 4.5`, Shopify evaluated the combination `(US 8.5, UK 4.5)` as non-existent, rendering the "UNAVAILABLE" badge and disabling the "Add to Bag" button.
3. Customers were forced into an unintuitive "matching game," needing to guess the exact corresponding UK size corresponding to their selected US size.
4. Furthermore, for the Indian target market (The Rare Avenue operates in INR ₹), Indian footwear standards (BIS 1638:1969) natively follow the UK footwear sizing scale. Maintaining two divergent size dimensions was both redundant and detrimental to user conversion.

## Decision
We decided to systematically eliminate dual size dimensions and standardize all footwear products to a **single canonical option**:
1. **Option Name Standardization**: All footwear variants use a single option named `Size`.
2. **Canonical Value Format**: Values strictly adhere to `UK {size}` formatting (e.g., `UK 7.5`, `UK 8`, `UK 8.5`).
3. **Inflow Normalizer Updates**: Updated `stores/jdsports/inflow.py`, `stores/footlocker/inflow.py`, and `stores/nordstrom/inflow.py` to produce variant options containing only `Size` (UK format) and `Color`.
4. **Defensive Normalization in Taxonomy Layer**: In `storage/shopify_taxonomy.py::resolve_options_and_variants`, added a defensive consolidation guard. If an incoming product payload contains both `Size (US)` and `Size (UK)`, the normalizer automatically collapses them into a single `Size` dimension preferring the UK value, preventing any Cartesian duplicate variant generation.
5. **Batch Migration Execution**: Created and ran `scripts/migrate_footwear_single_size_options.py` using Shopify Admin GraphQL `productSet` mutation, migrating all 1,021 footwear products on Shopify (`hewmvw-am.myshopify.com`) and updating the local JSON records.
6. **Responsive Size Guide Support**: A comprehensive, responsive US-to-UK-to-EU conversion table continues to be provided in the product description's `<details>` accordion and modal size guide for buyers requiring conversion assistance.

## Consequences
### Positive
- **Zero Cartesian Deadlocks**: 1-click size selection on storefront PDPs; impossible for customers to select invalid size pairings.
- **Market Alignment**: Directly conforms to Indian footwear standards (UK shoe sizes).
- **Reduced Variant Footprint**: Eliminates redundant option keys while preserving 100% SKU inventory integrity.
- **Resilient Taxonomy**: Automatic guard in `storage/shopify_taxonomy.py` ensures future imports can never re-introduce dual size dimensions.

### Negative / Trade-Offs
- Existing external links or bookmarks targeting specific old variant IDs required automatic variant redirection or default selection.
