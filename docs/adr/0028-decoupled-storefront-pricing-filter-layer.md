# 0028. Decoupled Storefront Pricing Filter Layer & Price Attack Engine

## Status
Accepted

## Date
2026-10-14

## Context
Across our 7 partner retailers (3,189 canonical products and 40,021 variants), raw catalog data is ingested with supplier-native currency and pricing (primarily USD). The 1-hour background freshner daemon (`sync_catalog.py`) continually sweeps live retailer endpoints to detect true supplier stock shifts and price alterations.

Prior to this decision, retail INR conversion in `storage/shopify_taxonomy.py` directly multiplied raw USD price by the live foreign exchange rate:
$$\text{INR Price} = \text{round}(\text{Source USD} \times \text{Live FX})$$

This model presented three major business and architectural challenges:
1. **Landed Cost & Overhead Deficit**: Direct forex conversion omits international logistics, customs import tariffs, payment gateway fees, and operating margins. For luxury boutique brands like JW PEI, a structured retail markup is mandatory to ensure profitability.
2. **Database Mutation Hazard (Invariant Risk)**: If retail markups were written directly into local JSON files (`storage/db/{store}/products/*.json`), the background freshner daemon would lose the raw supplier baseline. On subsequent check cycles, comparing live retailer USD against mutated local data would falsely trigger catastrophic delta storms and corrupted price shifts.
3. **Multi-Price Variant Flattening**: In luxury bags and footwear, different variants (materials, finishes, special collaborations) frequently carry different supplier USD costs (e.g., standard colorway at $99 vs croc-embossed leather at $139). Applying a single top-level price to all variants either destroys margins on premium finishes or overprices standard items.

## Decision

We designed and implemented a **Decoupled Storefront Pricing Filter Layer** ("Price Attack") governed by the following core architectural pillars:

### 1. Zero Database Mutation Invariant
The canonical database files in `storage/db/{store}/products/*.json` remain strictly immutable with respect to retail markups. The raw `source_price` and variant-level `source_price` in USD remain the sole single source of truth for supplier delta tracking. The pricing engine acts strictly as a non-destructive read filter during Shopify payload generation (`prepare_product_set_payload`) and delta event logging.

### 2. Pure Functional Pricing Engine (`storage/pricing_engine.py`)
In accordance with ADR 0005, the pricing engine is built entirely from pure, composable functions with zero classes and zero global state:
- `load_pricing_rules(config_path)`: Thread-safe, cached declarative rule loader.
- `commercial_round_half_up(value, nearest)`: Implements commercial rounding using `decimal.Decimal` with `ROUND_HALF_UP`, avoiding Python's default bankers rounding (round-half-to-even) so halfway values round away from zero.
- `apply_charm_rounding(value, nearest, charm_offset)`: Rounds to nearest multiple (e.g. ₹100) and applies charm offset (e.g. -₹1) to produce ₹X,X99 psychological retail charm pricing.
- `resolve_storefront_pricing(source_price, compare_source_price, store, product_type, forex_rate)`: Evaluates selling price and compare-at price in parallel. If compare price $\le$ selling price, compare-at is automatically suppressed to prevent false or negative discount displays.

### 3. Declarative Pricing Rules (`config/pricing_rules.json`)
Pricing strategies are decoupled into JSON configuration with hierarchical resolution:
1. `stores.{store}.categories.{product_type}` (category-specific override)
2. `stores.{store}.default` (store-level default)
3. `global_default` (direct forex conversion fallback)

#### JW PEI Formula Validation
For JW PEI, the validated formula:
$$\text{Final Price} = \text{ROUND}(\text{Source USD} \times \text{Live FX} + [₹2,955 + (\text{Source USD} - \$89) \times ₹14], -2) - 1$$
is algebraically simplified to:
$$\text{Final Price} = \text{ROUND}(\text{Source USD} \times (\text{Live FX} + 14) + ₹1,709, -2) - 1$$
Both representations produce identical penny-for-penny outputs and are fully supported.

### 4. Variant-Level Pricing Harmony
In `storage/shopify_taxonomy.py` (`resolve_options_and_variants`), the variant generation loop iterates through every variant row and invokes `resolve_storefront_pricing` on `v_source_price` individually. Each variant receives its own calculated INR price matching its specific USD source price, while out-of-stock variants are guarded against falling below the minimum in-stock variant price floor.

### 5. Resync Tooling & Delta Ledger
- Created `scripts/resync_storefront_prices.py` providing `--store {slug} --dry-run` for statistical fit analysis and `--store {slug} --execute` for live Shopify Admin GraphQL `productSet` deployment with rate limiting.
- In `sync_catalog.py`, `new_storefront_price_inr` is appended to all delta ledger events (`delta_events.jsonl`).

## Consequences

### Positive
- **Guaranteed Profitability**: Structured landed-cost and margin offsets are consistently applied.
- **Single Source of Truth**: Supplier cost tracking in `sync_catalog.py` remains completely intact and unaffected by retail pricing experiments.
- **Psychological Pricing**: 100% compliance with charm retail endings (₹X,X99).
- **Variant Parity**: Price-differentiated variants are faithfully mirrored on Shopify storefront.
- **Declarative Extensibility**: New retailer formulas can be tested and onboarded without touching core application logic.

### Negative / Trade-Offs
- Rule modifications in `config/pricing_rules.json` do not immediately update existing Shopify products; an operator must execute `scripts/resync_storefront_prices.py --execute` to project the new rules into Shopify.
