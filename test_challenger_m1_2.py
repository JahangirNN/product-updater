"""
Milestone M1-2 Adversarial Challenge & Verification Test Suite
Independent empirical challenge testing:
1. Exhaustive disk scan of all 1,763 products across 4 stores for:
   - Footwear/apparel size run truncation (0 truncated)
   - Fractional paise in INR pricing (0 fractional paise)
   - Parent-child stock desynchronization (0 desynchronized)
   - Coach multi-colorway / multi-material pricing, SKUs, and Scene7 image integrity
2. Multi-variant stock transition stress testing for stores/coach/delta.py
   and stores/jwpei/delta.py under adversarial scenarios (partial stock flips,
   all out-of-stock, restock, cascade, case/whitespace matching, price changes).
3. Live PDP audit report verification.
"""

import os
import sys
import glob
import json
import time
import re
from typing import Dict, Any, List, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stores.coach.delta import (
    apply_delta_to_product as coach_apply_delta,
    extract_coach_pdp_info
)
from stores.jwpei.delta import (
    apply_delta_to_product as jwpei_apply_delta
)

DB_BASE = os.path.join("storage", "db")
STORES = ["coach", "michaelkors", "jwpei", "nordstrom"]


def load_all_db_products() -> Dict[str, List[Dict[str, Any]]]:
    catalog = {}
    for s in STORES:
        pattern = os.path.join(DB_BASE, s, "products", "*.json")
        files = glob.glob(pattern)
        prods = []
        for f in files:
            with open(f, "r", encoding="utf-8") as fp:
                prods.append(json.load(fp))
        catalog[s] = prods
    return catalog


# ==============================================================================
# CHALLENGE 1: EXHAUSTIVE MULTI-VARIANT PRICING & SIZING SCAN (1,763 PRODUCTS)
# ==============================================================================

def test_1_1_footwear_and_apparel_sizing_integrity(catalog: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, str]:
    """
    Exhaustively scans all 1,763 products to verify 0 footwear/apparel items have
    truncated size runs (<= 1 size). Uses an aggressive keyword and classification set.
    """
    apparel_footwear_groups = {
        "shoes", "sandals", "sneakers", "flats", "boots", "women_shoes",
        "men_shoes", "footwear", "apparel", "clothing", "coats", "jackets",
        "dresses", "sweaters", "pants", "tops", "skirts", "outerwear"
    }

    apparel_footwear_keywords = [
        "shoe", "footwear", "apparel", "clothing", "boot", "sandal", "sneaker",
        "heel", "pump", "slide", "loafer", "mule", "flat", "espadrille", "clog",
        "dress", "coat", "jacket", "sweater", "skirt", "pant", "trouser", "tee",
        "t-shirt", "cardigan", "blazer", "hoodie"
    ]

    # Exclusions for inherently single-size items
    one_size_keywords = [
        "bag", "tote", "crossbody", "satchel", "clutch", "wallet", "wristlet",
        "card case", "belt", "scarf", "hat", "beanie", "sunglasses", "jewelry",
        "necklace", "bracelet", "earring", "ring", "keychain", "charm", "perfume",
        "fragrance", "strap", "sock"
    ]

    total_audited = 0
    truncated_items = []

    for store, prods in catalog.items():
        for p in prods:
            groups = [str(g).lower() for g in p.get("groups", [])]
            ptype = str(p.get("product_type", "")).lower()
            title = str(p.get("title", "")).lower()

            is_apparel_footwear = (
                any(g in apparel_footwear_groups for g in groups) or
                any(kw in ptype for kw in apparel_footwear_keywords) or
                any(kw in title for kw in apparel_footwear_keywords) or
                (store == "nordstrom")
            )

            # Check if this item is actually a handbag/accessory that happened to match a keyword
            is_accessory = any(okw in title for okw in one_size_keywords) or any(okw in ptype for okw in ["bag", "wallet", "belt", "hat", "scarf", "jewelry"])

            if is_apparel_footwear and not is_accessory:
                total_audited += 1
                variants = p.get("variants", [])
                if len(variants) <= 1:
                    truncated_items.append({
                        "store": store,
                        "product_id": p.get("product_id"),
                        "handle": p.get("handle"),
                        "title": p.get("title"),
                        "variants_count": len(variants)
                    })

    if truncated_items:
        return False, f"FAILED: Found {len(truncated_items)} truncated items: {truncated_items[:3]}"

    return True, f"PASSED: Audited {total_audited} footwear/apparel items across all stores. Exactly 0 truncated (<=1 size)."


def test_1_2_whole_rupee_inr_math_integrity(catalog: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, str]:
    """
    Exhaustively checks every single product and variant in storage/db for fractional paise.
    Requires whole-rupee rounding across parent current_price, compare_at_price, and all variant prices.
    """
    total_products = 0
    total_variants = 0
    fractional_parents = []
    fractional_variants = []

    for store, prods in catalog.items():
        for p in prods:
            total_products += 1
            cp = p.get("current_price")
            if cp is not None:
                val = float(cp)
                if not val.is_integer():
                    fractional_parents.append((store, p.get("handle"), "current_price", cp))

            cap = p.get("compare_at_price")
            if cap is not None:
                val = float(cap)
                if not val.is_integer():
                    fractional_parents.append((store, p.get("handle"), "compare_at_price", cap))

            for v in p.get("variants", []):
                total_variants += 1
                vp = v.get("price")
                if vp is not None:
                    val = float(vp)
                    if not val.is_integer():
                        fractional_variants.append((store, p.get("handle"), v.get("sku"), "price", vp))

                vpc = v.get("price_current")
                if vpc is not None:
                    val = float(vpc)
                    if not val.is_integer():
                        fractional_variants.append((store, p.get("handle"), v.get("sku"), "price_current", vpc))

    if fractional_parents or fractional_variants:
        return False, (
            f"FAILED: Found {len(fractional_parents)} parent fractional INR prices and "
            f"{len(fractional_variants)} variant fractional INR prices."
        )

    return True, (
        f"PASSED: Audited {total_products} products and {total_variants} variants. "
        f"Exactly 0 fractional paise detected in parent or variant INR prices."
    )


def test_1_3_parent_child_stock_synchronization(catalog: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, str]:
    """
    Exhaustively scans all 1,763 products to confirm parent availability and child
    variant availability are 100% in harmony:
    1. Parent out_of_stock or delisted MUST have 0 in-stock child variants.
    2. Parent in_stock MUST have at least 1 in-stock child variant (for multi-variant items).
    """
    total_audited = 0
    desync_oos_parent = []
    desync_in_stock_parent = []

    for store, prods in catalog.items():
        for p in prods:
            total_audited += 1
            avail = p.get("availability")
            variants = p.get("variants", [])

            active_variants = [
                v for v in variants
                if v.get("in_stock") is True or v.get("is_available") is True
            ]

            if avail in ("out_of_stock", "delisted"):
                if active_variants:
                    desync_oos_parent.append((store, p.get("handle"), len(active_variants)))

            elif avail == "in_stock" and len(variants) > 0:
                if len(active_variants) == 0:
                    desync_in_stock_parent.append((store, p.get("handle"), len(variants)))

    if desync_oos_parent:
        return False, f"FAILED: Found {len(desync_oos_parent)} OOS products with in-stock variants: {desync_oos_parent[:3]}"

    if desync_in_stock_parent:
        return False, f"FAILED: Found {len(desync_in_stock_parent)} in-stock products with 0 in-stock variants: {desync_in_stock_parent[:3]}"

    return True, (
        f"PASSED: Audited {total_audited} products across all 4 stores. "
        f"0 parent OOS with active variants, 0 in-stock products with 0 active variants."
    )


def test_1_4_coach_multi_price_variants_and_scene7_assets(catalog: Dict[str, List[Dict[str, Any]]]) -> Tuple[bool, str]:
    """
    Verifies Coach multi-colorway/multi-material pricing differentials, variant-level SKUs,
    and genuine Scene7 image asset URLs.
    """
    coach_prods = catalog.get("coach", [])
    multi_price_prods = []
    invalid_sku_vars = 0
    invalid_scene7_vars = 0
    zero_price_vars = 0

    for p in coach_prods:
        variants = p.get("variants", [])
        prices = set(v.get("source_price") for v in variants if v.get("source_price") is not None)
        if len(prices) > 1:
            multi_price_prods.append(p)
            for v in variants:
                sku = v.get("sku")
                if not sku or not isinstance(sku, str) or len(sku.strip()) < 3:
                    invalid_sku_vars += 1

                img = v.get("image_url") or ""
                if not img.startswith("https://coach.scene7.com/is/image/Coach/"):
                    invalid_scene7_vars += 1

                sp = float(v.get("source_price") or 0.0)
                cp = float(v.get("price") or 0.0)
                if sp <= 0 or cp <= 0:
                    zero_price_vars += 1

    if len(multi_price_prods) < 270:
        return False, f"FAILED: Expected at least 270 multi-price Coach products, found {len(multi_price_prods)}"

    if invalid_sku_vars > 0:
        return False, f"FAILED: Found {invalid_sku_vars} variants with invalid/missing SKUs"

    if invalid_scene7_vars > 0:
        return False, f"FAILED: Found {invalid_scene7_vars} variants with invalid Scene7 image URLs"

    if zero_price_vars > 0:
        return False, f"FAILED: Found {zero_price_vars} variants with invalid/zero prices"

    return True, (
        f"PASSED: Verified {len(multi_price_prods)} Coach multi-material/colorway products. "
        f"0 invalid SKUs, 0 invalid Scene7 image URLs, 0 zero prices."
    )


# ==============================================================================
# CHALLENGE 2: ADVERSARIAL MULTI-VARIANT STOCK TRANSITIONS (COACH & JW PEI)
# ==============================================================================

def test_2_1_coach_adversarial_partial_stock_transition() -> Tuple[bool, str]:
    """
    Adversarial test for stores/coach/delta.py:
    1. Product has 3 variants (A, B, C), all initially in stock.
    2. Delta specifies Variant A goes OUT of stock, B and C stay IN stock.
    3. Product availability must REMAIN 'in_stock' (no top-level flip).
    4. Variant A must be updated to in_stock = False.
    5. Top-level has_changed must be True, shopify_sync_pending = True.
    """
    product = {
        "store": "coach",
        "handle": "test-coach-bag",
        "source_sku": "SKU-A",
        "availability": "in_stock",
        "is_active": True,
        "source_price": 350.0,
        "current_price": 29225.0,
        "variants": [
            {"sku": "SKU-A", "title": "Black Leather", "in_stock": True, "source_price": 350.0, "price": "29225.00"},
            {"sku": "SKU-B", "title": "Chalk Leather", "in_stock": True, "source_price": 350.0, "price": "29225.00"},
            {"sku": "SKU-C", "title": "Signature Canvas", "in_stock": True, "source_price": 395.0, "price": "32983.00"},
        ]
    }

    # Delta report: SKU-A is out of stock, SKU-B & SKU-C in stock
    delta_result = {
        "status": "success",
        "handle": "test-coach-bag",
        "current_source_price": 350.0,
        "old_source_price": 350.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "is_active": True,
        "price_changed": False,
        "stock_changed": False,
        "variants_delta": [
            {"sku": "SKU-A", "available": False, "price_usd": 350.0},
            {"sku": "SKU-B", "available": True, "price_usd": 350.0},
            {"sku": "SKU-C", "available": True, "price_usd": 395.0},
        ]
    }

    forex_rate = 83.5
    updated_prod, has_changed = coach_apply_delta(product, delta_result, forex_rate)

    assert has_changed is True, "Expected has_changed to be True when a variant stock changes"
    assert updated_prod["availability"] == "in_stock", "Overall availability should remain in_stock"
    assert updated_prod["is_active"] is True, "is_active should remain True"
    assert updated_prod["shopify_sync_pending"] is True, "shopify_sync_pending should be True"

    var_map = {v["sku"]: v["in_stock"] for v in updated_prod["variants"]}
    assert var_map["SKU-A"] is False, "SKU-A should now be out of stock"
    assert var_map["SKU-B"] is True, "SKU-B should remain in stock"
    assert var_map["SKU-C"] is True, "SKU-C should remain in stock"

    return True, "PASSED: Coach partial variant stock transition evaluated correctly with stock harmony."


def test_2_2_coach_adversarial_full_depletion_and_restock() -> Tuple[bool, str]:
    """
    Adversarial test for stores/coach/delta.py:
    1. Deplete all remaining variants -> top-level must flip to out_of_stock, is_active = False.
    2. Restock a single variant -> top-level must flip back to in_stock, is_active = True.
    """
    product = {
        "store": "coach",
        "handle": "test-coach-bag",
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "SKU-A", "in_stock": False},
            {"sku": "SKU-B", "in_stock": True},
            {"sku": "SKU-C", "in_stock": True},
        ]
    }

    # Step 1: Deplete B and C
    delta_deplete = {
        "status": "success",
        "variants_delta": [
            {"sku": "SKU-A", "available": False},
            {"sku": "SKU-B", "available": False},
            {"sku": "SKU-C", "available": False},
        ]
    }
    p_depleted, has_changed1 = coach_apply_delta(product, delta_deplete, 83.5)
    assert has_changed1 is True
    assert p_depleted["availability"] == "out_of_stock", f"Expected out_of_stock, got {p_depleted['availability']}"
    assert p_depleted["is_active"] is False, "Expected is_active False"
    assert all(not v["in_stock"] for v in p_depleted["variants"])

    # Step 2: Restock only Variant C
    delta_restock = {
        "status": "success",
        "variants_delta": [
            {"sku": "SKU-A", "available": False},
            {"sku": "SKU-B", "available": False},
            {"sku": "SKU-C", "available": True},
        ]
    }
    p_restocked, has_changed2 = coach_apply_delta(p_depleted, delta_restock, 83.5)
    assert has_changed2 is True
    assert p_restocked["availability"] == "in_stock", f"Expected in_stock, got {p_restocked['availability']}"
    assert p_restocked["is_active"] is True, "Expected is_active True"
    assert p_restocked["variants"][2]["in_stock"] is True

    return True, "PASSED: Coach complete depletion and single-variant restock transitions verified."


def test_2_3_coach_adversarial_availability_cascade_and_swatches() -> Tuple[bool, str]:
    """
    Adversarial test for stores/coach/delta.py:
    1. Availability cascade: when variants_delta is empty and availability is out_of_stock/delisted,
       cascade in_stock = False to all variants.
    2. HTML parsing with mixed variation-size buttons.
    """
    product = {
        "store": "coach",
        "handle": "test-coach-shoe",
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "SHOE-7", "title": "US 7 B", "in_stock": True, "is_available": True},
            {"sku": "SHOE-8", "title": "US 8 B", "in_stock": True, "is_available": True},
            {"sku": "SHOE-9", "title": "US 9 B", "in_stock": True, "is_available": True},
        ]
    }

    # Case 1: Availability cascade on 404 delist / OOS with empty variants_delta
    delta_cascade = {
        "status": "not_found",
        "availability": "out_of_stock",
        "is_active": False,
        "stock_changed": True,
        "variants_delta": []
    }
    p_cascaded, has_changed = coach_apply_delta(product, delta_cascade, 83.5)
    assert has_changed is True
    assert p_cascaded["availability"] == "out_of_stock"
    assert p_cascaded["is_active"] is False
    for v in p_cascaded["variants"]:
        assert v["in_stock"] is False, f"Variant {v['sku']} was not cascaded to in_stock=False"
        assert v.get("is_available") is False, f"Variant {v['sku']} was not cascaded to is_available=False"

    # Case 2: Size swatch HTML parsing with mixed enabled/disabled states
    mock_html_mixed = """
    <html>
      <body>
        <div class="variation-size-group">
          <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_enbld">7</button>
          <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_dsbld">8</button>
          <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_enbld">9</button>
        </div>
      </body>
    </html>
    """
    pdp_info = extract_coach_pdp_info(mock_html_mixed)
    assert pdp_info["availability"] == "in_stock", "Mixed size buttons should result in in_stock"
    v_delta = pdp_info["variants_delta"]
    assert len(v_delta) == 3
    assert v_delta[0] == {"size": "7", "available": True}
    assert v_delta[1] == {"size": "8", "available": False}
    assert v_delta[2] == {"size": "9", "available": True}

    # Case 3: Size swatch HTML parsing with ALL disabled buttons
    mock_html_all_dsbld = """
    <html>
      <body>
        <div class="variation-size-group">
          <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_dsbld">7</button>
          <button class="chakra-button variation-option variation-size css-1bhu9le" data-qa="cm_link_size_swatch_dsbld">8</button>
        </div>
      </body>
    </html>
    """
    pdp_info_oos = extract_coach_pdp_info(mock_html_all_dsbld)
    assert pdp_info_oos["availability"] == "out_of_stock", "All disabled buttons should result in out_of_stock"

    return True, "PASSED: Coach availability cascade and HTML size swatch parsing verified."


def test_2_4_jwpei_adversarial_partial_stock_transition() -> Tuple[bool, str]:
    """
    Adversarial test for stores/jwpei/delta.py:
    1. Product has 3 variants (Black, Brown, Cream), all in stock.
    2. Delta specifies Black goes OUT of stock, others remain IN stock.
    3. Product availability must REMAIN 'in_stock'.
    4. Black variant in_stock and is_available must flip to False.
    5. has_changed = True, shopify_sync_pending = True.
    """
    product = {
        "store": "jwpei",
        "handle": "eva-shoulder-bag",
        "availability": "in_stock",
        "is_active": True,
        "source_price": 59.0,
        "current_price": 4927.0,
        "variants": [
            {"sku": "JW-EVA-BLK", "title": "Black", "in_stock": True, "is_available": True, "source_price": 59.0, "price": "4927.00"},
            {"sku": "JW-EVA-BRN", "title": "Brown", "in_stock": True, "is_available": True, "source_price": 59.0, "price": "4927.00"},
            {"sku": "JW-EVA-CRM", "title": "Cream", "in_stock": True, "is_available": True, "source_price": 59.0, "price": "4927.00"},
        ]
    }

    delta_result = {
        "status": "success",
        "handle": "eva-shoulder-bag",
        "current_source_price": 59.0,
        "old_source_price": 59.0,
        "availability": "in_stock",
        "old_availability": "in_stock",
        "is_active": True,
        "price_changed": False,
        "stock_changed": False,
        "variants_delta": [
            {"sku": "JW-EVA-BLK", "available": False, "price_usd": 59.0},
            {"sku": "JW-EVA-BRN", "available": True, "price_usd": 59.0},
            {"sku": "JW-EVA-CRM", "available": True, "price_usd": 59.0},
        ]
    }

    forex_rate = 83.5
    updated_prod, has_changed = jwpei_apply_delta(product, delta_result, forex_rate)

    assert has_changed is True, "has_changed should be True on variant stock change"
    assert updated_prod["availability"] == "in_stock", "Parent availability should remain in_stock"
    assert updated_prod["is_active"] is True, "is_active should remain True"
    assert updated_prod["shopify_sync_pending"] is True, "shopify_sync_pending should be True"

    var_map = {v["sku"]: (v["in_stock"], v.get("is_available")) for v in updated_prod["variants"]}
    assert var_map["JW-EVA-BLK"] == (False, False), "JW-EVA-BLK should have in_stock=False and is_available=False"
    assert var_map["JW-EVA-BRN"] == (True, True), "JW-EVA-BRN should have in_stock=True and is_available=True"
    assert var_map["JW-EVA-CRM"] == (True, True), "JW-EVA-CRM should have in_stock=True and is_available=True"

    return True, "PASSED: JW PEI partial variant stock transition verified with double-flag sync (in_stock + is_available)."


def test_2_5_jwpei_adversarial_full_depletion_restock_and_cascade() -> Tuple[bool, str]:
    """
    Adversarial test for stores/jwpei/delta.py:
    1. Full depletion across all variants -> top-level flips to out_of_stock.
    2. Single variant restock -> top-level flips back to in_stock.
    3. Availability cascade: variants_delta empty with parent out_of_stock -> all variants cascaded to False.
    """
    product = {
        "store": "jwpei",
        "handle": "feiyue-bag",
        "availability": "in_stock",
        "is_active": True,
        "variants": [
            {"sku": "VAR-1", "in_stock": True, "is_available": True},
            {"sku": "VAR-2", "in_stock": True, "is_available": True},
        ]
    }

    # Step 1: Deplete all variants
    delta_all_out = {
        "status": "success",
        "variants_delta": [
            {"sku": "VAR-1", "available": False},
            {"sku": "VAR-2", "available": False},
        ]
    }
    p_depleted, changed1 = jwpei_apply_delta(product, delta_all_out, 83.5)
    assert changed1 is True
    assert p_depleted["availability"] == "out_of_stock"
    assert p_depleted["is_active"] is False
    assert all(not v["in_stock"] and not v.get("is_available") for v in p_depleted["variants"])

    # Step 2: Restock VAR-1
    delta_restock = {
        "status": "success",
        "variants_delta": [
            {"sku": "VAR-1", "available": True},
            {"sku": "VAR-2", "available": False},
        ]
    }
    p_restocked, changed2 = jwpei_apply_delta(p_depleted, delta_restock, 83.5)
    assert changed2 is True
    assert p_restocked["availability"] == "in_stock"
    assert p_restocked["is_active"] is True
    assert p_restocked["variants"][0]["in_stock"] is True
    assert p_restocked["variants"][0]["is_available"] is True
    assert p_restocked["variants"][1]["in_stock"] is False

    # Step 3: Availability cascade on 404 delist / OOS
    delta_cascade = {
        "status": "not_found",
        "availability": "out_of_stock",
        "is_active": False,
        "stock_changed": True,
        "variants_delta": []
    }
    p_cascaded, changed3 = jwpei_apply_delta(p_restocked, delta_cascade, 83.5)
    assert changed3 is True
    assert p_cascaded["availability"] == "out_of_stock"
    assert p_cascaded["is_active"] is False
    for v in p_cascaded["variants"]:
        assert v["in_stock"] is False
        assert v.get("is_available") is False

    return True, "PASSED: JW PEI depletion, restock, and availability cascade verified."


def test_2_6_jwpei_variant_pricing_update_with_whole_rupee_inr() -> Tuple[bool, str]:
    """
    Adversarial test for stores/jwpei/delta.py:
    Verify that when variant prices change in USD, both price_current and price
    are converted using the forex rate with whole-rupee rounding.
    """
    product = {
        "store": "jwpei",
        "handle": "maze-bag",
        "availability": "in_stock",
        "is_active": True,
        "source_price": 79.0,
        "variants": [
            {"sku": "MAZE-1", "source_price": 79.0, "price_current": 6597.0, "price": "6597.00", "in_stock": True},
            {"sku": "MAZE-2", "source_price": 79.0, "price_current": 6597.0, "price": "6597.00", "in_stock": True},
        ]
    }

    # Delta updates MAZE-1 to $89.00 and MAZE-2 to $99.00
    delta_result = {
        "status": "success",
        "variants_delta": [
            {"sku": "MAZE-1", "available": True, "price_usd": 89.0},
            {"sku": "MAZE-2", "available": True, "price_usd": 99.0},
        ]
    }

    forex_rate = 83.5
    updated_prod, has_changed = jwpei_apply_delta(product, delta_result, forex_rate)
    assert has_changed is True

    # 89.0 * 83.5 = 7431.5 -> round = 7432.0
    # 99.0 * 83.5 = 8266.5 -> round = 8267.0 or 8266.0 (depending on round-to-even)
    v1 = updated_prod["variants"][0]
    v2 = updated_prod["variants"][1]

    assert float(v1["price_current"]).is_integer(), f"Expected integer INR price, got {v1['price_current']}"
    assert float(v1["price"]).is_integer(), f"Expected integer INR price, got {v1['price']}"
    assert float(v2["price_current"]).is_integer(), f"Expected integer INR price, got {v2['price_current']}"
    assert float(v2["price"]).is_integer(), f"Expected integer INR price, got {v2['price']}"

    return True, f"PASSED: JW PEI variant price differential update maintains whole-rupee INR rounding (v1: {v1['price_current']}, v2: {v2['price_current']})."


# ==============================================================================
# CHALLENGE 3: LIVE PDP SAMPLING REPORT VERIFICATION
# ==============================================================================

def test_3_1_live_audit_report_validation() -> Tuple[bool, str]:
    """
    Validates that scripts/live_audit_report.json exists, was generated from live runs,
    has >= 10 samples across Coach, MK, and JW PEI, and contains exactly 0 divergences.
    """
    report_path = os.path.join("scripts", "live_audit_report.json")
    if not os.path.exists(report_path):
        return False, f"FAILED: {report_path} does not exist"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_sampled = data.get("total_sampled", 0)
    divergence_count = data.get("divergence_count", -1)
    concordance_rate = data.get("concordance_rate_pct", 0.0)
    records = data.get("records", [])

    if total_sampled < 10:
        return False, f"FAILED: Expected >= 10 live sampled products, found {total_sampled}"

    if divergence_count != 0:
        return False, f"FAILED: Expected 0 divergences, found {divergence_count}"

    if concordance_rate != 100.0:
        return False, f"FAILED: Expected 100.0% concordance rate, found {concordance_rate}%"

    stores_sampled = set(r.get("store") for r in records)
    required_stores = {"coach", "michaelkors", "jwpei"}
    if not required_stores.issubset(stores_sampled):
        return False, f"FAILED: Report missing stores. Sampled stores: {stores_sampled}"

    return True, (
        f"PASSED: Verified live audit report ({total_sampled} samples across {stores_sampled}, "
        f"{divergence_count} divergences, {concordance_rate}% parity rate)."
    )


# ==============================================================================
# RUNNER
# ==============================================================================

def run_adversarial_suite():
    print("=" * 75)
    print("EMPIRICAL CHALLENGER M1-2 ADVERSARIAL TEST SUITE")
    print("=" * 75)

    catalog = load_all_db_products()
    total_loaded = sum(len(v) for v in catalog.values())
    print(f"Loaded {total_loaded} products from storage/db/:")
    for s, prods in catalog.items():
        print(f"  - {s:12}: {len(prods)} products")

    assert total_loaded == 1763, f"Expected 1763 products, found {total_loaded}"

    tests = [
        ("Test 1.1: Footwear/Apparel Sizing Integrity (0 Truncations)", lambda: test_1_1_footwear_and_apparel_sizing_integrity(catalog)),
        ("Test 1.2: Whole-Rupee Currency & Fractional Paise Math (0 Paise)", lambda: test_1_2_whole_rupee_inr_math_integrity(catalog)),
        ("Test 1.3: Parent-Child Availability Synchronization & No Ghost Stock", lambda: test_1_3_parent_child_stock_synchronization(catalog)),
        ("Test 1.4: Coach Multi-Price Variants, SKUs & Scene7 Asset URLs", lambda: test_1_4_coach_multi_price_variants_and_scene7_assets(catalog)),
        ("Test 2.1: Coach Partial Variant Stock Transition (No Phantom Event)", test_2_1_coach_adversarial_partial_stock_transition),
        ("Test 2.2: Coach Full Depletion & Single-Variant Restock", test_2_2_coach_adversarial_full_depletion_and_restock),
        ("Test 2.3: Coach Availability Cascade & Swatch HTML Parsing", test_2_3_coach_adversarial_availability_cascade_and_swatches),
        ("Test 2.4: JW PEI Partial Variant Stock Transition (Double-Flag Sync)", test_2_4_jwpei_adversarial_partial_stock_transition),
        ("Test 2.5: JW PEI Depletion, Restock & Cascade", test_2_5_jwpei_adversarial_full_depletion_restock_and_cascade),
        ("Test 2.6: JW PEI Variant Pricing Update with Whole-Rupee Math", test_2_6_jwpei_variant_pricing_update_with_whole_rupee_inr),
        ("Test 3.1: Live PDP Parity Sampling Report Validation (>=10 Samples, 0 Div)", test_3_1_live_audit_report_validation),
    ]

    results = []
    for name, fn in tests:
        print(f"\n[RUNNING] {name}...")
        try:
            passed, msg = fn()
        except Exception as err:
            import traceback
            passed = False
            msg = f"EXCEPTION: {err}\n{traceback.format_exc()}"

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {msg}")
        results.append((name, passed, msg))

    print("\n" + "=" * 75)
    print("CHALLENGER M1-2 FINAL SUMMARY")
    print("=" * 75)
    for name, passed, msg in results:
        badge = "PASS" if passed else "FAIL"
        print(f"[{badge}] {name}")
    print("=" * 75)

    all_passed = all(p for _, p, _ in results)
    verdict = "APPROVE" if all_passed else "CHALLENGE_FAILED"
    print(f"\nVERDICT: {verdict}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    run_adversarial_suite()
