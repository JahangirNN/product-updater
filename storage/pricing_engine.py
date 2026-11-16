"""
Decoupled Storefront Pricing Filter Layer
Pure functional engine for dynamic retail markups and charm pricing (ADR 0005, ADR 0028).

ZERO DATABASE MUTATION INVARIANT:
The local canonical database (storage/db/{store}/products/*.json) retains raw supplier
source prices in USD. This module acts strictly as a non-destructive read-filter layer
when projecting catalog items into Shopify storefront payloads and sync events.
"""
import os
import re
import json
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, Tuple, List

DEFAULT_PRICING_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "pricing_rules.json"
)

# In-memory config cache: (cached_dict, mtime)
_CONFIG_CACHE: Tuple[Optional[Dict[str, Any]], float] = (None, 0.0)

GLOBAL_DEFAULT_RULE = {
    "formula": "standard_forex",
    "description": "Universal fallback forex conversion with 99 charm rounding",
    "multiplier": 1.0,
    "round_nearest": 100,
    "charm_offset": -1
}


def load_pricing_rules(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load declarative pricing rules from config/pricing_rules.json.
    Uses in-memory caching validated against file mtime.
    Falls back gracefully to standard forex defaults if config is absent or unparseable.
    """
    global _CONFIG_CACHE
    path = config_path or DEFAULT_PRICING_CONFIG_PATH

    try:
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            cached_data, cached_mtime = _CONFIG_CACHE
            if cached_data is not None and cached_mtime == mtime and config_path is None:
                return cached_data

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if config_path is None:
                    _CONFIG_CACHE = (data, mtime)
                return data
    except Exception as exc:
        print(f"[WARN] Failed to load pricing rules from {path}: {exc}. Using standard forex defaults.")

    return {
        "version": "1.0.0",
        "stores": {},
        "global_default": GLOBAL_DEFAULT_RULE
    }


def _clean_price(val: Any) -> Optional[float]:
    """
    Defensively convert price/currency string, number, or None to clean float.
    Handles dirty strings (e.g. '$515.00', '1,299.50') and non-positive inputs.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val > 0 else 0.0
    try:
        clean = re.sub(r'[^\d.]', '', str(val))
        return float(clean) if clean else None
    except (ValueError, TypeError):
        return None


def commercial_round_half_up(value: float, nearest: int = 100) -> int:
    """
    Commercial round-half-up to the nearest multiple of `nearest`.
    Unlike Python's default bankers rounding (round-half-to-even),
    halfway points always round away from zero (e.g. 11,350 -> 11,400).
    """
    if value <= 0:
        return 0

    if nearest <= 1:
        d = Decimal(str(round(value, 4)))
        return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    d = Decimal(str(round(value, 4))) / Decimal(str(nearest))
    rounded = d.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(rounded * Decimal(str(nearest)))


def apply_charm_rounding(value: float, nearest: int = 100, charm_offset: int = -1) -> float:
    """
    Apply commercial round-half-up to nearest N, then adjust by charm_offset.
    E.g., value=11321.0, nearest=100, charm_offset=-1 -> 11300 - 1 = 11299.0
    Guarantees strictly positive result for positive inputs (prevents ₹0 checkout bug).
    """
    if value <= 0:
        return 0.0

    rounded = commercial_round_half_up(value, nearest)
    charmed = rounded + charm_offset
    if charmed <= 0:
        # Prevent free product checkout: minimum positive charmed threshold
        min_charm = nearest + charm_offset if (nearest + charm_offset) > 0 else 1
        return float(max(1, min_charm))

    return float(charmed)


DEFAULT_DISCOUNT_BRACKETS = [
    {"max_discount": 0.25, "markup": 0.16},
    {"min_discount": 0.25, "max_discount": 0.30, "markup": 0.18},
    {"min_discount": 0.30, "max_discount": 0.40, "markup": 0.29},
    {"min_discount": 0.40, "max_discount": 0.50, "markup": 0.40},
    {"min_discount": 0.50, "max_discount": 0.60, "markup": 0.50},
    {"min_discount": 0.60, "markup": 0.70},
]


def resolve_bracket_markup(
    discount_pct: float,
    brackets: Optional[List[Dict[str, Any]]] = None
) -> float:
    """
    Resolve the markup percentage for a given supplier discount off MSRP.
    Default schedule (ADR 0028):
    - < 25%: 16% (0.16)
    - 25% – 29.99%: 18% (0.18)
    - 30% – 39.99%: 29% (0.29)
    - 40% – 49.99%: 40% (0.40)
    - 50% – 59.99%: 50% (0.50)
    - 60%+: 70% (0.70)
    """
    active_brackets = brackets if (brackets and isinstance(brackets, list)) else DEFAULT_DISCOUNT_BRACKETS
    d_val = round(float(discount_pct), 6)

    for b in active_brackets:
        min_d = float(b["min_discount"]) if b.get("min_discount") is not None else float('-inf')
        max_d = b.get("max_discount")
        if max_d is not None:
            max_d_val = float(max_d)
            if min_d <= d_val < max_d_val:
                return float(b.get("markup", 0.0))
        else:
            if d_val >= min_d:
                return float(b.get("markup", 0.0))

    return 0.16


def resolve_price_bracket_markup(
    base_inr: float,
    brackets: Optional[List[Dict[str, Any]]] = None
) -> float:
    """
    Resolve the markup percentage for a given base converted price (base_inr = USD * FX).
    Supports bracket definitions with min_inr/max_inr (or min_price/max_price, min_cost/max_cost)
    and markup_percent (or markup).
    Default fallback: 0.35
    """
    if not brackets or not isinstance(brackets, list):
        return 0.35

    val = round(float(base_inr), 4)

    for b in brackets:
        min_v_raw = b.get("min_inr") if b.get("min_inr") is not None else b.get("min_price", b.get("min_cost"))
        max_v_raw = b.get("max_inr") if b.get("max_inr") is not None else b.get("max_price", b.get("max_cost"))

        min_val = float(min_v_raw) if min_v_raw is not None else float('-inf')
        max_val = float(max_v_raw) if max_v_raw is not None else float('inf')

        markup = b.get("markup_percent")
        if markup is None:
            markup = b.get("markup", 0.0)
        markup_float = float(markup)

        if min_v_raw is None:
            if val <= max_val:
                return markup_float
        elif max_v_raw is None:
            if val > min_val:
                return markup_float
        else:
            if min_val < val <= max_val:
                return markup_float

    return 0.35


def resolve_usd_bracket_markup(
    source_usd: float,
    brackets: Optional[List[Dict[str, Any]]] = None
) -> float:
    """
    Resolve the markup percentage for a given supplier USD source price.
    Evaluates USD brackets with precise inclusive/exclusive boundary semantics:
    - Under $20: val < 20.0
    - $20 to $30 inclusive: 20.0 <= val <= 30.0
    - Above $30 to $40 inclusive: 30.0 < val <= 40.0
    - Above $40: val > 40.0
    Fallback default: 0.40 (40%)
    """
    if not brackets or not isinstance(brackets, list):
        return 0.40

    val = round(float(source_usd), 4)

    for b in brackets:
        min_u_raw = b.get("min_usd")
        max_u_raw = b.get("max_usd")
        min_val = float(min_u_raw) if min_u_raw is not None else float('-inf')
        max_val = float(max_u_raw) if max_u_raw is not None else float('inf')

        markup = b.get("markup_percent")
        if markup is None:
            markup = b.get("markup", 0.40)
        markup_float = float(markup)

        if min_u_raw is None:
            # Under max_usd (e.g. < $20)
            if val < max_val:
                return markup_float
        elif max_u_raw is None:
            # Above min_usd (e.g. > $40)
            if val > min_val:
                return markup_float
        else:
            # Bounded tier (e.g. $20 to $30 inclusive, or above $30 to $40 inclusive)
            inclusive_min = b.get("inclusive_min", (abs(min_val - 20.0) < 0.001))
            if inclusive_min:
                if min_val <= val <= max_val:
                    return markup_float
            else:
                if min_val < val <= max_val:
                    return markup_float

    return 0.40


def get_rule_for_product(
    store: str,
    product_type: str = "",
    rules: Optional[Dict[str, Any]] = None,
    vendor: str = ""
) -> Dict[str, Any]:
    """
    Resolve the matching pricing rule for a given store, vendor/brand, and product category.
    Precedence:
    1. stores[store].vendors[vendor] / brands[vendor]
    2. stores[store].categories[product_type] / categories[vendor]
    3. Universal categories[product_type] (e.g. Watches across any store)
    4. stores[store].default
    5. global_default
    Handles store normalization (e.g. 'JW PEI', 'jw-pei', 'jwpei') and singular/plural category matching.
    """
    active_rules = rules or load_pricing_rules()
    safe_store = (store or "").lower().strip()
    norm_store = re.sub(r'[^a-z0-9]', '', safe_store)
    clean_type = (product_type or "").strip()
    clean_vendor = (vendor or "").strip()

    stores_dict = active_rules.get("stores", {})
    store_entry = stores_dict.get(safe_store)
    if not isinstance(store_entry, dict) and norm_store:
        for k, v in stores_dict.items():
            if re.sub(r'[^a-z0-9]', '', k.lower()) == norm_store:
                store_entry = v
                break

    if isinstance(store_entry, dict):
        # 1. Vendor / Brand specific override (e.g. Tissot)
        vendors_dict = {
            **(store_entry.get("brands") or {}),
            **(store_entry.get("vendors") or {})
        }
        if isinstance(vendors_dict, dict):
            if clean_vendor:
                if clean_vendor in vendors_dict:
                    return vendors_dict[clean_vendor]
                for v_name, v_rule in vendors_dict.items():
                    if v_name.lower() == clean_vendor.lower():
                        return v_rule
            if clean_type:
                if clean_type in vendors_dict:
                    return vendors_dict[clean_type]
                for v_name, v_rule in vendors_dict.items():
                    if v_name.lower() == clean_type.lower():
                        return v_rule

        # 2. Store category specific override
        cat_rules = store_entry.get("categories", {})
        if isinstance(cat_rules, dict):
            if clean_vendor:
                if clean_vendor in cat_rules:
                    return cat_rules[clean_vendor]
                for cat_name, cat_rule in cat_rules.items():
                    if cat_name.lower() == clean_vendor.lower() or cat_name.lower().rstrip('s') == clean_vendor.lower().rstrip('s'):
                        return cat_rule

            if clean_type:
                if clean_type in cat_rules:
                    return cat_rules[clean_type]
                for cat_name, cat_rule in cat_rules.items():
                    if cat_name.lower() == clean_type.lower() or cat_name.lower().rstrip('s') == clean_type.lower().rstrip('s'):
                        return cat_rule

        # 3. Universal Category override (e.g. Watches category across any store)
        global_cats = active_rules.get("categories", {})
        if isinstance(global_cats, dict) and clean_type:
            if clean_type in global_cats:
                return global_cats[clean_type]
            for cat_name, cat_rule in global_cats.items():
                if cat_name.lower() == clean_type.lower() or cat_name.lower().rstrip('s') == clean_type.lower().rstrip('s'):
                    return cat_rule

        # 4. Store default
        if "default" in store_entry and isinstance(store_entry["default"], dict):
            return store_entry["default"]

    # 5. Universal Category fallback for unconfigured store or vendor-as-category
    global_cats = active_rules.get("categories", {})
    if isinstance(global_cats, dict):
        if clean_type:
            if clean_type in global_cats:
                return global_cats[clean_type]
            for cat_name, cat_rule in global_cats.items():
                if cat_name.lower() == clean_type.lower() or cat_name.lower().rstrip('s') == clean_type.lower().rstrip('s'):
                    return cat_rule
        if clean_vendor:
            if clean_vendor in global_cats:
                return global_cats[clean_vendor]
            for cat_name, cat_rule in global_cats.items():
                if cat_name.lower() == clean_vendor.lower() or cat_name.lower().rstrip('s') == clean_vendor.lower().rstrip('s'):
                    return cat_rule

    # 6. Global default
    return active_rules.get("global_default", GLOBAL_DEFAULT_RULE)


def apply_pricing_formula(
    source_price: float,
    rule: Dict[str, Any],
    forex_rate: float,
    compare_source_price: Optional[float] = None
) -> float:
    """
    Compute storefront price in INR from USD source price using rule specifications.
    Pure function with zero side effects.
    Supports linear_markup, percentage_markup, discount_bracket_markup, and standard_forex.
    """
    price_val = _clean_price(source_price) or 0.0

    if price_val <= 0.0 or (forex_rate is not None and forex_rate <= 0.0):
        return 0.0

    formula = rule.get("formula", "standard_forex")
    raw_round = rule.get("round_nearest")
    round_nearest = int(raw_round) if raw_round is not None else 100
    raw_charm = rule.get("charm_offset")
    charm_offset = int(raw_charm) if raw_charm is not None else -1

    if formula == "discount_bracket_markup":
        comp_val = _clean_price(compare_source_price)

        # Calculate supplier discount off MSRP: (MSRP - USD) / MSRP
        # Discount and safety ceiling ONLY exist when official brand MSRP exceeds source price
        has_valid_msrp = comp_val is not None and comp_val > price_val
        if has_valid_msrp:
            discount_pct = (comp_val - price_val) / comp_val
        else:
            discount_pct = 0.0

        brackets = rule.get("brackets")
        markup_pct = resolve_bracket_markup(discount_pct, brackets)

        # Formula equation: Final Price = ROUND((SourceUSD × FX) × (1 + Markup), -2) - 1
        raw_inr = (price_val * forex_rate) * (1.0 + markup_pct)

        # Safety Ceiling Invariant: Ensure final price never exceeds official brand MSRP (source_compare_at_price × FX)
        # Protects low-discount items like the WNBA watch from exceeding brand retail.
        # NEVER applies when comp_val <= price_val (preventing negative-margin / below-cost selling).
        if has_valid_msrp:
            msrp_raw = comp_val * forex_rate
            raw_inr = min(raw_inr, msrp_raw)

        final_price = apply_charm_rounding(raw_inr, round_nearest, charm_offset)

        if has_valid_msrp:
            msrp_charmed = apply_charm_rounding(comp_val * forex_rate, round_nearest, charm_offset)
            if final_price > msrp_charmed:
                final_price = msrp_charmed

        return final_price

    elif formula == "linear_markup":
        # Check explicit base_markup_inr first (intuitive declarative config)
        if "base_markup_inr" in rule and ("per_usd_markup_inr" in rule or "fx_addon" in rule):
            base_usd = float(rule.get("base_usd", 89.0))
            base_markup = float(rule.get("base_markup_inr", 2955.0))
            per_usd = float(rule.get("per_usd_markup_inr", rule.get("fx_addon", 14.0)))
            markup = base_markup + (price_val - base_usd) * per_usd
            raw_inr = (price_val * forex_rate) + markup
        elif "fixed_offset_inr" in rule:
            fx_addon = float(rule.get("fx_addon", 0.0))
            fixed_offset = float(rule.get("fixed_offset_inr", 0.0))
            raw_inr = price_val * (forex_rate + fx_addon) + fixed_offset
        else:
            base_usd = float(rule.get("base_usd", 89.0))
            base_markup = float(rule.get("base_markup_inr", 2955.0))
            per_usd = float(rule.get("per_usd_markup_inr", 14.0))
            markup = base_markup + (price_val - base_usd) * per_usd
            raw_inr = (price_val * forex_rate) + markup

        return apply_charm_rounding(raw_inr, round_nearest, charm_offset)

    elif formula in ("price_bracket_markup", "tiered_percentage_markup"):
        base_inr = price_val * forex_rate
        brackets = rule.get("brackets") or []
        markup_pct = resolve_price_bracket_markup(base_inr, brackets)
        raw_inr = base_inr * (1.0 + markup_pct)
        return apply_charm_rounding(raw_inr, round_nearest, charm_offset)

    elif formula == "usd_tiered_percentage_markup":
        brackets = rule.get("brackets") or []
        markup_pct = resolve_usd_bracket_markup(price_val, brackets)
        raw_inr = (price_val * forex_rate) * (1.0 + markup_pct)
        return apply_charm_rounding(raw_inr, round_nearest, charm_offset)

    elif formula == "percentage_markup":
        markup_pct = float(rule.get("markup_percent", 0.0))
        fixed_fee = float(rule.get("fixed_fee_inr", 0.0))
        raw_inr = (price_val * forex_rate * (1.0 + markup_pct)) + fixed_fee
        return apply_charm_rounding(raw_inr, round_nearest, charm_offset)

    else:
        # Standard forex fallback: source_price * forex_rate * multiplier
        multiplier = float(rule.get("multiplier", 1.0))
        raw_inr = price_val * forex_rate * multiplier
        return apply_charm_rounding(raw_inr, round_nearest, charm_offset)


def calculate_storefront_price(
    source_price: float,
    store: str,
    product_type: str,
    forex_rate: float,
    rules: Optional[Dict[str, Any]] = None,
    vendor: str = "",
    compare_source_price: Optional[float] = None
) -> float:
    """
    Calculate final storefront INR price for a single source USD price.
    """
    price_val = _clean_price(source_price) or 0.0

    if price_val <= 0.0:
        return 0.0
    rule = get_rule_for_product(store, product_type, rules, vendor=vendor)
    return apply_pricing_formula(price_val, rule, forex_rate, compare_source_price=compare_source_price)


def resolve_storefront_pricing(
    source_price: float,
    compare_source_price: Optional[float],
    store: str,
    product_type: str,
    forex_rate: float,
    rules: Optional[Dict[str, Any]] = None,
    vendor: str = ""
) -> Tuple[float, Optional[float]]:
    """
    Resolve storefront pricing pair (price_inr, compare_at_price_inr).
    Variant-aware: call this for each variant with its specific source prices.

    Invariants:
    - If compare price <= selling price, compare_at_price is returned as None (prevents invalid discounts).
    - If source_price <= 0, returns (0.0, None).
    """
    price_val = _clean_price(source_price) or 0.0

    if price_val <= 0.0:
        return 0.0, None

    active_rules = rules or load_pricing_rules()
    rule = get_rule_for_product(store, product_type, active_rules, vendor=vendor)

    comp_float = _clean_price(compare_source_price)

    final_price = apply_pricing_formula(price_val, rule, forex_rate, compare_source_price=comp_float)

    final_compare: Optional[float] = None
    if comp_float is not None and comp_float > price_val:
        formula = rule.get("formula", "standard_forex")
        if formula == "discount_bracket_markup":
            # Compare-At Strategy: Storefront compare_at_price displays official brand retail MSRP in INR (ADR 0028)
            round_nearest = int(rule.get("round_nearest", 100))
            charm_offset = int(rule.get("charm_offset", -1))
            calc_comp = apply_charm_rounding(comp_float * forex_rate, round_nearest, charm_offset)
        else:
            calc_comp = apply_pricing_formula(comp_float, rule, forex_rate)

        if calc_comp > final_price:
            final_compare = calc_comp

    return final_price, final_compare


def resolve_product_storefront_pricing(
    prod: Dict[str, Any],
    forex_rate: Optional[float] = None,
    rules: Optional[Dict[str, Any]] = None
) -> Tuple[float, Optional[float]]:
    """
    Convenience pure function to calculate storefront pricing directly from a canonical product dictionary.
    Safely resolves store, category taxonomy, vendor, and live forex rate.
    """
    if forex_rate is None:
        from storage.forex import get_usd_to_inr_rate
        forex_rate = get_usd_to_inr_rate()

    from storage.shopify_taxonomy import resolve_product_type, resolve_authentic_vendor

    store = (prod.get("source_store") or prod.get("store") or "").lower()
    product_type = resolve_product_type(prod)
    vendor = prod.get("vendor") or prod.get("brand") or resolve_authentic_vendor(prod)
    source_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
    compare_source = prod.get("source_compare_at_price") or prod.get("compare_at_price_source")
    if compare_source is not None:
        try:
            compare_source = float(compare_source)
        except (ValueError, TypeError):
            compare_source = None

    return resolve_storefront_pricing(source_price, compare_source, store, product_type, forex_rate, rules, vendor=vendor)
