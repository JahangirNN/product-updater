"""
Empirical Verification & Deep Audit Suite: All 574 Jomashop Watches & Universal Watch Pricing
Validates:
1. Universal Watch Formula (ADR 0028 discount_bracket_markup) across all 574 Jomashop catalog items.
2. 100% Brand Coverage (Tissot, Citizen, Movado, Seiko, Michael Kors, Versace, Ferragamo).
3. Mathematical precision: whole-rupee INR ₹.99 charm rounding and brand MSRP safety ceiling.
4. Color / Option Multi-Variant Harmony: independent variant pricing and anti-deduplication.
5. Freshner Daemon Compatibility: price fluctuation projection, Shopify payload generation, and zero disk mutation.
"""
import os
import sys
import json
import glob
import copy
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.pricing_engine import (
    load_pricing_rules,
    get_rule_for_product,
    apply_pricing_formula,
    resolve_storefront_pricing,
    resolve_product_storefront_pricing,
    resolve_bracket_markup,
    commercial_round_half_up,
    apply_charm_rounding
)
from storage.shopify_taxonomy import (
    resolve_options_and_variants,
    prepare_product_set_payload,
    resolve_product_type,
    resolve_authentic_vendor
)
from storage.forex import get_usd_to_inr_rate
from stores.jomashop.delta import apply_delta_to_product

TOTAL_CATALOG_WATCHES = 574
EXPECTED_BRANDS = {
    "Tissot": 157,
    "Citizen": 119,
    "Movado": 102,
    "Seiko": 68,
    "Michael Kors": 67,
    "Versace": 46,
    "Ferragamo": 15
}


def test_audit_all_574_watches(forex_rate: float = 95.0) -> Dict[str, Any]:
    print("\n" + "=" * 78)
    print("PHASE 1: AUDITING ALL 574 JOMASHOP WATCHES IN THE LOCAL CANONICAL DATABASE")
    print("=" * 78)

    pattern = os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "*.json")
    files = glob.glob(pattern)
    assert len(files) == TOTAL_CATALOG_WATCHES, f"Expected {TOTAL_CATALOG_WATCHES} files, found {len(files)}"

    brand_counts = {}
    bracket_counts = {0.16: 0, 0.18: 0, 0.29: 0, 0.40: 0, 0.50: 0, 0.70: 0}
    ceiling_clamped = 0
    valid_compares = 0
    suppressed_compares = 0

    for idx, fpath in enumerate(files):
        with open(fpath, "r", encoding="utf-8") as f:
            prod = json.load(f)

        p_id = prod.get("id")
        vendor = prod.get("vendor") or prod.get("brand") or "Unknown"
        brand_counts[vendor] = brand_counts.get(vendor, 0) + 1

        # 1. Verify rule resolution
        rule = get_rule_for_product("jomashop", "Watches", vendor=vendor)
        assert rule.get("formula") == "discount_bracket_markup", f"Product {p_id} ({vendor}) did not resolve discount_bracket_markup"

        # 2. Verify pricing resolution
        src_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
        assert src_price > 0.0, f"Product {p_id} ({vendor}) has invalid source price: {src_price}"

        raw_comp = prod.get("source_compare_at_price") or prod.get("compare_at_price_source")
        src_comp = float(raw_comp) if raw_comp is not None else None

        p_inr, comp_inr = resolve_product_storefront_pricing(prod, forex_rate)

        # 3. Whole-rupee charm ending in .99
        assert p_inr > 0.0, f"Product {p_id} ({vendor}) generated invalid price {p_inr}"
        assert int(p_inr) % 100 == 99, f"Product {p_id} ({vendor}) price {p_inr} did not end in 99"

        # 4. Bracket verification
        if src_comp is not None and src_comp > src_price:
            valid_compares += 1
            discount_pct = (src_comp - src_price) / src_comp
            expected_markup = resolve_bracket_markup(discount_pct)
            bracket_counts[expected_markup] = bracket_counts.get(expected_markup, 0) + 1

            # Brand MSRP safety ceiling & compare-at price check
            msrp_raw = src_comp * forex_rate
            msrp_charmed = commercial_round_half_up(msrp_raw, 100) - 1
            assert p_inr <= msrp_charmed, f"Product {p_id} ({vendor}) price {p_inr} exceeded MSRP {msrp_charmed}"

            # Invariant: If selling price reached MSRP ceiling, compare_at must be None to prevent 0% discount strikethrough
            if p_inr >= msrp_charmed:
                ceiling_clamped += 1
                suppressed_compares += 1
                assert comp_inr is None, f"Product {p_id} ({vendor}) compare_at should be None when price reached MSRP ceiling"
            else:
                valid_compares += 1
                assert comp_inr is not None, f"Product {p_id} ({vendor}) missing compare_at_price"
                assert comp_inr > p_inr, f"Product {p_id} ({vendor}) compare_at {comp_inr} not > selling price {p_inr}"
                assert int(comp_inr) % 100 == 99, f"Product {p_id} ({vendor}) compare_at {comp_inr} did not end in 99"
        else:
            suppressed_compares += 1
            assert comp_inr is None, f"Product {p_id} ({vendor}) compare_at should be None for non-discounted item"

    print(f"  [PASS] Audited all {len(files)} watch products in canonical database.")
    print(f"  Brand distribution verified: {brand_counts}")
    for b_name, expected_cnt in EXPECTED_BRANDS.items():
        assert brand_counts.get(b_name) == expected_cnt, f"Brand {b_name}: expected {expected_cnt}, found {brand_counts.get(b_name)}"
    print(f"  All 7 brands match expected counts exactly 100%.")

    # Universal Watch rule resolution check across stores and singular/plural forms
    for st in ["jomashop", "michaelkors", "jwpei", "nordstrom", "unknown_store"]:
        for pt in ["Watches", "Watch"]:
            r = get_rule_for_product(st, pt)
            assert r.get("formula") == "discount_bracket_markup", f"Store {st} / {pt} failed to resolve discount_bracket_markup: {r}"
    # Verify non-watch items still resolve store defaults
    assert get_rule_for_product("michaelkors", "Handbags").get("formula") == "price_bracket_markup"
    assert get_rule_for_product("jwpei", "Shoulder Bags").get("formula") == "linear_markup"
    print(f"  [PASS] Universal watch formula resolution verified across all catalog stores.")

    print(f"  Discount bracket markup distribution: {bracket_counts}")
    print(f"  MSRP safety ceiling active clamps: {ceiling_clamped}")
    print(f"  Valid compare-at prices: {valid_compares}, cleanly suppressed compare-at: {suppressed_compares}")

    return {
        "status": "PASS",
        "total_audited": len(files),
        "brand_counts": brand_counts,
        "bracket_counts": bracket_counts,
        "ceiling_clamped": ceiling_clamped
    }


def test_multi_variant_color_pricing(forex_rate: float = 95.0) -> None:
    print("\n" + "=" * 78)
    print("PHASE 2: AUDITING COLOR / FINISH MULTI-VARIANT INDEPENDENT PRICING")
    print("=" * 78)

    mock_multivar_watch = {
        "id": "tissot_prx_multi",
        "source_store": "jomashop",
        "vendor": "Tissot",
        "product_type": "Watches",
        "title": "Tissot PRX Powermatic 80 Automatic",
        "source_price": 450.0,
        "source_compare_at_price": 750.0,
        "specifications": {
            "Case Diameter": "40 mm",
            "Water Resistance": "100 meters"
        },
        "variants": [
            {
                "sku": "T1374071104100",
                "title": "Ice Blue Dial / Stainless Steel",
                "color": "Ice Blue",
                "source_price": 450.0,
                "source_compare_at_price": 750.0,
                "in_stock": True,
                "image_url": "https://cdn2.jomashop.com/tissot-prx-ice-blue.jpg"
            },
            {
                "sku": "T1374071105100",
                "title": "Black Dial / Stainless Steel",
                "color": "Black",
                "source_price": 420.0,
                "source_compare_at_price": 725.0,
                "in_stock": True,
                "image_url": "https://cdn2.jomashop.com/tissot-prx-black.jpg"
            },
            {
                "sku": "T1374073302100",
                "title": "Gold PVD / Champagne Dial",
                "color": "Gold",
                "source_price": 550.0,
                "source_compare_at_price": 825.0,
                "in_stock": True,
                "image_url": "https://cdn2.jomashop.com/tissot-prx-gold.jpg"
            },
            {
                "sku": "T1374072103100",
                "title": "Two-Tone Rose Gold / Silver",
                "color": "Rose Gold",
                "source_price": 380.0,
                "source_compare_at_price": 750.0,
                "in_stock": False,
                "image_url": "https://cdn2.jomashop.com/tissot-prx-rosegold.jpg"
            }
        ]
    }

    opts, variants = resolve_options_and_variants(mock_multivar_watch, forex_rate, 450.0, 750.0)

    # 1. Anti-Deduplication: All 4 variants must be retained
    assert len(variants) == 4, f"Expected 4 variants, got {len(variants)}"

    # 2. Options schema
    opt_names = [o["name"] for o in opts]
    assert "Color" in opt_names, f"Missing 'Color' option: {opt_names}"
    assert "Case Diameter" in opt_names, f"Missing 'Case Diameter' option: {opt_names}"

    # 3. Dynamic variant pricing calculation
    p_blue_exp, c_blue_exp = resolve_storefront_pricing(450.0, 750.0, "jomashop", "Watches", forex_rate, vendor="Tissot")
    p_black_exp, c_black_exp = resolve_storefront_pricing(420.0, 725.0, "jomashop", "Watches", forex_rate, vendor="Tissot")
    p_gold_exp, c_gold_exp = resolve_storefront_pricing(550.0, 825.0, "jomashop", "Watches", forex_rate, vendor="Tissot")

    # Variant 0: Ice Blue
    v_blue = next(v for v in variants if "T1374071104100" in v["sku"])
    assert float(v_blue["price"]) == p_blue_exp, f"Expected {p_blue_exp}, got {v_blue['price']}"
    assert float(v_blue["compareAtPrice"]) == c_blue_exp, f"Expected {c_blue_exp}, got {v_blue['compareAtPrice']}"

    # Variant 1: Black
    v_black = next(v for v in variants if "T1374071105100" in v["sku"])
    assert float(v_black["price"]) == p_black_exp, f"Expected {p_black_exp}, got {v_black['price']}"
    assert float(v_black["compareAtPrice"]) == c_black_exp, f"Expected {c_black_exp}, got {v_black['compareAtPrice']}"

    # Variant 2: Gold
    v_gold = next(v for v in variants if "T1374073302100" in v["sku"])
    assert float(v_gold["price"]) == p_gold_exp, f"Expected {p_gold_exp}, got {v_gold['price']}"
    assert float(v_gold["compareAtPrice"]) == c_gold_exp, f"Expected {c_gold_exp}, got {v_gold['compareAtPrice']}"

    # Variant 3: OOS Rose Gold (clamped to min in-stock price floor)
    min_instock = min(p_blue_exp, p_black_exp, p_gold_exp)
    v_rg = next(v for v in variants if "T1374072103100" in v["sku"])
    assert float(v_rg["price"]) == min_instock, f"OOS price floor violated: expected {min_instock}, got {v_rg['price']}"
    assert v_rg["inventoryPolicy"] == "DENY"

    # All prices end in .99
    for v in variants:
        assert int(float(v["price"])) % 100 == 99

    # 4. Dial Color Anti-Duplication Check
    mock_dial_watch = {
        "product_type": "Watches",
        "source_store": "jomashop",
        "vendor": "Citizen",
        "source_price": 200.0,
        "source_compare_at_price": 400.0,
        "variants": [
            {"title": "Blue", "option_values": [{"option_name": "Dial Color", "name": "Blue"}], "source_price": 200.0, "source_compare_at_price": 400.0, "in_stock": True},
            {"title": "Black", "option_values": [{"option_name": "Dial Color", "name": "Black"}], "source_price": 220.0, "source_compare_at_price": 400.0, "in_stock": True}
        ]
    }
    opts_dial, vars_dial = resolve_options_and_variants(mock_dial_watch, forex_rate, 200.0, 400.0)
    opt_dial_names = [o["name"] for o in opts_dial]
    assert opt_dial_names == ["Dial Color"], f"Expected ['Dial Color'], got {opt_dial_names}"
    assert len(vars_dial) == 2

    # 5. Independent Variant Compare-at Price Check
    mock_comp_watch = {
        "product_type": "Watches",
        "source_store": "jomashop",
        "vendor": "Movado",
        "source_price": 300.0,
        "source_compare_at_price": 600.0,
        "variants": [
            {"sku": "MOV-STD", "title": "Standard", "color": "Silver", "source_price": 300.0, "source_compare_at_price": 600.0, "in_stock": True},
            {"sku": "MOV-DIA", "title": "Diamond", "color": "Gold", "source_price": 400.0, "source_compare_at_price": 1000.0, "in_stock": True}
        ]
    }
    _, vars_comp = resolve_options_and_variants(mock_comp_watch, forex_rate, 300.0, 600.0)
    v_std = next(v for v in vars_comp if "MOV-STD" in v["sku"])
    v_dia = next(v for v in vars_comp if "MOV-DIA" in v["sku"])
    p_std_exp, c_std_exp = resolve_storefront_pricing(300.0, 600.0, "jomashop", "Watches", forex_rate, vendor="Movado")
    p_dia_exp, c_dia_exp = resolve_storefront_pricing(400.0, 1000.0, "jomashop", "Watches", forex_rate, vendor="Movado")
    assert float(v_std["price"]) == p_std_exp, f"Expected {p_std_exp}, got {v_std['price']}"
    assert float(v_std["compareAtPrice"]) == c_std_exp, f"Expected {c_std_exp}, got {v_std['compareAtPrice']}"
    assert float(v_dia["price"]) == p_dia_exp, f"Expected {p_dia_exp}, got {v_dia['price']}"
    assert float(v_dia["compareAtPrice"]) == c_dia_exp, f"Expected {c_dia_exp}, got {v_dia['compareAtPrice']}"

    print("  [PASS] Multi-variant option discovery, anti-deduplication, independent bracket calculation, and OOS floor verified.")


def test_freshner_price_fluctuation_compatibility(forex_rate: float = 95.0) -> None:
    print("\n" + "=" * 78)
    print("PHASE 3: AUDITING FRESHNER DAEMON PRICE FLUCTUATION & CLEAN-ROOM INVARIANTS")
    print("=" * 78)

    sample_fpath = os.path.join(PROJECT_ROOT, "storage", "db", "jomashop", "products", "009e74a980966b3c.json")
    with open(sample_fpath, "r", encoding="utf-8") as f:
        prod_before = json.load(f)

    orig_usd = float(prod_before["source_price"])
    orig_msrp = float(prod_before["source_compare_at_price"])
    vendor = prod_before["vendor"]

    # Initial pricing
    p_init, comp_init = resolve_storefront_pricing(orig_usd, orig_msrp, "jomashop", "Watches", forex_rate, vendor=vendor)
    assert int(p_init) % 100 == 99

    # Simulation 1: Supplier price drops by $50 (e.g. flash sale)
    dropped_usd = orig_usd - 50.0
    delta_drop = {
        "status": "success",
        "current_source_price": dropped_usd,
        "current_compare_at_price": orig_msrp,
        "availability": "in_stock",
        "price_changed": True,
        "stock_changed": False,
        "variant_price_changed": False,
        "changed_variants": [],
        "changed_variant_prices": []
    }
    updated_drop, has_changed = apply_delta_to_product(copy.deepcopy(prod_before), delta_drop, forex_rate)
    assert has_changed is True
    # Disk invariant: USD price updated, NOT converted to INR on disk
    assert updated_drop["source_price"] == dropped_usd

    p_drop, comp_drop = resolve_storefront_pricing(dropped_usd, orig_msrp, "jomashop", "Watches", forex_rate, vendor=vendor)
    assert p_drop < p_init, f"Expected dropped price {p_drop} < {p_init}"
    assert int(p_drop) % 100 == 99

    # Simulation 2: Supplier price spikes by $100
    spiked_usd = orig_usd + 100.0
    p_spike, comp_spike = resolve_storefront_pricing(spiked_usd, orig_msrp, "jomashop", "Watches", forex_rate, vendor=vendor)
    assert p_spike > p_init, f"Expected spiked price {p_spike} > {p_init}"
    assert int(p_spike) % 100 == 99
    # MSRP ceiling test
    msrp_charmed = commercial_round_half_up(orig_msrp * forex_rate, 100) - 1
    assert p_spike <= msrp_charmed

    # Simulation 3: Clean-room disk read invariant (ensure disk file was not modified)
    with open(sample_fpath, "r", encoding="utf-8") as f:
        prod_after = json.load(f)
    assert prod_before == prod_after, "Clean-room invariant violated: database file was mutated!"

    # Simulation 4: Full GraphQL payload generation with fluctuating price
    payload = prepare_product_set_payload(updated_drop, forex_rate)
    v0_price = float(payload["variants"][0]["price"])
    assert v0_price == p_drop, f"Payload price {v0_price} did not match calculated price {p_drop}"

    # Simulation 5: Freshner poll_single_product attached price check in dry-run mode
    from sync_catalog import poll_single_product

    class MockFreshnerSweepMod:
        @staticmethod
        def check_price_and_stock(product, **kwargs):
            return {
                "status": "success",
                "current_source_price": dropped_usd,
                "current_compare_at_price": orig_msrp,
                "availability": "in_stock",
                "price_changed": True,
                "variant_price_changed": True,
                "changed_variant_prices": [
                    {
                        "sku": "TIST0992072211802",
                        "old_source_price": orig_usd,
                        "new_source_price": dropped_usd,
                        "source_compare_at_price": orig_msrp
                    }
                ]
            }

        @staticmethod
        def apply_delta_to_product(product, delta_res, fx):
            return product, True

    stub = {"id": "009e74a980966b3c", "store": "jomashop", "handle": prod_before.get("handle")}
    sweep_res = poll_single_product(stub, MockFreshnerSweepMod, dry_run=True, forex_rate=forex_rate)
    assert sweep_res.get("new_storefront_price_inr") == p_drop, f"Expected sweep attached price {p_drop}, got {sweep_res.get('new_storefront_price_inr')}"
    cvp_item = sweep_res.get("changed_variant_prices", [])[0]
    assert cvp_item.get("new_storefront_price_inr") == p_drop, f"Expected variant sweep attached price {p_drop}, got {cvp_item.get('new_storefront_price_inr')}"

    print("  [PASS] Freshner price drop, spike, MSRP ceiling, GraphQL payload, and zero disk mutation verified.")


def main():
    print("=" * 78)
    print("STARTING COMPREHENSIVE EMPIRICAL AUDIT: ALL 574 JOMASHOP WATCHES")
    print("=" * 78)

    forex = get_usd_to_inr_rate()
    print(f"Active Live USD to INR Forex Rate: {forex:.4f}")

    test_audit_all_574_watches(forex)
    test_multi_variant_color_pricing(forex)
    test_freshner_price_fluctuation_compatibility(forex)

    print("\n" + "=" * 78)
    print("SUCCESS: 100% OF ALL 574 JOMASHOP WATCHES & MULTI-VARIANT TESTS PASSED")
    print("=" * 78)


if __name__ == "__main__":
    main()
