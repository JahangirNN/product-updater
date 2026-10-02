# Shopify Integration & Storefront Progress Tracker: The Rare Avenue

**Store URL**: `https://therareavenue.com` (`hewmvw-am.myshopify.com`)  
**Store Currency**: Indian Rupee (INR ₹)  
**Store Protocol**: Shopify Admin GraphQL API (`2026-04`)  
**Last Updated**: October 2, 2026  

---

## 1. Master Milestone Roadmap

| Milestone | Status | Description | Key Deliverables |
| :--- | :---: | :--- | :--- |
| **M1: Prerequisites & Connectivity** | ✅ **COMPLETED** | Verified live GraphQL connectivity, dynamic CLI auth, installed skills (`shopify-admin`, `shopify-sync-engine`, `shopify-theme-dev`), and established ADR 0019. | `storage/shopify_auth.py`, ADR 0019, `docs/shopify/README.md` |
| **M2: Pilot Category Ingestion** | ✅ **COMPLETED** | Created automated smart collections on Shopify, mapped rich data schema, and uploaded pilot category (46 Versace Watches) with high-res images and whole-rupee INR math. | ADR 0020, `storage/shopify_sync.py`, `scripts/upload_versace_pilot.py` |
| **M3: Delta Freshner Live Sync Loop** | ✅ **COMPLETED** | Connected 1-hour background daemon to push price and stock shifts directly to Shopify via `productSet` in real-time. | `storage/shopify_sync.py`, `sync_catalog.py` live delta dispatch |
| **M4: Distributed Connector & High-Throughput Engine** | ✅ **COMPLETED** | Built distributed Shopify connector architecture: universal taxonomy normalizer with zero retailer leakage, declarative collection provisioner (27 smart collections), and high-throughput bulk uploader CLI. | `storage/shopify_taxonomy.py`, `storage/shopify_collections.py`, `scripts/shopify_bulk_uploader.py`, ADR 0021 |
| **M5: Storewide Catalog Ingestion** | 🔄 **IN PROGRESS** | Progressively ingesting remaining 2,612 products across JW PEI, COACH, Michael Kors, Nordstrom, Foot Locker, and JD Sports via bulk uploader. | `scripts/shopify_bulk_uploader.py`, `storage/db/index.json` |
| **M6: Code-Driven Storefront UI** | 🔄 **IN PROGRESS** | Prestige theme (v10.11) pulled locally; coded 3-tier luxury navigation sidebar (`snippets/luxury-sidebar-panels.liquid`) deployed directly to live theme (`#197348655270`). | `theme/`, ADR 0022, `config/shopify_navigation_manifest.json` |

---

## 2. Store Catalog Ingestion Ledger

| Source Store | Catalog Total | Status on Shopify | Ingested Count | Ingestion Date | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Jomashop (Watches Complete)** | 574 | 🟢 Ingestion Complete | 574 / 574 | 2026-09-25 | 100% of all 574 Luxury Watches Live (Tissot, Citizen, Movado, Seiko, MK, Versace, Ferragamo) |
| **JW PEI** | 491 | 🟢 Ingestion Complete | 491 / 491 | 2026-09-29 | 100% of Designer Vegan Leather Handbags Live with multi-color swatch linkage |
| **Coach** | 573 | 🟢 Ingestion Complete | 573 / 573 | 2026-10-01 | 100% of Handbags, Wallets, and Footwear Live with US/UK size matrix and S7 imagery |
| **Michael Kors** | 530 | 🟢 Ingestion Complete | 530 / 530 | 2026-10-01 | 100% of Designer Handbags, Eyewear, Belts, and Footwear Live |
| **Nordstrom** | 238 | 🟡 Ingesting | 92 / 238 | 2026-09-30 | Salomon, On Running, HOKA premium athletic footwear |
| **Foot Locker** | 307 | ⬜ Ready for Ingestion | 0 / 307 | - | Nike, adidas, ASICS sneakers |
| **JD Sports** | 476 | ⬜ Ready for Ingestion | 0 / 476 | - | Nike Footwear & Streetwear |
| **TOTAL** | **3,189** | - | **2,260 / 3,189** | - | **70.9% Ingested (Target: 100%)** |

---

## 3. Collections & Taxonomy Provisioning Ledger

| Collection Title | Type | Rule / Filter | Handle | Shopify GID | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Luxury Watches** | Smart | `TYPE EQUALS Watches` | `luxury-watches` | `gid://shopify/Collection/693133148326` | ✅ Live (574 prods) |
| **Men's Watches** | Smart | `TYPE EQUALS Watches` AND `TAG EQUALS Men's` | `mens-watches` | `gid://shopify/Collection/693144223910` | ✅ Live (367 prods) |
| **Women's Watches** | Smart | `TYPE EQUALS Watches` AND `TAG EQUALS Women's` | `womens-watches` | `gid://shopify/Collection/693144256678` | ✅ Live (207 prods) |
| **Versace** | Smart | `VENDOR EQUALS Versace` | `versace` | `gid://shopify/Collection/693133213862` | ✅ Live (46 prods) |
| **Tissot** | Smart | `VENDOR EQUALS Tissot` | `tissot` | `gid://shopify/Collection/693133246630` | ✅ Live (157 prods) |
| **Seiko** | Smart | `VENDOR EQUALS Seiko` | `seiko` | `gid://shopify/Collection/693133279398` | ✅ Live (68 prods) |
| **Citizen** | Smart | `VENDOR EQUALS Citizen` | `citizen` | `gid://shopify/Collection/693133312166` | ✅ Live (119 prods) |
| **Movado** | Smart | `VENDOR EQUALS Movado` | `movado` | `gid://shopify/Collection/693133344934` | ✅ Live (102 prods) |
| **Ferragamo** | Smart | `VENDOR EQUALS Ferragamo` | `ferragamo` | `gid://shopify/Collection/693161263270` | ✅ Live (15 prods) |
| **Michael Kors Watches** | Smart | `TYPE EQUALS Watches` AND `TITLE CONTAINS Michael Kors` | `michael-kors-watches` | `gid://shopify/Collection/693161296038` | ✅ Live (67 prods) |
| **Designer Bags** | Smart | `TAG EQUALS Designer Bags` | `designer-bags` | `gid://shopify/Collection/693162049702` | ✅ Live |
| **Premium Footwear** | Smart | `TAG EQUALS Premium Footwear` | `premium-footwear` | `gid://shopify/Collection/693162082470` | ✅ Live |
| **Wallets & Accessories**| Smart | `TAG EQUALS Wallets & Accessories` | `wallets-accessories` | `gid://shopify/Collection/693162115238` | ✅ Live |
| **Women's Handbags** | Smart | `TAG EQUALS Designer Bags` AND `TAG EQUALS Women` | `womens-handbags` | `gid://shopify/Collection/693162148006` | ✅ Live |
| **Men's Bags** | Smart | `TAG EQUALS Designer Bags` AND `TAG EQUALS Men` | `mens-bags` | `gid://shopify/Collection/693162180774` | ✅ Live |
| **Men's Shoes** | Smart | `TAG EQUALS Premium Footwear` AND `TAG EQUALS Men` | `mens-shoes` | `gid://shopify/Collection/693162213542` | ✅ Live |
| **Women's Shoes** | Smart | `TAG EQUALS Premium Footwear` AND `TAG EQUALS Women` | `womens-shoes` | `gid://shopify/Collection/693162246310` | ✅ Live |
| **JW PEI** | Smart | `VENDOR EQUALS JW PEI` | `jw-pei` | `gid://shopify/Collection/693162279078` | ✅ Live |
| **COACH** | Smart | `VENDOR EQUALS COACH` | `coach` | `gid://shopify/Collection/693162311846` | ✅ Live |
| **Michael Kors** | Smart | `VENDOR EQUALS Michael Kors` OR `MICHAEL Michael Kors` | `michael-kors` | `gid://shopify/Collection/693162344614` | ✅ Live |
| **Salomon** | Smart | `VENDOR EQUALS Salomon` | `salomon` | `gid://shopify/Collection/693162377382` | ✅ Live |
| **On Running** | Smart | `VENDOR EQUALS On` | `on-running` | `gid://shopify/Collection/693162410150` | ✅ Live |
| **HOKA** | Smart | `VENDOR EQUALS HOKA` | `hoka` | `gid://shopify/Collection/693162442918` | ✅ Live |
| **Nike** | Smart | `VENDOR EQUALS Nike` | `nike` | `gid://shopify/Collection/693162475686` | ✅ Live |
| **Jordan** | Smart | `VENDOR EQUALS Jordan` | `jordan` | `gid://shopify/Collection/693162508454` | ✅ Live |
| **adidas** | Smart | `VENDOR EQUALS adidas` | `adidas` | `gid://shopify/Collection/693162541222` | ✅ Live |
| **ASICS** | Smart | `VENDOR EQUALS ASICS` | `asics` | `gid://shopify/Collection/693162573990` | ✅ Live |
| **Designer Sunglasses & Eyewear** | Smart | `TYPE EQUALS Sunglasses` OR `TAG EQUALS Sunglasses` | `designer-eyewear` | `gid://shopify/Collection/693217951910` | ✅ Live (46 prods) |
| **Women's Sunglasses** | Smart | `TYPE EQUALS Sunglasses` AND `TAG EQUALS Women` | `womens-sunglasses` | `gid://shopify/Collection/693229584550` | ✅ Live (40 prods) |
| **Men's Sunglasses** | Smart | `TYPE EQUALS Sunglasses` AND `TAG EQUALS Men` | `mens-sunglasses` | `gid://shopify/Collection/693229617318` | ✅ Live (25 prods) |
| **Men** | Smart/Manual | Base Department | `men` | `gid://shopify/Collection/691279659174` | ✅ Existing |
| **Women** | Smart/Manual | Base Department | `women` | `gid://shopify/Collection/691279691942` | ✅ Existing |

---

## 4. Verification & Audit Trail

| Date | Verification Step | Result | Verified By |
| :--- | :--- | :---: | :--- |
| **2026-09-24** | Shopify Admin GraphQL Live Connectivity Test (`2026-04`) | `200 OK` (Plan: Basic, Currency: INR) | `test_cli_auth.py` |
| **2026-09-24** | Versace Luxury Watches Pilot Ingestion (46/46 items) | `46/46 PASS` (100% Success, 0 Errors) | `upload_versace_pilot.py` |
| **2026-09-24** | Tissot Luxury Watches Category Ingestion (157/157 items) | `157/157 PASS` (100% Success, 0 Errors) | `upload_tissot_category.py` |
| **2026-09-25** | All Remaining Watches Batch Ingestion (371/371 items) | `371/371 PASS` (100% Success, 0 Errors) | `upload_all_remaining_watches.py` |
| **2026-09-25** | Definitive 3-Pass Watch Catalog Audit | `100% PASS` across DB, GraphQL, & Endpoints | `run_watch_3pass_audit.py` |
| **2026-09-25** | Declarative Smart Collection Provisioning (17 new collections) | `17/17 CREATED` (0 Errors, 27/27 Total Active) | `storage/shopify_collections.py` |
| **2026-09-25** | Distributed Shopify Connector Unit Test Suite | `5/5 PASS` (0 Errors) | `test_shopify_connector.py` |
| **2026-09-25** | Live Watch Stock & Price Sync Deep Audit | `100% PASS` (Live polling, GIDs, GraphQL shift, OOS protection) | `scripts/audit_watch_live_sync.py` |
| **2026-09-25** | Luxury Watch PDP Reformatting & Zero Leakage Sync | `574/574 PASS` (100% Live on Shopify, 0 Leaks) | `scripts/reformat_and_sync_watches.py` |
| **2026-09-25** | Documentation Integrity & ADR Alignment Check | `100% PASS` | `verify_docs_alignment.py` |
| **2026-09-25** | 3-Tier Navigation Architecture & Manifest Established | `ADR 0022 ACCEPTED` | `docs/adr/0022-*` |
| **2026-09-25** | Live Theme 3-Tier Navigation Deployment (#197348655270) | `100% DEPLOYED & VERIFIED` (0 Errors) | `shopify theme push` & live curl verification |
| **2026-09-27** | MK Eyewear Tag Alignment & Partitioning (46/46 items) | `46/46 PASS` (6 Men, 19 Unisex, 21 Women, 0 leakage) | `execute_tag_alignment.py` / `verify_m1_eyewear.py` |
| **2026-09-27** | Eyewear Smart Collections Provisioning (3 collections) | `3/3 CREATED & PUBLISHED` (46, 40, 25 items, HTTP 200 OK) | `storage/shopify_collections.py` |
| **2026-09-27** | Hybrid Luxury Navigation Live Theme Deployment (#197348655270) | `3/3 SNIPPETS DEPLOYED` (`luxury-desktop-nav`, `luxury-sidebar-panels`, `facets`) | GraphQL `themeFilesUpsert` |
| **2026-09-27** | Automated Playwright Regression Verification (Tier 1 & Tier 4) | `46/46 PASS` (40 Tier 1 tests, 6 Tier 4 user journeys, 100% OK) | `scripts/test_hybrid_luxury_navigation_e2e.py` |
| **2026-09-27** | ADR 0023 Accepted (Hybrid Luxury Navigation & Eyewear) | `ADR 0023 ACCEPTED` | `docs/adr/0023-*` |
| **2026-10-01** | Coach Remaining Footwear & Wallets Ingestion (114 items) | `114/114 PASS` (Coach at 573/573, 100.0% Complete) | Subagent `Coach Ingestion Specialist` |
| **2026-10-01** | Michael Kors Remaining Footwear & Belts Ingestion (139 items) | `139/139 PASS` (MK at 530/530, 100.0% Complete) | Subagent `MK Ingestion Specialist` |
| **2026-10-01** | Online Store Sales Channel Batch Publication | `996/996 QUEUED & PUBLISHED` to Online Store Publication | `scripts/publish_active_coach_mk.py` |
| **2026-10-01** | Variant Stock Fallback Parity Bugfix | `FIXED & COMMITTED (54d7541e)`: Out-of-stock variants strictly enforce `DENY` policy | `storage/shopify_taxonomy.py` line 749 |
| **2026-10-02** | Truly Random Footwear Audit (8 Coach & MK Shoe Models) | `100% PASS` across 96 individual variants (Policy & Whole-Rupee INR) | `scratch/audit_random_shoes_variants.py` |


