# Shopify Storefront Theme Licensing & Copyright Compliance Guide

> **Priority**: Critical / Strict Operational Invariant  
> **Related Architecture Record**: [ADR 0030: Commercial Theme Licensing Compliance, DMCA Safe Harbor, and Anti-Piracy Invariant](file:///c:/workspace/dropship-scraper-portable-20260905/product-updater/docs/adr/0030-commercial-theme-licensing-compliance-and-dmca-safe-harbor.md)  
> **Last Updated**: 2026-10-21  

---

## 1. Executive Incident Summary (The "Coupon Fix" Case)

In October 2026, the live store `The Rare Avenue` (`therareavenue.com` / `hewmvw-am.myshopify.com`) received a formal DMCA copyright infringement notice and store suspension warning from Shopify Legal on behalf of **Maestrooo** (the French software studio that authors the commercial theme *Prestige*, which sells on the Shopify Theme Store for $400 USD).

Shopify locked theme publishing and issued a hard deadline: **resolve the issue by purchasing the theme or permanently deleting it, or the entire store will be suspended on October 20 at 9:25 PM UTC**.

### Root Cause Audit
1. **Unlicensed Base Theme**: An external ZIP containing Maestrooo's *Prestige* v10.11.1 had been uploaded directly to the Shopify Admin instead of being purchased through the Shopify Theme Store.
2. **Cosmetic Naming**: The theme was labeled in the admin dashboard as **"Coupon Fix - Overlay Group"** because an administrator previously edited `sections/overlay-group.json` to enable discount codes in the cart drawer (`"allow_discount_application": true`).
3. **Automated Crawlers**: Anti-piracy bots operated by Maestrooo (`unlicensed.app`) crawled the storefront, detected Prestige's proprietary Web Components and CSS assets, checked Shopify's purchase ledger for `hewmvw-am.myshopify.com`, and finding no purchase record, filed an automated DMCA takedown.

---

## 2. Technical Detection: How Theme Authors Catch Unlicensed Stores

Many merchants mistakenly believe that uploading a theme ZIP privately hides the theme's origins. In reality, Shopify storefronts publicly broadcast their theme metadata and code footprint:

### 2.1 The `window.Shopify.theme` Object
Every Shopify storefront renders a public JavaScript global variable accessible in browser developer tools:
```javascript
// Legitimate Purchased Theme:
window.Shopify.theme = {
  name: "Prestige",
  id: 197348655270,
  theme_store_id: 838, // Official Shopify Theme Store ID
  role: "main"
};

// Manually Uploaded ZIP (Flagged as Unlicensed):
window.Shopify.theme = {
  name: "Coupon Fix - Overlay Group",
  id: 197348655270,
  theme_store_id: null, // NULL indicates an unpurchased external upload
  role: "main"
};
```
Whenever `theme_store_id` is `null` on a store running commercial theme assets, automated systems instantly flag the store for a license ledger check.

### 2.2 Proprietary Web Components & Signatures
Themes like Prestige use proprietary custom HTML elements, script bundles, and schemas:
* Custom Elements: `<loading-bar>`, `<mega-menu-disclosure>`, `<facet-link>`
* Core JS: `/cdn/shop/t/{id}/assets/theme.js`
* Core CSS: `/cdn/shop/t/{id}/assets/theme.css`
* Configuration metadata: `config/settings_schema.json` containing `"theme_author": "Maestrooo"`, `"theme_name": "Prestige"`

Scanners match these DOM elements within seconds of visiting the homepage.

---

## 3. The 3 Common Fallacies (And Why They Fail)

| Fallacy | Why It Fails |
| :--- | :--- |
| **"If I rename the theme, Shopify won't know."** | Renaming a theme in the Shopify Admin only changes an administrative display string. It does **not** change the underlying 195+ theme files, compiled JavaScript, Web Components, or the missing `theme_store_id`. |
| **"I bought it once for my other store, so I can use it here."** | Shopify Theme Store licenses are strictly **single-store**. A theme license purchased for `store-a.myshopify.com` cannot legally be transferred, duplicated, or uploaded to `store-b.myshopify.com`. |
| **"A developer gave me the ZIP, so I'm covered."** | Freelancers and third-party agencies frequently distribute exported theme ZIPs without purchasing client licenses. The merchant whose `.myshopify.com` domain is live is legally responsible for copyright compliance under DMCA. |

---

## 4. The 4 Golden Rules for Storefront Engineering

To ensure our store never faces suspension or copyright claims again, adhere strictly to these 4 rules:

### Rule 1: Zero Unlicensed Commercial Themes
Never upload, clone, or deploy an unpurchased commercial Shopify theme (e.g., Prestige, Impact, Focal, Warehouse, Motion, Impulse). 

### Rule 2: Free Official Themes as the Customization Foundation
* The active store foundation is **Horizon** (`themeStoreId: 2481`), an official, 100% free open-source theme created and supported by Shopify.
* Any custom design requirements (luxury mega-menus, faceted drawer filters, CheckCheck authenticity protocols, marquee collection sliders) must be built as custom, modular Liquid snippets and sections on top of the free theme.
* Free themes carry zero licensing cost and zero copyright risk.

### Rule 3: Official Purchase Mandatory If Commercial Themes Are Needed
If the merchant explicitly decides to adopt a paid commercial theme:
1. It **must** be purchased directly through the [Shopify Theme Store](https://themes.shopify.com/) logged in under `hewmvw-am.myshopify.com`.
2. This binds the official `theme_store_id` to our billing account and permanently whitelists our domain with the author's legal databases.

### Rule 4: Protocol if a Licensing Inquiry Occurs
1. **Never File a False DMCA Counter-Notice**: Submitting a counter-notice without an official Shopify Theme Store invoice under penalty of perjury can trigger direct federal copyright litigation.
2. **Immediate Remediation**: Immediately switch the live storefront to the verified free theme (**Horizon**), permanently delete all copies of the reported theme, and reply to Shopify Legal confirming compliance.

---

## 5. Verification Checklist for Developers & Assistants

Before publishing or updating any theme on Shopify:
- [ ] Run GraphQL query to inspect `themeStoreId`:
  ```graphql
  {
    themes(roles: [MAIN]) {
      nodes {
        id
        name
        themeStoreId
      }
    }
  }
  ```
- [ ] Confirm `themeStoreId` is NOT `null`.
- [ ] If `themeStoreId` is `null`, verify the theme is 100% bespoke custom code or derived from an MIT/open-source Shopify template (like Dawn/Horizon), and does NOT contain copyrighted third-party vendor code.
- [ ] Confirm no proprietary vendor URLs (e.g. `support.maestrooo.com`, `archetypethemes.co`) exist in `config/settings_schema.json` without an active commercial license.
