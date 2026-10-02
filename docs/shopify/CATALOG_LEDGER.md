# Shopify Ingestion & Catalog Inventory Ledger

> **Authoritative Ingestion & Progress Ledger for The Rare Avenue**  
> **Store URL**: `https://therareavenue.com` (`hewmvw-am.myshopify.com`)  
> **Store Protocol**: Shopify Admin GraphQL API (`2026-04`)  
> **Last Verified Audit**: 2026-10-02 16:26 IST  
> **Automated Audit Script**: [`scripts/audit_shopify_catalog_counts.py`](file:///c:/Users/Administrator/WorkPlace/dropship-scraper-portable-20260905/product-updater/scripts/audit_shopify_catalog_counts.py)

---

## 1. High-Level Summary

| Metric | Count | Percentage | Status |
| :--- | :---: | :---: | :--- |
| **Total Products in Local Database** | **3,189** | 100% | Scraped across 7 active retailer stores |
| **Total Products Linked to Shopify** | **2,260** | **70.9%** | Formatted with tri-field whole-rupee INR pricing |
| **Live Active Storefront Silhouettes** | **1,837** | **57.6%** | Canonical pieces active on storefront |
| **Drafted Siblings / Clones** | **423** | 13.3% | JW PEI colorway duplicates consolidated into single PDPs |
| **Remaining to Onboard on Shopify** | **929** | **29.1%** | Footwear, Sneakers, Belts, Streetwear |

---

## 2. Store-by-Store Ingestion Ledger

| Retailer / Maison | Local DB Total | Live on Shopify | Remaining | Ingestion % | Live Categories | Remaining Backlog |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **Jomashop** | 574 | **574** | **0** | **100.0%** | Luxury Watches (Tissot, Citizen, Seiko, Movado, Versace, Ferragamo, MK) | Completed |
| **JW PEI** | 491 | **491** | **0** | **100.0%** | 68 Canonical Silhouettes (423 sibling clones drafted, variants unified) | Completed |
| **COACH** | 573 | **573** | **0** | **100.0%** | Handbags, Crossbody, Shoulder Bags, Satchels, Totes, Wallets, 50 Shoes | 109 Shoes & Sandals, 3 Wallets, 2 Shoulder Bags |
| **Michaelkors** | 530 | **530** | **0** | **100.0%** | Handbags (234), Wallets (60), Designer Sunglasses (46), 50 Shoes/Flats | 46 Sandals, 40 Sneakers, 20 Shoes, 14 Flats, 12 Belts, 4 Boots |
| **Nordstrom** | 238 | **92** | **146** | **38.7%** | Salomon Performance Outdoor Footwear (XT-4, XT-6) | 67 On Running, 27 HOKA, 18 Salomon, 34 Nordstrom Curated |
| **Footlocker** | 307 | **0** | **307** | **0.0%** | None | 122 Nike, 97 adidas Originals, 87 ASICS |
| **Jdsports** | 476 | **0** | **476** | **0.0%** | None | 476 Nike Footwear, Dunks & Streetwear |
| **TOTAL** | **3,189** | **2,260** | **929** | **70.9%** | **Watches (574), Bags & Wallets (1,291), Eyewear (46), Footwear (96)** | **Footwear & Streetwear (1,182)** |

---

## 3. How to Keep This Ledger Updated

Whenever new products are added or synced to Shopify, run the dedicated auto-update script:
```bash
python scripts/audit_shopify_catalog_counts.py
```
This script will re-query the Shopify Admin GraphQL API, scan the local JSON database, update this markdown file automatically, and stamp the latest audit timestamp.
