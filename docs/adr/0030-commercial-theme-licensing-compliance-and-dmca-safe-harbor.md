# ADR 0030: Commercial Theme Licensing Compliance, DMCA Safe Harbor, and Anti-Piracy Invariant

## Status
Accepted & Strictly Enforced (2026-10-21)

## Context
On October 2026, the live storefront `therareavenue.com` (`hewmvw-am.myshopify.com`) received a formal DMCA copyright infringement notice and account suspension ultimatum from Shopify Legal on behalf of **Maestrooo** (developer and copyright owner of the commercial Shopify theme *Prestige*, which retails exclusively on the Shopify Theme Store for $400 USD). Shopify imposed a hard suspension deadline of **October 20 at 9:25 PM UTC** unless the unlicensed theme was purchased or permanently removed.

### Root Cause Analysis
1. **Unlicensed Commercial Theme Asset**:
   - The theme active on the store (`gid://shopify/OnlineStoreTheme/197348655270`) was created from an external ZIP upload rather than an official Shopify Theme Store purchase.
   - Forensic analysis of the exported theme ZIP (`theme_download.zip`, 210 total files) proved that 195 of the 210 files were Maestrooo's proprietary *Prestige* v10.11.1 codebase.
   - `config/settings_schema.json` explicitly declared `"theme_name": "Prestige"`, `"theme_author": "Maestrooo"`, `"theme_version": "10.11.1"`, and `config/settings_data.json` declared `"installed_preset_name": "Prestige"`.
2. **The Cosmetic Naming Fallacy ("Coupon Fix - Overlay Group")**:
   - The theme had been labeled in the Shopify Admin as `"Coupon Fix - Overlay Group"`.
   - In Shopify Online Store 2.0, slide-out drawers and popups are grouped in `sections/overlay-group.json`. Inside that file, lines 14–22 had `"cart-drawer"` configured with `"allow_discount_application": true` to enable coupon code entry within the slide-out cart drawer.
   - A store administrator or developer previously created or duplicated the theme in the Shopify Admin to apply that cart drawer coupon fix and named the copy `"Coupon Fix - Overlay Group"`.
   - **Crucial Rule**: Renaming a theme in the Shopify Admin only changes an administrative text label. It does **not** alter the underlying proprietary codebase, remove digital signatures, or generate a valid commercial license.
3. **Automated Anti-Piracy Detection**:
   - Commercial theme developers (including Maestrooo) deploy automated crawlers (`unlicensed.app`) that scan live Shopify storefronts.
   - The public JavaScript object `window.Shopify.theme` exposed:
     `{ "name": "Coupon Fix - Overlay Group", "id": 197348655270, "theme_store_id": null, "role": "main" }`
   - When a theme is bought legally on the Shopify Theme Store, `theme_store_id` is set to the official theme ID (e.g., `838` for Prestige). When uploaded as an external ZIP, `theme_store_id` is `null`.
   - The crawler detected Maestrooo's proprietary Web Components (`<loading-bar>`, `<mega-menu-disclosure>`, `<facet-link>`), CSS utility classes, and `theme.js`.
   - Matching this against Shopify's Theme Store sales ledger for `hewmvw-am.myshopify.com` confirmed zero purchase records, automatically triggering a formal DMCA takedown request to Shopify Legal.

## Decision

To permanently protect The Rare Avenue from store shutdown, domain suspension, and federal copyright infringement liability, the following engineering and operational invariants are strictly enacted:

### 1. Zero Unlicensed Commercial Themes (Strict Invariant)
- **Prohibited**: Under no circumstances may any developer, merchant, or automated assistant upload, install, or deploy an unlicensed commercial Shopify theme (e.g., Prestige, Impact, Focal, Warehouse, Impulse, Motion) via external ZIP, third-party download, or unofficial store transfer.
- **Single-Store License Bound**: Per Shopify Theme Store Terms of Service, theme licenses are strictly single-store. A license purchased for `store-a.myshopify.com` cannot be legally transferred or shared to `store-b.myshopify.com`.

### 2. Approved Storefront Architectures
All storefront development must follow one of two legal paths:
* **Path A: Official Free Shopify Themes (Recommended / Zero Recurring Cost)**:
  - Base the storefront on an official free theme published by Shopify on the Theme Store (e.g., **Horizon**, **Dawn**, **Sense**, **Craft**), carrying an official Shopify `themeStoreId` (e.g., Horizon = `themeStoreId: 2481`).
  - All bespoke luxury features (luxury mega-nav, faceted category filters, marquee collection scrollers, CheckCheck authentication drawers, custom font palettes) are developed as clean, modular Liquid snippets and sections layered on top of the free foundation.
* **Path B: Legally Purchased Commercial Themes**:
  - If a proprietary commercial theme like Prestige is explicitly required for the store design, it **must** be purchased directly through the [Shopify Theme Store](https://themes.shopify.com/) under the target store account (`hewmvw-am.myshopify.com`).
  - An official purchase automatically registers `theme_store_id: 838`, writes the transaction to Shopify's ledger, and whitelists the domain against all developer crawlers.

### 3. Immediate DMCA Remediation & Safe Harbor Protocol
If a copyright notice, licensing warning, or DMCA takedown is received:
1. **Immediate Deletion**: Permanently delete the infringing theme and all duplicate/draft copies from the Shopify Admin dashboard (`Online Store -> Themes -> Delete`).
2. **Switch to Verified Free Theme**: Ensure the live active theme is an official free theme (**Horizon**, Theme ID `#198751387814`).
3. **Notify Shopify Legal**: Respond to the Shopify Trust & Safety notice confirming that the reported theme has been completely removed from the store and replaced with an official free theme.
4. **Never File False Counter-Notices**: A DMCA counter-notice must **never** be filed unless the merchant possesses a valid Shopify Theme Store invoice specifically purchased under that `.myshopify.com` domain. Filing a false counter-notice without a valid license exposes the business to direct statutory copyright litigation.

## Consequences
- **Positive**: Complete immunity from DMCA takedowns, store suspensions, and copyright claims. Preserves Shopify merchant standing and developer partner status.
- **Architectural**: Custom features developed for The Rare Avenue (`luxury-desktop-nav`, `facets`, `checkcheck-authenticity`, `marquee-collection-list`) remain 100% reusable across any legally compliant base theme.
