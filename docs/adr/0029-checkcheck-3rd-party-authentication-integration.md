# ADR 0029: CheckCheck 3rd-Party Authentication & Trust Kit Integration

## Status
Accepted (2026-10-16)

## Context
The Rare Avenue retails luxury, collector, and performance footwear alongside luxury accessories and timepieces sourced internationally. High-ticket luxury buyers demand verifiable authenticity proofs, yet standard dropshipping catalogs cannot display physical per-pair certificates prior to sourcing. Displaying generic static sample certificates on product listings can appear deceptive or amateurish, while omitting authentication signals elevates buyer hesitation.

The Rare Avenue established a verified B2B partnership with **CheckCheck for Business** (`business.getcheckcheck.com`), an industry-standard 3rd-party authentication platform with 4-hour SLA luxury evaluations and physical tamper-evident serialized green QR tags.

## Decision
1. **Pre-Purchase UI Architecture (Dual-Mode)**:
   - **Mode A (Pre-Authenticated / In-Stock Inventory)**: When a product record contains live CheckCheck verification metafields (`product.metafields.checkcheck.coa_url`, `coa_id`), the PDP displays `100% VERIFIED AUTHENTIC · COA #CC-XXXX` with direct one-click verification linking to the live digital certificate on CheckCheck's servers.
   - **Mode B (On-Demand Sourced / Partner Protocol)**: When items are drop-dispatched on order, the PDP displays `VERIFIED AUTHENTIC · CHECKCHECK PARTNER` with a `View Proof →` trigger. This opens the **Authenticity Protocol Drawer**, detailing the 3-step physical verification pipeline (Intake Inspection → 4-Hour CheckCheck Audit → Tamper-Evident Green Tagging & Scannable QR delivery) alongside The Rare Avenue Triple Guarantee (100% immediate refund if unverified).
2. **Shopify Connect & API Bridge**:
   - Integrated the official CheckCheck Connect Shopify App on store `hewmvw-am.myshopify.com` (`https://therareavenue.com/`).
   - Connected via dedicated production API key (`ck_live_...`) with `Full access`, `photos:read`, and `coa:read` scopes.
   - Automated metafield sync writes directly to namespace `checkcheck` (`coa_url`, `certificate_url`, `check_id`, `result`, `status`).
3. **Quiet Luxury Visual Standards**:
   - Replaced all ad-hoc trust marks with official CheckCheck vector assets (`checkcheck-wordmark.svg`, `checkcheck-badge-dark.png`, `checkcheck-badge-green.png`).
   - Teleported the modal container to `document.body` with max integer `z-index: 2147483647` to break free from nested theme stacking contexts.
   - Integrated zero-radius, refined typography matching The Rare Avenue's bespoke editorial palette.

## Consequences
- **Positive**: Eliminates customer trust friction for luxury footwear; ensures both pre-verified stock and incoming orders are truthfully presented without fraudulent claims or tacky badge clutter.
- **Maintenance**: CheckCheck credit consumption ($7/check standard luxury, $20/check Hermès) is managed via CheckCheck Business Dashboard; automated webhook updates write certificate URLs to Shopify product metafields as evaluations complete.
