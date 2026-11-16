"""
Dedicated Unit Test Suite: Intelligent Forex Drift Gate in Freshner (ADR 0028).

Verifies the user principle:
Pricing formulas absorb minor daily exchange rate vibrations (< ₹2.00 INR).
When live currency drift exceeds the ₹2.00 threshold (or when supplier USD/stock shifts),
products are dynamically re-anchored to the live exchange rate.

Test Matrix:
1. FX_DRIFT_THRESHOLD_INR constant is defined at 2.0.
2. Drift < ₹2.00 -> no sync triggered (has_changed=False, forex_drift_detected not True).
3. Drift >= ₹2.00 -> sync triggered (has_changed=True, forex_drift_detected=True, price_changed=True, last_synced_fx_rate updated).
4. Boundary precision: exact ₹2.00 drift triggers re-anchoring.
5. Negative forex drift >= ₹2.00 triggers re-anchoring (handles INR appreciation).
6. Supplier USD change -> sync triggered regardless of FX drift.
7. Supplier Stock change -> sync triggered regardless of FX drift.
8. Uninitialized last_synced_fx_rate (None) -> initialized on disk without triggering sync.
9. Structured drift log verification.
"""
import os
import sys
import copy
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sync_catalog import poll_single_product, FX_DRIFT_THRESHOLD_INR


class TestForexDriftGate(unittest.TestCase):
    """Verify intelligent forex drift threshold gating in poll_single_product."""

    def setUp(self):
        self.base_product = {
            "id": "prod_drift_test_001",
            "handle": "luxury-leather-tote",
            "title": "Luxury Leather Tote",
            "source_store": "jwpei",
            "store": "jwpei",
            "source_price": 89.0,
            "current_price": 8499.0,
            "source_compare_at_price": 119.0,
            "availability": "in_stock",
            "is_active": True,
            "last_synced_fx_rate": 90.0,
            "shopify_product_id": "gid://shopify/Product/1234567890",
            "variants": [
                {
                    "sku": "JW-TOTE-BLK",
                    "title": "Black",
                    "source_price": 89.0,
                    "in_stock": True,
                    "is_available": True
                }
            ]
        }

    def _create_mock_store_mod(self, price_changed=False, stock_changed=False, new_price=89.0):
        mock_mod = MagicMock()
        mock_mod.check_price_and_stock.return_value = {
            "status": "success",
            "handle": self.base_product["handle"],
            "current_source_price": new_price,
            "old_source_price": self.base_product["source_price"],
            "availability": "in_stock",
            "old_availability": "in_stock",
            "price_changed": price_changed,
            "stock_changed": stock_changed,
            "variant_stock_changed": False,
            "variant_price_changed": False,
            "changed_variants": [],
            "changed_variant_prices": []
        }

        def mock_apply(prod, delta_res, fx):
            p = copy.deepcopy(prod)
            has_changed = bool(delta_res.get("price_changed") or delta_res.get("stock_changed"))
            if delta_res.get("price_changed"):
                p["source_price"] = delta_res.get("current_source_price")
            return p, has_changed

        mock_mod.apply_delta_to_product.side_effect = mock_apply
        return mock_mod

    def test_fx_drift_threshold_constant(self):
        """Constant must be defined at 2.0 INR."""
        self.assertEqual(FX_DRIFT_THRESHOLD_INR, 2.0)

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_drift_under_threshold_no_sync(self, mock_sync, mock_save, mock_load):
        """Drift < ₹2.00 (91.5 - 90.0 = 1.5): no sync triggered, absorbed by buffer."""
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=91.5,
            dry_run=False
        )

        self.assertFalse(delta_res.get("has_changed"), "Drift < 2.0 must NOT trigger sync")
        self.assertFalse(delta_res.get("forex_drift_detected", False))
        mock_sync.assert_not_called()

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_drift_over_threshold_triggers_sync(self, mock_sync, mock_save, mock_load):
        """Drift >= ₹2.00 (92.5 - 90.0 = 2.5): sync triggered, last_synced_fx_rate updated."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=92.5,
            dry_run=False
        )

        self.assertTrue(delta_res.get("has_changed"), "Drift >= 2.0 MUST trigger sync")
        self.assertTrue(delta_res.get("forex_drift_detected"))
        self.assertTrue(delta_res.get("price_changed"))

        # Verify last_synced_fx_rate was updated in saved product
        mock_save.assert_called()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 92.5)

        # Verify sync_delta_to_shopify was called
        mock_sync.assert_called_once()
        self.assertEqual(mock_sync.call_args[0][2], 92.5)

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_drift_exact_boundary_triggers_sync(self, mock_sync, mock_save, mock_load):
        """Exact ₹2.00 drift (92.0 - 90.0 = 2.0): boundary condition triggers re-anchoring."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=92.0,
            dry_run=False
        )

        self.assertTrue(delta_res.get("has_changed"))
        self.assertTrue(delta_res.get("forex_drift_detected"))
        mock_sync.assert_called_once()

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_negative_drift_triggers_sync(self, mock_sync, mock_save, mock_load):
        """Negative drift <= -₹2.00 (87.5 - 90.0 = -2.5): INR appreciation triggers re-anchoring."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=87.5,
            dry_run=False
        )

        self.assertTrue(delta_res.get("has_changed"))
        self.assertTrue(delta_res.get("forex_drift_detected"))
        mock_sync.assert_called_once()

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_supplier_usd_change_syncs_regardless_of_fx_drift(self, mock_sync, mock_save, mock_load):
        """Supplier USD price shift triggers sync even if FX drift is minimal (0.3)."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=True, stock_changed=False, new_price=99.0)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=90.3,  # Minimal drift of 0.3
            dry_run=False
        )

        self.assertTrue(delta_res.get("has_changed"))
        self.assertTrue(delta_res.get("price_changed"))
        mock_sync.assert_called_once()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 90.3)

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_supplier_stock_change_syncs_regardless_of_fx_drift(self, mock_sync, mock_save, mock_load):
        """Supplier stock status shift triggers sync even if FX drift is 0.0."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=90.0,
            dry_run=False
        )

        self.assertTrue(delta_res.get("has_changed"))
        self.assertTrue(delta_res.get("stock_changed"))
        mock_sync.assert_called_once()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 90.0)

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_uninitialized_last_synced_fx_rate_initializes_without_sync(self, mock_sync, mock_save, mock_load):
        """If last_synced_fx_rate is None and USD/stock unchanged, initialize it on disk without Shopify sync."""
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = None
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=93.5,
            dry_run=False
        )

        self.assertFalse(delta_res.get("has_changed"), "Initial calibration must NOT trigger Shopify sync")
        self.assertFalse(delta_res.get("forex_drift_detected", False))
        mock_sync.assert_not_called()

        # Product must be persisted with initialized forex rate
        mock_save.assert_called()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 93.5)

    @patch("sync_catalog.log_info")
    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_drift_logging_format(self, mock_sync, mock_save, mock_load, mock_log_info):
        """Verify the exact info log message emitted upon FX drift."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=93.0,
            dry_run=False
        )

        expected_substring = f"[DRIFT] Re-anchoring product {prod['id']} ({prod['handle']}) due to FX drift >= ₹{FX_DRIFT_THRESHOLD_INR} (old FX: 90.00, live FX: 93.00)"
        logged_calls = [c[0][0] for c in mock_log_info.call_args_list if c[0]]
        self.assertTrue(
            any(expected_substring in call_msg for call_msg in logged_calls),
            f"Expected log '{expected_substring}' not found in {logged_calls}"
        )

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_corrupted_non_numeric_last_synced_fx_rate_graceful_recovery(self, mock_sync, mock_save, mock_load):
        """Corrupted non-numeric last_synced_fx_rate recovers to live FX rate gracefully without crashing."""
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = "invalid_string_fx"
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=93.5,
            dry_run=False
        )

        mock_save.assert_called()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 93.5)
        # Should not falsely trigger shopify sync
        mock_sync.assert_not_called()

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_preserve_last_synced_fx_rate_across_polls_when_drift_sub_threshold(self, mock_sync, mock_save, mock_load):
        """When drift is under ₹2.00, updated_product preserves the original last_synced_fx_rate on disk."""
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        # Force mock apply to return a new copy without last_synced_fx_rate to test defensive preservation
        def mock_apply_stripped(p_in, delta_res, fx):
            cleaned = copy.deepcopy(p_in)
            cleaned.pop("last_synced_fx_rate", None)
            return cleaned, False

        mock_store_mod.apply_delta_to_product.side_effect = mock_apply_stripped

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=91.0,
            dry_run=False
        )

        mock_save.assert_called()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 90.0, "Sub-threshold drift must NOT overwrite last_synced_fx_rate")

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_variant_price_changed_updates_last_synced_fx_rate(self, mock_sync, mock_save, mock_load):
        """When variant price changes, product is updated and last_synced_fx_rate is refreshed."""
        mock_sync.return_value = True
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = MagicMock()
        mock_store_mod.check_price_and_stock.return_value = {
            "status": "success",
            "handle": prod["handle"],
            "current_source_price": 89.0,
            "old_source_price": 89.0,
            "availability": "in_stock",
            "old_availability": "in_stock",
            "price_changed": False,
            "stock_changed": False,
            "variant_stock_changed": False,
            "variant_price_changed": True,
            "changed_variant_prices": [{"sku": "JW-TOTE-BLK", "old_source_price": 89.0, "new_source_price": 99.0}]
        }
        mock_store_mod.apply_delta_to_product.side_effect = lambda p, d, fx: (copy.deepcopy(p), True)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=90.5,
            dry_run=False
        )

        mock_sync.assert_called_once()
        saved_prod = mock_save.call_args[0][0]
        self.assertEqual(saved_prod["last_synced_fx_rate"], 90.5)

    @patch("sync_catalog.load_product")
    @patch("sync_catalog.save_product")
    @patch("sync_catalog.sync_delta_to_shopify")
    def test_dry_run_prevents_shopify_and_disk_mutation_on_drift(self, mock_sync, mock_save, mock_load):
        """In dry_run mode, FX drift >= ₹2.00 sets delta flags but NEVER touches Shopify or disk."""
        prod = copy.deepcopy(self.base_product)
        prod["last_synced_fx_rate"] = 90.0
        mock_load.return_value = prod
        mock_store_mod = self._create_mock_store_mod(price_changed=False, stock_changed=False)

        delta_res = poll_single_product(
            {"id": prod["id"], "source_store": "jwpei", "handle": prod["handle"]},
            store_mod=mock_store_mod,
            forex_rate=95.0,  # +₹5.0 drift
            dry_run=True
        )

        self.assertTrue(delta_res["has_changed"])
        self.assertTrue(delta_res["forex_drift_detected"])
        mock_sync.assert_not_called()
        mock_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
