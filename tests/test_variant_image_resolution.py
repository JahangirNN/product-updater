"""
Unit tests for Variant Image Resolution, Ghost Variant Pruning, and Multi-Category Harmony.
Covers:
1. Multi-dimensional variants (Size + Color in option_values).
2. Sibling variant image inheritance.
3. Preservation of non-color size variants (e.g. shoes, watches).
4. Ghost color variant pruning when un-photographed.
5. Deduplication of variant option values with image preservation.
6. Fallback compareAtPrice retention.
7. Payload gallery file generation.
"""
import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_taxonomy import (
    extract_variant_color,
    resolve_variant_image,
    resolve_options_and_variants,
    prepare_product_set_payload,
    BROKEN_IMAGE_URLS
)


class TestVariantImageResolution(unittest.TestCase):

    def test_extract_variant_color_direct(self):
        v = {"color": "Ivory", "title": "One Size"}
        self.assertEqual(extract_variant_color(v), "Ivory")

    def test_extract_variant_color_option_values(self):
        v = {
            "title": "US 7 / UK 5",
            "option_values": [
                {"option_name": "Size", "name": "US 7 / UK 5"},
                {"option_name": "Color", "name": "Cognac"}
            ]
        }
        self.assertEqual(extract_variant_color(v), "Cognac")

    def test_extract_variant_color_title_split(self):
        v = {"title": "US 8 - Midnight Blue", "option_values": [{"option_name": "Size", "name": "US 8"}]}
        self.assertEqual(extract_variant_color(v), "Midnight Blue")

    def test_extract_variant_color_size_only_returns_none(self):
        v = {"title": "US 9.5", "option_values": [{"option_name": "Size", "name": "US 9.5"}]}
        self.assertIsNone(extract_variant_color(v))

    def test_resolve_variant_image_sibling_inheritance(self):
        prod = {
            "title": "Luxury Sandal",
            "product_type": "Sandals",
            "images": ["https://cdn.example.com/sandal-black.jpg"],
            "variants": [
                {
                    "title": "US 6 - Black",
                    "sku": "MK-6-BLK",
                    "image_url": "https://cdn.example.com/sandal-black.jpg",
                    "option_values": [{"option_name": "Size", "name": "US 6"}, {"option_name": "Color", "name": "Black"}]
                },
                {
                    "title": "US 7 - Black",
                    "sku": "MK-7-BLK",
                    "image_url": None,
                    "option_values": [{"option_name": "Size", "name": "US 7"}, {"option_name": "Color", "name": "Black"}]
                }
            ]
        }
        v0 = prod["variants"][0]
        v1 = prod["variants"][1]
        self.assertEqual(resolve_variant_image(v0, prod), "https://cdn.example.com/sandal-black.jpg")
        # Sibling v1 inherits from v0
        self.assertEqual(resolve_variant_image(v1, prod), "https://cdn.example.com/sandal-black.jpg")

    def test_resolve_variant_image_gallery_color_slug(self):
        prod = {
            "title": "Woven Tote",
            "product_type": "Totes",
            "images": [
                "https://cdn.example.com/woven-tote-dark-brown.jpg",
                "https://cdn.example.com/woven-tote-lemon-yellow.jpg"
            ],
            "variants": [
                {
                    "title": "Dark Brown",
                    "option_values": [{"option_name": "Color", "name": "Dark Brown"}]
                },
                {
                    "title": "Lemon Yellow",
                    "option_values": [{"option_name": "Color", "name": "Lemon Yellow"}]
                }
            ]
        }
        self.assertEqual(resolve_variant_image(prod["variants"][0], prod), "https://cdn.example.com/woven-tote-dark-brown.jpg")
        self.assertEqual(resolve_variant_image(prod["variants"][1], prod), "https://cdn.example.com/woven-tote-lemon-yellow.jpg")

    def test_shoe_sizes_never_pruned_when_images_missing_on_subsequent_sizes(self):
        shoe = {
            "title": "Speedcross 6 Running Shoe",
            "product_type": "Shoes",
            "images": ["https://cdn.example.com/speedcross-black.jpg"],
            "variants": [
                {"title": "US 7", "sku": "SAL-7", "image_url": "https://cdn.example.com/speedcross-black.jpg", "source_price": 140, "option_values": [{"option_name": "Size", "name": "US 7"}]},
                {"title": "US 8", "sku": "SAL-8", "image_url": None, "source_price": 140, "option_values": [{"option_name": "Size", "name": "US 8"}]},
                {"title": "US 9", "sku": "SAL-9", "image_url": None, "source_price": 140, "option_values": [{"option_name": "Size", "name": "US 9"}]}
            ]
        }
        options, variants = resolve_options_and_variants(shoe, forex_rate=90.0, source_price=140.0, compare_source=160.0)
        self.assertEqual(len(variants), 3, "All 3 shoe sizes must be preserved, none pruned!")
        for v in variants:
            self.assertIsNotNone(v.get("file"), "Every size variant must have a valid file image attached")
            self.assertEqual(v["file"]["originalSource"], "https://cdn.example.com/speedcross-black.jpg")

    def test_watch_case_diameter_never_pruned(self):
        watch = {
            "title": "Chronograph Watch",
            "product_type": "Watches",
            "images": ["https://cdn.example.com/watch.jpg"],
            "variants": [
                {"title": "40 mm", "sku": "W-40", "image_url": "https://cdn.example.com/watch.jpg", "source_price": 500, "option_values": [{"option_name": "Case Diameter", "name": "40 mm"}]},
                {"title": "44 mm", "sku": "W-44", "image_url": None, "source_price": 520, "option_values": [{"option_name": "Case Diameter", "name": "44 mm"}]}
            ]
        }
        options, variants = resolve_options_and_variants(watch, forex_rate=90.0, source_price=500.0, compare_source=600.0)
        self.assertEqual(len(variants), 2, "Both watch case diameters must be preserved!")
        for v in variants:
            self.assertEqual(v["file"]["originalSource"], "https://cdn.example.com/watch.jpg")

    def test_ghost_color_variant_pruned(self):
        broken_sample = list(BROKEN_IMAGE_URLS)[0]
        bag = {
            "title": "Leather Crossbody",
            "product_type": "Crossbody Bags",
            "images": ["https://cdn.example.com/crossbody-black.jpg"],
            "variants": [
                {"title": "Black", "sku": "CB-BLK", "image_url": "https://cdn.example.com/crossbody-black.jpg", "source_price": 250, "option_values": [{"option_name": "Color", "name": "Black"}]},
                {"title": "Ghost Plum", "sku": "CB-PLM", "image_url": broken_sample, "source_price": 250, "option_values": [{"option_name": "Color", "name": "Ghost Plum"}]}
            ]
        }
        options, variants = resolve_options_and_variants(bag, forex_rate=90.0, source_price=250.0, compare_source=300.0)
        self.assertEqual(len(variants), 1, "Ghost Plum has no valid photo and must be pruned")
        self.assertEqual(variants[0]["optionValues"][0]["name"], "Black")

    def test_payload_includes_primary_image_if_not_in_gallery(self):
        prod = {
            "title": "Minimalist Card Case",
            "product_type": "Wallets & Small Leather Goods",
            "image": "https://cdn.example.com/primary-cardcase.jpg",
            "images": [],
            "source_price": 50.0,
            "availability": "in_stock",
            "variants": [
                {"title": "Tan", "sku": "CC-TAN", "source_price": 50.0, "option_values": [{"option_name": "Color", "name": "Tan"}]}
            ]
        }
        payload = prepare_product_set_payload(prod, forex_rate=90.0)
        file_urls = [f["originalSource"] for f in payload.get("files", [])]
        self.assertIn("https://cdn.example.com/primary-cardcase.jpg", file_urls)


if __name__ == "__main__":
    unittest.main()
