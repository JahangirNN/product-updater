# Shopify Integration & Storefront Progress Tracker: The Rare Avenue

**Store URL**: `https://therareavenue.com` (`hewmvw-am.myshopify.com`)  
**Store Currency**: Indian Rupee (INR ₹)  
**API Protocol**: Shopify Admin GraphQL API (`2026-04`)  
**Last Updated**: September 25, 2026  

---

## 1. Master Milestone Roadmap

| Milestone | Status | Description | Key Deliverables |
| :--- | :---: | :--- | :--- |
| **M1: Prerequisites & Connectivity** | ✅ **COMPLETED** | Verified live GraphQL connectivity, dynamic CLI auth, installed skills (`shopify-admin`, `shopify-sync-engine`, `shopify-theme-dev`), and established ADR 0019. | `storage/shopify_auth.py`, ADR 0019, `docs/shopify/README.md` |
| **M2: Pilot Category Ingestion** | ✅ **COMPLETED** | Created automated smart collections on Shopify, mapped rich data schema, and uploaded pilot category (46 Versace Watches) with high-res images and whole-rupee INR math. | ADR 0020, `storage/shopify_sync.py`, `scripts/upload_versace_pilot.py` |
| **M3: Delta Freshner Live Sync Loop** | ✅ **COMPLETED** | Connected 1-hour background daemon to push price and stock shifts directly to Shopify via `productSet` in real-time. | `storage/shopify_sync.py`, `sync_catalog.py` live delta dispatch |
| **M4: Distributed Connector & High-Throughput Engine** | ✅ **COMPLETED** | Built distributed Shopify connector architecture: universal taxonomy normalizer with zero retailer leakage, declarative collection provisioner (27 smart collections), and high-throughput bulk uploader CLI. | `storage/shopify_taxonomy.py`, `storage/shopify_collections.py`, `scripts/shopify_bulk_uploader.py`, ADR 0021 |
| **M5: Storewide Catalog Ingestion** | 🔄 **IN PROGRESS** | Progressively ingesting remaining 2,612 products across JW PEI, COACH, Michael Kors, Nordstrom, Foot Locker, and JD Sports via bulk uploader. | `scripts/shopify_bulk_uploader.py`, `storage/db/index.json` |
| **M6: Code-Driven Storefront UI** | ⬜ **PENDING** | Develop custom theme using Liquid OS 2.0, Vite (`vite-plugin-shopify`), and Tailwind CSS v4 with size pills, live stock badges, and specs accordions. | `theme/`, Vite configuration, Tailwind CSS v4 components |

---

## 2. Store Catalog Ingestion Ledger

| Source Store | Catalog Total | Status on Shopify | Ingested Count | Ingestion Date | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Jomashop (Watches Complete)** | 574 | 🟢 Ingestion Complete | 574 / 574 | 2026-09-25 | 100% of all 574 Luxury Watches Live (Tissot, Citizen, Movado, Seiko, MK, Versace, Ferragamo) |
| **JW PEI** | 491 | 🟡 Ingesting | 4 / 491 | 2026-09-25 | Designer Vegan Leather Handbags |
| **Nordstrom** | 238 | ⬜ Ready for Ingestion | 0 / 238 | - | Salomon, On Running, HOKA |
| **Foot Locker** | 307 | ⬜ Ready for Ingestion | 0 / 307 | - | Nike, adidas, ASICS |
| **Michael Kors** | 530 | ⬜ Ready for Ingestion | 0 / 530 | - | Handbags, Wallets, Sandals, Sneakers |
| **Coach** | 573 | ⬜ Ready for Ingestion | 0 / 573 | - | Handbags, Crossbody, Wallets, Footwear |
| **JD Sports** | 476 | ⬜ Ready for Ingestion | 0 / 476 | - | Nike Footwear & Streetwear |
| **TOTAL** | **3,189** | - | **578 / 3,189** | - | **Target: 100% Ingested** |

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
