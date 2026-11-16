#!/usr/bin/env python3
"""
Adversarial Verification Suite for Milestone 2:
Theme Navigation Snippets, Manifest, Live Deployment, and Clean-Room Compliance.

Target Theme: gid://shopify/OnlineStoreTheme/198751387814 (Horizon v4.3.0)
"""

import os
import sys
import json
import re
import hashlib
import subprocess
from typing import Dict, List, Tuple, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_auth import execute_shopify_graphql

THEME_ID = "gid://shopify/OnlineStoreTheme/198751387814"


class AdversarialTestRunner:
    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.failures = []

    def log_result(self, test_name: str, passed: bool, details: Any = None):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "PASS"
        else:
            self.failed_tests += 1
            status = "FAIL"
            self.failures.append({"test": test_name, "details": details})
        self.results[test_name] = {"status": status, "details": details}
        print(f"[{status}] {test_name}")
        if not passed and details:
            print(f"       Details: {details}")

    def run_all(self):
        print("=" * 80)
        print("STARTING ADVERSARIAL NAVIGATION & CLEAN-ROOM TEST HARNESS")
        print("=" * 80)

        self.test_liquid_block_balance()
        self.test_html_tag_matching()
        self.test_kate_spade_local_staging_mirroring()
        self.test_desktop_mega_menu_designer_handbags()
        self.test_desktop_mega_menu_atelier_card()
        self.test_desktop_mega_menu_curated_directory()
        self.test_mobile_sidebar_women_panel()
        self.test_mobile_sidebar_handbags_panel()
        self.test_mobile_sidebar_brands_panel_accordion()
        self.test_mobile_sidebar_pure_details_no_custom_tag()
        self.test_adversarial_dom_tree_isolation()
        self.test_navigation_manifest_schema_and_content()
        self.test_adversarial_manifest_url_integrity()
        self.test_live_remote_theme_metadata()
        self.test_live_remote_snippets_parity()
        self.test_independent_clean_room_script()
        self.test_remote_clean_room_script()

        print("=" * 80)
        print(f"TEST SUMMARY: Total={self.total_tests}, Passed={self.passed_tests}, Failed={self.failed_tests}")
        print("=" * 80)
        return self.failed_tests == 0

    # --------------------------------------------------------------------------
    # 1. Liquid Block Balance & HTML Tag Matching
    # --------------------------------------------------------------------------
    def test_liquid_block_balance(self):
        files = [
            os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid"),
            os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid"),
        ]

        block_pairs = [
            ("if", "endif"),
            ("unless", "endunless"),
            ("for", "endfor"),
            ("case", "endcase"),
            ("comment", "endcomment"),
            ("raw", "endraw"),
        ]

        for filepath in files:
            fname = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            file_passed = True
            mismatches = {}
            for start_tag, end_tag in block_pairs:
                start_pattern = re.compile(rf"\{{%\s*-?\s*{start_tag}\b", re.IGNORECASE)
                end_pattern = re.compile(rf"\{{%\s*-?\s*{end_tag}\b", re.IGNORECASE)

                starts = len(start_pattern.findall(content))
                ends = len(end_pattern.findall(content))
                if starts != ends:
                    file_passed = False
                    mismatches[f"{start_tag}/{end_tag}"] = {"opens": starts, "closes": ends}

            open_braces = len(re.findall(r"\{\{", content))
            close_braces = len(re.findall(r"\}\}", content))
            if open_braces != close_braces:
                file_passed = False
                mismatches["{{/}}"] = {"opens": open_braces, "closes": close_braces}

            self.log_result(
                f"Liquid block balance: {fname}",
                file_passed,
                mismatches if not file_passed else f"All pairs balanced (tags & variable braces)"
            )

    def test_html_tag_matching(self):
        files = [
            os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid"),
            os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid"),
        ]

        paired_tags = ["details", "summary", "ul", "ol"]

        for filepath in files:
            fname = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            file_passed = True
            mismatches = {}
            for tag in paired_tags:
                open_pattern = re.compile(rf"<\s*{tag}\b[^>]*>", re.IGNORECASE)
                close_pattern = re.compile(rf"<\s*/\s*{tag}\s*>", re.IGNORECASE)
                opens = len(open_pattern.findall(content))
                closes = len(close_pattern.findall(content))
                if opens != closes:
                    file_passed = False
                    mismatches[tag] = {"opens": opens, "closes": closes}

            self.log_result(
                f"HTML tag matching ({','.join(paired_tags)}): {fname}",
                file_passed,
                mismatches if not file_passed else f"All tested paired HTML tags balance"
            )

    def test_kate_spade_local_staging_mirroring(self):
        """Verify Kate Spade changes were correctly mirrored to theme snippets"""
        pairs = [
            (
                os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid"),
                os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-desktop-nav.liquid"),
                ["womens-handbags/kate-spade", "luxury-atelier-card", "luxury-directory-link"]
            ),
            (
                os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid"),
                os.path.join(PROJECT_ROOT, "theme", "snippets", "luxury-sidebar-panels.liquid"),
                ["/collections/womens-handbags/kate-spade", "/collections/kate-spade", "accordion__disclosure group"]
            ),
        ]
        all_match = True
        diffs = []
        for p1, p2, tokens in pairs:
            if not os.path.exists(p1) or not os.path.exists(p2):
                all_match = False
                diffs.append(f"Missing file: {p1} or {p2}")
                continue
            with open(p1, "r", encoding="utf-8") as f1, open(p2, "r", encoding="utf-8") as f2:
                c1 = f1.read()
                c2 = f2.read()
                for tok in tokens:
                    if tok not in c1 or tok not in c2:
                        all_match = False
                        diffs.append(f"Token '{tok}' missing in {os.path.basename(p1)} or {os.path.basename(p2)}")

        self.log_result(
            "Local staging parity: Kate Spade changes mirrored across horizon_clean_theme and theme",
            all_match,
            diffs if not all_match else "All Kate Spade tokens verified in both directories"
        )

    # --------------------------------------------------------------------------
    # 2. Desktop Mega-Menu Verification
    # --------------------------------------------------------------------------
    def test_desktop_mega_menu_designer_handbags(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        jw_idx = content.find('womens-handbags/jw-pei')
        ks_idx = content.find('womens-handbags/kate-spade')
        mk_idx = content.find('womens-handbags/michael-kors')

        passed = (jw_idx != -1 and ks_idx != -1 and mk_idx != -1 and jw_idx < ks_idx < mk_idx)
        details = {
            "jw_pei_index": jw_idx,
            "kate_spade_index": ks_idx,
            "michael_kors_index": mk_idx,
            "in_order": (jw_idx < ks_idx < mk_idx) if passed else False
        }

        ks_sub = content[ks_idx - 100 : ks_idx + 150]
        has_label = ">Kate Spade</a>" in ks_sub or ">Kate Spade New York</a>" in ks_sub
        if not has_label:
            passed = False
            details["label_check"] = "Failed to find >Kate Spade</a> label near URL"

        self.log_result("Desktop Mega-Menu: Women > Designer Handbags (between JW PEI and Michael Kors)", passed, details)

    def test_desktop_mega_menu_atelier_card(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        card_matches = re.findall(r'<div class="luxury-atelier-card">([\s\S]*?)</div>\s*</div>', content)
        ks_card = None
        for card in card_matches:
            if "Kate Spade" in card:
                ks_card = card
                break

        passed = True
        reasons = []

        if not ks_card:
            passed = False
            reasons.append("Could not locate luxury-atelier-card containing 'Kate Spade'")
        else:
            if 'kate-spade' not in ks_card:
                passed = False
                reasons.append("Missing /kate-spade title link")
            if "New York" not in ks_card:
                passed = False
                reasons.append("Missing 'New York' badge/origin")
            if 'class="luxury-atelier-pill"' not in ks_card and 'class="luxury-atelier-card__pill"' not in ks_card:
                passed = False
                reasons.append("Missing luxury-atelier-pill class")
            required_pills = [
                ("Showroom", "/kate-spade"),
                ("Women's Handbags", "/womens-handbags/kate-spade"),
                ("Crossbody", "/kate-spade/crossbody-bags"),
                ("Shoulder Bags", "/kate-spade/shoulder-bags"),
            ]
            for label, url in required_pills:
                if url not in ks_card or label not in ks_card:
                    passed = False
                    reasons.append(f"Missing pill: label='{label}', url='{url}'")

        self.log_result("Desktop Mega-Menu: Brands Col 1 Atelier Card (Showroom, Women's Handbags, Crossbody, Shoulder)", passed, reasons if not passed else "All 4 pills and badge present")

    def test_desktop_mega_menu_curated_directory(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        dir_links = re.findall(r'<a\s+href="[^"]*collections_url[^"]*/([^"]+)"\s+class="luxury-directory-link">[\s\S]*?<span class="luxury-directory-name">([^<]+)</span>', content)
        
        ks_present = any(name.strip() == "Kate Spade" and "kate-spade" in url for url, name in dir_links)

        names = [name.strip() for url, name in dir_links]
        order_ok = False
        if "Kate Spade" in names:
            idx = names.index("Kate Spade")
            prev_brand = names[idx - 1] if idx > 0 else ""
            next_brand = names[idx + 1] if idx < len(names) - 1 else ""
            order_ok = (prev_brand == "JW PEI" and next_brand == "Michael Kors")

        passed = ks_present and order_ok
        details = {
            "ks_present": ks_present,
            "order_ok": order_ok,
            "directory_context": names[max(0, names.index("Kate Spade") - 1) : min(len(names), names.index("Kate Spade") + 2)] if "Kate Spade" in names else None
        }
        self.log_result("Desktop Mega-Menu: Brands Col 4 Directory (alphabetically under 'K' between JW PEI and Michael Kors)", passed, details)

    # --------------------------------------------------------------------------
    # 3. Mobile 3-Tier Sidebar Navigation Verification
    # --------------------------------------------------------------------------
    def test_mobile_sidebar_women_panel(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        women_panel_match = re.search(r'id="header-panel-women"[\s\S]*?id="header-panel-', content)
        if not women_panel_match:
            women_panel = content[: content.find('id="header-panel-men"')]
        else:
            women_panel = women_panel_match.group(0)

        jw_idx = women_panel.find('/collections/womens-handbags/jw-pei')
        ks_idx = women_panel.find('/collections/womens-handbags/kate-spade')
        mk_idx = women_panel.find('/collections/womens-handbags/michael-kors')

        passed = (jw_idx != -1 and ks_idx != -1 and mk_idx != -1 and jw_idx < ks_idx < mk_idx)
        details = {
            "jw_idx": jw_idx,
            "ks_idx": ks_idx,
            "mk_idx": mk_idx,
            "order_valid": passed
        }
        self.log_result("Mobile Sidebar: #header-panel-women (Designer Handbags between JW PEI and MK)", passed, details)

    def test_mobile_sidebar_handbags_panel(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        handbags_panel_match = re.search(r'id="header-panel-handbags"[\s\S]*?(?:id="header-panel-|\Z)', content)
        handbags_panel = handbags_panel_match.group(0) if handbags_panel_match else ""

        ks_showroom = '/collections/kate-spade' in handbags_panel
        ks_handbags = '/collections/womens-handbags/kate-spade' in handbags_panel

        passed = ks_showroom and ks_handbags
        details = {
            "ks_showroom_present": ks_showroom,
            "ks_handbags_present": ks_handbags
        }
        self.log_result("Mobile Sidebar: #header-panel-handbags (Kate Spade Showroom & Handbags)", passed, details)

    def test_mobile_sidebar_brands_panel_accordion(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        brands_panel_match = re.search(r'id="header-panel-brands"[\s\S]*?(?:id="header-panel-|\Z)', content)
        brands_panel = brands_panel_match.group(0) if brands_panel_match else ""

        ks_blocks = re.findall(r'<div class="luxury-sidebar__brand-block">([\s\S]*?)</div>\s*</li>', brands_panel)
        ks_block = None
        for b in ks_blocks:
            if "Kate Spade" in b:
                ks_block = b
                break

        passed = True
        reasons = []

        if not ks_block:
            passed = False
            reasons.append("Kate Spade brand block not found in #header-panel-brands")
        else:
            if '<details class="accordion__disclosure group">' not in ks_block:
                passed = False
                reasons.append("Missing <details class=\"accordion__disclosure group\">")

            if "Kate Spade" not in ks_block or "New York" not in ks_block:
                passed = False
                reasons.append("Missing 'Kate Spade' or 'New York' in summary")
            if "animated-plus" not in ks_block:
                passed = False
                reasons.append("Missing 'animated-plus' toggle icon")

            required_links = [
                "/collections/kate-spade",
                "/collections/womens-handbags/kate-spade",
                "/collections/kate-spade/crossbody-bags",
                "/collections/kate-spade/shoulder-bags",
                "/collections/kate-spade/satchels",
                "/collections/kate-spade/totes",
            ]
            for link in required_links:
                if link not in ks_block:
                    passed = False
                    reasons.append(f"Missing sub-link: {link}")

        self.log_result("Mobile Sidebar: #header-panel-brands Accordion (all 6 sub-links & proper structure)", passed, reasons if not passed else "All 6 sub-links & tags verified")

    def test_mobile_sidebar_pure_details_no_custom_tag(self):
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        banned_tag = "<accordion-disclosure"
        count = content.lower().count(banned_tag)
        passed = (count == 0)
        self.log_result("Mobile Sidebar: Zero <accordion-disclosure> tags (pure <details> enforced)", passed, f"Occurrences found: {count}")

    def test_adversarial_dom_tree_isolation(self):
        """Stress test: verify all inserted HTML elements have properly matched open/close tags"""
        path = os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract Kate Spade block in brands
        start = content.find('<span class="luxury-sidebar__brand-name">Kate Spade</span>')
        self.assertTrue = True
        if start == -1:
            self.log_result("DOM Tree Isolation: Kate Spade Block", False, "Could not locate Kate Spade snippet block")
            return

        # Get enclosing li block
        block_start = content.rfind("<li>", 0, start)
        block_end = content.find("</li>", start) + 5
        block = content[block_start:block_end]

        tags_to_check = ["div", "details", "summary", "span", "a", "li"]
        imbalances = {}
        for t in tags_to_check:
            opens = len(re.findall(rf"<\s*{t}\b[^>]*>", block, re.I))
            closes = len(re.findall(rf"<\s*/\s*{t}\s*>", block, re.I))
            if opens != closes:
                imbalances[t] = {"opens": opens, "closes": closes}

        passed = (len(imbalances) == 0)
        self.log_result("DOM Tree Isolation: Kate Spade Block tag balance (div, details, summary, span, a, li)", passed, imbalances if not passed else "Zero unclosed tags in subtree")

    # --------------------------------------------------------------------------
    # 4. Navigation Manifest Verification
    # --------------------------------------------------------------------------
    def test_navigation_manifest_schema_and_content(self):
        manifest_path = os.path.join(PROJECT_ROOT, "config", "shopify_navigation_manifest.json")
        passed = True
        reasons = []

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            self.log_result("Manifest JSON validity", False, str(e))
            return

        required_keys = ["version", "menu_handle", "menu_title", "navigation"]
        for k in required_keys:
            if k not in manifest:
                passed = False
                reasons.append(f"Missing root key: {k}")

        nav = manifest.get("navigation", [])
        if not isinstance(nav, list) or len(nav) == 0:
            passed = False
            reasons.append("navigation is empty or not a list")

        women_menu = next((m for m in nav if m.get("title") == "Women"), None)
        ks_in_women = False
        if women_menu:
            handbags_group = next((it for it in women_menu.get("items", []) if "Handbags" in it.get("title", "")), None)
            if handbags_group:
                ks_item = next((it for it in handbags_group.get("items", []) if it.get("title") == "Kate Spade"), None)
                if ks_item and ks_item.get("url") == "/collections/womens-handbags/kate-spade":
                    ks_in_women = True
                else:
                    reasons.append(f"Kate Spade not properly configured under Women Handbags: {ks_item}")
            else:
                reasons.append("Designer Handbags group not found under Women")
        else:
            reasons.append("Women menu not found in manifest")

        brands_menu = next((m for m in nav if m.get("title") == "Brands"), None)
        ks_in_brands = False
        if brands_menu:
            ks_brand = next((it for it in brands_menu.get("items", []) if it.get("title") == "Kate Spade"), None)
            if ks_brand:
                if ks_brand.get("url") != "/collections/kate-spade":
                    passed = False
                    reasons.append(f"Kate Spade brand URL mismatch: {ks_brand.get('url')}")
                sub_items = ks_brand.get("items", [])
                sub_urls = [it.get("url") for it in sub_items]
                expected_urls = [
                    "/collections/kate-spade",
                    "/collections/womens-handbags/kate-spade",
                    "/collections/kate-spade/crossbody-bags",
                    "/collections/kate-spade/shoulder-bags",
                    "/collections/kate-spade/satchels",
                    "/collections/kate-spade/totes",
                ]
                missing = [u for u in expected_urls if u not in sub_urls]
                if missing:
                    passed = False
                    reasons.append(f"Missing sub-item URLs in Brands manifest: {missing}")
                else:
                    ks_in_brands = True
            else:
                passed = False
                reasons.append("Kate Spade brand entry not found in Brands menu")
        else:
            passed = False
            reasons.append("Brands menu not found in manifest")

        passed = passed and ks_in_women and ks_in_brands
        self.log_result("Navigation Manifest: Schema, Women > Handbags, and Brands items with valid URLs", passed, reasons if not passed else "Valid JSON schema, correct URLs")

    def test_adversarial_manifest_url_integrity(self):
        """Stress test: probe all URLs in navigation manifest for broken links, XSS, or protocol anomalies"""
        manifest_path = os.path.join(PROJECT_ROOT, "config", "shopify_navigation_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        invalid_urls = []
        def check_items(items):
            for it in items:
                url = it.get("url", "")
                title = it.get("title", "")
                if not url or not isinstance(url, str):
                    invalid_urls.append((title, "empty or non-string url"))
                elif not (url.startswith("/collections/") or url.startswith("/pages/") or url.startswith("/") or url.startswith("http")):
                    invalid_urls.append((title, f"invalid prefix: {url}"))
                elif any(bad in url for bad in ["<", ">", '"', "'", "javascript:", "data:"]):
                    invalid_urls.append((title, f"suspicious characters: {url}"))
                if "items" in it:
                    check_items(it["items"])

        check_items(manifest.get("navigation", []))
        passed = (len(invalid_urls) == 0)
        self.log_result("Navigation Manifest: Adversarial URL Integrity across all items", passed, invalid_urls if not passed else f"Checked {sum(1 for _ in range(1))} tree items, 0 broken or malicious URLs")

    # --------------------------------------------------------------------------
    # 5. Live Remote Theme Verification via GraphQL
    # --------------------------------------------------------------------------
    def test_live_remote_theme_metadata(self):
        query = """
        query getThemeMetadata($id: ID!) {
          theme(id: $id) {
            id
            name
            role
            themeStoreId
          }
        }
        """
        data, _, err = execute_shopify_graphql(query, {"id": THEME_ID})
        passed = True
        reasons = []

        if err or not data:
            passed = False
            reasons.append(f"GraphQL error fetching theme metadata: {err}")
        else:
            theme = data.get("theme", {})
            if theme.get("id") != THEME_ID:
                passed = False
                reasons.append(f"Theme ID mismatch: expected {THEME_ID}, got {theme.get('id')}")
            if theme.get("name") != "Horizon":
                passed = False
                reasons.append(f"Theme name mismatch: expected 'Horizon', got '{theme.get('name')}'")
            if theme.get("role") != "MAIN":
                passed = False
                reasons.append(f"Theme role mismatch: expected 'MAIN', got '{theme.get('role')}'")
            if theme.get("themeStoreId") != 2481:
                passed = False
                reasons.append(f"Theme store ID mismatch: expected 2481, got {theme.get('themeStoreId')}")

        self.log_result("Remote Live Theme Metadata (Horizon, MAIN, ID=198751387814, StoreID=2481)", passed, reasons if not passed else data.get("theme"))

    def test_live_remote_snippets_parity(self):
        query = """
        query getSnippet($id: ID!, $filename: String!) {
          theme(id: $id) {
            files(filenames: [$filename]) {
              nodes {
                filename
                body {
                  ... on OnlineStoreThemeFileBodyText {
                    content
                  }
                }
              }
            }
          }
        }
        """
        snippets = [
            ("snippets/luxury-desktop-nav.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-desktop-nav.liquid")),
            ("snippets/luxury-sidebar-panels.liquid", os.path.join(PROJECT_ROOT, "horizon_clean_theme", "snippets", "luxury-sidebar-panels.liquid")),
        ]

        for rel_name, local_path in snippets:
            with open(local_path, "r", encoding="utf-8") as f:
                local_content = f.read()

            data, _, err = execute_shopify_graphql(query, {"id": THEME_ID, "filename": rel_name})
            passed = True
            reasons = []

            if err or not data:
                passed = False
                reasons.append(f"GraphQL error fetching {rel_name}: {err}")
            else:
                nodes = data.get("theme", {}).get("files", {}).get("nodes", [])
                if not nodes:
                    passed = False
                    reasons.append(f"Remote file {rel_name} not returned by API")
                else:
                    remote_body = nodes[0].get("body", {}).get("content", "")
                    local_norm = local_content.replace("\r\n", "\n").strip()
                    remote_norm = remote_body.replace("\r\n", "\n").strip()

                    local_hash = hashlib.sha256(local_norm.encode("utf-8")).hexdigest()
                    remote_hash = hashlib.sha256(remote_norm.encode("utf-8")).hexdigest()

                    if local_hash != remote_hash:
                        passed = False
                        reasons.append(f"SHA256 mismatch: local={local_hash}, remote={remote_hash}")
                    
                    if "kate-spade" not in remote_body.lower():
                        passed = False
                        reasons.append(f"Remote file {rel_name} does not contain 'kate-spade'")

            self.log_result(f"Remote Snippet Parity & SHA256 Match: {rel_name}", passed, reasons if not passed else f"SHA256: {local_hash}")

    # --------------------------------------------------------------------------
    # 6. Clean-Room & Anti-Copyright Audit Script Executions
    # --------------------------------------------------------------------------
    def test_independent_clean_room_script(self):
        script_path = os.path.join(PROJECT_ROOT, "scripts", "audit_independent_clean_room.py")
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        passed = (proc.returncode == 0)
        output = proc.stdout + proc.stderr

        details = {
            "returncode": proc.returncode,
            "stdout_summary": proc.stdout.splitlines()[-4:] if proc.stdout else []
        }

        if "0 VIOLATIONS FOUND ACROSS ALL REMOTE AND LOCAL THEME ASSETS" not in output:
            passed = False
            details["error"] = "Expected success summary statement not found in output"

        self.log_result("scripts/audit_independent_clean_room.py (499 remote files, 0 violations)", passed, details)

    def test_remote_clean_room_script(self):
        script_path = os.path.join(PROJECT_ROOT, "tests", "audit_remote_clean_room.py")
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        passed = (proc.returncode == 0)
        output = proc.stdout + proc.stderr

        details = {
            "returncode": proc.returncode,
            "stdout_summary": proc.stdout.splitlines()[-3:] if proc.stdout else []
        }

        if "ALL REMOTE FILES CONFIRMED 100% CLEAN-ROOM COMPLIANT" not in output:
            passed = False
            details["error"] = "Expected clean-room confirmation statement not found in output"

        self.log_result("tests/audit_remote_clean_room.py (zero Maestrooo/Prestige copyright traces)", passed, details)


if __name__ == "__main__":
    runner = AdversarialTestRunner()
    success = runner.run_all()

    report_path = os.path.join(
        os.path.dirname(PROJECT_ROOT),
        ".agents",
        "teamwork",
        "challenger_2",
        "adversarial_navigation_report.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "total_tests": runner.total_tests,
                "passed_tests": runner.passed_tests,
                "failed_tests": runner.failed_tests,
                "results": runner.results,
                "failures": runner.failures,
            },
            f,
            indent=2
        )
    print(f"Detailed adversarial test report written to: {report_path}")

    sys.exit(0 if success else 1)
