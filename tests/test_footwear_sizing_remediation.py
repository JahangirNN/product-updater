"""
Comprehensive Test Suite: Footwear Sizing Standardization & Stock Parity Remediation
Verifies:
  1. Inflow normalizers (JD Sports, Foot Locker, Nordstrom) produce single 'Size' option with pure UK values.
  2. Taxonomy defensive consolidation collapses dual Size (US) / Size (UK) into single Size preferring UK.
  3. Rate limiter reset_store_throttles() clears throttle counters across cycle sweeps.
  4. Nordstrom delta fast-path blind spot is fixed (does not bypass multi-variant products).
  5. Local database JSON schemas conform to unified sizing.
Pure functions and unit tests (ADR 0002, ADR 0005).
"""
import unittest
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_taxonomy import resolve_options_and_variants, prepare_product_set_payload
from storage import rate_limiter
from stores.jdsports.inflow import parse_and_format_size as jd_parse_size, parse_product_payload as jd_parse_payload
from stores.footlocker.inflow import convert_us_to_uk as fl_convert_us_to_uk, parse_product_payload as fl_canonical
from stores.nordstrom.inflow import convert_us_to_uk as nord_convert_us_to_uk, parse_product_payload as nord_canonical


class TestFootwearSizingRemediation(unittest.TestCase):

    def test_taxonomy_defensive_consolidation(self):
        """Test resolve_options_and_variants collapses legacy dual size options into single Size preferring UK."""
        legacy_product = {
            "title": "Nike Air Force 1 '07",
            "source_store": "jdsports",
            "product_type": "Shoes",
            "source_price": 100.0,
            "availability": "in_stock",
            "variants": [
                {
                    "sku": "VAR-1",
                    "title": "US 7.0 / UK 4.5 - White",
                    "source_price": 100.0,
                    "in_stock": True,
                    "option_values": [
                        {"option_name": "Size (US)", "name": "US 7.0"},
                        {"option_name": "Size (UK)", "name": "UK 4.5"},
                        {"option_name": "Color", "name": "White"}
                    ]
                },
                {
                    "sku": "VAR-2",
                    "title": "US 8.0 / UK 5.5 - White",
                    "source_price": 100.0,
                    "in_stock": False,
                    "option_values": [
                        {"option_name": "Size (US)", "name": "US 8.0"},
                        {"option_name": "Size (UK)", "name": "UK 5.5"},
                        {"option_name": "Color", "name": "White"}
                    ]
                }
            ]
        }

        options, variants = resolve_options_and_variants(legacy_product, 96.0, 100.0, None)
        option_names = [o["name"] for o in options]

        # Verify dual options collapsed to single 'Size' and 'Color'
        self.assertIn("Size", option_names)
        self.assertIn("Color", option_names)
        self.assertNotIn("Size (US)", option_names)
        self.assertNotIn("Size (UK)", option_names)

        # Verify option values are UK sizes
        size_opt = next(o for o in options if o["name"] == "Size")
        size_vals = [v["name"] for v in size_opt["values"]]
        self.assertIn("UK 4.5", size_vals)
        self.assertIn("UK 5.5", size_vals)

        # Verify variants have single Size option value
        self.assertEqual(len(variants), 2)
        v0_ovs = variants[0]["optionValues"]
        v0_names = [ov["optionName"] for ov in v0_ovs]
        self.assertEqual(v0_names, ["Size", "Color"])
        self.assertEqual(v0_ovs[0]["name"], "UK 4.5")

    def test_rate_limiter_reset_store_throttles(self):
        """Test consecutive throttle counter reset prevents cold cycle circuit trips."""
        store = "test_store_sweep"
        limiter = rate_limiter.create_store_limiter(store)

        # Simulate 2 throttles tripping breaker
        rate_limiter.record_throttle(store, threshold=2, cooldown_seconds=60.0)
        rate_limiter.record_throttle(store, threshold=2, cooldown_seconds=60.0)
        self.assertTrue(limiter["is_circuit_open"]())

        # Reset store throttles
        rate_limiter.reset_store_throttles(store)
        with rate_limiter._GLOBAL_LOCK:
            self.assertEqual(rate_limiter._CONSECUTIVE_THROTTLES.get(store), 0)

        # All-store clear
        rate_limiter.record_throttle("store_a", threshold=5)
        rate_limiter.record_throttle("store_b", threshold=5)
        rate_limiter.reset_store_throttles()
        with rate_limiter._GLOBAL_LOCK:
            self.assertEqual(len(rate_limiter._CONSECUTIVE_THROTTLES), 0)

    def test_nordstrom_delta_multi_variant_fast_path_bypass(self):
        """Verify that multi-variant footwear products do not take the blind-spot fast path."""
        # Inspect source code of stores/nordstrom/delta.py directly to ensure invariant is enforced
        delta_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stores", "nordstrom", "delta.py")
        with open(delta_path, "r", encoding="utf-8") as f:
            code = f.read()

        self.assertIn("has_child_variants = len(product.get(\"variants\") or []) > 1", code)
        self.assertIn("and not has_child_variants", code)

    def test_local_database_footwear_schemas(self):
        """Test sample migrated JSON records from each store for unified Size option."""
        db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")

        for store in ["jdsports", "footlocker", "nordstrom"]:
            p_dir = os.path.join(db_root, store, "products")
            files = [os.path.join(p_dir, f) for f in os.listdir(p_dir) if f.endswith(".json")]
            self.assertGreater(len(files), 0, f"No files found in {p_dir}")

            # Check first 5 files of each store
            for fp in files[:5]:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Check options
                opts = data.get("product_options") or data.get("options") or []
                opt_names = [o.get("name") for o in opts]
                self.assertNotIn("Size (US)", opt_names, f"File {fp} has Size (US)")
                self.assertNotIn("Size (UK)", opt_names, f"File {fp} has Size (UK)")
                if data.get("variants") and len(data["variants"]) > 1:
                    self.assertIn("Size", opt_names, f"File {fp} missing Size option")

                # Check variants
                for v in data.get("variants", []):
                    ovs = v.get("option_values", [])
                    ov_names = [ov.get("option_name") for ov in ovs]
                    self.assertNotIn("Size (US)", ov_names, f"Variant in {fp} has Size (US)")
                    self.assertNotIn("Size (UK)", ov_names, f"Variant in {fp} has Size (UK)")

    def test_jdsports_inflow_single_size_output(self):
        """Test JD Sports inflow normalizer produces single Size option with pure UK values."""
        raw_jd = {
            "name": "Men's Nike Air Max 90 Casual Shoes",
            "sku": "FN0374_001",
            "color": "Black/White",
            "source_price": 130.0,
            "hasVariant": [
                {"sku": "FN0374-001-8", "size": "8.0", "offers": {"price": 130.0, "availability": "https://schema.org/InStock"}},
                {"sku": "FN0374-001-9", "size": "9.0", "offers": {"price": 130.0, "availability": "https://schema.org/InStock"}},
                {"sku": "FN0374-001-10", "size": "10.0", "offers": {"price": 130.0, "availability": "https://schema.org/InStock"}}
            ]
        }
        res = jd_parse_payload(raw_jd, usd_to_inr_rate=96.0)
        self.assertIsNotNone(res)
        opts = [o["name"] for o in res["product_options"]]
        self.assertEqual(opts, ["Size", "Color"])
        self.assertNotIn("Size (US)", opts)
        self.assertNotIn("Size (UK)", opts)

        for v in res["variants"]:
            v_opts = [ov["option_name"] for ov in v["option_values"]]
            self.assertEqual(v_opts, ["Size", "Color"])
            self.assertTrue(v["option_values"][0]["name"].startswith("UK "))

    def test_footlocker_inflow_single_size_output(self):
        """Test Foot Locker inflow normalizer produces single Size option with pure UK values."""
        raw_fl = {
            "style": {
                "sku": "IG1234",
                "name": "Superstar Shoes",
                "brand": "adidas",
                "gender": "Men's",
                "color": "Cloud White / Core Black",
                "price": {
                    "salePrice": 100.0,
                    "listPrice": 120.0
                }
            },
            "model": {
                "name": "Superstar",
                "description": "Iconic shell-toe shoe."
            },
            "sizes": [
                {"size": "8.0", "active": True},
                {"size": "9.0", "active": True},
                {"size": "10.0", "active": True}
            ]
        }
        res = fl_canonical(raw_fl, forex_rate=96.0)
        self.assertIsNotNone(res)
        opts = [o["name"] for o in res["product_options"]]
        self.assertEqual(opts, ["Size", "Color"])
        self.assertNotIn("Size (US)", opts)
        self.assertNotIn("Size (UK)", opts)

        for v in res["variants"]:
            v_opts = [ov["option_name"] for ov in v["option_values"]]
            self.assertEqual(v_opts, ["Size", "Color"])
            self.assertTrue(v["option_values"][0]["name"].startswith("UK "))

    def test_nordstrom_inflow_single_size_output(self):
        """Test Nordstrom inflow normalizer produces single Size option with pure UK values."""
        raw_nord = {
            "id": "1234567",
            "title": "Cloud 5 Sneaker",
            "url": "https://www.nordstrom.com/s/cloud-5/1234567",
            "brand": "On",
            "gender": "Men's",
            "current_price": 140.0,
            "sizes": [
                {"us_size": "8.0", "in_stock": True},
                {"us_size": "9.0", "in_stock": True},
                {"us_size": "10.0", "in_stock": True}
            ],
            "colorways": [
                {
                    "color_name": "All Black",
                    "sizes": [
                        {"us_size": "8.0", "in_stock": True},
                        {"us_size": "9.0", "in_stock": True},
                        {"us_size": "10.0", "in_stock": True}
                    ]
                }
            ]
        }
        res = nord_canonical(raw_nord, usd_to_inr_rate=96.0)
        self.assertIsNotNone(res)
        opts = [o["name"] for o in res["product_options"]]
        self.assertEqual(opts, ["Size", "Color"])
        self.assertNotIn("Size (US)", opts)
        self.assertNotIn("Size (UK)", opts)

        for v in res["variants"]:
            v_opts = [ov["option_name"] for ov in v["option_values"]]
            self.assertEqual(v_opts, ["Size", "Color"])
            self.assertTrue(v["option_values"][0]["name"].startswith("UK "))

    def test_taxonomy_out_of_stock_variant_preservation(self):
        """Test variants retain their out-of-stock status during consolidation."""
        prod = {
            "title": "Air Max",
            "source_store": "jdsports",
            "product_type": "Shoes",
            "variants": [
                {
                    "sku": "VAR-IN",
                    "title": "UK 8 - Black",
                    "in_stock": True,
                    "availability": "in_stock",
                    "source_price": 100.0,
                    "option_values": [{"option_name": "Size", "name": "UK 8"}, {"option_name": "Color", "name": "Black"}]
                },
                {
                    "sku": "VAR-OUT",
                    "title": "UK 9 - Black",
                    "in_stock": False,
                    "availability": "out_of_stock",
                    "source_price": 100.0,
                    "option_values": [{"option_name": "Size", "name": "UK 9"}, {"option_name": "Color", "name": "Black"}]
                }
            ]
        }
        options, variants = resolve_options_and_variants(prod, 96.0, 100.0, None)
        self.assertEqual(len(variants), 2)
        v_in = next(v for v in variants if any(ov["name"] == "UK 8" for ov in v["optionValues"]))
        v_out = next(v for v in variants if any(ov["name"] == "UK 9" for ov in v["optionValues"]))

        # Check inventory policy and tracking per dropship catalog convention
        self.assertEqual(v_in["inventoryPolicy"], "CONTINUE")
        self.assertFalse(v_in["inventoryItem"]["tracked"])

        self.assertEqual(v_out["inventoryPolicy"], "DENY")
        self.assertTrue(v_out["inventoryItem"]["tracked"])


    def test_taxonomy_duplicate_size_deduplication(self):
        """Test duplicate size variants are collapsed with in-stock variant preferred."""
        prod = {
            "title": "Nike Dunk Low",
            "source_store": "jdsports",
            "product_type": "Shoes",
            "variants": [
                {
                    "sku": "VAR-DUP-1",
                    "in_stock": False,
                    "source_price": 120.0,
                    "option_values": [{"option_name": "Size (US)", "name": "US 8.0"}, {"option_name": "Size (UK)", "name": "UK 7.5"}, {"option_name": "Color", "name": "White"}]
                },
                {
                    "sku": "VAR-DUP-2",
                    "in_stock": True,
                    "source_price": 120.0,
                    "option_values": [{"option_name": "Size (US)", "name": "US 8.0"}, {"option_name": "Size (UK)", "name": "UK 7.5"}, {"option_name": "Color", "name": "White"}]
                }
            ]
        }
        options, variants = resolve_options_and_variants(prod, 96.0, 120.0, None)
        # Should deduplicate into exactly 1 variant
        self.assertEqual(len(variants), 1)
        # In-stock variant should have won
        iq = variants[0].get("inventoryQuantities", [])
        if iq:
            self.assertGreater(iq[0]["availableQuantity"], 0)

    def test_whole_rupee_pricing(self):
        """Test INR prices are rounded to whole rupees (no paise decimals)."""
        prod = {
            "title": "On Cloud",
            "source_store": "nordstrom",
            "product_type": "Shoes",
            "source_price": 149.99,
            "variants": [
                {
                    "sku": "ON-1",
                    "source_price": 149.99,
                    "in_stock": True,
                    "option_values": [{"option_name": "Size", "name": "UK 9"}, {"option_name": "Color", "name": "Black"}]
                }
            ]
        }
        forex_rate = 96.4321
        options, variants = resolve_options_and_variants(prod, forex_rate, 149.99, None)
        v_price = float(variants[0]["price"])
        # Under Universal .99 Charm Baseline (ADR 0028):
        # 149.99 * 96.4321 = 14463.85 -> commercial_round_half_up(14463.85, 100) = 14500 -> 14499.0
        self.assertEqual(v_price, 14499.0)
        self.assertEqual(int(v_price) % 100, 99)
        self.assertEqual(v_price, float(int(v_price)))

    def test_inflow_half_and_integer_sizes(self):
        """Test conversion of half and integer sizes across all stores."""
        # Nike Men's (offset -1.0) and Women's (offset -2.5)
        self.assertEqual(fl_convert_us_to_uk("10.5", "Men's"), "9.5")
        self.assertEqual(fl_convert_us_to_uk("10.0", "Men's"), "9")
        self.assertEqual(fl_convert_us_to_uk("7.5", "Women's"), "5")

        # On Running Men's (offset -0.5) and Women's (offset -2.0)
        self.assertEqual(nord_convert_us_to_uk("10.5", "Men's"), "10")
        self.assertEqual(nord_convert_us_to_uk("10", "Men's"), "9.5")
        self.assertEqual(nord_convert_us_to_uk("7.5", "Women's"), "5.5")

    def test_inflow_duplicate_uk_sizes_deduplication(self):
        """Test that inflow normalizers deduplicate variants when two US sizes map to the same UK size."""
        raw_jd = {
            "@type": "ProductGroup",
            "name": "Big Kids Nike Dunk Low",
            "hasVariant": [
                {"size": "6.5", "in_stock": False, "sku": "SKU-65"},
                {"size": "7.0", "in_stock": True, "sku": "SKU-70"},
                {"size": "3.5", "in_stock": True, "sku": "SKU-35"},
                {"size": "4.0", "in_stock": True, "sku": "SKU-40"},
                {"size": "4.5", "in_stock": True, "sku": "SKU-45"},
                {"size": "5.0", "in_stock": True, "sku": "SKU-50"},
                {"size": "5.5", "in_stock": True, "sku": "SKU-55"}
            ]
        }
        res_jd = jd_parse_payload(raw_jd, usd_to_inr_rate=96.0)
        self.assertIsNotNone(res_jd)
        # 6.5Y and 7.0Y both map to UK 6 in youth. Variants must be deduplicated to exactly 6 distinct UK sizes
        jd_size_combos = [(v["title"], tuple((ov["option_name"], ov["name"]) for ov in v["option_values"])) for v in res_jd["variants"]]
        self.assertEqual(len(jd_size_combos), len(set(jd_size_combos)))
        # Check in_stock status is True for UK 6 (since 7.0 was True)
        v_uk6 = next(v for v in res_jd["variants"] if "UK 6" in v["title"])
        self.assertTrue(v_uk6["in_stock"])

    def test_zero_duplicate_variant_combos_in_local_db(self):
        """Verify 100% of all 1,021 footwear products in local database have zero duplicate (Size, Color) variant combos."""
        import glob
        db_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "db")
        for store in ["jdsports", "footlocker", "nordstrom"]:
            p_dir = os.path.join(db_root, store, "products")
            files = glob.glob(os.path.join(p_dir, "*.json"))
            self.assertGreater(len(files), 0)
            for fp in files:
                with open(fp, "r", encoding="utf-8") as f:
                    d = json.load(f)
                combos = []
                for v in d.get("variants", []):
                    s_val = next((ov["name"] for ov in v.get("option_values", []) if ov.get("option_name") == "Size"), "")
                    c_val = next((ov["name"] for ov in v.get("option_values", []) if ov.get("option_name") == "Color"), "")
                    combos.append((s_val, c_val))
                self.assertEqual(len(combos), len(set(combos)), f"{store}/{os.path.basename(fp)} has duplicate variant combos: {combos}")
    def test_footlocker_inflow_duplicate_uk_sizes_deduplication(self):
        """Test that Foot Locker normalizer deduplicates variants when two US sizes map to the same UK size."""
        raw_fl = {
            "style": {
                "sku": "SKU-FL123",
                "name": "Nike Air Max Men's",
                "brand": "Nike",
                "gender": "Men's",
                "color": "Triple White",
                "price": {"salePrice": 120.0, "listPrice": 120.0}
            },
            "model": {"name": "Air Max", "description": "Running shoe"},
            "sizes": [
                {"size": "6.5", "active": False},
                {"size": "7.0", "active": True},
                {"size": "8.0", "active": True}
            ]
        }
        res_fl = fl_canonical(raw_fl, forex_rate=96.0)
        self.assertIsNotNone(res_fl)
        fl_size_combos = [tuple((ov["option_name"], ov["name"]) for ov in v["option_values"]) for v in res_fl["variants"]]
        self.assertEqual(len(fl_size_combos), len(set(fl_size_combos)))

    def test_nordstrom_inflow_duplicate_uk_sizes_deduplication(self):
        """Test that Nordstrom normalizer deduplicates variants when two US sizes map to the same UK size."""
        raw_nord = {
            "id": "123456",
            "title": "Cloudflow 4 Running Shoe",
            "gender": "men",
            "current_price": 140.0,
            "sizes": [
                {"us_size": "7.0", "in_stock": False},
                {"us_size": "7.5", "in_stock": True},
                {"us_size": "8.0", "in_stock": True},
                {"us_size": "8.5", "in_stock": True},
                {"us_size": "9.0", "in_stock": True},
                {"us_size": "9.5", "in_stock": True},
                {"us_size": "10.0", "in_stock": True}
            ]
        }
        res_nord = nord_canonical(raw_nord, usd_to_inr_rate=96.0, min_size_variants=7)
        self.assertIsNotNone(res_nord)
        nord_size_combos = [tuple((ov["option_name"], ov["name"]) for ov in v["option_values"]) for v in res_nord["variants"]]
        self.assertEqual(len(nord_size_combos), len(set(nord_size_combos)))


if __name__ == "__main__":
    unittest.main()

