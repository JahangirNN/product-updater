# Shopify Integration & Storefront Progress Tracker: The Rare Avenue

**Store URL**: `https://therareavenue.com` (`hewmvw-am.myshopify.com`)  
**Store Currency**: Indian Rupee (INR ₹)  
**API Protocol**: Shopify Admin GraphQL API (`2026-04`)  
**Last Updated**: September 2026  

---

## 1. Master Milestone Roadmap

| Milestone | Status | Description | Key Deliverables |
| :--- | :---: | :--- | :--- |
| **M1: Prerequisites & Connectivity** | ✅ **COMPLETED** | Verified live GraphQL connectivity, dynamic CLI auth, installed skills (`shopify-admin`, `shopify-sync-engine`, `shopify-theme-dev`), and established ADR 0019. | `storage/shopify_auth.py`, ADR 0019, `docs/shopify/README.md` |
| **M2: Pilot Category Ingestion** | ✅ **COMPLETED** | Created automated smart collections on Shopify, mapped rich data schema, and uploaded pilot category (46 Versace Watches) with high-res images and whole-rupee INR math. | ADR 0020, `storage/shopify_sync.py`, `scripts/upload_versace_pilot.py` |
| **M3: Delta Freshner Live Sync Loop** | ✅ **COMPLETED** | Connected 1-hour background daemon to push price and stock shifts directly to Shopify via `productSet` in real-time. | `storage/shopify_sync.py`, `sync_catalog.py` live delta dispatch |
| **M4: Full Catalog Batch Upload** | ⬜ **PENDING** | Stage and ingest all remaining products across all 7 stores via high-throughput GraphQL upload / `productSet`. | `scripts/shopify_bulk_uploader.py`, staged upload JSONL |
| **M5: Code-Driven Storefront UI** | ⬜ **PENDING** | Develop custom theme using Liquid OS 2.0, Vite (`vite-plugin-shopify`), and Tailwind CSS v4 with size pills, live stock badges, and specs accordions. | `theme/`, Vite configuration, Tailwind CSS v4 components |

---

## 2. Store Catalog Ingestion Ledger

| Source Store | Catalog Total | Status on Shopify | Ingested Count | Ingestion Date | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Jomashop (Watches Complete)** | 574 | 🟢 Ingestion Complete | 574 / 574 | 2026-09-25 | 100% of all 574 Luxury Watches Live |
| **Nordstrom** | 238 | ⬜ Pending M4 | 0 / 238 | - | Salomon, On Running, HOKA |
| **Foot Locker** | 307 | ⬜ Pending M4 | 0 / 307 | - | Nike, Adidas, ASICS |
| **JW PEI** | 491 | ⬜ Pending M4 | 0 / 491 | - | Designer Vegan Leather Handbags |
| **Michael Kors** | 530 | ⬜ Pending M4 | 0 / 530 | - | Handbags, Wallets, Sandals, Sneakers |
| **Coach** | 573 | ⬜ Pending M4 | 0 / 573 | - | Handbags, Crossbody, Wallets, Footwear |
| **JD Sports** | 476 | ⬜ Pending M4 | 0 / 476 | - | Nike Footwear & Streetwear |
| **TOTAL** | **3,189** | - | **574 / 3,189** | - | **Target: 100% Ingested** |

---

## 3. Collections & Taxonomy Provisioning Ledger

| Collection Title | Type | Rule / Filter | Handle | Shopify GID | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Luxury Watches** | Smart | `product_type EQUALS Watches` | `luxury-watches` | `gid://shopify/Collection/693133148326` | ✅ Live (574 prods) |
| **Men's Watches** | Smart | `product_type EQUALS Watches` AND `tag EQUALS Men's` | `mens-watches` | `gid://shopify/Collection/693144223910` | ✅ Live (367 prods) |
| **Women's Watches** | Smart | `product_type EQUALS Watches` AND `tag EQUALS Women's` | `womens-watches` | `gid://shopify/Collection/693144256678` | ✅ Live (207 prods) |
| **Versace** | Smart | `vendor EQUALS Versace` | `versace` | `gid://shopify/Collection/693133213862` | ✅ Live (46 prods) |
| **Tissot** | Smart | `vendor EQUALS Tissot` | `tissot` | `gid://shopify/Collection/693133246630` | ✅ Live (157 prods) |
| **Seiko** | Smart | `vendor EQUALS Seiko` | `seiko` | `gid://shopify/Collection/693133279398` | ✅ Live (68 prods) |
| **Citizen** | Smart | `vendor EQUALS Citizen` | `citizen` | `gid://shopify/Collection/693133312166` | ✅ Live (119 prods) |
| **Movado** | Smart | `vendor EQUALS Movado` | `movado` | `gid://shopify/Collection/693133344934` | ✅ Live (102 prods) |
| **Ferragamo** | Smart | `vendor EQUALS Ferragamo` | `ferragamo` | `gid://shopify/Collection/693161263270` | ✅ Live (15 prods) |
| **Michael Kors Watches** | Smart | `product_type EQUALS Watches` AND `vendor EQUALS Michael Kors` | `michael-kors-watches` | `gid://shopify/Collection/693161296038` | ✅ Live (67 prods) |
| **Designer Bags** | Smart | `product_type IN (Handbags, Shoulder Bags, Tote Bags)` | `designer-bags` | - | ⏳ Pending |
| **Premium Footwear** | Smart | `product_type IN (Shoes, Sneakers, Athletic Shoes)` | `premium-footwear` | - | ⏳ Pending |
| **Men** | Smart | `tag EQUALS Gender:Men` OR `tag EQUALS Gender:Unisex` | `men` | `gid://shopify/Collection/691279659174` | ✅ Existing |
| **Women** | Smart | `tag EQUALS Gender:Women` OR `tag EQUALS Gender:Unisex` | `women` | `gid://shopify/Collection/691279691942` | ✅ Existing |

---

## 4. Verification & Audit Trail

| Date | Verification Step | Result | Verified By |
| :--- | :--- | :---: | :--- |
| **2026-09-24** | Shopify Admin GraphQL Live Connectivity Test (`2026-04`) | `200 OK` (Plan: Basic, Currency: INR) | `test_cli_auth.py` |
| **2026-09-24** | Versace Luxury Watches Pilot Ingestion (46/46 items) | `46/46 PASS` (100% Success, 0 Errors) | `upload_versace_pilot.py` |
| **2026-09-24** | Tissot Luxury Watches Category Ingestion (157/157 items) | `157/157 PASS` (100% Success, 0 Errors) | `upload_tissot_category.py` |
| **2026-09-25** | All Remaining Watches Batch Ingestion (371/371 items) | `371/371 PASS` (100% Success, 0 Errors) | `upload_all_remaining_watches.py` |
| **2026-09-25** | Definitive 3-Pass Watch Catalog Audit | `100% PASS` across DB, GraphQL, & Endpoints | `run_watch_3pass_audit.py` |
| **2026-09-25** | Documentation Integrity & ADR Alignment Check | `100% PASS` | `verify_docs_alignment.py` |
