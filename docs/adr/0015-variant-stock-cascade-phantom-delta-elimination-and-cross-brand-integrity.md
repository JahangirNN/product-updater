# ADR 0015: Parent-Child Availability Cascade, Phantom Delta Elimination, and Granular Variant State Harmonization

## Status
Accepted

## Date
2026-09-18

## Context

1. **Parent-to-Child Stock Desynchronization & Ghost Stock**:
   Across large multi-brand catalogs (Coach, Michael Kors, JW PEI, Nordstrom), store delta scrapers frequently encounter partial or store-level responses. When a top-level product flips to `out_of_stock` or `delisted` (e.g., via HTTP 404 or category landing), if the store module returns an empty `variants_delta`, child variants historically retained their prior `in_stock = True` flags. This created "ghost stock" where parent records indicated unavailable while child variants falsely showed available sizes. Conversely, when a previously depleted product restocked, variants were not refreshed, resulting in products marked `in_stock` with zero available variants.

2. **Phantom Delta Transitions in Michael Kors**:
   In `stores/michaelkors/delta.py`, top-level `stock_changed` was conflated with child variant stock changes via:
   ```python
   stock_changed = (curr_avail != old_availability) or variant_stock_changed
   ```
   When a product remained `in_stock` at the parent level while a single size variant sold out, the delta engine logged a redundant top-level `DELTA:STOCK: in_stock -> in_stock` transition and queued duplicate Shopify sync events, muddying audit trails and triggering unnecessary downstream API traffic.

3. **Inconsistent Cross-Brand Variant Delta Interfaces**:
   Different store modules historically structured variant-level diffs inconsistently. Coach returned variant lists with SKUs, Michael Kors returned boolean flags, Nordstrom used Camoufox extraction dicts, and JW PEI returned single-variant dictionaries. A unified contract was required to enable generic delta event queuing and automated verification.

4. **Nordstrom Footwear Sizing Truncation & Camoufox Rehydration**:
   Initial extraction of footwear on Nordstrom suffered from variant truncation (89 of 238 products had <= 6 variants; 22 had only 1 variant) due to LLM extraction constraints on complex multi-width matrices. Rehydration via Camoufox headless browsing extracted the complete `window.__INITIAL_CONFIG__` entity tree, expanding the Nordstrom partition from 2,258 to 3,040 verified sizes (averaging 12.8 sizes/shoe), which necessitated strict adult shoe size parsing (>= 3.5) and rejection of width tokens (`2E`, `4E`, `EE`, `D`, `W`).

## Decision

1. **Parent-to-Child Availability Cascade**:
   In all store delta modules (`stores/coach/delta.py`, `stores/jwpei/delta.py`, `stores/michaelkors/delta.py`):
   - **Depletion Cascade**: When top-level availability transitions to `out_of_stock` or `delisted` and `variants_delta` is empty, cascade `in_stock = False` (and `is_available = False` for JW PEI) to every child variant.
   - **Restock Cascade**: When an out-of-stock or delisted product restocks to `in_stock` with empty `variants_delta`, cascade `in_stock = True` to child variants.
   - **Invariant Harmonization**: Whenever child variants are updated from live retailer matrices, parent availability is strictly derived from the union of its child variants:
     ```python
     any_var_stock = any(v.get("in_stock", False) for v in product["variants"])
     product["availability"] = "in_stock" if any_var_stock else "out_of_stock"
     product["is_active"] = (product["availability"] == "in_stock")
     ```

2. **Decoupling Top-Level Availability from Variant Diff Events**:
   Top-level `stock_changed` strictly measures parent state transitions:
   ```python
   stock_changed = (curr_avail != old_availability)
   ```
   Variant-level mutations are tracked independently in `variant_stock_changed` and `changed_variants`:
   ```python
   changed_variants.append({
       "sku": v_sku,
       "old_in_stock": old_v_stock,
       "new_in_stock": new_v_stock
   })
   ```
   Top-level product modification flags evaluate:
   ```python
   has_changed = price_changed or stock_changed or variant_stock_changed
   ```
   This completely eliminates phantom `in_stock -> in_stock` delta events while capturing all variant inventory shifts.

3. **Standardized Cross-Brand Delta Contract**:
   All store modules conform to a consistent dictionary return contract:
   - `status`: `"success"` | `"not_found"` | `"rate_limited"` | `"error"`
   - `price_changed`: `bool`
   - `stock_changed`: `bool` (parent level only)
   - `variant_stock_changed`: `bool`
   - `changed_variants`: `List[Dict[str, Any]]`
   - `variants_delta`: `List[Dict[str, Any]]`
   - `timestamp`: ISO-8601 UTC string

4. **Empirical Adversarial & Challenger Verification Gates**:
   Codified two comprehensive automated test suites:
   - `test_m1_catalog_adversarial.py`: 15 stress tests validating boundary scenarios, malformed inputs, 404 delistings, 429 backoffs, and whole-rupee INR rounding.
   - `test_challenger_m1_2.py`: 11 exhaustive catalog scans validating all 1,763 products and 12,240 variants for zero sizing truncations, zero fractional paise, zero ghost stock, and 100% live PDP parity.

## Consequences

- **Positive**:
  - **Zero Ghost Stock**: Guaranteed synchronization between parent availability and child variants across 1,763 products.
  - **Clean Delta Feeds**: Eliminated phantom MK transitions in `logs/freshner.log` and `storage/db/history/delta_events.jsonl`.
  - **Complete Sizing Runs**: 100% of footwear products maintain full size matrices (0 truncated models).
  - **Automated Quality Gates**: Continuous verification prevents regressions in catalog hygiene, currency conversion, and delta reporting.
- **Negative / Trade-offs**:
  - Store modules require defensive isinstance checks and cascade handling logic for both modern and legacy data shapes.
