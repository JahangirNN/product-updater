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
| **M2: Pilot Category Ingestion** | ⏳ **IN PROGRESS** | Create automated smart collections on Shopify, map rich data schema, and upload pilot category (15–46 products) with high-res images and whole-rupee INR math. | ADR 0020, `scripts/shopify_collection_provisioner.py`, `scripts/shopify_pilot_uploader.py` |
| **M3: Delta Freshner Live Sync Loop** | ⬜ **PENDING** | Connect 1-hour background daemon to push price and stock shifts directly to Shopify via `productSet` and `inventorySetQuantities`. | `storage/shopify_sync_bridge.py`, delta queue dispatcher |
| **M4: Full Catalog Batch Upload** | ⬜ **PENDING** | Stage and ingest all 3,189 products across all 7 stores via high-throughput `bulkOperationRunMutation`. | `scripts/shopify_bulk_uploader.py`, staged upload JSONL |
| **M5: Code-Driven Storefront UI** | ⬜ **PENDING** | Develop custom theme using Liquid OS 2.0, Vite (`vite-plugin-shopify`), and Tailwind CSS v4 with size pills, live stock badges, and specs accordions. | `theme/`, Vite configuration, Tailwind CSS v4 components |

---

## 2. Store Catalog Ingestion Ledger

| Source Store | Catalog Total | Status on Shopify | Ingested Count | Ingestion Date | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Jomashop (Pilot)** | 574 | ⏳ Staging Pilot | 0 / 574 | 2026-09-24 | Pilot Category: Versace (46) / Ferragamo (15) |
| **Nordstrom** | 238 | ⬜ Pending M4 | 0 / 238 | - | Salomon, On Running, HOKA |
| **Foot Locker** | 307 | ⬜ Pending M4 | 0 / 307 | - | Nike, Adidas, ASICS |
| **JW PEI** | 491 | ⬜ Pending M4 | 0 / 491 | - | Designer Vegan Leather Handbags |
| **Michael Kors** | 530 | ⬜ Pending M4 | 0 / 530 | - | Handbags, Wallets, Sandals, Sneakers |
| **Coach** | 573 | ⬜ Pending M4 | 0 / 573 | - | Handbags, Crossbody, Wallets, Footwear |
| **JD Sports** | 476 | ⬜ Pending M4 | 0 / 476 | - | Nike Footwear & Streetwear |
| **TOTAL** | **3,189** | - | **0 / 3,189** | - | **Target: 100% Ingested** |

---

## 3. Collections & Taxonomy Provisioning Ledger

| Collection Title | Type | Rule / Filter | Handle | Shopify GID | Status |
| :--- | :---: | :--- | :--- | :--- | :---: |
| **Luxury Watches** | Smart | `product_type EQUALS Watches` | `luxury-watches` | - | ⏳ Pending |
| **Designer Bags** | Smart | `product_type IN (Handbags, Shoulder Bags, Tote Bags)` | `designer-bags` | - | ⏳ Pending |
| **Premium Footwear** | Smart | `product_type IN (Shoes, Sneakers, Athletic Shoes)` | `premium-footwear` | - | ⏳ Pending |
| **Men** | Smart | `tag EQUALS Gender:Men` OR `tag EQUALS Gender:Unisex` | `men` | `gid://shopify/Collection/691279659174` | ✅ Existing |
| **Women** | Smart | `tag EQUALS Gender:Women` OR `tag EQUALS Gender:Unisex` | `women` | `gid://shopify/Collection/691279691942` | ✅ Existing |
| **Versace** | Smart | `vendor EQUALS Versace` | `versace` | - | ⏳ Pending |
| **Tissot** | Smart | `vendor EQUALS Tissot` | `tissot` | - | ⏳ Pending |
| **COACH** | Smart | `vendor EQUALS COACH` | `coach` | - | ⏳ Pending |
| **Michael Kors** | Smart | `vendor EQUALS Michael Kors` | `michael-kors` | - | ⏳ Pending |

---

## 4. Verification & Audit Trail

| Date | Verification Step | Result | Verified By |
| :--- | :--- | :---: | :--- |
| **2026-09-24** | Shopify Admin GraphQL Live Connectivity Test (`2026-04`) | `200 OK` (Plan: Basic, Currency: INR) | `test_cli_auth.py` |
| **2026-09-24** | Multi-Store Delta Engine Integration Test | `16/16 PASS` (100% Success) | `test_delta_engine.py` |
| **2026-09-24** | Documentation Integrity & ADR Alignment Check | `100% PASS` | `verify_docs_alignment.py` |
