# Decoupled Storefront Pricing Engine ("Price Attack")

The **Decoupled Storefront Pricing Engine** is the dynamic retail markup and charm pricing filter layer for The Rare Avenue. It sits between our canonical product database and the Shopify Admin GraphQL sync bridge, projecting supplier USD costs into customer-ready INR storefront prices without mutating raw storage.

---

## 1. Core Architecture & Invariants

```
                                      [ config/pricing_rules.json ]
                                                    │
                                                    ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────┐   ┌────────────────────────────────┐
│   storage/db/{store}/products/*.json  │   │  storage/pricing_engine.py    │   │  Shopify Admin GraphQL Bridge  │
│                                       │──▶│                               │──▶│                                │
│   • Raw source_price (USD)            │   │   Pure Functions (ADR 0005)   │   │   • ProductSetInput mutation   │
│   • Variant source_prices (USD)       │   │   Zero Database Mutation      │   │   • Storefront INR (₹X,X99)    │
│   • Supplier Single Source of Truth   │   │   Commercial Half-Up Rounding │   │   • Compare-at Price Discounter│
└───────────────────────────────────────┘   └───────────────────────────────┘   └────────────────────────────────┘
                 ▲                                          │
                 │                                          ▼
   ┌───────────────────────────┐             ┌───────────────────────────────┐
   │ 1-Hour Background Freshner│             │  storage/db/history/          │
   │      (sync_catalog.py)    │             │       delta_events.jsonl      │
   │ Detects authentic shifts  │             │   new_storefront_price_inr    │
   └───────────────────────────┘             └───────────────────────────────┘
```

### The Zero Database Mutation Invariant
- **Rule**: `storage/db/{store}/products/*.json` must **NEVER** be overwritten with retail markups.
- **Rationale**: The background freshner daemon (`sync_catalog.py`) polls supplier endpoints and compares live supplier USD prices against local USD prices. Overwriting local data with INR markups breaks the comparator, creating false positive price changes and continuous desynchronization.
- **Enforcement**: The pricing engine is purely functional (`def resolve_storefront_pricing(...) -> Tuple[float, Optional[float]]`). It returns in-memory numbers used exclusively for Shopify payloads and event logging.

---

## 2. Mathematical Models & Formulas

### A. JW PEI Linear Charm Markup (`linear_markup`)
Designed for boutique luxury bags to cover import tariffs, air freight, customs handling, and operating margin.

**Unsimplified Formulation**:
$$\text{Final Price} = \text{ROUND}\Big(\text{Source USD} \times \text{Live FX} + \big[₹2,955 + (\text{Source USD} - \$89) \times ₹14\big], -2\Big) - 1$$

**Simplified Formulation**:
$$\text{Final Price} = \text{ROUND}\Big(\text{Source USD} \times (\text{Live FX} + 14) + ₹1,709, -2\Big) - 1$$

**Parameters**:
- `base_usd`: 89.0
- `base_markup_inr`: 2955.0
- `per_usd_markup_inr`: 14.0
- `fx_addon`: 14.0
- `fixed_offset_inr`: 1709.0
- `round_nearest`: 100
- `charm_offset`: -1

### B. Percentage Markup (`percentage_markup`)
$$\text{Final Price} = \text{ROUND}\Big(\text{Source USD} \times \text{Live FX} \times (1 + \text{markup\_percent}) + \text{fixed\_fee\_inr},\; \text{nearest}\Big) + \text{charm\_offset}$$

### C. Standard Forex Fallback (`standard_forex`)
$$\text{Final Price} = \text{ROUND}\Big(\text{Source USD} \times \text{Live FX} \times \text{multiplier},\; 1\Big)$$
Used by default for unconfigured stores (e.g. Coach, Michael Kors, JD Sports) to ensure 100% backward compatibility.

---

## 3. Commercial Rounding & Charm Pricing Math

Standard Python `round()` uses **bankers rounding** (round-half-to-even), where `150` rounds to `200`, but `250` rounds to `200`. In retail pricing, this creates inconsistent price stepping.

`storage/pricing_engine.py` implements **commercial round-half-up** using Python's `decimal` module:
```python
from decimal import Decimal, ROUND_HALF_UP

def commercial_round_half_up(value: float, nearest: int = 100) -> int:
    d = Decimal(str(round(value, 4))) / Decimal(str(nearest))
    rounded = d.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(rounded * Decimal(str(nearest)))
```

Charm offset (`charm_offset = -1`) subtracts ₹1 from the rounded figure:
- ₹11,321 $\rightarrow$ Rounded: ₹11,300 $\rightarrow$ Charmed: **₹11,299**
- ₹13,481 $\rightarrow$ Rounded: ₹13,500 $\rightarrow$ Charmed: **₹13,499**
- ₹26,634 $\rightarrow$ Rounded: ₹26,600 $\rightarrow$ Charmed: **₹26,599**

Every price consistently ends in **₹.99**.

---

## 4. Multi-Price Variant Handling

Many products feature multiple variants with distinct USD source prices. For instance, in JW PEI's *Lucia Classic Top Handle Woven Bag* (`06fd42b9e640944b`):
- Standard Vegan Leather (`2T68-1`): USD $99.00
- Croc-Embossed Vegan Leather (`2T68-21`): USD $139.00

In `storage/shopify_taxonomy.py` (`resolve_options_and_variants`), the engine iterates over each individual variant:
```python
for row_key, (v, opt_val_list, v_img) in seen_variants.items():
    v_source_price = float(v.get("source_price") or prod.get("source_price") or source_price or 0.0)
    v_compare_source = v.get("source_compare_at_price") or compare_source
    
    v_inr_price, v_calc_compare = resolve_storefront_pricing(
        v_source_price, v_compare_source, store, product_type, forex_rate
    )
```

**Results**:
- Variant 1 ($99.00 USD) $\rightarrow$ **₹12,599.00**
- Variant 2 ($139.00 USD) $\rightarrow$ **₹16,999.00**

Each variant receives its own authentic, charm-rounded retail price matching its specific supplier cost.

### Out-of-Stock (OOS) Variant Floor Guard
If an out-of-stock variant is cheaper than the lowest priced in-stock variant, the OOS variant's price is automatically clamped to the in-stock floor. This prevents Shopify collection cards from advertising an artificially low, unpurchasable "from ₹X" teaser price.

---

## 5. Declarative Configuration (`config/pricing_rules.json`)

Rules are configured declaratively by store and category:

```json
{
  "version": "1.0.0",
  "stores": {
    "jwpei": {
      "default": {
        "formula": "linear_markup",
        "base_usd": 89.0,
        "base_markup_inr": 2955.0,
        "per_usd_markup_inr": 14.0,
        "fx_addon": 14.0,
        "fixed_offset_inr": 1709.0,
        "round_nearest": 100,
        "charm_offset": -1
      },
      "categories": {
        "Wallets & Small Leather Goods": {
          "formula": "percentage_markup",
          "markup_percent": 0.35,
          "fixed_fee_inr": 800.0,
          "round_nearest": 100,
          "charm_offset": -1
        }
      }
    }
  },
  "global_default": {
    "formula": "standard_forex",
    "multiplier": 1.0,
    "round_nearest": 1,
    "charm_offset": 0
  }
}
```

---

## 6. CLI Tooling (`scripts/resync_storefront_prices.py` & `scripts/research_pricing.py`)

### Step 1: Research Catalog USD Distribution
Analyzes empirical USD price distribution, quantiles (P10, P25, Median, P75, P90), price brackets, and variant spreads:
```bash
python scripts/resync_storefront_prices.py --store jwpei --research
# Or via shortcut:
python scripts/research_pricing.py --store jwpei
```

### Step 2: Formula Simulation
Tests candidate markup equations on real products without modifying configuration files:
```bash
python scripts/resync_storefront_prices.py --store jwpei --simulate \
  --formula linear_markup \
  --base-usd 89.0 --base-markup 2955.0 --per-usd 14.0
```

### Step 3: Dry-Run Verification
Previews prices calculated from active `config/pricing_rules.json`, audits charm compliance, and checks variant pricing differentiation:
```bash
python scripts/resync_storefront_prices.py --store jwpei --dry-run
python scripts/resync_storefront_prices.py --store jwpei --dry-run --category "Totes" --limit 20
```

### Step 4: Live Rollout Execution
Pushes recalculated prices and compare-at prices to Shopify Admin via GraphQL `productSet` with rate-limiting:
```bash
python scripts/resync_storefront_prices.py --store jwpei --execute --workers 3
```
