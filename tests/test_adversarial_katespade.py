"""
Adversarial Stress Test Suite for Kate Spade Taxonomy, Silhouette Resolution,
Supplier Leakage Stripping, and Shopify Smart Collection Auto-Population.
"""
import os
import sys
import glob
import json
import re
import unittest
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_taxonomy import (
    resolve_authentic_vendor,
    resolve_gender,
    resolve_luxury_bag_silhouette,
    resolve_product_type,
    is_wallet_product,
    generate_taxonomy_tags,
    prepare_product_set_payload,
)
from storage.shopify_collections import COLLECTIONS_MANIFEST


def evaluate_rule_set(rule_set: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """Simulate Shopify Smart Collection rule matching logic."""
    disjunctive = rule_set.get("appliedDisjunctively", False)
    rules = rule_set.get("rules", [])
    if not rules:
        return False

    tags = set(payload.get("tags", []))
    vendor = payload.get("vendor", "")
    p_type = payload.get("productType", "")
    title = payload.get("title", "")

    matches = []
    for r in rules:
        col = r["column"]
        rel = r["relation"]
        cond = r["condition"]

        matched = False
        if col == "TAG":
            if rel == "EQUALS":
                matched = cond in tags
            elif rel == "CONTAINS":
                matched = any(cond.lower() in t.lower() for t in tags)
        elif col == "VENDOR":
            if rel == "EQUALS":
                matched = (vendor.lower() == cond.lower())
            elif rel == "CONTAINS":
                matched = (cond.lower() in vendor.lower())
        elif col == "TYPE":
            if rel == "EQUALS":
                matched = (p_type.lower() == cond.lower())
            elif rel == "CONTAINS":
                matched = (cond.lower() in p_type.lower())
        elif col == "TITLE":
            if rel == "EQUALS":
                matched = (title.lower() == cond.lower())
            elif rel == "CONTAINS":
                matched = (cond.lower() in title.lower())

        matches.append(matched)

    if disjunctive:
        return any(matches)
    else:
        return all(matches)


class TestAdversarialKateSpade(unittest.TestCase):

    def test_01_fringe_bags_resolution(self):
        """Verify genuine bags with fringe resolve correctly to luxury silhouettes."""
        fringe_cases = [
            ("Margot Fringe Shoulder Bag", "Shoulder Bags"),
            ("Chelsea Fringe Medium Satchel", "Satchels & Top Handles"),
            ("Spade Flower Fringe Tote", "Totes"),
            ("Fringe Crossbody Bag", "Crossbody & Messenger Bags"),
            ("Bleecker Large Fringe Carryall", "Totes"),
            ("Knott Fringe Leather Backpack", "Backpacks"),
            ("FRINGE SHOULDER BAG", "Shoulder Bags"),
            ("KATIE FRINGE CROSSBODY - OUTLET EXCLUSIVE", "Crossbody & Messenger Bags"),
        ]
        for title, expected_sil in fringe_cases:
            mock_prod = {"source_store": "katespade", "title": title, "product_type": "Handbags"}
            sil = resolve_luxury_bag_silhouette(mock_prod)
            self.assertEqual(sil, expected_sil, f"Fringe bag failed: {title} -> {sil}")

    def test_02_decorative_charm_edge_cases(self):
        """
        Adversarial probe on decorative charm product titles.
        Demonstrates the bug where titles with 'bag charm' or 'key charm' unconditionally resolve to None.
        """
        passing_charms = [
            ("Staci Charm Crossbody", "Crossbody & Messenger Bags"),
            ("Margot Suede Shoulder Bag With Floral Charm", "Shoulder Bags"),
            ("Knott Medium Satchel with Charm", "Satchels & Top Handles"),
            ("Chelsea Charm Pouch", "Clutches & Evening Bags"),
            ("Tessa Tote Bag With Charm", "Totes"),
        ]
        for title, expected_sil in passing_charms:
            mock_prod = {"source_store": "katespade", "title": title, "product_type": "Handbags"}
            sil = resolve_luxury_bag_silhouette(mock_prod)
            self.assertEqual(sil, expected_sil, f"Passed charm bag failed: {title} -> {sil}")

        # Remediated charm bags must resolve to their genuine luxury bag silhouettes
        remediated_charms = [
            ("Hudson Large Tote With Bag Charm", "Totes"),
            ("Gramercy Bag Charm Bucket Bag", "Satchels & Top Handles"),
            ("Staci Flap Crossbody With Bag Charm", "Crossbody & Messenger Bags"),
            ("Spade Flower Key Charm Crossbody", "Crossbody & Messenger Bags"),
        ]
        for title, expected_sil in remediated_charms:
            mock_prod = {"source_store": "katespade", "title": title, "product_type": "Handbags"}
            sil = resolve_luxury_bag_silhouette(mock_prod)
            self.assertEqual(sil, expected_sil, f"Remediated charm bag failed: {title} -> {sil}")

    def test_03_key_ring_wallet_edge_cases(self):
        """
        Adversarial probe on wallets with key ring or keychain in title.
        Verifies wallets and card cases with key rings or keychains resolve correctly to Wallets & Small Leather Goods.
        """
        remediated_wallets = [
            ("Leather Key Ring Wallet", "Wallets & Small Leather Goods"),
            ("Staci Key Ring Card Case", "Wallets & Small Leather Goods"),
            ("Spade Flower Keychain Wallet", "Wallets & Small Leather Goods"),
            ("Morgan Card Case With Key Ring", "Wallets & Small Leather Goods"),
        ]
        for title, expected_sil in remediated_wallets:
            mock_prod = {"source_store": "katespade", "title": title, "product_type": "Wallets"}
            sil = resolve_luxury_bag_silhouette(mock_prod)
            self.assertEqual(sil, expected_sil, f"Remediated wallet failed: {title} -> {sil}")

    def test_04_care_products_and_standalone_accessories_rejected(self):
        """Verify care products and standalone accessories are correctly rejected (resolve to None)."""
        rejected_items = [
            "Leather Cleaner & Conditioner",
            "Fabric Protector Spray",
            "Leather Care Kit",
            "Suede Refresher Spray",
            "Waterproof Leather Protector",
            "Stain Remover Sponge",
            # Standalone charms & keychains
            "Spade Flower Metal Bag Charm",
            "Glitter Heart Bag Charm",
            "Heritage Spade Key Charm",
            "Enamel Heart Keychain",
            "Leather Keychain",
            # Jewelry & Fragrance
            "Heritage Spade Flower Ring",
            "Pave Crystal Band Ring",
            "Pave Stud Earrings",
            "Tennis Bangle Bracelet",
            "Heart Pendant Necklace",
            "Signature Travel Umbrella",
            "Cherie Eau De Parfum Spray",
            "Truly Dazzling Perfume Rollerball",
        ]

        for item_title in rejected_items:
            mock_prod = {
                "source_store": "katespade",
                "title": item_title,
                "product_type": "Accessories",
            }
            sil = resolve_luxury_bag_silhouette(mock_prod)
            self.assertIsNone(
                sil,
                f"Non-bag accessory '{item_title}' was NOT rejected! Got: {sil}"
            )

    def test_05_supplier_leak_stripping_under_all_conditions(self):
        """Verify supplier leak 'katespadeoutlet' is stripped under all permutations."""
        leak_variations = [
            "katespadeoutlet",
            "KateSpadeOutlet",
            "KATESPADEOUTLET",
            "kate-spade-outlet",
            "katespadeoutlet.com",
            "outlet.katespade.com",
            "https://www.katespadeoutlet.com/products/staci-satchel",
        ]

        for leak in leak_variations:
            mock_prod = {
                "source_store": "katespade",
                "vendor": leak,
                "title": f"Staci Crossbody - {leak}",
                "source_url": f"https://www.katespadeoutlet.com/products/{leak}",
                "tags": [leak, f"Supplier:{leak}", "katespadeoutlet_special", "Women", "Crossbody Bags"],
            }
            # Vendor resolution
            vendor = resolve_authentic_vendor(mock_prod)
            self.assertEqual(
                vendor,
                "Kate Spade",
                f"Failed to resolve authentic vendor for leak '{leak}': got '{vendor}'"
            )

            # Tag stripping
            tags = generate_taxonomy_tags(mock_prod, vendor, "Crossbody & Messenger Bags", "Women")
            for t in tags:
                self.assertNotIn(
                    "katespadeoutlet",
                    t.lower(),
                    f"Leak survived in tag '{t}' for input '{leak}'"
                )

    def test_06_full_catalog_429_products_silhouette_and_vendor(self):
        """Test all 429 catalog products in storage/db/katespade/products/*.json."""
        catalog_files = glob.glob(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "storage", "db", "katespade", "products", "*.json"
            )
        )
        self.assertEqual(len(catalog_files), 429, f"Expected 429 files, found {len(catalog_files)}")

        silhouettes = {}
        vendors = {}
        genders = {}
        none_silhouettes = []
        wallet_items = []
        bag_items = []

        for fpath in catalog_files:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)

            vendor = resolve_authentic_vendor(prod)
            vendors[vendor] = vendors.get(vendor, 0) + 1

            sil = resolve_luxury_bag_silhouette(prod)
            if sil is None:
                none_silhouettes.append((prod.get("id"), prod.get("title")))
            else:
                silhouettes[sil] = silhouettes.get(sil, 0) + 1

            gender = resolve_gender(prod)
            genders[gender] = genders.get(gender, 0) + 1

            if sil == "Wallets & Small Leather Goods" or is_wallet_product(prod):
                wallet_items.append((prod.get("id"), prod.get("title"), sil))
            else:
                bag_items.append((prod.get("id"), prod.get("title"), sil))

        # Assertions
        self.assertEqual(
            len(none_silhouettes), 0,
            f"Found {len(none_silhouettes)} products with None silhouette: {none_silhouettes}"
        )
        self.assertEqual(
            vendors, {"Kate Spade": 429},
            f"Vendor mismatch across catalog: {vendors}"
        )
        self.assertEqual(
            genders, {"Women": 429},
            f"Gender mismatch across catalog: {genders}"
        )

        # Silhouette breakdown check
        self.assertEqual(
            len(wallet_items), 8,
            f"Expected exactly 8 wallets, found {len(wallet_items)}: {wallet_items}"
        )
        self.assertEqual(
            len(bag_items), 421,
            f"Expected exactly 421 true bags, found {len(bag_items)}"
        )

    def test_07_smart_collection_simulation(self):
        """Simulate smart collection matching for all 429 catalog products."""
        catalog_files = glob.glob(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "storage", "db", "katespade", "products", "*.json"
            )
        )
        manifest_by_handle = {c["handle"]: c for c in COLLECTIONS_MANIFEST}

        # Check required collections exist in manifest
        required_handles = [
            "kate-spade",
            "women",
            "womens-handbags",
            "designer-bags",
            "luxury-bags",
            "womens-bags",
            "crossbody-bags",
            "totes",
            "wallets-leather-goods",
            "wallets-accessories",
            "womens-wallets",
        ]
        for handle in required_handles:
            self.assertIn(handle, manifest_by_handle, f"Collection handle '{handle}' missing from COLLECTIONS_MANIFEST")

        match_counts = {h: 0 for h in required_handles}
        wallet_matched_in_handbags = []

        for fpath in catalog_files:
            with open(fpath, "r", encoding="utf-8") as f:
                prod = json.load(f)

            payload = prepare_product_set_payload(prod, 95.0)
            is_wallet = (payload["productType"] == "Wallets & Small Leather Goods") or is_wallet_product(prod)

            for handle in required_handles:
                col = manifest_by_handle[handle]
                if evaluate_rule_set(col["ruleSet"], payload):
                    match_counts[handle] += 1
                    if is_wallet and handle in ("womens-handbags", "designer-bags", "luxury-bags", "womens-bags", "crossbody-bags", "totes"):
                        wallet_matched_in_handbags.append((prod.get("id"), prod.get("title"), handle))

        # Invariants:
        # 1. 429 match /collections/kate-spade
        self.assertEqual(
            match_counts["kate-spade"], 429,
            f"Expected 429 products to match /collections/kate-spade, got {match_counts['kate-spade']}"
        )

        # 2. 429 match /collections/women
        self.assertEqual(
            match_counts["women"], 429,
            f"Expected 429 products to match /collections/women, got {match_counts['women']}"
        )

        # 3. 421 true bags match /collections/womens-handbags
        self.assertEqual(
            match_counts["womens-handbags"], 421,
            f"Expected 421 products to match /collections/womens-handbags, got {match_counts['womens-handbags']}"
        )

        # 4. 421 true bags match /collections/designer-bags
        self.assertEqual(
            match_counts["designer-bags"], 421,
            f"Expected 421 products to match /collections/designer-bags, got {match_counts['designer-bags']}"
        )

        # 5. 421 true bags match /collections/luxury-bags
        self.assertEqual(
            match_counts["luxury-bags"], 421,
            f"Expected 421 products to match /collections/luxury-bags, got {match_counts['luxury-bags']}"
        )

        # 6. 421 true bags match /collections/womens-bags
        self.assertEqual(
            match_counts["womens-bags"], 421,
            f"Expected 421 products to match /collections/womens-bags, got {match_counts['womens-bags']}"
        )

        # 7. 8 wallets match wallet collections
        self.assertEqual(
            match_counts["wallets-leather-goods"], 8,
            f"Expected 8 products to match /collections/wallets-leather-goods, got {match_counts['wallets-leather-goods']}"
        )
        self.assertEqual(
            match_counts["wallets-accessories"], 8,
            f"Expected 8 products to match /collections/wallets-accessories, got {match_counts['wallets-accessories']}"
        )
        self.assertEqual(
            match_counts["womens-wallets"], 8,
            f"Expected 8 products to match /collections/womens-wallets, got {match_counts['womens-wallets']}"
        )

        # 8. Zero wallets in handbag collections
        self.assertEqual(
            len(wallet_matched_in_handbags), 0,
            f"Wallets matched handbag collections! Violations: {wallet_matched_in_handbags}"
        )


if __name__ == "__main__":
    unittest.main()
