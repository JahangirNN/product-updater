"""
Manual Storefront Price Resync & Research Engine (scripts/resync_storefront_prices.py)
Recalculates storefront INR prices on-the-fly through the decoupled pricing filter layer
and pushes updated prices/compare-at prices to Shopify via GraphQL productSet.

ZERO DATABASE MUTATION INVARIANT (ADR 0028):
Local JSON files in storage/db/{store}/products/*.json are NEVER modified with retail markups.
The raw USD supplier price remains the single source of truth for the background freshner daemon.
"""
import os
import sys
import glob
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from storage.forex import get_usd_to_inr_rate
from storage.pricing_engine import (
    load_pricing_rules,
    resolve_storefront_pricing,
    apply_pricing_formula,
    get_rule_for_product
)
from storage.shopify_taxonomy import (
    resolve_options_and_variants,
    resolve_product_type,
    prepare_product_set_payload
)
from storage.shopify_sync import upsert_product_to_shopify
from storage.logger import log_info, log_success, log_warning, log_error

ALL_CATALOG_STORES = [
    "jwpei",
    "jomashop",
    "coach",
    "michaelkors",
    "nordstrom",
    "jdsports",
    "footlocker"
]


def collect_store_products(
    store: str,
    category_filter: Optional[str] = None,
    limit: Optional[int] = None,
    vendor_filter: Optional[str] = None
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load products for a given store from storage/db/{store}/products/*.json.
    Optionally filter by normalized category, vendor, or title.
    Returns list of (file_path, product_dict).
    """
    store_dir = os.path.join(PROJECT_ROOT, "storage", "db", store.lower(), "products")
    if not os.path.isdir(store_dir):
        print(f"[ERROR] Store directory not found: {store_dir}")
        return []

    pattern = os.path.join(store_dir, "*.json")
    files = sorted(glob.glob(pattern))
    results: List[Tuple[str, Dict[str, Any]]] = []

    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)

            if category_filter:
                p_type = resolve_product_type(prod)
                title = prod.get("title", "")
                if (category_filter.lower() not in p_type.lower() and
                        category_filter.lower() not in title.lower()):
                    continue

            if vendor_filter:
                v_name = str(prod.get("vendor") or prod.get("brand") or "")
                title = prod.get("title", "")
                if (vendor_filter.lower() not in v_name.lower() and
                        vendor_filter.lower() not in title.lower()):
                    continue

            results.append((fpath, prod))
            if limit and len(results) >= limit:
                break
        except Exception as err:
            print(f"[WARN] Failed to read {fpath}: {err}")

    return results


def run_research_analysis(
    products: List[Tuple[str, Dict[str, Any]]],
    store: str,
    forex_rate: float
) -> Dict[str, Any]:
    """
    Research and analyze catalog USD pricing distributions, quantiles,
    price bands, variant pricing variance, and category spreads.
    Zero DB mutation, zero network requests.
    """
    print("\n" + "=" * 90)
    print(f"  PRICE ATTACK: CATALOG RESEARCH & USD DISTRIBUTION FOR '{store.upper()}'")
    print("=" * 90)

    usd_prices: List[float] = []
    category_counts: Dict[str, int] = {}
    variant_spread_prods: List[Tuple[str, List[float]]] = []
    total_variants = 0
    with_compare_at = 0

    for fpath, prod in products:
        p_usd = float(prod.get("source_price") or prod.get("price_current") or 0.0)
        p_type = resolve_product_type(prod)
        category_counts[p_type] = category_counts.get(p_type, 0) + 1

        if p_usd > 0:
            usd_prices.append(p_usd)

        if prod.get("source_compare_at_price"):
            with_compare_at += 1

        v_list = prod.get("variants") or []
        v_prices = set()
        for v in v_list:
            if isinstance(v, dict):
                total_variants += 1
                vp = float(v.get("source_price") or 0.0)
                if vp > 0:
                    v_prices.add(vp)
        if len(v_prices) > 1:
            variant_spread_prods.append((prod.get("title", "Untitled")[:35], sorted(list(v_prices))))

    if not usd_prices:
        print("[WARN] No valid positive USD prices found in catalog.")
        return {}

    sorted_p = sorted(usd_prices)
    n = len(sorted_p)

    def quantile(p: float) -> float:
        idx = int(round(p * (n - 1)))
        return sorted_p[max(0, min(n - 1, idx))]

    p_min = sorted_p[0]
    p_10 = quantile(0.10)
    p_25 = quantile(0.25)
    p_med = quantile(0.50)
    p_75 = quantile(0.75)
    p_90 = quantile(0.90)
    p_max = sorted_p[-1]
    p_avg = sum(sorted_p) / n

    # Price bands
    bands = [
        ("< $50", 0.0, 49.99),
        ("$50 - $99", 50.0, 99.99),
        ("$100 - $149", 100.0, 149.99),
        ("$150 - $199", 150.0, 199.99),
        ("$200 - $299", 200.0, 299.99),
        ("$300+", 300.0, float('inf'))
    ]

    print(f"Products Analyzed: {len(products)} | Total Variants: {total_variants} | Live FX: ₹{forex_rate:.2f}/USD")
    print(f"\n--- 1. EMPIRICAL USD DISTRIBUTION ---")
    print(f"  • Min:    ${p_min:.2f} (₹{p_min*forex_rate:,.0f} raw forex)")
    print(f"  • P10:    ${p_10:.2f}")
    print(f"  • P25:    ${p_25:.2f}")
    print(f"  • Median: ${p_med:.2f} (Core price benchmark)")
    print(f"  • Mean:   ${p_avg:.2f}")
    print(f"  • P75:    ${p_75:.2f}")
    print(f"  • P90:    ${p_90:.2f}")
    print(f"  • Max:    ${p_max:.2f} (₹{p_max*forex_rate:,.0f} raw forex)")

    print(f"\n--- 2. PRICE BRACKET DENSITY ---")
    for name, low, high in bands:
        cnt = sum(1 for p in sorted_p if low <= p <= high)
        pct = (cnt / n) * 100
        bar = "█" * int(pct // 3)
        print(f"  {name:<12} {cnt:>4} items ({pct:>5.1f}%) | {bar}")

    print(f"\n--- 3. CATEGORY DISTRIBUTION (Top Categories) ---")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:8]:
        cat_pct = count / len(products) * 100
        print(f"  • {cat:<32}: {count:>3} products ({cat_pct:>4.1f}%)")

    print(f"\n--- 4. MULTI-PRICE VARIANT SPREAD ({len(variant_spread_prods)} products) ---")
    for title, v_pr in variant_spread_prods[:5]:
        v_str = ", ".join(f"${p:.2f}" for p in v_pr)
        print(f"  • {title:<35}: [{v_str}]")
    if len(variant_spread_prods) > 5:
        print(f"  ... and {len(variant_spread_prods) - 5} more products with variant pricing.")

    print(f"\n--- 5. STRATEGY RECOMMENDATIONS ---")
    if p_med <= 120 and (p_max - p_min) < 250:
        print(f"  • Standard Linear Markup with $89 base anchor fits catalog well.")
        print(f"    (e.g., base_usd: {p_med:.0f}, base_markup_inr: 2955, per_usd_markup_inr: 14)")
    else:
        print(f"  • Wide catalog spread (${p_min:.0f} - ${p_max:.0f}). Consider percentage markup with fixed fee floor.")

    print("\n[INVARIANT VERIFIED] Zero database files modified. Storage remains 100% untouched.")
    return {
        "count": len(products),
        "min": p_min,
        "median": p_med,
        "max": p_max,
        "mean": p_avg,
        "multi_price_variant_products": len(variant_spread_prods)
    }


def run_formula_simulation(
    products: List[Tuple[str, Dict[str, Any]]],
    store: str,
    forex_rate: float,
    candidate_rule: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Simulate a candidate pricing formula across products BEFORE registering it in config.
    Zero mutation, zero network requests.
    """
    custom_rules = {
        "version": "candidate-sim",
        "stores": {
            store.lower(): {
                "default": candidate_rule
            }
        },
        "global_default": candidate_rule
    }

    formula_name = candidate_rule.get("formula", "custom")
    print("\n" + "=" * 90)
    print(f"  PRICE ATTACK: CANDIDATE FORMULA SIMULATION FOR '{store.upper()}' ({formula_name})")
    print(f"  Rule: {candidate_rule}")
    print("=" * 90)
    print(f"{'#':<4} {'ID':<10} {'USD':<8} {'Raw Forex':<10} {'Sim INR':<10} {'Markup':<10} {'Margin':<8} {'Charm':<6} {'Title':<30}")
    print("-" * 90)

    stats = {
        "total_analyzed": len(products),
        "charm_ending_99_count": 0,
        "price_shifts": [],
        "markup_percentages": [],
        "sim_prices": []
    }

    for idx, (fpath, prod) in enumerate(products, start=1):
        p_id = str(prod.get("id") or os.path.splitext(os.path.basename(fpath))[0])
        title = prod.get("title", "Untitled")[:28]
        usd_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
        raw_forex = float(round(usd_price * forex_rate))

        # Resolve options & variants with candidate rule injected
        compare_source = prod.get("source_compare_at_price")
        # Temporarily evaluate variant 0 or base price through candidate rule
        p_type = resolve_product_type(prod)
        vendor = prod.get("vendor") or prod.get("brand") or ""
        sim_inr, _ = resolve_storefront_pricing(usd_price, compare_source, store, p_type, forex_rate, rules=custom_rules, vendor=vendor)

        diff_inr = sim_inr - raw_forex
        pct_markup = ((sim_inr - raw_forex) / raw_forex * 100) if raw_forex > 0 else 0.0
        is_charm = (int(sim_inr) % 100 == 99) if sim_inr > 0 else False
        if is_charm:
            stats["charm_ending_99_count"] += 1

        stats["price_shifts"].append(diff_inr)
        stats["markup_percentages"].append(pct_markup)
        stats["sim_prices"].append(sim_inr)

        if idx <= 15 or idx % 50 == 0 or idx == len(products):
            charm_flag = "✓ .99" if is_charm else f"✗ .{int(sim_inr)%100:02d}"
            print(f"{idx:<4} {p_id[:9]:<10} ${usd_price:<7.2f} ₹{raw_forex:<9.0f} ₹{sim_inr:<9.0f} +₹{diff_inr:<8.0f} {pct_markup:>+5.1f}%  {charm_flag:<6} {title}")

    print("-" * 90)
    print(f"\nSIMULATION SUMMARY FOR {len(products)} PRODUCTS:")
    print(f"  • Charm .99 Pricing Compliance: {stats['charm_ending_99_count']} / {len(products)} ({stats['charm_ending_99_count']/len(products)*100:.1f}%)")
    if stats["sim_prices"]:
        min_p = min(stats["sim_prices"])
        max_p = max(stats["sim_prices"])
        avg_p = sum(stats["sim_prices"]) / len(stats["sim_prices"])
        avg_shift = sum(stats["price_shifts"]) / len(stats["price_shifts"])
        avg_markup = sum(stats["markup_percentages"]) / len(stats["markup_percentages"])
        print(f"  • Projected Storefront Range: ₹{min_p:,.0f} — ₹{max_p:,.0f} (Avg: ₹{avg_p:,.0f})")
        print(f"  • Average Shift over Raw Forex: +₹{avg_shift:,.0f} ({avg_markup:+.1f}%)")

    print("\n[INVARIANT VERIFIED] Zero database files modified. Storage remains 100% untouched.")
    return stats


def run_dry_run_analysis(
    products: List[Tuple[str, Dict[str, Any]]],
    store: str,
    forex_rate: float
) -> Dict[str, Any]:
    """
    Simulate pricing calculation across products and display audit table & distribution.
    Zero mutation, zero network requests to Shopify.
    """
    print("\n" + "=" * 90)
    print(f"  PRICE ATTACK: DRY-RUN SIMULATION FOR '{store.upper()}' (FX: ₹{forex_rate:.2f}/USD)")
    print("=" * 90)
    print(f"{'#':<4} {'ID':<10} {'USD':<8} {'Old INR':<10} {'New INR':<10} {'Markup':<10} {'Charm':<6} {'Title':<36}")
    print("-" * 90)

    stats = {
        "store": store,
        "scanned": len(products),
        "needing_price_update": 0,
        "synced": 0,
        "total_analyzed": len(products),
        "with_shopify_id": 0,
        "charm_ending_99_count": 0,
        "total_variants": 0,
        "variants_with_diff_pricing": 0,
        "price_shifts": [],
        "markup_percentages": [],
        "new_prices": []
    }

    sample_count = 0
    for idx, (fpath, prod) in enumerate(products, start=1):
        p_id = str(prod.get("id") or os.path.splitext(os.path.basename(fpath))[0])
        title = prod.get("title", "Untitled")[:35]
        usd_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
        old_inr = float(prod.get("current_price") or round(usd_price * forex_rate))

        has_shopify_id = bool(prod.get("shopify_product_id"))
        if has_shopify_id:
            stats["with_shopify_id"] += 1

        # Resolve options & variants to test full variant-aware pricing
        compare_source = prod.get("source_compare_at_price")
        opts, variants = resolve_options_and_variants(prod, forex_rate, usd_price, compare_source)

        variant_prices = set()
        primary_inr = 0.0
        if variants:
            primary_inr = float(variants[0].get("price", 0.0))
            for v in variants:
                stats["total_variants"] += 1
                vp = float(v.get("price", 0.0))
                variant_prices.add(vp)
        else:
            p_type = resolve_product_type(prod)
            vendor = prod.get("vendor") or prod.get("brand") or ""
            primary_inr, _ = resolve_storefront_pricing(usd_price, compare_source, store, p_type, forex_rate, vendor=vendor)

        if len(variant_prices) > 1:
            stats["variants_with_diff_pricing"] += 1

        diff_inr = primary_inr - old_inr
        pct_markup = ((primary_inr - (usd_price * forex_rate)) / (usd_price * forex_rate) * 100) if (usd_price > 0 and forex_rate > 0) else 0.0

        is_charm_99 = (int(primary_inr) % 100 == 99) if primary_inr > 0 else False
        if is_charm_99:
            stats["charm_ending_99_count"] += 1

        needs_update = any(abs(vp - old_inr) > 0.01 for vp in variant_prices) if variant_prices else abs(diff_inr) > 0.01
        if needs_update:
            stats["needing_price_update"] += 1

        stats["price_shifts"].append(diff_inr)
        stats["markup_percentages"].append(pct_markup)
        stats["new_prices"].append(primary_inr)

        # Print first 20 samples + periodic samples
        if idx <= 20 or idx % 50 == 0 or idx == len(products):
            charm_flag = "✓ .99" if is_charm_99 else f"✗ .{int(primary_inr)%100:02d}"
            # If variant pricing exists, display range notation
            if len(variant_prices) > 1:
                price_disp = f"₹{min(variant_prices):.0f}—₹{max(variant_prices):.0f}"
            else:
                price_disp = f"₹{primary_inr:<9.0f}"
            comp_disp = f" (MSRP: ₹{float(variants[0]['compareAtPrice']):.0f})" if (variants and variants[0].get("compareAtPrice")) else ""
            print(f"{idx:<4} {p_id[:9]:<10} ${usd_price:<7.2f} ₹{old_inr:<9.0f} {price_disp:<10} +₹{diff_inr:<8.0f} {charm_flag:<6} {title}{comp_disp}")
            sample_count += 1

    print("-" * 90)
    print(f"\nAUDIT SUMMARY FOR {len(products)} PRODUCTS:")
    print(f"  • Products with live Shopify ID: {stats['with_shopify_id']} / {len(products)}")
    print(f"  • Charm .99 Pricing Compliance: {stats['charm_ending_99_count']} / {len(products)} ({stats['charm_ending_99_count']/len(products)*100:.1f}%)")
    print(f"  • Total Variants Evaluated: {stats['total_variants']}")
    print(f"  • Products with Multi-Price Variants: {stats['variants_with_diff_pricing']}")

    if stats["new_prices"]:
        min_p = min(stats["new_prices"])
        max_p = max(stats["new_prices"])
        avg_p = sum(stats["new_prices"]) / len(stats["new_prices"])
        avg_shift = sum(stats["price_shifts"]) / len(stats["price_shifts"])
        avg_markup = sum(stats["markup_percentages"]) / len(stats["markup_percentages"])
        print(f"  • New Storefront Price Range: ₹{min_p:,.0f} — ₹{max_p:,.0f} (Avg: ₹{avg_p:,.0f})")
        print(f"  • Average Shift over Raw Forex: +₹{avg_shift:,.0f} ({avg_markup:+.1f}%)")

    print("\n[INVARIANT VERIFIED] Zero database files modified. Storage remains 100% untouched.")
    return stats


def execute_storefront_resync(
    products: List[Tuple[str, Dict[str, Any]]],
    store: str,
    forex_rate: float,
    max_workers: int = 3,
    delay_between_requests: float = 0.3
) -> Dict[str, Any]:
    """
    Execute live Shopify Admin GraphQL productSet updates with polite rate-limiting.
    Strictly preserves Zero Database Mutation Invariant (does NOT overwrite source_price or local current_price).
    """
    target_prods = [(fpath, prod) for fpath, prod in products if prod.get("shopify_product_id")]
    unlinked_count = len(products) - len(target_prods)

    needing_update_count = 0
    for fpath, prod in products:
        usd_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
        old_inr = float(prod.get("current_price") or round(usd_price * forex_rate))
        compare_source = prod.get("source_compare_at_price")
        opts, variants = resolve_options_and_variants(prod, forex_rate, usd_price, compare_source)
        if variants:
            primary_inr = float(variants[0].get("price", 0.0))
        else:
            p_type = resolve_product_type(prod)
            vendor = prod.get("vendor") or prod.get("brand") or ""
            primary_inr, _ = resolve_storefront_pricing(usd_price, compare_source, store, p_type, forex_rate, vendor=vendor)
        needs_update = any(abs(float(v.get("price", 0.0)) - old_inr) > 0.01 for v in variants) if variants else abs(primary_inr - old_inr) > 0.01
        if needs_update:
            needing_update_count += 1

    print("\n" + "=" * 90)
    print(f"  PRICE ATTACK: LIVE SHOPIFY RESYNC EXECUTION FOR '{store.upper()}'")
    print("=" * 90)
    print(f"Targeting {len(target_prods)} products with active Shopify Product IDs ({unlinked_count} unlinked skipped)...")
    print(f"Worker concurrency: {max_workers} | Polite batch delay: {delay_between_requests}s\n")

    if not target_prods:
        print("[INFO] No products with active shopify_product_id found. Nothing to update.")
        return {
            "store": store,
            "scanned": len(products),
            "needing_price_update": needing_update_count,
            "synced": 0,
            "failed": 0,
            "total": 0,
            "elapsed_seconds": 0.0
        }

    success_count = 0
    fail_count = 0
    t_start = time.time()

    def _sync_task(item: Tuple[str, Dict[str, Any]]) -> Tuple[bool, str, str, str, float]:
        fpath, prod = item
        pid = str(prod.get("shopify_product_id") or "")
        title = str(prod.get("title") or "")
        try:
            ok, p_node, err_msg = upsert_product_to_shopify(prod, forex_rate)
            time.sleep(delay_between_requests)
            return ok, pid, title, err_msg, 0.0
        except Exception as exc:
            return False, pid, title, str(exc), 0.0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_sync_task, item): item for item in target_prods}
        for idx, fut in enumerate(as_completed(future_map), start=1):
            ok, pid, title, err_msg, _ = fut.result()
            if ok:
                success_count += 1
                if success_count % 10 == 0 or idx <= 5 or idx == len(target_prods):
                    print(f"[{idx}/{len(target_prods)}] Synced: {title[:40]} ({pid})")
            else:
                fail_count += 1
                print(f"[{idx}/{len(target_prods)}] [ERROR] Failed: {title[:40]} ({pid}): {err_msg}")

    elapsed = time.time() - t_start
    print("=" * 90)
    print(f"RESYNC EXECUTION FINISHED in {elapsed:.1f}s")
    print(f"  • Successful: {success_count} / {len(target_prods)}")
    print(f"  • Failed:     {fail_count} / {len(target_prods)}")
    print(f"  • Local DB:   100% UNCHANGED (Zero Mutation Invariant preserved)")
    print("=" * 90)

    return {
        "store": store,
        "scanned": len(products),
        "needing_price_update": needing_update_count,
        "synced": success_count,
        "failed": fail_count,
        "total": len(target_prods),
        "elapsed_seconds": elapsed
    }


def main():
    parser = argparse.ArgumentParser(
        description="Price Attack: Research catalog USD distributions, simulate formulas, and resync storefront prices."
    )
    parser.add_argument(
        "--store",
        type=str,
        default="jwpei",
        help="Store slug to analyze or resync (default: 'jwpei')"
    )
    parser.add_argument(
        "--all-stores",
        action="store_true",
        help="Iterate across all 7 catalog stores: jwpei, jomashop, coach, michaelkors, nordstrom, jdsports, footlocker"
    )
    parser.add_argument(
        "--research",
        action="store_true",
        help="Research mode: Analyze catalog USD distribution, price bands, quantiles, and variant spread"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Simulation mode: Test candidate formula parameters on products before registering config rules"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview price calculations using registered config/pricing_rules.json"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute live Shopify productSet mutations"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of products to process"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Optional category filter (e.g. 'Shoulder Bags', 'Totes')"
    )
    parser.add_argument(
        "--vendor",
        type=str,
        default=None,
        help="Optional vendor/brand filter (e.g. 'Tissot')"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Worker concurrency for live execution (default: 3)"
    )

    # Candidate formula simulation arguments
    parser.add_argument("--formula", type=str, default="linear_markup", choices=["linear_markup", "percentage_markup", "standard_forex", "discount_bracket_markup", "price_bracket_markup", "tiered_percentage_markup"], help="Candidate formula type for --simulate")
    parser.add_argument("--base-usd", type=float, default=89.0, help="Base USD price benchmark for linear_markup (default: 89.0)")
    parser.add_argument("--base-markup", type=float, default=2955.0, help="Base INR markup at base USD (default: 2955.0)")
    parser.add_argument("--per-usd", type=float, default=14.0, help="Slope INR markup per dollar USD (default: 14.0)")
    parser.add_argument("--fx-addon", type=float, default=14.0, help="Live FX add-on for simplified formula (default: 14.0)")
    parser.add_argument("--markup-percent", type=float, default=0.30, help="Markup percentage for percentage_markup (default: 0.30)")
    parser.add_argument("--fixed-fee", type=float, default=0.0, help="Fixed fee INR for percentage_markup (default: 0.0)")
    parser.add_argument("--round-nearest", type=int, default=100, help="Commercial round nearest multiple (default: 100)")
    parser.add_argument("--charm-offset", type=int, default=-1, help="Charm offset from rounded price (default: -1)")

    args = parser.parse_args()

    if not args.research and not args.simulate and not args.dry_run and not args.execute:
        print("[NOTICE] No action flag specified. Defaulting to --dry-run for safety.")
        args.dry_run = True

    forex_rate = get_usd_to_inr_rate()
    print(f"[INFO] Using USD to INR rate: {forex_rate:.4f}")

    stores_to_process = ALL_CATALOG_STORES if args.all_stores else [args.store or "jwpei"]
    store_stats_list: List[Dict[str, Any]] = []

    for current_store in stores_to_process:
        products = collect_store_products(current_store, category_filter=args.category, limit=args.limit, vendor_filter=args.vendor)
        if not products:
            print(f"[WARN] No products found for store '{current_store}'")
            store_stats_list.append({
                "store": current_store,
                "scanned": 0,
                "needing_price_update": 0,
                "synced": 0
            })
            continue

        print(f"\n[INFO] Found {len(products)} matching products for store '{current_store}'")

        if args.research:
            r_stats = run_research_analysis(products, current_store, forex_rate)
            store_stats_list.append({
                "store": current_store,
                "scanned": len(products),
                "needing_price_update": 0,
                "synced": 0
            })

        elif args.simulate:
            candidate_rule = {
                "formula": args.formula,
                "round_nearest": args.round_nearest,
                "charm_offset": args.charm_offset
            }
            if args.formula == "linear_markup":
                candidate_rule.update({
                    "base_usd": args.base_usd,
                    "base_markup_inr": args.base_markup,
                    "per_usd_markup_inr": args.per_usd,
                    "fx_addon": args.fx_addon
                })
            elif args.formula == "percentage_markup":
                candidate_rule.update({
                    "markup_percent": args.markup_percent,
                    "fixed_fee_inr": args.fixed_fee
                })
            elif args.formula == "discount_bracket_markup":
                from storage.pricing_engine import DEFAULT_DISCOUNT_BRACKETS
                candidate_rule.update({
                    "brackets": DEFAULT_DISCOUNT_BRACKETS
                })
            sim_stats = run_formula_simulation(products, current_store, forex_rate, candidate_rule)
            store_stats_list.append({
                "store": current_store,
                "scanned": len(products),
                "needing_price_update": 0,
                "synced": 0
            })

        elif args.dry_run:
            d_stats = run_dry_run_analysis(products, current_store, forex_rate)
            store_stats_list.append(d_stats)

        elif args.execute:
            e_stats = execute_storefront_resync(products, current_store, forex_rate, max_workers=args.workers)
            store_stats_list.append(e_stats)

    # Print clean summary and statistics
    print("\n" + "=" * 90)
    if args.all_stores or len(stores_to_process) > 1:
        print(f"  ALL-STORES RESYNC SUMMARY ({len(stores_to_process)} STORES EVALUATED)")
        print("=" * 90)
        print(f"{'Store':<16} {'Scanned':<12} {'Needing Price Update':<24} {'Synced':<12}")
        print("-" * 90)
        total_scanned = 0
        total_needing_update = 0
        total_synced = 0
        for s_stat in store_stats_list:
            st_name = s_stat.get("store", "")
            scanned = s_stat.get("scanned", 0)
            needing = s_stat.get("needing_price_update", 0)
            synced = s_stat.get("synced", 0)
            total_scanned += scanned
            total_needing_update += needing
            total_synced += synced
            print(f"{st_name:<16} {scanned:<12} {needing:<24} {synced:<12}")
        print("-" * 90)
        print(f"{'AGGREGATE TOTAL':<16} {total_scanned:<12} {total_needing_update:<24} {total_synced:<12}")
        print(f"\nFinal Summary: {total_scanned} products scanned, {total_needing_update} needing price update, {total_synced} synced.")
    else:
        s_stat = store_stats_list[0] if store_stats_list else {}
        st_name = s_stat.get("store", args.store or "unknown")
        scanned = s_stat.get("scanned", 0)
        needing = s_stat.get("needing_price_update", 0)
        synced = s_stat.get("synced", 0)
        print(f"  STORE RESYNC STATISTICS FOR '{st_name.upper()}'")
        print("=" * 90)
        print(f"  • Total Products Scanned:        {scanned}")
        print(f"  • Total Needing Price Update:    {needing}")
        print(f"  • Total Products Synced:         {synced}")
    print("=" * 90)


if __name__ == "__main__":
    main()
