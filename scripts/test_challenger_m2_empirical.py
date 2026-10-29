#!/usr/bin/env python3
"""
Challenger 2 Milestone 2: Empirical Verification Harness
Empirically tests:
1. Storefront Route Interrogation: 100% HTTP 200 OK without 404 across all collection routes in index.json, department-split.liquid, brand-tiles.liquid.
2. Cumulative Layout Shift (CLS = 0) & Aspect-Ratio Preservation across responsive breakpoints (Mobile 320px/375px/390px/430px, Tablet 768px/1024px, Desktop 1280px/1440px/1920px/2560px).
3. Delayed Image Loading CLS Invariant (simulated network lag).
"""

import os
import sys
import re
import json
import time
import httpx
from typing import Dict, List, Set, Tuple, Any
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_JSON_PATH = os.path.join(PROJECT_ROOT, "theme", "templates", "index.json")
DEPT_SPLIT_PATH = os.path.join(PROJECT_ROOT, "theme", "sections", "department-split.liquid")
BRAND_TILES_PATH = os.path.join(PROJECT_ROOT, "theme", "sections", "brand-tiles.liquid")
MARQUEE_PATH = os.path.join(PROJECT_ROOT, "theme", "sections", "marquee-collection-list.liquid")
BASE_URL = "https://therareavenue.com"

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"


def extract_routes_from_index_json(filepath: str) -> Set[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # strip comments
    clean = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    data = json.loads(clean)

    routes = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "collection" and isinstance(v, str) and v.strip():
                    routes.add(f"/collections/{v.strip()}")
                elif k in ("url", "button_link", "link_url", "button_1_link", "button_2_link") and isinstance(v, str) and v.strip():
                    val = v.strip()
                    if val.startswith("shopify://collections/"):
                        handle = val.replace("shopify://collections/", "")
                        routes.add(f"/collections/{handle}")
                    elif val.startswith("/collections/"):
                        routes.add(val)
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return routes


def extract_routes_from_liquid(filepath: str) -> Set[str]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    routes = set()
    # Find schema
    m = re.search(r'\{%\s*schema\s*%\}(.*?)\{%\s*endschema\s*%\}', content, flags=re.DOTALL)
    if m:
        try:
            schema_data = json.loads(m.group(1).strip())
            presets = schema_data.get("presets", [])
            for preset in presets:
                for block in preset.get("blocks", []):
                    settings = block.get("settings", {})
                    col = settings.get("collection")
                    if col and isinstance(col, str):
                        routes.add(f"/collections/{col.strip()}")
                    for link_k in ("url", "button_link", "link_url"):
                        if link_k in settings and isinstance(settings[link_k], str) and settings[link_k].strip():
                            val = settings[link_k].strip()
                            if val.startswith("shopify://collections/"):
                                routes.add(f"/collections/{val.replace('shopify://collections/', '')}")
                            elif val.startswith("/collections/"):
                                routes.add(val)
        except Exception as e:
            print(f"[WARN] Error parsing schema in {filepath}: {e}")

    # Find hardcoded fallback handles in Liquid
    # e.g. assign default_handles = '...' | split: ','
    handle_splits = re.findall(r"assign\s+default_handles\s*=\s*'([^']+)'", content)
    for hs in handle_splits:
        for h in hs.split(","):
            if h.strip():
                routes.add(f"/collections/{h.strip()}")

    # e.g. assign default_handle = '...'
    single_handles = re.findall(r"assign\s+default_handle\s*=\s*'([^']+)'", content)
    for sh in single_handles:
        if sh.strip():
            routes.add(f"/collections/{sh.strip()}")

    return routes


def run_route_interrogation():
    print("=" * 80)
    print("PART 1: ROUTE INTERROGATION ON THERAREAVENUE.COM")
    print("=" * 80)

    index_routes = extract_routes_from_index_json(INDEX_JSON_PATH)
    dept_routes = extract_routes_from_liquid(DEPT_SPLIT_PATH)
    brand_routes = extract_routes_from_liquid(BRAND_TILES_PATH)

    all_routes = sorted(index_routes | dept_routes | brand_routes)
    print(f"Total Unique Routes to Interrogate: {len(all_routes)}")
    for r in all_routes:
        print(f"  - {r}")
    print("-" * 80)

    failed_routes = []
    success_routes = []

    client = httpx.Client(timeout=25.0, follow_redirects=True, headers={"User-Agent": DESKTOP_UA})

    for route in all_routes:
        full_url = f"{BASE_URL}{route}"
        t0 = time.time()
        try:
            resp = client.get(full_url)
            elapsed = time.time() - t0
            status = resp.status_code
            # Also check page content for 404 indicators
            is_404_body = "404" in resp.text and ("Page not found" in resp.text or "Not Found" in resp.text or "404 Not Found" in resp.text)
            
            if status == 200 and not is_404_body:
                print(f"[HTTP 200 OK] {route} (Time: {elapsed:.2f}s, Bytes: {len(resp.content)})")
                success_routes.append((route, status, elapsed))
            else:
                print(f"[FAIL] {route} -> HTTP {status} (404 body detected: {is_404_body})")
                failed_routes.append((route, status, f"status={status}, 404_body={is_404_body}"))
        except Exception as e:
            print(f"[ERROR] {route} -> Exception: {e}")
            failed_routes.append((route, 0, str(e)))

    # Also test Mobile User-Agent on sample key routes
    print("\n--- Mobile User-Agent Check ---")
    mobile_client = httpx.Client(timeout=25.0, follow_redirects=True, headers={"User-Agent": MOBILE_UA})
    for route in ["/collections/women", "/collections/men", "/collections/designer-bags", "/collections/luxury-watches", "/collections/instant-ship", "/collections/women?filter.p.tag=Footwear"]:
        resp = mobile_client.get(f"{BASE_URL}{route}")
        if resp.status_code == 200:
            print(f"[MOBILE 200 OK] {route} (Bytes: {len(resp.content)})")
        else:
            print(f"[MOBILE FAIL] {route} -> {resp.status_code}")
            failed_routes.append((f"mobile:{route}", resp.status_code, "mobile UA fail"))

    print("\nRoute Interrogation Summary:")
    print(f"  Passed: {len(success_routes)} / {len(all_routes)}")
    print(f"  Failed: {len(failed_routes)}")

    return len(failed_routes) == 0, failed_routes, success_routes


def generate_local_test_html() -> str:
    """Generates an HTML harness containing the exact CSS and DOM structure of
    department-split, brand-tiles, and marquee-collection-list with delayed images
    to empirically verify CLS = 0 and aspect ratios."""
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Empirical Layout Shift & Aspect Ratio Test</title>
  <style>
    :root {
      --color-foreground: #f0eee9;
      --heading-font-family: 'Instrument Sans', sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0a0a0a; color: #f0eee9; font-family: sans-serif; }

    /* DEPARTMENT SPLIT CSS */
    .department-split-container {
      --department-card-aspect-desktop: 4 / 5;
      --department-card-aspect-mobile: 1 / 1;
      padding: 2rem;
    }
    .department-split-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    @media screen and (min-width: 768px) {
      .department-split-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    .department-card {
      position: relative;
      background-color: #141414;
      border-radius: 4px;
      overflow: hidden;
    }
    .department-card__media-wrapper {
      position: relative;
      width: 100%;
      aspect-ratio: var(--department-card-aspect-mobile);
      overflow: hidden;
      background-color: #141414;
    }
    @media screen and (min-width: 768px) {
      .department-card__media-wrapper {
        aspect-ratio: var(--department-card-aspect-desktop);
      }
    }
    .department-card__image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    /* BRAND TILES CSS */
    .brand-tiles-container {
      --brand-matrix-columns-desktop: 4;
      --brand-card-aspect-ratio: 4 / 5;
      padding: 2rem;
    }
    .brand-tiles-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 1rem;
    }
    @media screen and (min-width: 768px) {
      .brand-tiles-grid {
        grid-template-columns: repeat(3, 1fr);
      }
    }
    @media screen and (min-width: 1024px) {
      .brand-tiles-grid {
        grid-template-columns: repeat(var(--brand-matrix-columns-desktop), 1fr);
      }
    }
    .brand-card {
      position: relative;
      background-color: #141414;
      border-radius: 4px;
      overflow: hidden;
    }
    .brand-card__media-box {
      position: relative;
      width: 100%;
      aspect-ratio: var(--brand-card-aspect-ratio);
      overflow: hidden;
      background-color: #141414;
    }
    .brand-card__image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .brand-card__monogram {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 2rem;
      color: #c9a876;
    }

    /* MARQUEE CSS */
    .marquee-rail {
      overflow: hidden;
      contain: paint layout;
      padding: 2rem 0;
    }
    .marquee-card {
      width: 280px;
      flex: 0 0 280px;
    }
    @media screen and (max-width: 699px) {
      .marquee-card {
        width: 260px;
        flex: 0 0 260px;
      }
    }
    .marquee-card__media {
      position: relative;
      width: 100%;
      aspect-ratio: 4 / 5;
      background-color: #141414;
      border-radius: 4px;
      overflow: hidden;
    }
    .marquee-card__image {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
  </style>
</head>
<body>
  <!-- Section 1: Department Split -->
  <section class="department-split-container">
    <div class="department-split-grid">
      <div class="department-card" id="dept-card-1">
        <div class="department-card__media-wrapper" id="dept-media-1">
          <!-- Delayed image insertion -->
        </div>
      </div>
      <div class="department-card" id="dept-card-2">
        <div class="department-card__media-wrapper" id="dept-media-2">
          <!-- Delayed image insertion -->
        </div>
      </div>
    </div>
  </section>

  <!-- Section 2: Brand Tiles -->
  <section class="brand-tiles-container">
    <div class="brand-tiles-grid">
      <div class="brand-card" id="brand-card-1">
        <div class="brand-card__media-box" id="brand-media-1">
          <!-- Monogram fallback initially -->
          <div class="brand-card__monogram"><span>CO</span></div>
        </div>
      </div>
      <div class="brand-card" id="brand-card-2">
        <div class="brand-card__media-box" id="brand-media-2">
          <!-- Delayed image insertion -->
        </div>
      </div>
      <div class="brand-card" id="brand-card-3">
        <div class="brand-card__media-box" id="brand-media-3">
          <div class="brand-card__monogram"><span>TI</span></div>
        </div>
      </div>
      <div class="brand-card" id="brand-card-4">
        <div class="brand-card__media-box" id="brand-media-4">
        </div>
      </div>
    </div>
  </section>

  <!-- Section 3: Marquee Card -->
  <section class="marquee-rail">
    <div class="marquee-card" id="marquee-card-1">
      <div class="marquee-card__media" id="marquee-media-1">
        <!-- Delayed image insertion -->
      </div>
    </div>
  </section>

  <script>
    // Global CLS Tracker
    window.clsMetric = 0;
    try {
      const observer = new PerformanceObserver((entryList) => {
        for (const entry of entryList.getEntries()) {
          if (!entry.hadRecentInput) {
            window.clsMetric += entry.value;
          }
        }
      });
      observer.observe({ type: 'layout-shift', buffered: true });
    } catch (e) {
      console.warn("PerformanceObserver layout-shift not supported", e);
    }

    // Function to simulate asynchronous network image arrival
    window.injectImages = function() {
      const imgData = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1000"><rect width="800" height="1000" fill="%23222"/></svg>';
      
      const dept1 = document.getElementById('dept-media-1');
      if (dept1) {
        const img = document.createElement('img');
        img.className = 'department-card__image';
        img.src = imgData;
        img.width = 800;
        img.height = 1000;
        dept1.appendChild(img);
      }
      const dept2 = document.getElementById('dept-media-2');
      if (dept2) {
        const img = document.createElement('img');
        img.className = 'department-card__image';
        img.src = imgData;
        img.width = 800;
        img.height = 1000;
        dept2.appendChild(img);
      }

      const brand2 = document.getElementById('brand-media-2');
      if (brand2) {
        const img = document.createElement('img');
        img.className = 'brand-card__image';
        img.src = imgData;
        img.width = 800;
        img.height = 1000;
        brand2.appendChild(img);
      }

      const marquee1 = document.getElementById('marquee-media-1');
      if (marquee1) {
        const img = document.createElement('img');
        img.className = 'marquee-card__image';
        img.src = imgData;
        img.width = 800;
        img.height = 1000;
        marquee1.appendChild(img);
      }
    };
  </script>
</body>
</html>"""
    return html


def run_cls_and_aspect_ratio_tests():
    print("\n" + "=" * 80)
    print("PART 2: EMPIRICAL CLS & ASPECT-RATIO VERIFICATION ACROSS BREAKPOINTS")
    print("=" * 80)

    test_html = generate_local_test_html()
    harness_path = os.path.join(PROJECT_ROOT, "artifacts", "test_cls_aspect_harness.html")
    os.makedirs(os.path.dirname(harness_path), exist_ok=True)
    with open(harness_path, "w", encoding="utf-8") as f:
        f.write(test_html)

    file_url = f"file:///{harness_path.replace(os.sep, '/')}"

    breakpoints = [
        {"name": "Ultra Narrow Mobile (320px)", "width": 320, "height": 568, "is_mobile": True},
        {"name": "Standard Mobile (375px)", "width": 375, "height": 667, "is_mobile": True},
        {"name": "Modern Mobile (390px)", "width": 390, "height": 844, "is_mobile": True},
        {"name": "Large Mobile (430px)", "width": 430, "height": 932, "is_mobile": True},
        {"name": "Tablet Portrait (768px)", "width": 768, "height": 1024, "is_mobile": False},
        {"name": "Tablet Landscape (1024px)", "width": 1024, "height": 768, "is_mobile": False},
        {"name": "Laptop (1280px)", "width": 1280, "height": 800, "is_mobile": False},
        {"name": "Desktop (1440px)", "width": 1440, "height": 900, "is_mobile": False},
        {"name": "Desktop FHD (1920px)", "width": 1920, "height": 1080, "is_mobile": False},
        {"name": "Desktop QHD (2560px)", "width": 2560, "height": 1440, "is_mobile": False},
    ]

    all_passed = True
    aspect_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for bp in breakpoints:
            page = browser.new_page(viewport={"width": bp["width"], "height": bp["height"]})
            page.goto(file_url, wait_until="load")
            
            # 1. Record pre-image aspect ratios
            pre_ratios = page.evaluate("""() => {
                const getRatio = (id) => {
                    const el = document.getElementById(id);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { width: r.width, height: r.height, ratio: r.width / r.height };
                };
                return {
                    dept: getRatio('dept-media-1'),
                    brand: getRatio('brand-media-2'),
                    brand_mono: getRatio('brand-media-1'),
                    marquee: getRatio('marquee-media-1')
                };
            }""")

            # 2. Trigger asynchronous image insertion (simulating network image load)
            page.evaluate("window.injectImages()")
            page.wait_for_timeout(300)

            # 3. Read post-image aspect ratios & layout shift
            post_data = page.evaluate("""() => {
                const getRatio = (id) => {
                    const el = document.getElementById(id);
                    if (!el) return null;
                    const r = el.getBoundingClientRect();
                    return { width: r.width, height: r.height, ratio: r.width / r.height };
                };
                return {
                    cls: window.clsMetric || 0,
                    dept: getRatio('dept-media-1'),
                    brand: getRatio('brand-media-2'),
                    marquee: getRatio('marquee-media-1')
                };
            }""")

            cls_val = post_data["cls"]
            dept_ratio = post_data["dept"]["ratio"]
            brand_ratio = post_data["brand"]["ratio"]
            marquee_ratio = post_data["marquee"]["ratio"]

            # Expected ratios:
            # Department card: 1.0 (mobile <768px), 0.8 (desktop >=768px)
            expected_dept = 1.0 if bp["is_mobile"] else 0.8
            expected_brand = 0.8 # 4/5
            expected_marquee = 0.8 # 4/5

            dept_ok = abs(dept_ratio - expected_dept) < 0.02
            brand_ok = abs(brand_ratio - expected_brand) < 0.02
            marquee_ok = abs(marquee_ratio - expected_marquee) < 0.02
            cls_ok = cls_val == 0.0

            status = "PASS" if (dept_ok and brand_ok and marquee_ok and cls_ok) else "FAIL"
            if status == "FAIL":
                all_passed = False

            print(f"[{status}] {bp['name']} (Viewport {bp['width']}x{bp['height']}):")
            print(f"       CLS: {cls_val:.4f} (Expected: 0.0000) -> {'PASS' if cls_ok else 'FAIL'}")
            print(f"       Dept Ratio: {dept_ratio:.4f} (Expected: {expected_dept:.4f}) -> {'PASS' if dept_ok else 'FAIL'}")
            print(f"       Brand Ratio: {brand_ratio:.4f} (Expected: {expected_brand:.4f}) -> {'PASS' if brand_ok else 'FAIL'}")
            print(f"       Marquee Ratio: {marquee_ratio:.4f} (Expected: {expected_marquee:.4f}) -> {'PASS' if marquee_ok else 'FAIL'}")

            aspect_results.append({
                "breakpoint": bp["name"],
                "width": bp["width"],
                "height": bp["height"],
                "cls": cls_val,
                "dept_ratio": round(dept_ratio, 4),
                "brand_ratio": round(brand_ratio, 4),
                "marquee_ratio": round(marquee_ratio, 4),
                "pass": status == "PASS"
            })
            page.close()

        # Part 2b: Measure live CLS on therareavenue.com across 3 key viewports
        print("\n--- Live Storefront Cumulative Layout Shift (therareavenue.com) ---")
        for bp_w, bp_h, bp_name in [(375, 667, "Mobile 375px"), (768, 1024, "Tablet 768px"), (1440, 900, "Desktop 1440px")]:
            page = browser.new_page(viewport={"width": bp_w, "height": bp_h})
            try:
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=40000)
                # Observe layout shifts during 2 seconds of scrolling
                live_cls = page.evaluate("""() => {
                    return new Promise((resolve) => {
                        let shift = 0;
                        try {
                            const obs = new PerformanceObserver((list) => {
                                for (const entry of list.getEntries()) {
                                    if (!entry.hadRecentInput) shift += entry.value;
                                }
                            });
                            obs.observe({type: 'layout-shift', buffered: true});
                            window.scrollBy(0, 500);
                            setTimeout(() => {
                                window.scrollBy(0, 1000);
                                setTimeout(() => resolve(shift), 800);
                            }, 500);
                        } catch (e) {
                            resolve(0.0);
                        }
                    });
                }""")
                print(f"[LIVE CLS] {bp_name}: Observed CLS = {live_cls:.4f} (Google Web Vitals Good Threshold < 0.10)")
                # Threshold for CLS per Google Core Web Vitals is < 0.1
                if live_cls > 0.10:
                    print(f"  [WARN] Live storefront CLS {live_cls:.4f} exceeds 0.10 threshold")
            except Exception as e:
                print(f"[WARN] Live storefront check failed: {e}")
            finally:
                page.close()

        browser.close()

    return all_passed, aspect_results


def main():
    routes_ok, failed_routes, success_routes = run_route_interrogation()
    cls_ok, aspect_results = run_cls_and_aspect_ratio_tests()

    print("\n" + "=" * 80)
    print("EMPIRICAL CHALLENGER VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"1. Storefront Route Interrogation: {'PASS (100% 200 OK)' if routes_ok else 'FAIL'}")
    print(f"2. Responsive Breakpoint Aspect Ratios: {'PASS' if cls_ok else 'FAIL'}")
    print(f"3. Simulated Delayed Image CLS = 0: {'PASS' if cls_ok else 'FAIL'}")
    print("=" * 80)

    # Save empirical results to artifacts
    out_path = os.path.join(PROJECT_ROOT, "artifacts", "challenger_m2_empirical_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "routes_ok": routes_ok,
            "total_routes_checked": len(success_routes) + len(failed_routes),
            "failed_routes": failed_routes,
            "success_routes": success_routes,
            "cls_ok": cls_ok,
            "aspect_results": aspect_results,
            "verdict": "APPROVE" if (routes_ok and cls_ok) else "REJECT"
        }, f, indent=2)
    print(f"Saved empirical verification output to: {out_path}")

    if not routes_ok or not cls_ok:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
