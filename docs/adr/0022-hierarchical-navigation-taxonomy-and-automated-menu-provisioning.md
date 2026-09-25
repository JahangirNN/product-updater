# ADR 0022: Hierarchical Navigation Taxonomy & Menu Provisioning Architecture

## Status
Accepted

## Date
2026-09-25

## Context
Following the successful ingestion of all 574 luxury watches and their live delta synchronization on Shopify (*The Rare Avenue*, hewmvw-am.myshopify.com), catalog expansion across the remaining 2,605 products (handbags, footwear, wallets) necessitates a structured, multi-dimensional browsing hierarchy.

Key challenges identified:
1. **Navigational Depth vs Collection Explosion**: Direct multiplication of Department x Category x Brand (e.g., 2 Genders x 5 Categories x 25 Brands) would create 250+ redundant smart collections, cluttering Shopify Admin and creating maintenance drift.
2. **Customer Intent**: Luxury shoppers browse either by department and category (e.g. *Women -> Watches -> Seiko*) or directly by designer showroom (e.g. *Tissot*, *JW PEI*).
3. **Manual Menu Labor**: Manually typing, linking, and organizing dozens of nested menu items in Shopify Admin UI (Online Store > Navigation > Menus) is labor-intensive and prone to human error.

## Decisions

### 1. Three-Tier Hierarchical Catalog Taxonomy
We adopt a standardized 3-tier navigation tree across the entire catalog:
- **Tier 1 (Department)**: Women, Men, Designers / Brands (A-Z).
- **Tier 2 (Master Category Hubs)**:
  - Luxury Watches (/collections/luxury-watches, womens-watches, mens-watches)
  - Designer Bags (/collections/designer-bags, womens-handbags, mens-bags)
  - Premium Footwear (/collections/premium-footwear, womens-shoes, mens-shoes)
  - Wallets & Accessories (/collections/wallets-accessories)
- **Tier 3 (Brand / Sub-Category Views)**:
  - Specific brand selections under a department category (e.g. Women > Watches > Seiko, Men > Shoes > Salomon).

### 2. Hybrid Collection Architecture
To prevent collection explosion while delivering precise brand filtering:
- **Hub Collections with Faceted Filtering**: The category hubs (womens-watches, mens-watches, designer-bags, etc.) serve as the primary landing pages. Sub-links in the menu target native vendor-filtered URLs:
  /collections/womens-watches?filter.p.vendor=Seiko
  or tag-filtered URLs (/collections/womens-watches/seiko).
- **Brand Showrooms**: Master brand collections (/collections/seiko, /collections/tissot, /collections/jw-pei) exist independently to present the brand's full cross-department collection.

### 3. Programmatic Navigation & Menu Automation
To eliminate manual menu creation in the Shopify Admin:
- **Declarative Navigation Manifest (config/shopify_navigation_manifest.json)**: A centralized JSON file defining the complete navigation tree, titles, URLs, and nesting structure.
- **Admin GraphQL Menu Script (scripts/shopify_menu_sync.py)**: Automates menu creation and updates via Shopify Admin GraphQL mutations (menuCreate, menuUpdate) using the write_online_store_navigation scope.
- **Theme Code Integration**: In the storefront theme (	heme/ or live theme #197348655270), provide code-driven sidebar templates that can render directly from the manifest or native collections, eliminating manual dashboard configuration.

## Consequences
- **Zero Manual Menu Data Entry**: Store menus can be provisioned or updated in seconds via script or theme code.
- **Future-Proof Scalability**: Adding future brands (e.g. Balenciaga, Prada) requires only updating the manifest; no manual collection rewiring is necessary.
- **Optimized Luxury UX**: Matches customer expectations on premier luxury shopping destinations (SSENSE, Farfetch, Net-a-Porter).
