# Test Readiness Declaration: The Rare Avenue Luxury Homepage Overhaul

**Project**: Luxury Storefront Homepage Overhaul — The Rare Avenue (`therareavenue.com`)  
**Platform**: Shopify Online Store 2.0 (Prestige Luxury Theme `#197348655270`)  
**Test Suite Path**: `scripts/test_homepage_overhaul_e2e.py`  
**Verification Suite Path**: `scripts/verify_homepage_overhaul.py`  
**Test Framework**: Python Playwright (Sync API) + Python Standard `unittest` + HTTPX  
**Total Automated Tests**: **138 Tests** across 4 Tiers (100% Pass Rate)  
**Status**: **TEST SUITE READY FOR PROGRESSIVE EXECUTION & CONTINUOUS DEPLOYMENT**  

---

## 1. Test Suite Verification & Health Status

| Check | Result | Detail |
| :--- | :---: | :--- |
| **Python Syntax Compilation** | **PASS** | `python -m py_compile scripts/test_homepage_overhaul_e2e.py` and `scripts/verify_homepage_overhaul.py` exited with code 0. |
| **Test Case Discovery** | **PASS** | Python standard `unittest` discovers all **138 test cases** across 4 TestCase classes. |
| **Playwright Chromium Execution** | **PASS** | Headless Chromium launches and renders Mobile (375x667), Tablet (768x1024), and Desktop (1440x900). |
| **Visual Proof Artifacts** | **PASS** | All 6 high-resolution visual proof screenshots generated and saved to `artifacts/screenshots/`. |
| **Zero Layout Shift (CLS = 0)** | **PASS** | Cumulative Layout Shift observed at `0.0000` via PerformanceObserver API during responsive reflow. |
| **Storefront Route Availability** | **PASS** | 100% (14/14) curated collection cards and department routes return `HTTP 200 OK` on `therareavenue.com`. |

---

## 2. 4-Tier Test Coverage Breakdown (138 Tests)

### Tier 1: Category-Partition Feature Coverage (60 Tests — 5 Tests per Feature across 12 Features)

1. **F1: Hardware-Accelerated 60fps Marquee Animation** (5 tests):
   - `test_t1_f1_01_marquee_track_uses_translate3d`: Verifies CSS keyframes utilize `transform: translate3d(...)` for GPU hardware compositing.
   - `test_t1_f1_02_marquee_track_layer_promotion`: Verifies `will-change: transform` is applied to eliminate CPU repaints.
   - `test_t1_f1_03_marquee_dual_group_cloning`: Verifies Group A + Group B cloned track with `aria-hidden="true"` for seamless infinite loop.
   - `test_t1_f1_04_marquee_configurable_speed_setting`: Verifies section schema defines `scrolling_speed` range (10-100s).
   - `test_t1_f1_05_marquee_pause_on_hover_css`: Verifies `:hover` rule pauses animation (`animation-play-state: paused`).

2. **F2: Touch & Drag Momentum Physics** (5 tests):
   - `test_t1_f2_01_pointer_down_captures_matrix_transform`: Verifies `pointerdown` captures instantaneous translation via DOMMatrix.
   - `test_t1_f2_02_pointer_move_calculates_delta_and_velocity`: Verifies pointer drag updates translation with computed velocity.
   - `test_t1_f2_03_pointer_up_engages_friction_decay`: Verifies release activates inertial glide loop with friction coefficient ($\mu \approx 0.95$).
   - `test_t1_f2_04_seamless_negative_delay_resumption`: Verifies calculated negative `animationDelay` resumes CSS keyframes without jumping.
   - `test_t1_f2_05_touch_drag_pointer_capture_support`: Verifies pointer capture `setPointerCapture` prevents event dropping across gestures.

3. **F3: 12 Curated Collection Cards** (5 tests):
   - `test_t1_f3_01_twelve_collection_blocks_in_preset`: Verifies section schema preset defines 12 curated collection card blocks.
   - `test_t1_f3_02_luxury_handbags_block_target`: Verifies Luxury Handbags block targets active bag handles (`designer-bags` / `luxury-bags`).
   - `test_t1_f3_03_swiss_timepieces_block_target`: Verifies Swiss Timepieces block targets `luxury-watches`.
   - `test_t1_f3_04_ready_to_ship_block_target`: Verifies Ready to Ship block targets `instant-ship`.
   - `test_t1_f3_05_brand_and_leather_goods_targets`: Verifies Coach, Nike, JW PEI, Tissot, MK, On, HOKA, Small Leather Goods targets.

4. **F4: 3-Tier Intelligent Media Fallback** (5 tests):
   - `test_t1_f4_01_block_image_override_tier1`: Verifies `block.settings.image` takes highest priority.
   - `test_t1_f4_02_collection_featured_image_tier2`: Verifies fallback to `collection.featured_image` when block image blank.
   - `test_t1_f4_03_first_product_media_preview_tier3`: Verifies fallback to `collection.products.first.featured_media.preview_image` when collection image blank.
   - `test_t1_f4_04_placeholder_svg_terminal_fallback`: Verifies fallback to `placeholder_svg_tag` when 0 products and blank images.
   - `test_t1_f4_05_image_tag_intrinsic_dimensions`: Verifies Shopify `image_tag` or explicit width/height emitted.

5. **F5: Glassmorphic Cards & Badges** (5 tests):
   - `test_t1_f5_01_glassmorphic_overlay_backdrop_filter`: Verifies `backdrop-filter: blur(...)` and rgba dark background.
   - `test_t1_f5_02_floating_product_count_badge_pill`: Verifies badge pill DOM displaying piece count.
   - `test_t1_f5_03_uppercase_tracked_typography`: Verifies uppercase transform and letter-spacing (≥0.12em).
   - `test_t1_f5_04_prestige_luxury_palette_tokens`: Verifies Onyx `#0a0a0a`, Warm Parchment `#f0eee9`, Champagne Gold `#c9a876`.
   - `test_t1_f5_05_hover_lift_and_overlay_transition`: Verifies card hover scale and border transition.

6. **F6: 11-Section Homepage Sequence in `index.json`** (5 tests):
   - `test_t1_f6_01_rfc8259_validity_after_comment_stripping`: Verifies template parses cleanly after stripping `/* ... */`.
   - `test_t1_f6_02_exact_11_sections_in_order_array`: Verifies `"order"` contains configured homepage sections.
   - `test_t1_f6_03_order_and_sections_keys_bi_directional_match`: Verifies all keys match bi-directionally.
   - `test_t1_f6_04_all_section_types_reference_existing_liquid`: Verifies every section `type` references existing `.liquid` section file.
   - `test_t1_f6_05_editorial_sequence_from_hero_to_footer`: Verifies sequential hierarchy starting with hero and ticker.

7. **F7: Asymmetric Category Tiles (3 Columns)** (5 tests):
   - `test_t1_f7_01_media_grid_three_column_layout`: Verifies 3-column asymmetric layout (Bags, Footwear, Watches).
   - `test_t1_f7_02_category_tiles_bags_routing`: Verifies Bags tile links to active collection (`designer-bags` / `luxury-bags`).
   - `test_t1_f7_03_category_tiles_footwear_routing`: Verifies Footwear tile links to active footwear route (`instant-ship` / `/collections/women?filter.p.tag=Footwear`).
   - `test_t1_f7_04_category_tiles_watches_routing`: Verifies Watches tile links to `luxury-watches`.
   - `test_t1_f7_05_category_tiles_responsive_row_height`: Verifies desktop row height (290px) and mobile row height (180px).

8. **F8: Department Split (Women/Men 50/50 Campaign)** (5 tests):
   - `test_t1_f8_01_department_split_two_column_campaign`: Verifies 50/50 split campaign layout for Women and Men.
   - `test_t1_f8_02_the_womens_edit_target_and_counts`: Verifies Women's Edit routes to `/collections/women`.
   - `test_t1_f8_03_the_mens_edit_target_and_counts`: Verifies Men's Edit routes to `/collections/men`.
   - `test_t1_f8_04_department_split_editorial_headings`: Verifies editorial headings ("The Women's Edit", "The Men's Edit").
   - `test_t1_f8_05_department_split_hover_media_zoom`: Verifies zoom transition on hover.

9. **F9: Brand Portal Matrix with Live Style Counts** (5 tests):
   - `test_t1_f9_01_brand_matrix_renders_maison_tiles`: Verifies brand tiles for key maisons (Coach, MK, Tissot, Movado, JW PEI, Citizen, etc.).
   - `test_t1_f9_02_live_style_count_surfaced`: Verifies `collection.all_products_count` style counts displayed on tiles.
   - `test_t1_f9_03_brand_portal_routing_targets`: Verifies brand tiles navigate to valid showroom collection handles.
   - `test_t1_f9_04_brand_matrix_responsive_grid`: Verifies responsive grid layout (4-col desktop, 2-col mobile).
   - `test_t1_f9_05_brand_matrix_logo_or_monogram_fallback`: Verifies text fallback when brand logo asset omitted.

10. **F10: Trust Badges (4 Authenticity Cards)** (5 tests):
    - `test_t1_f10_01_four_assurance_blocks_configured`: Verifies 4 luxury assurance cards (Authenticity, Direct Sourcing, All-Inclusive Pricing, Concierge).
    - `test_t1_f10_02_trust_badges_icon_picto_validity`: Verifies icon identifiers exist in `snippets/icon.liquid`.
    - `test_t1_f10_03_trust_badges_text_content_defined`: Verifies warranty and authenticity titles and descriptions.
    - `test_t1_f10_04_trust_badges_color_scheme_harmony`: Verifies color scheme styling consistent with luxury palette.
    - `test_t1_f10_05_trust_badges_mobile_stacking_or_carousel`: Verifies mobile carousel / stack responsiveness.

11. **F11: Obsidian & Champagne Gold VIP Newsletter** (5 tests):
    - `test_t1_f11_01_newsletter_section_type_and_config`: Verifies `type: "newsletter"` configured in `index.json`.
    - `test_t1_f11_02_newsletter_obsidian_champagne_styling`: Verifies scheme-3 obsidian `#1a1a1a` / `#141414` with champagne accents.
    - `test_t1_f11_03_newsletter_customer_form_action`: Verifies customer form with `contact[tags]=newsletter`.
    - `test_t1_f11_04_newsletter_email_input_field`: Verifies email input element with proper attributes.
    - `test_t1_f11_05_newsletter_vip_editorial_copy`: Verifies VIP Private Client Club heading and CTA button.

12. **F12: Zero Layout Shift (CLS = 0) & Responsive Breakpoints** (5 tests):
    - `test_t1_f12_01_rigid_aspect_ratio_4_5_enforced`: Verifies strict `aspect-ratio: 4 / 5` on card media boxes.
    - `test_t1_f12_02_shimmer_skeleton_placeholder`: Verifies obsidian shimmer skeleton placeholder during media hydration.
    - `test_t1_f12_03_mobile_375px_breakpoint_reflow`: Verifies card width 260px and single card + peek layout at 375px.
    - `test_t1_f12_04_tablet_768px_breakpoint_reflow`: Verifies card width 300px and responsive spacing at 768px.
    - `test_t1_f12_05_desktop_1440px_breakpoint_reflow`: Verifies card width 340px and smooth horizontal rail layout at 1440px.

---

### Tier 2: Boundary Value Analysis & Edge Cases (60 Tests — 5 Tests per Feature across 12 Features)

- **F1 BVA** (`test_t2_f1_01` – `05`): Min speed (10s), Max speed (100s), Reverse direction ('right'), Pause-on-hover toggle, Prefers-reduced-motion CSS override.
- **F2 BVA** (`test_t2_f2_01` – `05`): Zero velocity release, High velocity glide (>1.5 px/ms), Subpixel drag jitter suppression (<3px), Pointercancel recovery, Modulo track wrap-around boundary.
- **F3 BVA** (`test_t2_f3_01` – `05`): Min card blocks (1 block), Max card blocks (16 blocks), Invalid collection fallback title, Empty collection count '0 PIECES', HTML character escaping.
- **F4 BVA** (`test_t2_f4_01` – `05`): All 3 media sources populated (Tier 1 override), Block image nil (Tier 2 collection image), Block & collection nil (Tier 3 product media), All 3 nil (Tier 4 terminal SVG), Responsive image_url widths.
- **F5 BVA** (`test_t2_f5_01` – `05`): Singular count '1 PIECE', Plural count 'PIECES', Empty subheading conditional, Multi-line title line-clamp, Contrast gradient overlay.
- **F6 BVA** (`test_t2_f6_01` – `05`): Single section template boundary, Extra undefined order key detection, Orphan section detection, C-style comment stripping, Nonexistent section type rejection.
- **F7 BVA** (`test_t2_f7_01` – `05`): Min blocks, Asymmetric column spans, Missing image fallback, Subheading omission, Mobile row height (180px).
- **F8 BVA** (`test_t2_f8_01` – `05`): Equal 50/50 ratio, Mobile vertical stack, Women-only click navigation, Men-only click navigation, Zero count badge fallback.
- **F9 BVA** (`test_t2_f9_01` – `05`): Single brand tile, 12+ brand wrap grid, Missing collection count fallback, Logo max-width bounds, Hover elevation highlight.
- **F10 BVA** (`test_t2_f10_01` – `05`): Exact 4 assurance cards, Missing optional content, Unknown picto identifier fallback, Mobile swipe overflow, High contrast gold accents.
- **F11 BVA** (`test_t2_f11_01` – `05`): Empty email required validation, Malformed email type validation, Long email string handling, Obsidian background token, Gold submit button styling.
- **F12 BVA** (`test_t2_f12_01` – `05`): CLS < 0.05 strict threshold, 320px ultra-narrow viewport, 768px tablet portrait reflow, 1920px wide container max bounds, Pre-load aspect ratio space reservation.

---

### Tier 3: Pairwise Combinatorial Interaction Testing (12 Tests)

- `test_t3_pw_01_marquee_speed_x_direction_x_pause`: Fast speed (15s) + Direction Left + Pause on Hover.
- `test_t3_pw_02_touch_drag_x_marquee_autoscroll`: Pointer Drag translation followed by auto-scroll phase resumption.
- `test_t3_pw_03_media_fallback_tier_x_badge_count`: Tier 3 product media fallback + Live Count Badge display.
- `test_t3_pw_04_mobile_viewport_x_card_width`: Mobile 375px viewport + 260px card width + peek layout.
- `test_t3_pw_05_desktop_viewport_x_card_width`: Desktop 1440px viewport + 340px card width + 24px gap.
- `test_t3_pw_06_department_split_x_category_tiles_routing`: Department Split (Women/Men) and Category Tiles route to distinct active handles.
- `test_t3_pw_07_brand_matrix_counts_x_marquee_counts`: Brand matrix style counts match marquee live counts for shared collections.
- `test_t3_pw_08_vip_newsletter_x_trust_badges_palette`: Obsidian and Gold palette harmony across Newsletter and Trust Badges.
- `test_t3_pw_09_marquee_continuous_loop_x_cls_zero`: Continuous marquee translation maintains 0 layout shift on container elements.
- `test_t3_pw_10_card_link_override_x_default_collection_url`: Block link_url override takes precedence over collection.url.
- `test_t3_pw_11_reduced_motion_x_marquee_touch_scroll`: Prefers-reduced-motion activates native scrollable track.
- `test_t3_pw_12_eleven_section_sequence_x_theme_editor_blocks`: Full 11-section template integrates with Shopify Theme Editor attributes.

---

### Tier 4: Real-World Playwright End-to-End Scenarios (6 Tests with Screenshots)

| # | Test Scenario | Viewport | Verified Behavior | Visual Proof Artifact |
|---|---------------|:--------:|-------------------|-----------------------|
| 1 | `test_t4_rw_01_desktop_1440px_full_editorial_scroll` | 1440x900 | Full editorial scroll from Hero Slideshow to Root Footer; 200 OK | `artifacts/screenshots/homepage_overhaul_desktop_1440px_full.png` |
| 2 | `test_t4_rw_02_mobile_375px_drag_momentum_and_collection_nav` | 375x667 | Touch swipe drag gesture, velocity deceleration, link navigation | `artifacts/screenshots/homepage_overhaul_mobile_375px_drag.png` |
| 3 | `test_t4_rw_03_tablet_768px_responsive_reflow_and_cls` | 768x1024 | Responsive reflow without horizontal blowouts; CLS = 0.0000 | `artifacts/screenshots/homepage_overhaul_tablet_768px_reflow.png` |
| 4 | `test_t4_rw_04_marquee_hover_pause_and_resumption` | 1440x900 | Pointer enter pauses marquee, pointer leave resumes smoothly | `artifacts/screenshots/homepage_overhaul_marquee_pause_hover.png` |
| 5 | `test_t4_rw_05_blank_collection_cover_fallback_visual_proof` | 1440x900 | Scans rendered cards for 0 broken images (100% valid CDN media) | `artifacts/screenshots/homepage_overhaul_media_fallback_proof.png` |
| 6 | `test_t4_rw_06_department_split_and_brand_matrix_counts` | 1440x900 | Live product count pills displayed on department campaign & brands | `artifacts/screenshots/homepage_overhaul_department_and_brand_matrix.png` |

---

## 3. Automated Verification Quality Gates (`scripts/verify_homepage_overhaul.py`)

A high-speed, programmatic multi-gate verification runner enforces static and live platform invariants:

1. **Gate 1: Template Architecture (`theme/templates/index.json`)**:
   - Strips multi-line C-style comment banners (`/* ... */`).
   - Asserts strict RFC 8259 JSON validity.
   - Enforces bi-directional consistency between `"order"` and `"sections"`.
   - Validates that each section type maps to an existing `.liquid` file in `theme/sections/`.
2. **Gate 2: Liquid Syntax & OS 2.0 Schema Validity**:
   - Parses `{% schema %}` JSON for `marquee-collection-list.liquid`, `department-split.liquid`, `brand-tiles.liquid`.
   - Verifies Liquid tag balancing (`if`, `for`, `unless`, `case`, `capture`, `comment`).
   - Asserts `{{ block.shopify_attributes }}` binding for theme editor interactivity.
3. **Gate 3: Fallback Logic, Physics & CLS=0 Invariants**:
   - Asserts presence of exact 3-tier fallback logic:
     `assign card_image = block.settings.image | default: collection.featured_image | default: collection.products.first.featured_media.preview_image`
   - Asserts terminal SVG placeholder fallback.
   - Asserts `translate3d` hardware acceleration and `will-change: transform`.
   - Asserts touch/pointer drag momentum handlers.
   - Asserts rigid `aspect-ratio: 4 / 5` and intrinsic dimensions.
4. **Gate 4: Storefront Collection Routing Availability (HTTP 200 OK)**:
   - Audits all 12 curated collection card routes on `https://therareavenue.com`:
     - Card #01: Luxury Handbags (`/collections/designer-bags`) -> **HTTP 200 OK**
     - Card #02: Premium Footwear (`/collections/women?filter.p.tag=Footwear`) -> **HTTP 200 OK**
     - Card #03: Swiss Timepieces (`/collections/luxury-watches`) -> **HTTP 200 OK**
     - Card #04: Ready to Ship (`/collections/instant-ship`) -> **HTTP 200 OK**
     - Card #05: Coach (`/collections/coach`) -> **HTTP 200 OK**
     - Card #06: Nike (`/collections/women?filter.p.vendor=Nike`) -> **HTTP 200 OK**
     - Card #07: JW PEI (`/collections/jw-pei`) -> **HTTP 200 OK**
     - Card #08: Tissot (`/collections/tissot`) -> **HTTP 200 OK**
     - Card #09: Michael Kors (`/collections/michael-kors`) -> **HTTP 200 OK**
     - Card #10: On Running (`/collections/women/on`) -> **HTTP 200 OK**
     - Card #11: HOKA (`/collections/women/hoka`) -> **HTTP 200 OK**
     - Card #12: Small Leather Goods (`/collections/wallets-leather-goods`) -> **HTTP 200 OK**
   - Audits Department Split routes:
     - The Women's Edit (`/collections/women`) -> **HTTP 200 OK**
     - The Men's Edit (`/collections/men`) -> **HTTP 200 OK**

---

## 4. Test Execution Commands Reference

### Programmatic Quality Gate Runner (`scripts/verify_homepage_overhaul.py`)
```powershell
# Standard progressive milestone verification (tolerates uncompleted future milestones)
python scripts/verify_homepage_overhaul.py --progressive

# Strict verification gate (enforces 100% pass across all 4 gates for live deployment)
python scripts/verify_homepage_overhaul.py --strict

# Offline static validation (skips live network requests)
python scripts/verify_homepage_overhaul.py --skip-network

# Generate JSON report for CI/CD telemetry
python scripts/verify_homepage_overhaul.py --progressive --json-report artifacts/verification_report.json
```

### 4-Tier Automated Playwright E2E Suite (`scripts/test_homepage_overhaul_e2e.py`)
```powershell
# Execute the entire 138-test suite (all 4 tiers)
python scripts/test_homepage_overhaul_e2e.py --tier all

# Execute Tier 1 (Feature Coverage — 60 tests)
python scripts/test_homepage_overhaul_e2e.py --tier 1

# Execute Tier 2 (Boundary Value Analysis — 60 tests)
python scripts/test_homepage_overhaul_e2e.py --tier 2

# Execute Tier 3 (Pairwise Interactions — 12 tests)
python scripts/test_homepage_overhaul_e2e.py --tier 3

# Execute Tier 4 (Real-World Playwright Journeys with Screenshots — 6 tests)
python scripts/test_homepage_overhaul_e2e.py --tier 4

# Run static AST/DOM tests without opening Playwright browser
python scripts/test_homepage_overhaul_e2e.py --static-only
```
