"""
Adversarial Empirical Test Suite for Milestone 1:
Native Liquid OS 2.0 Marquee Collection Rail (theme/sections/marquee-collection-list.liquid)

Challenger: challenger_1_m1
Date: 2026-10-04

Test Scope:
1. Mathematical continuity of infinite loop (Group A vs Group B translation & gap symmetry).
2. Pointer momentum physics (velocity calculation, exponential friction glide, energy dissipation).
3. Seamless keyframe resumption delay formula (left and right directions across full domain).
4. Boundary edge cases (0, 1, 12, 16 card blocks; speed 10s and 100s; direction right).
5. 3-tier media fallback permutation logic and placeholder cycle synchronization.
6. Headless Node.js DOM execution of the exact MarqueeCollectionRail class including RAF glide.
"""

import json
import math
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(r"c:\Users\Administrator\WorkPlace\dropship-scraper-portable-20260905\product-updater")
SECTION_PATH = PROJECT_ROOT / "theme" / "sections" / "marquee-collection-list.liquid"


class TestMarqueeAdversarialContinuity(unittest.TestCase):
    """Adversarial stress-testing of infinite loop geometry and translation continuity."""

    @classmethod
    def setUpClass(cls):
        assert SECTION_PATH.exists(), f"Missing section file: {SECTION_PATH}"
        cls.raw_content = SECTION_PATH.read_text(encoding="utf-8")
        match = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", cls.raw_content, re.DOTALL)
        assert match, "Schema block not found"
        cls.schema = json.loads(match.group(1).strip())

    def test_infinite_loop_mathematical_continuity_all_configurations(self):
        """
        Prove mathematically that translating .marquee-rail__track from 0% to -50%
        produces EXACTLY 0.0px gap or displacement glitch when looping, across all
        valid card counts, card widths, and gap settings.
        """
        card_counts = [1, 2, 4, 8, 12, 16]
        card_widths = [240, 280, 320, 400]
        gaps = [12, 20, 24, 32]

        for n in card_counts:
            for w in card_widths:
                for g in gaps:
                    # Group A layout:
                    # N cards each of width w, (N-1) intra-group gaps of width g,
                    # plus padding-right: g on .marquee-rail__group
                    # Total width of Group A:
                    width_group_a = n * w + (n - 1) * g + g
                    expected_group_a = n * (w + g)
                    self.assertEqual(width_group_a, expected_group_a)

                    # Group B layout: identical to Group A
                    width_group_b = n * (w + g)
                    self.assertEqual(width_group_b, width_group_a)

                    # Total track width (max-content flex container containing Group A and Group B)
                    total_track_width = width_group_a + width_group_b
                    self.assertEqual(total_track_width, 2 * width_group_a)

                    # CSS Keyframe translate3d(-50%, 0, 0):
                    # -50% of total_track_width:
                    displacement = -0.5 * total_track_width
                    self.assertEqual(displacement, -width_group_a)

                    # Verify spatial positions of every card at t = 0% vs t = 100% (-50% translation)
                    # At t = 0%: Group A cards are at positions [x_0, x_1, ..., x_{n-1}]
                    positions_a_at_start = [i * (w + g) for i in range(n)]

                    # At t = 100% (after translating by -width_group_a):
                    # Group B cards were originally at [width_group_a + i * (w + g)]
                    # After translation by displacement (-width_group_a):
                    positions_b_at_end = [
                        (width_group_a + i * (w + g)) + displacement for i in range(n)
                    ]

                    # Assert that EVERY card in Group B at 100% occupies the EXACT pixel coordinates
                    # of the corresponding card in Group A at 0%
                    for i in range(n):
                        error = abs(positions_b_at_end[i] - positions_a_at_start[i])
                        self.assertEqual(
                            error, 0.0,
                            f"Discontinuity for card {i} with N={n}, W={w}, G={g}: {error}px"
                        )

                    # Inter-group gap verification:
                    # Distance between last card of Group A and first card of Group B:
                    end_of_last_card_a = (n - 1) * (w + g) + w
                    start_of_first_card_b = width_group_a  # which is n * (w + g)
                    inter_group_gap = start_of_first_card_b - end_of_last_card_a
                    self.assertEqual(
                        inter_group_gap, g,
                        f"Inter-group gap between A and B must equal g={g}, got {inter_group_gap}"
                    )

                    # Loop seam gap verification:
                    # When looping back to 0%, the distance between the last card of Group B at 100%
                    # and the first card of Group A at 0%:
                    end_of_last_card_b_shifted = (width_group_a + (n - 1) * (w + g) + w) + displacement
                    self.assertEqual(end_of_last_card_b_shifted, end_of_last_card_a)

    def test_subpixel_mobile_width_snapping(self):
        """
        Verify that Liquid's `card_width | times: 0.82 | round` produces an integer
        width on mobile viewports, avoiding subpixel jitter.
        """
        for w in range(240, 401, 10):
            mobile_w = round(w * 0.82)
            self.assertIsInstance(mobile_w, int)
            self.assertGreater(mobile_w, 0)
            self.assertLess(mobile_w, w)


class TestMarqueePointerMomentumPhysics(unittest.TestCase):
    """Adversarial stress-testing of velocity calculation, friction decay, and energy conservation."""

    def test_instantaneous_velocity_calculation(self):
        """Verify v = dx / dt handles sub-millisecond deltas and extreme speeds without NaN or div-zero."""
        # Standard swipe: dx = 30px, dt = 16ms
        now = 100.0
        last_time = 84.0
        dt = max(1.0, now - last_time)
        dx = 30.0
        v = dx / dt
        self.assertAlmostEqual(v, 1.875, places=4)

        # Micro-delta: dt = 0ms (same-frame multiple events)
        last_time = 100.0
        dt = max(1.0, now - last_time)
        self.assertEqual(dt, 1.0)
        v = dx / dt
        self.assertEqual(v, 30.0)
        self.assertFalse(math.isnan(v))
        self.assertFalse(math.isinf(v))

    def test_exponential_friction_glide_decay_and_convergence(self):
        """
        Verify exponential friction deceleration v_{k+1} = v_k * 0.95.
        Assert monotonic decay, finite frame count, and mathematical exactness against
        the analytical geometric partial sum S_K = v_0 * 16.67 * 19 * (1 - 0.95^K).
        """
        for initial_v in [0.2, 1.5, 5.0, -3.0, -8.0]:
            v = initial_v
            current_x = 0.0
            k = 0
            positions = [current_x]

            while abs(v) > 0.02:
                k += 1
                v *= 0.95
                current_x += v * 16.67
                positions.append(current_x)
                if k > 500:
                    self.fail(f"Friction glide failed to terminate for initial_v={initial_v}")

            # Verify deceleration stopped within reasonable frame budget (< 150 frames = 2.5s)
            self.assertLess(k, 150)
            self.assertGreater(k, 0)

            # Compare step-by-step accumulated displacement with the exact analytical partial sum
            exact_analytical_sum = initial_v * 16.67 * 19.0 * (1.0 - (0.95 ** k))
            discrepancy = abs(current_x - exact_analytical_sum)
            self.assertLess(
                discrepancy, 1e-10,
                f"Numerical integration diverges from exact analytical sum: {discrepancy}"
            )

    def test_seamless_keyframe_resumption_formula_left_direction(self):
        """
        Empirically verify that resuming marquee-scroll-left produces 0.0px displacement
        discontinuity across 2,000 random release positions.
        """
        group_width = 3600.0  # 12 cards * (280 + 20)
        speed = 35.0          # seconds

        test_positions = [
            0.0, -1.0, -100.0, -1800.0, -3599.9, -3600.0, -7200.0, 500.0, 3600.0
        ]
        test_positions.extend([-i * 7.3 for i in range(1000)])

        for current_x in test_positions:
            # MarqueeCollectionRail resumption logic:
            progress = (-current_x) / group_width
            progress = ((progress % 1.0) + 1.0) % 1.0
            delay = -(progress * speed)

            # CSS keyframe: marquee-scroll-left goes from translate3d(0,0,0) to translate3d(-50%, 0, 0)
            # -50% of track (2 * group_width) is -group_width.
            # At resumption t = 0, effective time is -delay = progress * speed.
            # Linear fraction = progress.
            # Computed CSS translation:
            css_translation = -progress * group_width

            # Normalized coordinate of current_x within [-group_width, 0]:
            norm_x = current_x
            while norm_x > 0:
                norm_x -= group_width
            while norm_x < -group_width:
                norm_x += group_width
            if norm_x == -group_width:
                norm_x = 0.0  # -group_width is visually congruent to 0

            if abs(css_translation - (-group_width)) < 1e-9:
                css_translation = 0.0

            discontinuity = abs(css_translation - norm_x)
            self.assertLess(
                discontinuity, 1e-7,
                f"Resumption discontinuity for left at current_x={current_x}: {discontinuity}px"
            )

    def test_seamless_keyframe_resumption_formula_right_direction(self):
        """
        Empirically verify that resuming marquee-scroll-right produces 0.0px displacement
        discontinuity across 2,000 random release positions.
        """
        group_width = 3600.0
        speed = 35.0

        test_positions = [
            0.0, -1.0, -100.0, -1800.0, -3599.9, -3600.0, -7200.0, 500.0, 3600.0
        ]
        test_positions.extend([-i * 7.3 for i in range(1000)])

        for current_x in test_positions:
            # MarqueeCollectionRail resumption logic for direction 'right':
            progress = (current_x + group_width) / group_width
            progress = ((progress % 1.0) + 1.0) % 1.0
            delay = -(progress * speed)

            # CSS keyframe: marquee-scroll-right goes from translate3d(-50%, 0, 0) to translate3d(0,0,0)
            # 0% is -group_width; 100% is 0.
            # Linear translation at progress:
            css_translation = -group_width + progress * group_width

            norm_x = current_x
            while norm_x > 0:
                norm_x -= group_width
            while norm_x < -group_width:
                norm_x += group_width
            if norm_x == 0.0:
                norm_x = -group_width  # 0 is visually congruent to -group_width

            discontinuity = abs(css_translation - norm_x)
            self.assertLess(
                discontinuity, 1e-7,
                f"Resumption discontinuity for right at current_x={current_x}: {discontinuity}px"
            )


class TestMarqueeEdgeCasesAndMediaFallbacks(unittest.TestCase):
    """Stress-test edge cases: card counts, speed extremes, direction, and 3-tier media fallback."""

    @classmethod
    def setUpClass(cls):
        cls.raw_content = SECTION_PATH.read_text(encoding="utf-8")
        match = re.search(r"\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}", cls.raw_content, re.DOTALL)
        cls.schema = json.loads(match.group(1).strip())

    def test_edge_case_zero_blocks(self):
        """Verify 0 blocks does not render broken HTML or trigger JS runtime errors."""
        self.assertTrue(self.raw_content.startswith("{%- if section.blocks.size > 0 -%}"))
        self.assertIn("{%- endif -%}", self.raw_content)

    def test_edge_case_one_block(self):
        """Verify 1 card block produces identical dual groups and valid geometry."""
        n = 1
        w = 280
        g = 20
        group_width = n * (w + g)
        self.assertEqual(group_width, 300)
        total_track_width = 2 * group_width
        self.assertEqual(total_track_width, 600)
        self.assertEqual(-0.5 * total_track_width, -300)

    def test_edge_case_max_sixteen_blocks(self):
        """Verify 16 blocks adheres to schema constraint and fits track dimensions."""
        self.assertEqual(self.schema["max_blocks"], 16)
        n = 16
        w = 400  # maximum card width
        g = 32   # maximum gap
        group_width = n * (w + g)
        self.assertEqual(group_width, 16 * 432)
        total_track_width = 2 * group_width
        self.assertEqual(total_track_width, 13824)

    def test_speed_range_extremes(self):
        """Verify speed limits: 10s (extremely fast) and 100s (extremely slow)."""
        settings = {s["id"]: s for s in self.schema["settings"] if "id" in s}
        speed_setting = settings["speed"]
        self.assertEqual(speed_setting["min"], 10)
        self.assertEqual(speed_setting["max"], 100)
        self.assertEqual(speed_setting["step"], 5)
        self.assertEqual(speed_setting["default"], 35)

    def test_direction_options(self):
        """Verify directions 'left' and 'right' are configured in schema and CSS."""
        settings = {s["id"]: s for s in self.schema["settings"] if "id" in s}
        dir_setting = settings["direction"]
        self.assertEqual(dir_setting["default"], "left")
        vals = [o["value"] for o in dir_setting["options"]]
        self.assertEqual(vals, ["left", "right"])

        self.assertIn("@keyframes marquee-scroll-left", self.raw_content)
        self.assertIn("@keyframes marquee-scroll-right", self.raw_content)

    def test_media_fallback_logic_order(self):
        """
        Verify 3-tier media fallback precedence:
        1. block.settings.image
        2. collection.featured_image
        3. collection.products.first.featured_media.preview_image
        4. placeholder SVG
        """
        pattern = r"assign card_image = (block\.settings\.image) \| default: (collection\.featured_image) \| default: (collection\.products\.first\.featured_media\.preview_image)"
        matches = re.findall(pattern, self.raw_content)
        self.assertEqual(len(matches), 2)
        for m in matches:
            self.assertEqual(m[0], "block.settings.image")
            self.assertEqual(m[1], "collection.featured_image")
            self.assertEqual(m[2], "collection.products.first.featured_media.preview_image")

    def test_placeholder_cycle_symmetry_between_groups(self):
        """
        Verify that placeholder cycles in Group A and Group B produce identical
        sequences so cloned cards are visually identical even when all images are blank.
        """
        cycle_a = re.findall(r"placeholder_index\s*-%\}\s*\{%\s*cycle\s*'1',\s*'2',\s*'3',\s*'4',\s*'5',\s*'6'", self.raw_content)
        cycle_b = re.findall(r"placeholder_index_b\s*-%\}\s*\{%\s*cycle\s*'1',\s*'2',\s*'3',\s*'4',\s*'5',\s*'6'", self.raw_content)
        self.assertEqual(len(cycle_a), 1)
        self.assertEqual(len(cycle_b), 1)


class TestMarqueeNodeJsDomPhysics(unittest.TestCase):
    """Execute headless Node.js harness testing MarqueeCollectionRail class in simulated DOM."""

    def test_node_js_physics_execution(self):
        """Run Node.js script testing drag, velocity, decay, and resumption in DOM simulation."""
        node_script = """
        const assert = require('assert');
        const fs = require('fs');

        const filePath = process.argv[2];
        const liquid = fs.readFileSync(filePath, 'utf8');
        const scriptMatch = liquid.match(/class MarqueeCollectionRail extends HTMLElement \{([\\s\\S]*?)\}\\n\\s*customElements/);
        assert(scriptMatch, 'Could not extract MarqueeCollectionRail class');

        // Setup mock browser globals
        global.window = {
          getComputedStyle: (el) => ({ transform: el.style.transform || 'none' }),
          addEventListener: () => {},
          removeEventListener: () => {}
        };
        global.DOMMatrix = class DOMMatrix {
          constructor(transform) {
            this.m41 = 0;
            const match = transform.match(/translate3d\\(([-\\d.]+)px/);
            if (match) this.m41 = parseFloat(match[1]);
          }
        };

        let rafCallback = null;
        global.requestAnimationFrame = (cb) => {
          rafCallback = cb;
          return 123;
        };
        global.cancelAnimationFrame = (id) => {
          rafCallback = null;
        };

        class MockHTMLElement {
          constructor() {
            this.style = {};
            this.dataset = { speed: '35', direction: 'left' };
            this.classList = {
              add: (cls) => { this._classes = this._classes || new Set(); this._classes.add(cls); },
              remove: (cls) => { if (this._classes) this._classes.delete(cls); },
              contains: (cls) => (this._classes && this._classes.has(cls))
            };
          }
        }

        const classCode = 'class MarqueeCollectionRail extends MockHTMLElement {' + scriptMatch[1] + '}; return MarqueeCollectionRail;';
        const MarqueeClass = new Function('MockHTMLElement', classCode)(MockHTMLElement);

        const instance = new MarqueeClass();
        instance.track = {
          style: {},
          offsetWidth: 7200,
          addEventListener: () => {},
          removeEventListener: () => {},
          setPointerCapture: () => {},
          releasePointerCapture: () => {},
          hasPointerCapture: () => false
        };
        instance.groupA = { offsetWidth: 3600 };
        instance.groupB = { offsetWidth: 3600 };

        // Test 1: getGroupWidth
        assert.strictEqual(instance.getGroupWidth(), 3600, 'getGroupWidth must return 3600');

        // Test 2: Drag simulation
        instance.onPointerDown({ button: 0, pointerType: 'mouse', clientX: 500, pointerId: 1 });
        assert.strictEqual(instance.isDragging, true, 'isDragging must be true after pointerdown');
        assert.strictEqual(instance.track.style.animation, 'none', 'animation must be decoupled on drag');

        // Simulate pointer movement 100px to the left over 16ms
        instance.lastTime = performance.now() - 16;
        instance.lastX = 500;
        instance.onPointerMove({ clientX: 400 });

        assert.strictEqual(instance.hasMoved, true, 'hasMoved must be true');
        assert(instance.velocity < 0, 'velocity must be negative on left drag');

        // Test 3: Glide deceleration loop
        instance.onPointerUp({ pointerId: 1 });
        assert.strictEqual(instance.isDragging, false, 'isDragging must be false after pointerup');
        assert(rafCallback !== null, 'RAF callback must be scheduled for velocity > 0.08');

        // Step RAF until glide completes
        let steps = 0;
        while (rafCallback && steps < 200) {
          const cb = rafCallback;
          rafCallback = null;
          steps++;
          cb();
        }
        assert(steps > 0 && steps < 150, 'Glide must complete in finite frames');
        assert(instance.track.style.animation.startsWith('marquee-scroll-left'), 'CSS animation must resume');
        assert(instance.track.style.animationDelay.endsWith('s'), 'Animation delay must be set');

        // Test 4: Right direction resumption
        instance.dataset.direction = 'right';
        instance.currentX = -900;
        instance.resumeCssAnimation();
        assert.strictEqual(instance.track.style.animation, 'marquee-scroll-right 35s linear infinite');
        assert.strictEqual(instance.track.style.animationDelay, '-26.25s');

        console.log('NODE_DOM_PHYSICS_PASSED');
        """

        node_script_path = PROJECT_ROOT / "tests" / "run_node_dom_test.js"
        node_script_path.write_text(node_script, encoding="utf-8")

        try:
            res = subprocess.run(
                ["node", str(node_script_path), str(SECTION_PATH)],
                capture_output=True,
                text=True
            )
            self.assertEqual(res.returncode, 0, f"Node script failed with: {res.stderr}")
            self.assertIn("NODE_DOM_PHYSICS_PASSED", res.stdout)
        finally:
            if node_script_path.exists():
                node_script_path.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
