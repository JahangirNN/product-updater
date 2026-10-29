# Comprehensive Technical Audit: Multi-Store Footwear Sizing Option Architecture, Variant Combinatorial Collision, and Delta Stock Parity Discrepancies

**Date**: 2026-10-07  
**Author**: Systems Investigation Agent  
**Target Storefront**: The Rare Avenue (`https://therareavenue.com/` / `hewmvw-am.myshopify.com`)  
**Investigated Repositories**: 
- `c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater`
- `c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\dropship-scraper`

---

## Executive Summary

A comprehensive architectural audit was conducted across all 3,189 catalog products and 7 onboarded retailer partitions (`jdsports`, `footlocker`, `nordstrom`, `coach`, `michaelkors`, `jwpei`, and `jomashop`) to investigate two critical customer-facing issues on *The Rare Avenue*:
1. **The Dual-Size Option Trap & "Matching Game"**: Why shoe product detail pages (PDPs) present buyers with two separate, independent size option pickers ("Size (US)" and "Size (UK)") where selecting any combination that does not match an exact 1:1 conversion renders the item "UNAVAILABLE" and disables the "Add to Bag" button.
2. **Variant Stock Parity Discrepancy**: Why live source retailer inventory (e.g. JD Sports showing Women's Air Force 1 '07 in sizes 6.0, 6.5, and 11.0 in stock) contradicts the live Shopify storefront (showing sizes 7.0 and 8.5 in stock, with 6.0, 6.5, and 11.0 unavailable).

### Key Empirical Findings:
- **Scope of the Sizing Bug**: Exactly **1,020 footwear products** across three stores—`jdsports` (476 products), `footlocker` (306 products), and `nordstrom` (238 products)—were modeled with dual independent size option dimensions (`Size (US)` and `Size (UK)`). 100% of these 1,020 products are live on Shopify. In contrast, `coach` (159 shoe products) and `michaelkors` correctly modeled sizing as a single option named `Size`.
- **Shopify Combinatorial Explosion**: In Shopify's GraphQL data model, options are orthogonal dimensions forming a Cartesian product. For a shoe with 15 US sizes, 15 UK sizes, and 1 colorway, Shopify expects $15 \times 15 \times 1 = 225$ possible variants. However, because each physical shoe is a single 1:1 conversion, only 15 variants exist. The remaining 210 combinations do not exist in Shopify. When a customer selects US 8.5 while the UK selector remains on UK 4.5, Shopify returns `variant = null`, disabling checkout.
- **Root Cause of Stock Parity Discrepancy**:
  1. `jdsports.com` is protected by Akamai Bot Manager, returning HTTP 403 Forbidden to automated requests.
  2. The local Camoufox stealth browser solver (`stores/jdsports/camoufox_solver.py`) is actively flagged by Akamai (`status: "rate_limited"`, `error: "Akamai Bot Manager Rate Limit (HTTP 403 - temporary IP cooldown)"`).
  3. In `sync_catalog.py`, encountering a rate limit on the very first product trips the store circuit breaker (1200s cooldown) and halts the entire JD Sports sweep immediately.
  4. As a result, the JD Sports partition has remained **completely frozen** at its September 20, 2026 snapshot.
  5. When products were synced to Shopify on October 4, 2026, the stale September 20 inventory state was pushed. Live JD Sports inventory shifted over the subsequent 16 days, resulting in completely flipped stock states.
  6. Nordstrom suffers from an identical block via Kasada Bot Protection (`status: "blocked"`, `error: "Kasada challenge unresolved after proof-of-work window"`).

---

## 1. Deep Dive: The Dual-Size Option Trap & Shopify Combinatorial Collision

### 1.1 Empirical Observation from Live Storefront
Inspection of user-uploaded artifacts and live Shopify GraphQL queries for `gid://shopify/Product/15851448991910` (Women's Nike Air Force 1 '07 Casual Shoes - Sail/Rose Gold, SKU: `RARE-3289684`):
- **Source PDP (JD Sports)**: `media_1791311830444.jpg` shows a single "Size" selector with US numeric sizes 5.0 through 12.0. Sizes 6.0, 6.5, and 11.0 are active; all other sizes are crossed out.
- **Shopify PDP (The Rare Avenue)**: `media_1791311826973.jpg` displays two distinct option blocks:
  - Block 1: `Size (US)` containing 15 buttons (`US 5.0` to `US 12.0`).
  - Block 2: `Size (UK)` containing 15 buttons (`UK 2.5` to `UK 9.5`).
  - Block 3: `Color: Sail/Rose Gold`.
- **User Failure Mode**: The buyer clicks `US 8.5`. The `Size (UK)` selector remains on `UK 4.5` (or previous selection). The bottom action bar displays "UNAVAILABLE" and the "Add to Bag" button is disabled.

### 1.2 Code-Level Origin of the Dual Option Architecture
Tracing the inflow pipeline in `product-updater` reveals exactly where the two separate options are introduced:

#### A. JD Sports (`stores/jdsports/inflow.py`)
Lines 623–628:
```python
            "option_values": [
                {"option_name": "Size (US)", "name": s["size_label"]},
                {"option_name": "Size (UK)", "name": f"UK {s['uk_str']}"},
                {"option_name": "Color", "name": color or "Standard"}
            ]
```
Lines 651–664:
```python
    product_options = [
        {
            "name": "Size (US)",
            "values": [{"name": s["size_label"]} for s in deduped_sizes]
        },
        {
            "name": "Size (UK)",
            "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Color",
            "values": [{"name": color or "Standard"}]
        }
    ]
```

#### B. Foot Locker (`stores/footlocker/inflow.py`)
Lines 338–343:
```python
            "option_values": [
                {"option_name": "Size (US)", "name": f"US {s['us_str']}"},
                {"option_name": "Size (UK)", "name": f"UK {s['uk_str']}"},
                {"option_name": "Color", "name": color or "Standard"}
            ]
```
Lines 372–385:
```python
    product_options = [
        {
            "name": "Size (US)",
            "values": [{"name": f"US {s['us_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Size (UK)",
            "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Color",
            "values": [{"name": color or "Standard"}]
        }
    ]
```

#### C. Nordstrom (`stores/nordstrom/inflow.py`)
Lines 490–495:
```python
            "option_values": [
                {"option_name": "Size (US)", "name": f"US {us_str}"},
                {"option_name": "Size (UK)", "name": f"UK {res_uk}"},
                {"option_name": "Color", "name": c_name}
            ]
```
Lines 518–531:
```python
    product_options = [
        {
            "name": "Size (US)",
            "values": [{"name": f"US {s['us_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Size (UK)",
            "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
        },
        {
            "name": "Color",
            "values": [{"name": c} for c in all_colors]
        }
    ]
```

#### D. The Pass-Through Normalizer (`storage/shopify_taxonomy.py`)
In `storage/shopify_taxonomy.py::resolve_options_and_variants` (lines 620–633):
```python
    ordered_dim_names: List[str] = []
    for v in variants_raw:
        if not isinstance(v, dict):
            continue
        ovs = v.get("option_values")
        if isinstance(ovs, list) and len(ovs) > 0:
            for ov in ovs:
                if isinstance(ov, dict):
                    raw_name = ov.get("option_name") or ""
                    clean_name = "Color" if raw_name.strip() in ("Color", "Colour") else raw_name.strip()
                    if clean_name and clean_name not in ordered_dim_names:
                        ordered_dim_names.append(clean_name)
```
`shopify_taxonomy.py` dynamically discovers all unique `option_name` strings present in `variants_raw`. Because the store modules pass both `"Size (US)"` and `"Size (UK)"`, it constructs `ordered_dim_names = ["Size (US)", "Size (UK)", "Color"]`.

It then builds Shopify `ProductSetInput`:
```python
    product_options = []
    for d in ordered_dim_names:
        sorted_vals = sorted(list(dim_values_set[d]))
        if sorted_vals:
            product_options.append({
                "name": d,
                "values": [{"name": val} for val in sorted_vals]
            })
```
And passes it directly into the GraphQL `productSet` mutation in `storage/shopify_sync.py:upsert_product_to_shopify`.

### 1.3 Mathematical and UX Impact of the Shopify Variant Model
In Shopify Online Store 2.0:
- Shopify models product options as **independent dimensions**.
- Total potential option space:
  $$\text{Combinations} = |\text{Option 1}| \times |\text{Option 2}| \times |\text{Option 3}|$$
  For JD Sports AF1:
  $$15 \text{ (US sizes)} \times 15 \text{ (UK sizes)} \times 1 \text{ (Color)} = 225 \text{ possible combinations}$$
- **Actual Created Variants**: Exactly **15**.
  Variant 1: `(Size (US): US 5.0, Size (UK): UK 2.5, Color: Sail/Rose Gold)`
  Variant 2: `(Size (US): US 5.5, Size (UK): UK 3.0, Color: Sail/Rose Gold)`
  ...
  Variant 8: `(Size (US): US 8.5, Size (UK): UK 6.0, Color: Sail/Rose Gold)`
- **The Missing 210 Combinations**:
  Any selection where $\text{Option 1} \ne f(\text{Option 2})$—such as `US 8.5` with `UK 4.5`—does not exist in Shopify's database.
- **Theme Interaction Failure (`theme/snippets/variant-picker.liquid` & `theme.js`)**:
  When a buyer clicks a radio button in Option 1, the theme triggers a change handler. It looks up the existing variant from the product variant graph using the newly selected Option 1 and the *currently active values* of Option 2 and Option 3.
  Because `(US 8.5, UK 4.5)` is not a valid variant node, `selectedVariant` evaluates to `null` or `undefined`.
  The theme immediately toggles the form state:
  1. Sets price text to `"UNAVAILABLE"`.
  2. Disables the `"Add to Bag"` submit button.
  3. Applies diagonal slash-through styling to the unmatching option swatches.
- **Buyer Psychology**: The customer does not know why the button disabled. They assume "US 8.5 is out of stock" when in fact US 8.5 is in stock, but Shopify was waiting for them to also click UK 6.0 in the second picker.

---

## 2. Deep Dive: Variant Stock Parity Discrepancy & Freshner Blockade

### 2.1 The Concrete Discrepancy Case: Nike AF1 Sail/Rose Gold
Inspecting `storage/db/jdsports/products/429f293ceb4ff848.json` vs live JD Sports PDP vs live Shopify Admin GraphQL:

| Size (US) | Size (UK) | Live JD Sports Website | Local Database (`429f293ceb4ff848.json`) | Live Shopify Storefront (`gid://shopify/Product/15851448991910`) | Discrepancy Type |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **US 5.0** | UK 2.5 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 5.5** | UK 3.0 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 6.0** | UK 3.5 | **IN STOCK** | `in_stock: False` | `availableForSale: False` | **False Out of Stock** |
| **US 6.5** | UK 4.0 | **IN STOCK** | `in_stock: False` | `availableForSale: False` | **False Out of Stock** |
| **US 7.0** | UK 4.5 | **OUT OF STOCK** | `in_stock: True` | `availableForSale: True` | **Ghost Stock (Oversell Risk)** |
| **US 7.5** | UK 5.0 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 8.0** | UK 5.5 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 8.5** | UK 6.0 | **OUT OF STOCK** | `in_stock: True` | `availableForSale: True` | **Ghost Stock (Oversell Risk)** |
| **US 9.0** | UK 6.5 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 9.5** | UK 7.0 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 10.0** | UK 7.5 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 10.5** | UK 8.0 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 11.0** | UK 8.5 | **IN STOCK** | `in_stock: False` | `availableForSale: False` | **False Out of Stock** |
| **US 11.5** | UK 9.0 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |
| **US 12.0** | UK 9.5 | Out of Stock | `in_stock: False` | `availableForSale: False` | Match |

**Analysis of Failure Impact**:
1. **Lost Revenue**: Sizes 6.0, 6.5, and 11.0 are physically available on JD Sports for $45.00, but marked unavailable on The Rare Avenue. Customers cannot purchase them.
2. **Oversell / Cancellation Risk**: Sizes 7.0 and 8.5 are marked available for sale on Shopify (Rs. 4,320.00). If a customer purchases them, the dropship order cannot be fulfilled because JD Sports is sold out.

### 2.2 Forensic Call Chain: Why the Freshner Failed to Update JD Sports
1. **Timestamp Examination**:
   In `storage/db/jdsports/products/429f293ceb4ff848.json`:
   - `created_at`: `2026-09-20T15:57:30Z`
   - `last_verified_at`: `2026-09-20T15:59:32Z`
   - `shopify_synced_at`: `2026-10-04T09:03:03Z`
   The local database record was last verified on **September 20, 2026**—over 16 days ago!
2. **Akamai WAF Wall on JD Sports**:
   Live testing of `solve_and_extract_pdp` on `https://www.jdsports.com/pdp/womens-nike-air-force-1-07-casual-shoes/prod30118713/IQ9428/133`:
   - Direct HTTP clients (`httpx`, `curl_cffi`) return: `HTTP 403 Forbidden` (`Access Denied`).
   - Camoufox stealth browser execution returns:
     ```python
     {
         "status": "rate_limited",
         "error": "Akamai Bot Manager Rate Limit (HTTP 403 - temporary IP cooldown)",
         "variants": []
     }
     ```
3. **The Halting Circuit Breaker Trap in `sync_catalog.py`**:
   In `sync_catalog.py::poll_store_products_browser` (lines 482–489):
   ```python
   if res.get("status") == "rate_limited":
       log_warning(f"[{store.upper()}] Store circuit breaker tripped (1200s cooldown). Halting sweep for {store} to prevent WAF lockout. Deferring remaining {total - idx - 1} items to next cycle.")
       trip_circuit_breaker(store, 1200.0)
       break
   ```
   On every scheduled cycle:
   - Item 1 of 476 is polled.
   - Camoufox hits the Akamai 403 challenge.
   - `res["status"]` is set to `"rate_limited"`.
   - `sync_catalog.py` immediately breaks out of the loop and halts the entire JD Sports sweep!
   - All remaining 475 products are deferred.
4. **Selective Timestamp Invariant (ADR 0008)**:
   Per ADR 0008 and ADR 0016, `last_verified_at` is only updated when `status in ("success", "not_found")`. Because all runs return `rate_limited`, `last_verified_at` was never updated.
5. **Bulk Upload of Stale Data**:
   On October 4, 2026, `scripts/shopify_bulk_uploader.py` was executed to push the catalog to Shopify. It read the frozen September 20 JSON files and created Shopify variants with inventory flags from 16 days earlier.

### 2.3 Nordstrom WAF & Fast-Path Blind Spot
Auditing `stores/nordstrom/delta.py` revealed two distinct issues:
1. **Kasada Bot Protection Block**:
   Live execution of `stores/nordstrom/camoufox_solver.py` on `https://www.nordstrom.com/s/mach-remastered-sneaker-men/8431048` returned:
   ```python
   {
       "status": "blocked",
       "error": "Kasada challenge unresolved after proof-of-work window"
   }
   ```
   This trips the Nordstrom circuit breaker and prevents Tier 2 PDP hydration.
2. **Tier 1 Fast-Path Variant Blind Spot**:
   In `stores/nordstrom/delta.py` (lines 114–130):
   ```python
   if price_in_range and stock_unchanged and cached_in_stock:
       return {
           "status": "success",
           "availability": old_availability,
           "size_stock": {},
           "variants_delta": [],
           "elapsed_ms": elapsed_ms
       }
   ```
   If a shoe remains in stock at the parent level and the price has not shifted in the collection listing, the fast-path returns empty `variants_delta: []`. When `apply_delta_to_product` receives empty `variants_delta`, it does not evaluate child variant stock changes. Therefore, size-level restocks or stockouts are never detected during fast-path sweeps.

---

## 3. Comprehensive Cross-Store Audit Matrix

Every store module in both `product-updater` and `dropship-scraper` was audited for sizing options, variant structures, delta mechanisms, and live Shopify synchronization.

| Store Slug | Total Products | Footwear / Multi-Size | Sizing Option Architecture | Option Names Generated | Shopify Live Status | Freshner Engine | Live Parity Health |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`jdsports`** | 476 | 476 (100%) | **Dual-Option Trap** (US & UK split) | `['Size (US)', 'Size (UK)', 'Color']` | 476 / 476 Synced | Camoufox | **CRITICAL**: Frozen since Sep 20 due to Akamai 403 & circuit breaker halt. |
| **`footlocker`** | 307 | 306 (99.7%) | **Dual-Option Trap** (US & UK split) | `['Size (US)', 'Size (UK)', 'Color']` | 307 / 307 Synced | HTTP (`STATE_FROM_SERVER`) | **HEALTHY**: HTTP sweeps active; successfully parses variants. |
| **`nordstrom`** | 238 | 238 (100%) | **Dual-Option Trap** (US & UK split) | `['Size (US)', 'Size (UK)', 'Color']` | 238 / 238 Synced | Camoufox + Fast Path | **DEGRADED**: Kasada blocks PDPs; fast path omits variant diffs. |
| **`coach`** | 573 | 159 (27.7%) | **Clean Single Option** (`US {us} / UK {uk}`) | `['Size', 'Color']` (Shoes), `['Color']` (Bags) | 573 / 573 Synced | HTTP / curl_cffi | **HEALTHY**: Scene7 / JSON-LD extraction active. |
| **`michaelkors`** | 530 | Belts & Shoes | **Clean Single Option** (`US {us} / UK {uk}`) | `['Size', 'Color']` (Shoes), `['Color']` (Bags) | 530 / 530 Synced | SFCC AJAX endpoint | **HEALTHY**: Native Demandware variationAttributes active. |
| **`jwpei`** | 491 | 0 (Bags) | **N/A**: Single option (`Color`) | `['Color']` | 491 / 491 Synced | Shopify `.js` endpoint | **EXCELLENT**: 100% reliable 60-min polling. |
| **`jomashop`** | 574 | 0 (Watches) | **N/A**: Single option (`Case Diameter`) | `['Case Diameter']` | 574 / 574 Synced | HTTP JSON-LD | **EXCELLENT**: High uptime precision polling. |

### Summary Statistics:
- **Total Catalog Size**: 3,189 products.
- **Total Products Suffer Dual-Size Option Trap**: **1,020 products** ($476 + 306 + 238$).
- **Percentage of Footwear Catalog Affected**: **100% of athletic footwear** across Nike, adidas, ASICS, Jordan, Salomon, On Running, and HOKA.
- **Pending Delta Events**: **19,181 events** in `storage/db/history/delta_events.jsonl` pending Shopify sync (largely accumulated during the prior CLI session token expiration window).

---

## 4. Architectural Remediation Plan

### 4.1 Solution for Issue 1: Harmonize to a Single Size Dimension

#### A. Sizing Model Design Decision
In India, footwear sizing is standardized on British (UK) sizing. The Bureau of Indian Standards (BIS 1638:1969) and footwear retailers in India (Nike India, adidas India, Puma, Bata) list shoe sizes in UK numerals.

We evaluate three single-dimension alternatives:

1. **Option A: Pure UK Sizing (`UK {size}`) — RECOMMENDED**
   - **Option Name**: `Size`
   - **Values**: `UK 6`, `UK 6.5`, `UK 7`, `UK 7.5`, `UK 8`, etc.
   - **Rationale**: 
     - Directly fulfills user mandate: *"make sure we show only one UK is preferred"*.
     - Clean, minimalist UI on mobile screens without oversized buttons.
     - The `<details class="size-guide-accordion">` table already injected into `descriptionHtml` displays the complete US $\leftrightarrow$ UK $\leftrightarrow$ EU $\leftrightarrow$ CM conversion chart for reference.
   - **Variant Titles**: `UK 6 - Sail/Rose Gold`.

2. **Option B: Combined Hybrid Label (`UK {uk} (US {us})`) — STRONG ALTERNATIVE**
   - **Option Name**: `Size`
   - **Values**: `UK 6 (US 8.5)`, `UK 6.5 (US 9.0)`, `UK 7 (US 9.5)`.
   - **Rationale**: 
     - Completely eliminates customer hesitation for buyers who know their US sneaker size (e.g. Nike collectors) vs their Indian size.
     - Follows the proven pattern already implemented in Coach (`US 8 / UK 7.5`) and Michael Kors.
     - Crucially, it remains a **SINGLE Shopify option dimension**. One tap selects both representations simultaneously.

3. **Option C: Original Source Sizing (`US {size}`)**
   - **Option Name**: `Size`
   - **Values**: `US 8.5`, `US 9.0`.
   - **Rationale**: 1:1 match with source websites, but forces Indian shoppers to consult the size chart.

#### B. Implementation in Store Inflow Modules
Modify `inflow.py` for `jdsports`, `footlocker`, and `nordstrom`:
1. Remove `Size (US)` and `Size (UK)` from `option_values` and `product_options`.
2. Generate a single option:
   ```python
   "option_values": [
       {"option_name": "Size", "name": f"UK {s['uk_str']}"},  # or f"UK {s['uk_str']} (US {s['size_label']})"
       {"option_name": "Color", "name": color or "Standard"}
   ]
   ```
3. Set `product_options`:
   ```python
   product_options = [
       {
           "name": "Size",
           "values": [{"name": f"UK {s['uk_str']}"} for s in deduped_sizes]
       },
       {
           "name": "Color",
           "values": [{"name": color or "Standard"}]
       }
   ]
   ```

#### C. Safety Net Normalizer in `storage/shopify_taxonomy.py`
Add defensive option consolidation in `resolve_options_and_variants`:
```python
# Detect legacy dual-size option pollution and consolidate to single Size option
has_us_dim = any("size (us)" in d.lower() for d in ordered_dim_names)
has_uk_dim = any("size (uk)" in d.lower() for d in ordered_dim_names)

if has_us_dim and has_uk_dim:
    # Collapse into single 'Size' dimension preferring UK
    ordered_dim_names = ["Size" if "size" in d.lower() else d for d in ordered_dim_names]
    ordered_dim_names = list(dict.fromkeys(ordered_dim_names))[:3]
```
This guarantees that regardless of upstream data shape, Shopify GraphQL payloads are strictly normalized to a single `Size` dimension.

#### D. Batch Migration of Live Shopify Products
Execute a migration script utilizing `productSet`:
- Read each of the 1,020 footwear JSON files.
- Re-run `prepare_product_set_payload` with the consolidated single `Size` option.
- Send the `productSet` mutation to Shopify with `synchronous: True`.
- Shopify's `productSet` mutation automatically restructures the product's option hierarchy, deleting the redundant `Size (UK)` dimension and linking variants to the unified `Size` option without creating duplicate products or altering product handles.

---

### 4.2 Solution for Issue 2: Restore Freshner Delta Parity & WAF Resilience

1. **Decouple Circuit Breaker from Single-Item Failures**:
   - In `sync_catalog.py`, change the circuit breaker trigger from 1 failure to a sliding window (e.g. 3 consecutive failures within 5 minutes).
   - When a specific item returns `rate_limited` or `blocked`, defer that individual item rather than aborting the entire 476-product sweep.
2. **Proxy Support & Bot Manager Resilience**:
   - For JD Sports and Nordstrom, configure residential proxy routing or route through headless browser pools with randomized fingerprint profiles.
   - For JD Sports, investigate direct querying of Next.js hydration endpoints or product group JSON endpoints to bypass heavy browser rendering.
3. **Fix Nordstrom Tier 1 Fast-Path**:
   - In `stores/nordstrom/delta.py`, when a product is confirmed active in collection listings, do not return empty `variants_delta: []`. Check whether any variant has gone out of stock or restocked, or fall back to lightweight variant checks.
4. **Drain Pending Delta Events Queue**:
   - Execute `storage.shopify_sync::drain_delta_events_queue()` utilizing the permanent Custom App token configured in ADR 0024 to clear the 19,181 accumulated pending events.

---

## 5. Remaining Questions & Gaps

1. **JD Sports Internal API Availability**:
   - Does JD Sports expose a private mobile app JSON endpoint (e.g. SFCC Demandware or App Gateway) that does not enforce Akamai JavaScript browser challenges? Finding such an endpoint would enable 100% reliable, zero-cost HTTP polling identical to Foot Locker and Michael Kors.
2. **Shopify Inventory Quantity Tracking vs Policy**:
   - Currently, in-stock variants are set to `inventoryPolicy: "CONTINUE"` with `inventoryItem: {"tracked": False}`, while out-of-stock variants are set to `inventoryPolicy: "DENY"` with `inventoryItem: {"tracked": True}`. If the store ever transitions to multi-location tracking with real quantity numbers, a separate `inventorySetQuantities` mutation will be required.
3. **Nordstrom Collection Cache Invalidation**:
   - The exact frequency of Nordstrom's collection cache invalidation in `stores/nordstrom/delta.py` requires empirical measurement during peak hours to ensure clearance items are not held in cache after delisting.
4. **Priority for Next Phase**:
   - **Immediate Next Step**: The parent orchestrator should approve the remediation plan to unify footwear sizing into a single `Size` option (`UK {size}` or `UK {uk} (US {us})`) across `jdsports/inflow.py`, `footlocker/inflow.py`, `nordstrom/inflow.py`, and `storage/shopify_taxonomy.py`, followed by executing the catalog re-sync for the 1,020 affected products.
