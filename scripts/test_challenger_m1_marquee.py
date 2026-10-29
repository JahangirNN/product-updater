"""
Challenger Adversarial Test Suite for Milestone 1:
theme/sections/marquee-collection-list.liquid

Empirical Verification of:
1. CSS Layout Performance & Keyframe Loop Purity (GPU acceleration, translate3d, will-change, no layout triggers)
2. Cumulative Layout Shift Rigidity (CLS = 0, aspect-ratio 4/5, dimensions, shimmer placeholder)
3. 12 Preset Collection Handles & Storefront Route Resolution (Live HTTP verification)
4. Accessibility & Dual-Group ARIA Integrity (Group B aria-hidden, tabindex=-1, focus-within pause, reduced motion)
5. Liquid Syntax, Schema Structure & Edge Case Robustness (Precedence, boundary conditions)
"""

import os
import sys
import re
import json
import urllib.request
import urllib.error
import unittest
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
TARGET_FILE = PROJECT_ROOT / "theme" / "sections" / "marquee-collection-list.liquid"

class ChallengerAdversarialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not TARGET_FILE.exists():
            raise FileNotFoundError(f"Target file missing: {TARGET_FILE}")
        cls.content = TARGET_FILE.read_text(encoding="utf-8")
        
        # Extract schema JSON
        schema_match = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", cls.content, re.DOTALL)
        if not schema_match:
            raise ValueError("Schema block not found in marquee-collection-list.liquid")
        cls.schema = json.loads(schema_match.group(1).strip())
        
        # Extract CSS block
        css_match = re.search(r"<style>(.*?)</style>", cls.content, re.DOTALL)
        cls.css = css_match.group(1) if css_match else ""

        # Extract JS block
        js_match = re.search(r"<script>(.*?)</script>", cls.content, re.DOTALL)
        cls.js = js_match.group(1) if js_match else ""

    # =========================================================================
    # DIMENSION 1: CSS Layout Performance & Keyframe Loop Purity
    # =========================================================================
    def test_gpu_acceleration_translate3d(self):
        """Assert track uses transform: translate3d and will-change: transform."""
        self.assertIn("transform: translate3d(0, 0, 0)", self.css)
        self.assertIn("will-change: transform", self.css)
        self.assertIn("contain: paint layout", self.css)

    def test_keyframes_no_layout_triggering_properties(self):
        """
        Adversarially parse keyframe animations.
        Ensure ONLY transform is animated. No layout triggering properties (left, margin, width, etc.).
        """
        keyframe_blocks = re.findall(r"@keyframes\s+([a-zA-Z0-9_-]+)\s*\{([^}]+(?:\{[^}]+\}[^}]+)*)\}", self.css)
        self.assertGreaterEqual(len(keyframe_blocks), 2, "Expected keyframe animations for marquee")

        forbidden_props = [
            r"\bleft\s*:", r"\bright\s*:", r"\btop\s*:", r"\bbottom\s*:",
            r"\bmargin\s*:", r"\bmargin-left\s*:", r"\bmargin-right\s*:", r"\bmargin-inline\s*:",
            r"\bpadding\s*:", r"\bpadding-left\s*:", r"\bpadding-right\s*:",
            r"\bwidth\s*:", r"\bmin-width\s*:", r"\bmax-width\s*:",
            r"\bheight\s*:", r"\bmin-height\s*:", r"\bmax-height\s*:",
            r"\bflex\s*:", r"\bflex-basis\s*:", r"\bposition\s*:"
        ]

        for kf_name, kf_body in keyframe_blocks:
            if "marquee-scroll" in kf_name:
                for prop in forbidden_props:
                    match = re.search(prop, kf_body, re.IGNORECASE)
                    self.assertIsNone(
                        match,
                        f"CRITICAL: Keyframe '{kf_name}' contains layout-triggering property '{prop}'! Body: {kf_body}"
                    )
                # Verify translate3d is present in the keyframe
                self.assertIn("translate3d", kf_body, f"Keyframe '{kf_name}' missing translate3d!")

    def test_touch_action_and_pointer_behavior(self):
        """Verify touch-action: pan-y to prevent gesture conflicts with vertical page scroll."""
        self.assertIn("touch-action: pan-y", self.css)
        self.assertIn("cursor: grab", self.css)
        self.assertIn("cursor: grabbing", self.css)

    def test_javascript_momentum_uses_transform_only(self):
        """
        Verify custom element JS does NOT touch element.style.left or margin.
        Only element.style.transform = translate3d(...) must be manipulated.
        """
        self.assertNotIn(".style.left", self.js)
        self.assertNotIn(".style.marginLeft", self.js)
        self.assertNotIn(".style.right", self.js)
        self.assertIn("translate3d(${this.currentX}px, 0, 0)", self.js)

    # =========================================================================
    # DIMENSION 2: Cumulative Layout Shift (CLS = 0) Rigidity & Shimmer
    # =========================================================================
    def test_rigid_aspect_ratio_4_5(self):
        """Verify explicit aspect-ratio: 4 / 5 on card media container."""
        self.assertIn("aspect-ratio: 4 / 5;", self.css)

    def test_fixed_card_width_and_flex_shrink_prevention(self):
        """Verify card width is rigid and flex-shrink is 0 to prevent layout collapse."""
        self.assertIn("width: var(--marquee-card-width-desktop);", self.css)
        self.assertIn("flex: 0 0 var(--marquee-card-width-desktop);", self.css)
        self.assertIn("width: var(--marquee-card-width-mobile);", self.css)
        self.assertIn("flex: 0 0 var(--marquee-card-width-mobile);", self.css)

    def test_card_image_absolute_containment(self):
        """Verify image fills absolute container so image loading causes 0 layout shift."""
        img_css_match = re.search(r"\.marquee-card__image\s*\{([^}]+)\}", self.css)
        self.assertIsNotNone(img_css_match, "marquee-card__image CSS block not found")
        img_body = img_css_match.group(1)
        self.assertIn("position: absolute", img_body)
        self.assertIn("inset: 0", img_body)
        self.assertIn("width: 100%", img_body)
        self.assertIn("height: 100%", img_body)
        self.assertIn("object-fit: cover", img_body)

    def test_image_tag_filter_with_sizes_and_lazy_loading(self):
        """Verify Liquid uses image_tag with loading: lazy, explicit sizes, and widths."""
        self.assertIn("image_tag:", self.content)
        self.assertIn("loading: 'lazy'", self.content)
        self.assertIn("sizes: '(max-width: 699px) 240px, 320px'", self.content)
        self.assertIn("widths: '240,320,480,640,800'", self.content)

    def test_obsidian_skeleton_shimmer_placeholder(self):
        """Verify Obsidian (#141414) background and champagne shimmer sweep exist."""
        self.assertIn("background-color: #141414;", self.css)
        self.assertIn(".marquee-card__media::before", self.css)
        self.assertIn("marquee-shimmer", self.css)
        self.assertIn("rgba(201, 168, 118, 0.08)", self.css)

    def test_fallback_placeholder_geometry_integrity(self):
        """Verify fallback placeholder SVG maintains identical class and absolute geometry."""
        self.assertIn("placeholder marquee-card__image", self.content)

    # =========================================================================
    # DIMENSION 3: Preset Collection Handles & Storefront Route Resolution
    # =========================================================================
    def test_preset_contains_exactly_12_blocks(self):
        """Assert preset has exactly 12 collection blocks matching editorial curriculum."""
        presets = self.schema.get("presets", [])
        self.assertEqual(len(presets), 1)
        blocks = presets[0].get("blocks", [])
        self.assertEqual(len(blocks), 12)

    def test_preset_routes_resolve_live_http_200(self):
        """
        Adversarially ping the live storefront (therareavenue.com)
        for every single one of the 12 preset blocks to guarantee 0 broken links (0 404s).
        """
        blocks = self.schema["presets"][0]["blocks"]
        for idx, block in enumerate(blocks):
            settings = block.get("settings", {})
            title = settings.get("title")
            url = settings.get("url")
            col = settings.get("collection")

            if url:
                target_url = f"https://therareavenue.com{url}"
            elif col:
                target_url = f"https://therareavenue.com/collections/{col}"
            else:
                target_url = None

            self.assertIsNotNone(target_url, f"Block {idx} ({title}) has no valid target URL or collection")

            req = urllib.request.Request(target_url, headers={"User-Agent": "Challenger-Bot/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    self.assertEqual(
                        resp.status, 200,
                        f"Block {idx} ({title}) URL {target_url} returned status {resp.status}"
                    )
            except urllib.error.HTTPError as e:
                self.fail(f"Block {idx} ({title}) URL {target_url} returned HTTP {e.code}")
            except Exception as e:
                self.fail(f"Block {idx} ({title}) URL {target_url} connection error: {e}")

    def test_preset_base_collections_contain_active_catalog(self):
        """
        Verify all unique base collection handles configured in presets
        have active product catalogs on the live store via /collections/{handle}/products.json.
        """
        blocks = self.schema["presets"][0]["blocks"]
        unique_handles = {b["settings"]["collection"] for b in blocks if "collection" in b["settings"]}
        
        for handle in unique_handles:
            url = f"https://therareavenue.com/collections/{handle}/products.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Challenger-Bot/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.read().decode("utf-8"))
                    products = data.get("products", [])
                    self.assertGreater(
                        len(products), 0,
                        f"Collection '{handle}' exists but returned 0 products in catalog!"
                    )
            except Exception as e:
                self.fail(f"Failed querying catalog for handle '{handle}': {e}")

    # =========================================================================
    # DIMENSION 4: Accessibility & Dual-Group ARIA Integrity
    # =========================================================================
    def test_group_b_aria_hidden_and_tabindex_isolation(self):
        """
        Verify cloned Group B has strict ARIA and keyboard isolation:
        1. data-group="b" has aria-hidden="true"
        2. individual cards in Group B have aria-hidden="true"
        3. links in Group B have tabindex="-1" and aria-hidden="true"
        """
        # Match Group B container
        group_b_match = re.search(r'<div class="marquee-rail__group" data-group="b"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</marquee-collection-rail>', self.content, re.DOTALL)
        self.assertIsNotNone(group_b_match, "Group B track container not found")
        group_b_content = group_b_match.group(1)

        # Assert container has aria-hidden="true"
        self.assertIn('data-group="b" aria-hidden="true"', self.content)

        # Assert card link in Group B has tabindex="-1" and aria-hidden="true"
        self.assertIn('tabindex="-1"', group_b_content)
        self.assertIn('aria-hidden="true"', group_b_content)

    def test_group_a_keyboard_accessible(self):
        """
        Verify primary Group A is fully keyboard accessible:
        1. Links in Group A do NOT have tabindex="-1"
        2. Group A container does NOT have aria-hidden="true"
        """
        group_a_match = re.search(r'<div class="marquee-rail__group" data-group="a">(.*?)</div>\s*\{%-\s*comment\s*-%\} Group B', self.content, re.DOTALL)
        self.assertIsNotNone(group_a_match, "Group A track container not found")
        group_a_content = group_a_match.group(1)

        self.assertNotIn('tabindex="-1"', group_a_content)
        self.assertNotIn('data-group="a" aria-hidden="true"', self.content)

    def test_keyboard_focus_within_pauses_marquee(self):
        """Verify :focus-within pauses animation for keyboard tabbing users."""
        self.assertIn(":focus-within .marquee-rail__track", self.css)
        self.assertIn("animation-play-state: paused;", self.css)

    def test_prefers_reduced_motion_accessibility(self):
        """Verify WCAG prefers-reduced-motion stops auto-animation and enables manual scroll."""
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
        idx = self.css.find("@media (prefers-reduced-motion: reduce)")
        self.assertNotEqual(idx, -1)
        sub = self.css[idx:idx + 500]
        self.assertIn("animation: none !important", sub)
        self.assertIn("overflow-x: auto", sub)

    # =========================================================================
    # DIMENSION 5: Liquid Syntax, Edge Cases & Custom Overrides
    # =========================================================================
    def test_empty_blocks_safe_guard(self):
        """Verify section conditionally renders only when blocks > 0."""
        self.assertTrue(self.content.startswith("{%- if section.blocks.size > 0 -%}"))
        self.assertIn("{%- endif -%}", self.content)

    def test_fallback_chain_precedence(self):
        """Verify 3-tier fallback chains for image, title, url, count."""
        # Image fallback
        self.assertIn(
            "assign card_image = block.settings.image | default: collection.featured_image | default: collection.products.first.featured_media.preview_image",
            self.content
        )
        # Title fallback
        self.assertIn("assign card_title = block.settings.title | default: collection.title | default: 'Maison Collection'", self.content)
        # URL fallback
        self.assertIn("assign card_url = block.settings.url | default: collection.url | default: '#'", self.content)
        # Count fallback
        self.assertIn("assign card_count = block.settings.custom_count | default: collection.all_products_count", self.content)

    def test_count_badge_singular_plural_and_zero_fallback(self):
        """
        Verify count badge:
        - Displays 'EXPLORE' when count is 0 or empty.
        - Displays '1 PIECE' (singular) when count is 1.
        - Displays 'X PIECES' (plural) when count > 1.
        """
        self.assertIn("{% if card_count == 1 %}PIECE{% else %}PIECES{% endif %}", self.content)
        self.assertIn("EXPLORE", self.content)

    def test_prevent_native_image_drag_ghosting(self):
        """Verify draggable='false' on links and images to prevent interference with pointer drag momentum."""
        self.assertIn('draggable="false"', self.content)

if __name__ == "__main__":
    unittest.main()
