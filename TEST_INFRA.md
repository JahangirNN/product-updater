# Test Infrastructure: Hybrid Luxury Navigation Architecture E2E Suite

## 1. Overview & Purpose
This document describes the automated End-to-End (E2E) testing infrastructure for the **Hybrid Luxury Navigation Architecture** on The Rare Avenue (`therareavenue.com` / Shopify theme `#197348655270`).

The suite provides **requirements-driven opaque-box verification** from the customer's perspective across desktop and mobile devices. It exercises the entire navigation loop: desktop mega-menus, mobile sidebar drawer disclosures, collection facet accordions, compound tag filtering, and product detail page transitions.

---

## 2. Test Architecture: 4-Tier Matrix (77 Tests)

The test suite is partitioned into four distinct tiers covering interaction mechanics, boundary limits, combinatorial state transitions, and real-world customer journeys:

| Tier | Name | Target Scope | Test Count | Key Invariants Tested |
| :--- | :--- | :--- | :---: | :--- |
| **Tier 1** | **Feature Coverage** | 8 Primary Navigation Components | **40 Tests** | Mega-menu disclosures, category column headers, shape sub-links, mobile accordions, gender pills, single-gender scoping. |
| **Tier 2** | **Boundary & Corner Cases** | Direct Routing, Exact Counts, 0 Broken Links, 0 Leakage | **22 Tests** | HTTP 200 on all entry points, exact counts (40 W, 25 M, 46 All), zero 404/500 errors, zero cross-gender leakage. |
| **Tier 3** | **Cross-Feature Combinations** | Pairwise Interactivity & State Preservation | **9 Tests** | Facet drawer + tags, price range + gender scoping, availability + scoping, individual chip dismissal, Clear All, browser Back/Forward. |
| **Tier 4** | **Real-World Scenarios** | Complete Customer Journeys with Visual Proof | **6 Tests** | Desktop & Mobile journeys (Women, Men, Brands), automated visual screenshots saved to `artifacts/screenshots/`. |
| **TOTAL** | | | **77 Tests** | **100% Automated Playwright Verification** |

---

## 3. Authoritative Sources & Expected Output Derivation

All expected values, locators, and counts are derived directly from authoritative project specifications:

### Catalog Ground Truth (`storage/db/michaelkors/products/*.json`):
- **Total Sunglasses**: Exactly 46 Michael Kors sunglasses uploaded with active Shopify GIDs and whole-rupee INR pricing ending in `.00` (ADR 0006).
- **Men's Exclusive (6 models)**: *City, Toledo, Bowery, Forio, Camden, Avenue* (MK-9000 series).
- **Unisex (19 models)**: *Monte Carlo, Suffolk, Biarritz, Melbourne, Gold Coast, Manchester, Patra, Cape Town, Kona, Perledo, Dana Point, Brentwood, Oxford, Key West, Mar Vista, Denver, Andros, Buenos Aires, Sea Island* (MK-1000 series).
- **Women's Exclusive (21 models)**: *Andermatt, Lucerne, Edgewater, Molokai, Siesta Key, Lake Tahoe, Nagoya, Santo Domingo, Napa Valley, Grand Cayman, Atlanta, Agra, Catalina, Athens, Roanoke, Mumbai, Isle of Palms, Piedmont, Tokyo, Wilmington, Grenada* (MK-2000 series).

### Collection Membership Mathematical Invariants:
- `/collections/designer-eyewear` (Master Eyewear Hub): **46 products** (6 Men + 19 Unisex + 21 Women).
- `/collections/womens-sunglasses` (Women's Sunglasses): **40 products** (21 Women + 19 Unisex). Must contain **0 Men-exclusive models**.
- `/collections/mens-sunglasses` (Men's Sunglasses): **25 products** (6 Men + 19 Unisex). Must contain **0 Women-exclusive models**.
- Multi-tag route `/collections/designer-eyewear/women`: **40 products**.
- Multi-tag route `/collections/designer-eyewear/men`: **25 products**.

---

## 4. Environment & Prerequisites

### Toolchain:
- **Runtime**: Python 3.11+
- **Browser Automation**: `playwright` (`pip install playwright && playwright install chromium`)
- **Test Runner**: Python standard `unittest` (zero external runner dependency) or `pytest`

### Target Viewports:
- **Desktop Canvas**: `1440 x 900`
- **Mobile Device**: `430 x 932` (Apple iPhone 14/15/16 Pro Max viewport with Mobile Safari User Agent)

### Artifact Persistence:
Screenshots captured during Tier 4 scenarios are dual-written:
1. `artifacts/screenshots/scenario_*.png` (Relative to project root)
2. `C:\Users\Administrator\.gemini\antigravity\brain\94d518c6-9597-4450-872a-73e538db496a/` (System brain artifact store)

---

## 5. Execution Guide

### Run Full Suite (All 77 Tests):
```powershell
python scripts/test_hybrid_luxury_navigation_e2e.py --tier all
```

### Run via Standard Python unittest Runner:
```powershell
python -m unittest scripts/test_hybrid_luxury_navigation_e2e.py -v
```

### Run Specific Tiers:
```powershell
# Tier 1 only (Feature Coverage - 40 tests)
python scripts/test_hybrid_luxury_navigation_e2e.py --tier 1

# Tier 2 only (Boundary & Zero Leakage - 22 tests)
python scripts/test_hybrid_luxury_navigation_e2e.py --tier 2

# Tier 3 only (Cross-Feature Combinations - 9 tests)
python scripts/test_hybrid_luxury_navigation_e2e.py --tier 3

# Tier 4 only (Real-World Scenarios with Screenshots - 6 tests)
python scripts/test_hybrid_luxury_navigation_e2e.py --tier 4
```

### Override Base Storefront URL:
```powershell
python scripts/test_hybrid_luxury_navigation_e2e.py --base-url https://therareavenue.com --tier 2
```

---

## 6. Telemetry & Reporting

Upon completion of any run, a structured summary report is automatically generated at:
`artifacts/screenshots/test_results_summary.json`

The JSON report records:
- Execution timestamp and total duration (seconds)
- Total test count, pass count, failure count, and warning count
- Per-test telemetry: tier, feature name, test case ID, pass/fail status, HTTP response code, and diagnostic message
