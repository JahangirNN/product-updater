"""
Comprehensive Test Suite: Supplier Delisting Detection, Resilient Strike Counter,
Shopify Synchronization, and Auto-Restock Restoration.

Verifies:
  1. Delist strike counter: 1st soft-404 strike sets strikes=1, preserves Shopify state (has_changed=False);
     2nd consecutive soft-404 strike confirms delisting (has_changed=True, supplier_delisted=True).
  2. Confirmed HTTP 404 immediately confirms delisting (strikes=2, supplier_delisted=True, has_changed=True).
  3. Auto-restock restoration: valid product data resets strikes to 0, clears supplier_delisted,
     removes 'supplier-delisted' tag, and queues restoration.
  4. Shopify taxonomy & payload generation:
     - generate_taxonomy_tags strips shipping tags ('Ready to Ship', 'instant-ship', 'manual-instant-ship-active')
       and adds 'supplier-delisted' when delisted; removes 'supplier-delisted' when restocked.
     - resolve_options_and_variants forces inventoryPolicy='DENY' and inventoryItem={'tracked': True} when delisted.
     - prepare_product_set_payload sets status='DRAFT' when delisted, status='ACTIVE' when restocked.
  5. Multi-store delta solvers (JD Sports, Coach, Nordstrom, Michael Kors, Foot Locker, JW Pei)
     correctly identify HTTP 404 and soft-404 states and return status='not_found' with appropriate metadata.

Architecture: Pure functional tests (ADR 0002, ADR 0005, ADR 0015, ADR 0021).
"""

import copy
import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_taxonomy import (
    generate_taxonomy_tags,
    resolve_options_and_variants,
    prepare_product_set_payload,
    is_product_delisted
)
from sync_catalog import poll_single_product
import stores.jdsports.delta as jdsports_delta
import stores.jdsports.camoufox_solver as jdsports_solver
import stores.coach.delta as coach_delta
import stores.nordstrom.camoufox_solver as nordstrom_solver
import stores.michaelkors.delta as michaelkors_delta
import stores.michaelkors.camoufox_solver as michaelkors_solver
import stores.footlocker.delta as footlocker_delta
import stores.jwpei.delta as jwpei_delta


class MockHttpResponse:
    def __init__(self, status_code: int = 200, text: str = "", json_data: Any = None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data

    def json(self):
        if self._json_data is not None:
            return self._json_data
        if self.text:
            return json.loads(self.text)
        return {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP error {self.status_code}")


class MockHttpClient:
    def __init__(self, responses: Optional[Dict[str, MockHttpResponse]] = None, default_response: Optional[MockHttpResponse] = None):
        self.responses = responses or {}
        self.default_response = default_response or MockHttpResponse(status_code=200, text="")

    def get(self, url: str, **kwargs):
        for key, resp in self.responses.items():
            if key in url:
                return resp
        return self.default_response

    def post(self, url: str, **kwargs):
        for key, resp in self.responses.items():
            if key in url:
                return resp
        return self.default_response


class MockPage:
    def __init__(self, status_code: int = 200, content_html: str = "", page_title: str = "Test Title", eval_return: Any = None, redirect_url: Optional[str] = None):
        self._status_code = status_code
        self._content = content_html
        self._title = page_title
        self._eval_return = eval_return
        self.redirect_url = redirect_url
        self.url = redirect_url or "https://example.com/product/123"

    def goto(self, url: str, **kwargs):
        if self.redirect_url:
            self.url = self.redirect_url
        else:
            self.url = url
        resp = MagicMock()
        resp.status = self._status_code
        resp.url = self.url
        return resp

    def content(self):
        return self._content

    def title(self):
        return self._title

    def evaluate(self, script: str):
        if callable(self._eval_return):
            return self._eval_return(script)
        return self._eval_return

    def wait_for_timeout(self, ms: int):
        pass

    def route(self, pattern: str, handler: Any):
        pass


class TestDelistStrikeCounter(unittest.TestCase):
    """Test strike counter logic, resilient soft-404 thresholding, and HTTP 404 delisting."""

    def setUp(self):
        self.base_product = {
            "id": "prod_nike_dunk_test",
            "source_store": "jdsports",
            "title": "Nike Dunk Low Retro Casual Shoes",
            "handle": "nike-dunk-low-retro",
            "source_url": "https://www.jdsports.com/store/product/nike-dunk-low/123",
            "availability": "in_stock",
            "is_active": True,
            "source_price": 115.0,
            "current_price": 10925.0,
            "delist_strikes": 0,
            "supplier_delisted": False,
            "tags": ["Footwear", "Shoes", "Ready to Ship", "Brand:Nike"],
            "variants": [
                {
                    "sku": "VAR-001",
                    "title": "UK 8.0",
                    "source_price": 115.0,
                    "in_stock": True,
                    "is_available": True
                },
                {
                    "sku": "VAR-002",
                    "title": "UK 9.0",
                    "source_price": 115.0,
                    "in_stock": True,
                    "is_available": True
                }
            ]
        }

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_soft_404_strike_1_preserves_shopify_state(self, mock_save, mock_load):
        """1st soft-404: strike counter increments to 1, has_changed=False, does not alter Shopify."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 0
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "not_found",
            "handle": prod["handle"],
            "availability": "out_of_stock",
            "is_http_404": False,
            "http_status": 200,
            "message": "Product delisted (soft-404 / missing ProductGroup JSON-LD)"
        }

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "not_found")
        self.assertFalse(delta_res["has_changed"], "Strike 1/2 must NOT trigger Shopify sync")
        self.assertEqual(prod["delist_strikes"], 1)
        self.assertFalse(prod["supplier_delisted"])
        self.assertEqual(prod["availability"], "in_stock")
        self.assertTrue(prod["variants"][0]["in_stock"])
        self.assertIsNotNone(prod.get("last_verified_at"))
        self.assertIsNotNone(prod.get("updated_at"))

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_soft_404_strike_2_confirms_delisting(self, mock_save, mock_load):
        """2nd soft-404: strike counter increments to 2, has_changed=True, depletes variants and sets supplier-delisted."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 1
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "not_found",
            "handle": prod["handle"],
            "availability": "out_of_stock",
            "is_http_404": False,
            "http_status": 200,
            "message": "Product delisted (soft-404 / missing ProductGroup JSON-LD)"
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "not_found")
        self.assertTrue(delta_res["has_changed"], "Strike 2 must confirm delisting and trigger sync")
        self.assertEqual(prod["delist_strikes"], 2)
        self.assertTrue(prod["supplier_delisted"])
        self.assertEqual(prod["availability"], "out_of_stock")
        self.assertFalse(prod["is_active"])
        for v in prod["variants"]:
            self.assertFalse(v["in_stock"])
            self.assertFalse(v["is_available"])
        self.assertIn("supplier-delisted", prod["tags"])
        self.assertNotIn("Ready to Ship", prod["tags"])

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_confirmed_http_404_immediate_delisting(self, mock_save, mock_load):
        """HTTP 404 immediately confirms delisting (strikes=2, supplier_delisted=True, has_changed=True)."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 0
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "not_found",
            "handle": prod["handle"],
            "availability": "out_of_stock",
            "is_http_404": True,
            "http_status": 404,
            "message": "Product delisted (HTTP 404)"
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "not_found")
        self.assertTrue(delta_res["has_changed"], "Confirmed HTTP 404 must immediately trigger Shopify sync")
        self.assertGreaterEqual(prod["delist_strikes"], 2)
        self.assertTrue(prod["supplier_delisted"])
        self.assertEqual(prod["availability"], "out_of_stock")
        self.assertFalse(prod["is_active"])
        for v in prod["variants"]:
            self.assertFalse(v["in_stock"])
        self.assertIn("supplier-delisted", prod["tags"])
        self.assertNotIn("Ready to Ship", prod["tags"])

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_auto_restock_restores_product(self, mock_save, mock_load):
        """Restock on supplier: status='success' resets strikes to 0, clears supplier_delisted and delist tag."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 3
        prod["supplier_delisted"] = True
        prod["availability"] = "out_of_stock"
        prod["is_active"] = False
        prod["tags"] = ["Footwear", "Shoes", "supplier-delisted", "Brand:Nike"]
        for v in prod["variants"]:
            v["in_stock"] = False
            v["is_available"] = False
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "success",
            "handle": prod["handle"],
            "availability": "in_stock",
            "current_source_price": 115.0,
            "variants_delta": [
                {"sku": "VAR-001", "available": True, "price_usd": 115.0},
                {"sku": "VAR-002", "available": True, "price_usd": 115.0}
            ]
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "success")
        self.assertTrue(delta_res["has_changed"], "Auto-restock must trigger Shopify restoration sync")
        self.assertEqual(prod["delist_strikes"], 0)
        self.assertFalse(prod["supplier_delisted"])
        self.assertNotIn("supplier-delisted", prod["tags"])

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_transient_error_does_not_clear_or_increment_strikes(self, mock_save, mock_load):
        """Transient rate limits or errors do not clear or increment delist strikes."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 1
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "rate_limited",
            "handle": prod["handle"],
            "availability": "in_stock",
            "message": "HTTP 429 WAF throttled"
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "rate_limited")
        self.assertFalse(delta_res["has_changed"])
        self.assertEqual(prod["delist_strikes"], 1, "Transient rate limit must preserve existing strikes")
        self.assertFalse(prod["supplier_delisted"])

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_repeated_strikes_beyond_threshold_accumulate(self, mock_save, mock_load):
        """Repeated soft-404 failures beyond threshold continue to increment strikes while remaining confirmed delisted."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 3
        prod["supplier_delisted"] = True
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "not_found",
            "handle": prod["handle"],
            "availability": "out_of_stock",
            "is_http_404": False,
            "http_status": 200,
            "message": "Product delisted (soft-404)"
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertEqual(delta_res["status"], "not_found")
        self.assertTrue(delta_res["has_changed"])
        self.assertEqual(prod["delist_strikes"], 4)
        self.assertTrue(prod["supplier_delisted"])

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    def test_variant_price_preservation_on_delist_cascade(self, mock_save, mock_load):
        """When delisted cascade runs, all variant prices remain strictly preserved."""
        prod = copy.deepcopy(self.base_product)
        prod["delist_strikes"] = 1
        mock_load.return_value = prod

        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "not_found",
            "handle": prod["handle"],
            "availability": "out_of_stock",
            "is_http_404": False,
            "http_status": 200,
            "message": "Delisted"
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, r: (copy.deepcopy(p), True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jdsports"},
            dry_run=True,
            store_mod=mock_store_mod,
            forex_rate=95.0
        )

        self.assertTrue(delta_res["has_changed"])
        self.assertEqual(prod["variants"][0]["source_price"], 115.0)
        self.assertEqual(prod["variants"][1]["source_price"], 115.0)
        self.assertFalse(prod["variants"][0]["in_stock"])
        self.assertFalse(prod["variants"][1]["in_stock"])


class TestTaxonomyAndPayloadSync(unittest.TestCase):
    """Test Shopify taxonomy tag generation, variant policy, and ProductSet payload construction."""

    def test_generate_taxonomy_tags_delisted(self):
        """Delisted product strips shipping tags and appends 'supplier-delisted'."""
        prod = {
            "title": "Nike Air Force 1",
            "source_store": "jdsports",
            "product_type": "Shoes",
            "supplier_delisted": True,
            "tags": [
                "Footwear",
                "Shoes",
                "Ready to Ship",
                "instant-ship",
                "manual-instant-ship-active",
                "Brand:Nike"
            ]
        }
        tags = generate_taxonomy_tags(prod, vendor="Nike", product_type="Shoes", gender="Men")
        self.assertIn("supplier-delisted", tags)
        self.assertNotIn("Ready to Ship", tags)
        self.assertNotIn("instant-ship", tags)
        self.assertNotIn("manual-instant-ship-active", tags)

    def test_generate_taxonomy_tags_restocked(self):
        """Active/restocked product removes 'supplier-delisted' tag."""
        prod = {
            "title": "Nike Air Force 1",
            "source_store": "jdsports",
            "product_type": "Shoes",
            "supplier_delisted": False,
            "delist_strikes": 0,
            "tags": [
                "Footwear",
                "Shoes",
                "supplier-delisted",
                "Brand:Nike"
            ]
        }
        tags = generate_taxonomy_tags(prod, vendor="Nike", product_type="Shoes", gender="Men")
        self.assertNotIn("supplier-delisted", tags)

    def test_resolve_options_and_variants_delisted(self):
        """Delisted product forces inventoryPolicy='DENY' and inventoryItem={'tracked': True} across all variants."""
        prod = {
            "title": "Nike Air Force 1",
            "source_store": "jdsports",
            "supplier_delisted": True,
            "variants": [
                {"sku": "VAR-1", "title": "UK 8.0", "in_stock": True, "source_price": 100.0},
                {"sku": "VAR-2", "title": "UK 9.0", "in_stock": False, "source_price": 100.0}
            ]
        }
        options, variants = resolve_options_and_variants(prod, forex_rate=95.0, source_price=100.0, compare_source=None)
        for v in variants:
            self.assertEqual(v["inventoryPolicy"], "DENY")
            self.assertEqual(v["inventoryItem"], {"tracked": True})

    def test_resolve_options_and_variants_single_variant_delisted(self):
        """Delisted single-variant product receives inventoryPolicy='DENY'."""
        prod = {
            "title": "JW PEI Gabbi Bag",
            "source_store": "jwpei",
            "supplier_delisted": True,
            "availability": "out_of_stock",
            "variants": []
        }
        options, variants = resolve_options_and_variants(prod, forex_rate=95.0, source_price=80.0, compare_source=None)
        self.assertEqual(len(variants), 1)
        self.assertEqual(variants[0]["inventoryPolicy"], "DENY")
        self.assertEqual(variants[0]["inventoryItem"], {"tracked": True})

    def test_prepare_product_set_payload_draft_when_delisted(self):
        """ProductSet payload transitions to status='DRAFT' when delisted."""
        prod = {
            "title": "Nike Air Force 1 '07",
            "vendor": "Nike",
            "source_store": "jdsports",
            "supplier_delisted": True,
            "delist_strikes": 2,
            "availability": "out_of_stock",
            "shopify_product_id": "gid://shopify/Product/12345678",
            "image": "https://example.com/nike.jpg",
            "variants": [
                {"sku": "VAR-1", "title": "UK 8.0", "in_stock": False, "source_price": 100.0}
            ]
        }
        payload = prepare_product_set_payload(prod, forex_rate=95.0)
        self.assertEqual(payload["status"], "DRAFT")
        self.assertEqual(payload["id"], "gid://shopify/Product/12345678")
        self.assertIn("supplier-delisted", payload["tags"])
        for v in payload["variants"]:
            self.assertEqual(v["inventoryPolicy"], "DENY")
            self.assertEqual(v["inventoryItem"], {"tracked": True})

    def test_prepare_product_set_payload_active_when_restocked(self):
        """ProductSet payload transitions to status='ACTIVE' when restocked and in stock with media."""
        prod = {
            "title": "Nike Air Force 1 '07",
            "vendor": "Nike",
            "source_store": "jdsports",
            "supplier_delisted": False,
            "delist_strikes": 0,
            "availability": "in_stock",
            "shopify_product_id": "gid://shopify/Product/12345678",
            "image": "https://example.com/nike.jpg",
            "variants": [
                {"sku": "VAR-1", "title": "UK 8.0", "in_stock": True, "source_price": 100.0}
            ]
        }
        payload = prepare_product_set_payload(prod, forex_rate=95.0)
        self.assertEqual(payload["status"], "ACTIVE")
        self.assertNotIn("supplier-delisted", payload["tags"])
        for v in payload["variants"]:
            self.assertEqual(v["inventoryPolicy"], "CONTINUE")
            self.assertEqual(v["inventoryItem"], {"tracked": False})

    def test_legacy_delisted_product_recognized(self):
        """Legacy or alternate delist flags ('status': 'not_found', 'delisted': True) are respected in taxonomy & payload."""
        prod_legacy_1 = {
            "title": "Legacy Item",
            "source_store": "nordstrom",
            "status": "not_found",
            "availability": "out_of_stock",
            "variants": [{"sku": "LEG-1", "title": "Standard", "in_stock": True, "source_price": 50.0}]
        }
        payload_1 = prepare_product_set_payload(prod_legacy_1, forex_rate=95.0)
        self.assertEqual(payload_1["status"], "DRAFT")
        self.assertEqual(payload_1["variants"][0]["inventoryPolicy"], "DENY")
        self.assertIn("supplier-delisted", payload_1["tags"])

        prod_legacy_2 = {
            "title": "Legacy Item 2",
            "source_store": "coach",
            "delisted": True,
            "availability": "out_of_stock",
            "variants": [{"sku": "LEG-2", "title": "Standard", "in_stock": True, "source_price": 50.0}]
        }
        payload_2 = prepare_product_set_payload(prod_legacy_2, forex_rate=95.0)
        self.assertEqual(payload_2["status"], "DRAFT")
        self.assertEqual(payload_2["variants"][0]["inventoryPolicy"], "DENY")
        self.assertIn("supplier-delisted", payload_2["tags"])

    def test_restocked_sold_out_product_remains_draft_without_delisted_tag(self):
        """Restocked product that is genuinely sold out (in_stock=False) becomes DRAFT without 'supplier-delisted' tag."""
        prod = {
            "title": "Restocked But Sold Out Item",
            "source_store": "jdsports",
            "supplier_delisted": False,
            "delist_strikes": 0,
            "availability": "out_of_stock",
            "image": "https://example.com/item.jpg",
            "variants": [
                {"sku": "SO-1", "title": "UK 8.0", "in_stock": False, "source_price": 100.0}
            ]
        }
        payload = prepare_product_set_payload(prod, forex_rate=95.0)
        self.assertEqual(payload["status"], "DRAFT")
        self.assertNotIn("supplier-delisted", payload["tags"])

    def test_mixed_case_shipping_tags_stripped_when_delisted(self):
        """Mixed-case active shipping tags ('READY TO SHIP', 'Instant-Ship') are cleanly stripped when delisted."""
        prod = {
            "title": "Sneaker",
            "source_store": "jdsports",
            "supplier_delisted": True,
            "tags": [
                "READY TO SHIP",
                "Instant-Ship",
                "Manual-Instant-Ship-Active",
                "Footwear"
            ]
        }
        tags = generate_taxonomy_tags(prod, vendor="Nike", product_type="Shoes", gender="Men")
        self.assertIn("supplier-delisted", tags)
        for t in tags:
            self.assertNotIn(t.lower(), {"ready to ship", "instant-ship", "manual-instant-ship-active"})


class TestMultiStoreDelistingSolvers(unittest.TestCase):
    """Test solver classification of HTTP 404 and soft-404 responses across all supported supplier stores."""

    def test_jdsports_delta_http_404_and_soft_404(self):
        """JD Sports delta handles HTTP 404 and soft-404 (missing ProductGroup JSON-LD)."""
        prod = {
            "handle": "nike-dunk-low",
            "source_url": "https://www.jdsports.com/store/product/nike-dunk-low/123",
            "variants": [{"sku": "SKU-1", "in_stock": True}]
        }

        # 1. HTTP 404
        client_404 = MockHttpClient(default_response=MockHttpResponse(status_code=404))
        res_404 = jdsports_delta.check_price_and_stock(prod, client=client_404)
        self.assertEqual(res_404["status"], "not_found")
        self.assertTrue(res_404["is_http_404"])
        self.assertEqual(res_404["http_status"], 404)

        # 2. Soft-404: 200 OK without ProductGroup JSON-LD
        client_soft = MockHttpClient(default_response=MockHttpResponse(status_code=200, text="<html><body>No schema here</body></html>"))
        res_soft = jdsports_delta.check_price_and_stock(prod, client=client_soft)
        self.assertEqual(res_soft["status"], "not_found")
        self.assertFalse(res_soft["is_http_404"])
        self.assertEqual(res_soft["http_status"], 200)

    def test_coach_delta_http_404_and_soft_404(self):
        """Coach delta handles HTTP 404 and soft-404 (missing JSON-LD or 'Page Not Found')."""
        prod = {
            "handle": "coach-tabby-shoulder-bag",
            "source_url": "https://www.coach.com/products/tabby/CP123.html",
            "variants": [{"sku": "CP123", "in_stock": True}]
        }

        # 1. HTTP 404
        client_404 = MockHttpClient(default_response=MockHttpResponse(status_code=404))
        res_404 = coach_delta.check_price_and_stock(prod, client=client_404)
        self.assertEqual(res_404["status"], "not_found")
        self.assertTrue(res_404["is_http_404"])
        self.assertEqual(res_404["http_status"], 404)

        # 2. Soft-404: 200 OK with page not found / no JSON-LD
        client_soft = MockHttpClient(default_response=MockHttpResponse(status_code=200, text="<html><body>We could not find the page you requested</body></html>"))
        res_soft = coach_delta.check_price_and_stock(prod, client=client_soft)
        self.assertEqual(res_soft["status"], "not_found")
        self.assertFalse(res_soft["is_http_404"])
        self.assertEqual(res_soft["http_status"], 200)

    def test_nordstrom_solver_http_404_and_soft_404(self):
        """Nordstrom Camoufox solver handles HTTP 404 and rendered soft-404."""
        # 1. HTTP 404
        page_404 = MockPage(status_code=404, page_title="Page Not Found")
        res_404 = nordstrom_solver.solve_and_extract_pdp(page_404, "https://www.nordstrom.com/s/sample/123", "sample-prod")
        self.assertEqual(res_404["status"], "not_found")
        self.assertTrue(res_404["is_http_404"])
        self.assertEqual(res_404["http_status"], 404)

        # 2. Soft-404: 200 OK with missing product JSON-LD
        page_soft = MockPage(status_code=200, page_title="Women's Shoes | Nordstrom", content_html="<html><body>Category browse</body></html>")
        res_soft = nordstrom_solver.solve_and_extract_pdp(page_soft, "https://www.nordstrom.com/s/sample/123", "sample-prod")
        self.assertEqual(res_soft["status"], "not_found")
        self.assertFalse(res_soft["is_http_404"])
        self.assertEqual(res_soft["http_status"], 200)

    def test_michaelkors_delta_sfcc_404_and_500(self):
        """Michael Kors delta handles SFCC 404 and SFCC 500 retired product variations."""
        prod = {
            "handle": "mk-jet-set-tote",
            "source_url": "https://www.michaelkors.com/jet-set-large-saffiano-leather-tote-bag/30F2GTTT8L.html",
            "source_sku": "30F2GTTT8L",
            "variants": [{"sku": "30F2GTTT8L-001", "in_stock": True}]
        }

        # 1. SFCC 404
        with patch("stores.michaelkors.delta.fetch_sfcc_product_data", return_value=(None, 404, "Not Found")):
            res_404 = michaelkors_delta.check_price_and_stock(prod)
            self.assertEqual(res_404["status"], "not_found")
            self.assertTrue(res_404["is_http_404"])
            self.assertEqual(res_404["http_status"], 404)

        # 2. SFCC 500 (Demandware returns 500 when variation is retired/delisted)
        with patch("stores.michaelkors.delta.fetch_sfcc_product_data", return_value=(None, 500, "Internal Server Error")):
            res_500 = michaelkors_delta.check_price_and_stock(prod)
            self.assertEqual(res_500["status"], "not_found")
            self.assertFalse(res_500["is_http_404"])
            self.assertEqual(res_500["http_status"], 500)

    def test_michaelkors_camoufox_solver_soft_404(self):
        """Michael Kors Camoufox solver handles soft-404 'page not found' text."""
        page_soft = MockPage(
            status_code=200,
            content_html="<html><body><h1>We're sorry, page not found</h1></body></html>",
            page_title="Michael Kors"
        )
        res = michaelkors_solver.solve_and_extract_pdp(page_soft, "https://www.michaelkors.com/sample.html", "sample")
        self.assertEqual(res["status"], "not_found")
        self.assertFalse(res["is_http_404"])
        self.assertEqual(res["http_status"], 200)

    def test_footlocker_delta_missing_server_state(self):
        """Foot Locker delta returns status='not_found' when STATE_FROM_SERVER is missing (no ValueError crash)."""
        prod = {
            "handle": "nike-air-max-plus",
            "source_url": "https://www.footlocker.com/product/nike-air-max-plus/123.html",
            "variants": [{"sku": "FL-123", "in_stock": True}]
        }

        # Missing STATE_FROM_SERVER stub
        client_stub = MockHttpClient(default_response=MockHttpResponse(status_code=200, text="<html><body>Unnavigable redirect stub</body></html>"))
        res = footlocker_delta.check_price_and_stock(prod, client=client_stub)
        self.assertEqual(res["status"], "not_found")
        self.assertFalse(res["is_http_404"])
        self.assertIn("STATE_FROM_SERVER missing", res["message"])

        # Internal API @api/FAILED / code 20016 (Product style inactive) with HTTP 200: MUST be soft-404 (is_http_404=False)
        failed_state_html = (
            '<html><body><script>var x = 1;</script>'
            'STATE_FROM_SERVER:{"api":{"productDetails":{"getDetails":{'
            '"status":"@api/FAILED","statusCode":404,"errors":[{"message":"Product style inactive","code":"20016"}],"data":{}'
            '}}}}</body></html>'
        )
        client_failed = MockHttpClient(default_response=MockHttpResponse(status_code=200, text=failed_state_html))
        res_failed = footlocker_delta.check_price_and_stock(prod, client=client_failed)
        self.assertEqual(res_failed["status"], "not_found")
        self.assertFalse(res_failed["is_http_404"])
        self.assertEqual(res_failed["http_status"], 200)
        self.assertIn("Product inactive / delisted", res_failed["message"])

        # HTTP 404
        client_404 = MockHttpClient(default_response=MockHttpResponse(status_code=404))
        res_404 = footlocker_delta.check_price_and_stock(prod, client=client_404)
        self.assertEqual(res_404["status"], "not_found")
        self.assertTrue(res_404["is_http_404"])
        self.assertEqual(res_404["http_status"], 404)

    def test_jwpei_delta_empty_payload_and_404(self):
        """JW Pei delta handles HTTP 404 and empty product JSON payload."""
        prod = {
            "handle": "jwpei-eva-bag",
            "source_url": "https://www.jwpei.com/products/eva-shoulder-bag.js",
            "variants": [{"sku": "JW-1", "in_stock": True}]
        }

        # 1. HTTP 404
        client_404 = MockHttpClient(default_response=MockHttpResponse(status_code=404))
        res_404 = jwpei_delta.check_price_and_stock(prod, client=client_404)
        self.assertEqual(res_404["status"], "not_found")
        self.assertTrue(res_404["is_http_404"])
        self.assertEqual(res_404["http_status"], 404)

        # 2. Empty JSON payload
        client_empty = MockHttpClient(default_response=MockHttpResponse(status_code=200, json_data={}))
        res_empty = jwpei_delta.check_price_and_stock(prod, client=client_empty)
        self.assertEqual(res_empty["status"], "not_found")
        self.assertFalse(res_empty["is_http_404"])
        self.assertIn("empty product payload", res_empty["message"])

        # 3. Homepage Redirect (discontinued product redirects to https://www.jwpei.com)
        mock_redirect = MockHttpResponse(status_code=200, text="<html><body>Homepage</body></html>")
        mock_redirect.url = "https://www.jwpei.com"
        client_redirect = MockHttpClient(default_response=mock_redirect)
        res_redirect = jwpei_delta.check_price_and_stock(prod, client=client_redirect)
        self.assertEqual(res_redirect["status"], "not_found")
        self.assertFalse(res_redirect["is_http_404"])
        self.assertEqual(res_redirect["http_status"], 200)
        self.assertIn("redirected to homepage", res_redirect["message"])

    def test_jdsports_camoufox_soft_404_redirect(self):
        """JD Sports Camoufox solver immediately classifies redirects to category/error as not_found without delay."""
        page_cat = MockPage(
            status_code=200,
            page_title="Men's Casual Shoes | JD Sports",
            redirect_url="https://www.jdsports.com/c/men/mens-shoes"
        )
        res = jdsports_solver.solve_and_extract_pdp(page_cat, "https://www.jdsports.com/store/product/nike-dunk/123", "nike-dunk")
        self.assertEqual(res["status"], "not_found")
        self.assertFalse(res["is_http_404"])
        self.assertEqual(res["http_status"], 200)
        self.assertIn("soft-404 redirect", res["message"])

    def test_jdsports_camoufox_http_404(self):
        """JD Sports Camoufox solver classifies HTTP 404 response as not_found with is_http_404=True."""
        page_404 = MockPage(status_code=404, page_title="Page Not Found")
        page_404.url = "https://www.jdsports.com/store/product/nike-dunk/123"
        res = jdsports_solver.solve_and_extract_pdp(page_404, "https://www.jdsports.com/store/product/nike-dunk/123", "nike-dunk")
        self.assertEqual(res["status"], "not_found")
        self.assertTrue(res["is_http_404"])
        self.assertEqual(res["http_status"], 404)

    def test_variant_stock_change_tracking_on_delist(self):
        """When products with in-stock variants hit 404, variant_stock_changed and changed_variants are properly tracked."""
        prod_fl = {
            "handle": "nike-dunk",
            "source_url": "https://www.coach.com/product/123",
            "variants": [
                {"sku": "SKU-1", "in_stock": True},
                {"sku": "SKU-2", "in_stock": False}
            ]
        }
        client_404 = MockHttpClient(default_response=MockHttpResponse(status_code=404))
        res = coach_delta.check_price_and_stock(prod_fl, client=client_404)
        self.assertEqual(res["status"], "not_found")
        self.assertTrue(res["variant_stock_changed"])
        self.assertEqual(len(res["changed_variants"]), 1)
        self.assertEqual(res["changed_variants"][0]["sku"], "SKU-1")
        self.assertFalse(res["changed_variants"][0]["new_in_stock"])

    def test_is_product_delisted_robustness(self):
        """is_product_delisted handles None, strings, and missing attributes gracefully."""
        self.assertTrue(is_product_delisted({"supplier_delisted": True}))
        self.assertTrue(is_product_delisted({"delist_strikes": 2}))
        self.assertTrue(is_product_delisted({"delist_strikes": "3"}))
        self.assertTrue(is_product_delisted({"status": "not_found"}))
        self.assertTrue(is_product_delisted({"availability": "delisted"}))
        self.assertFalse(is_product_delisted({"delist_strikes": 1}))
        self.assertFalse(is_product_delisted({"delist_strikes": "invalid"}))
        self.assertFalse(is_product_delisted({}))

    def test_auto_restock_case_insensitive_tag_removal(self):
        """Mixed-case 'Supplier-Delisted' tag is stripped on auto-restock."""
        prod = {
            "title": "Nike Air Force 1",
            "source_store": "jdsports",
            "supplier_delisted": False,
            "availability": "in_stock",
            "tags": ["Footwear", "Supplier-Delisted", "Brand:Nike"],
            "variants": [{"sku": "SKU-1", "in_stock": True, "source_price": 100.0}]
        }
        tags = generate_taxonomy_tags(prod, vendor="Nike", product_type="Shoes", gender="Men")
        self.assertNotIn("supplier-delisted", [t.lower() for t in tags])


if __name__ == "__main__":
    unittest.main()
