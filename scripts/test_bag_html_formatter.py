import os
import sys
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scripts.audit_luxury_bags_catalog import get_luxury_bag_products
from storage.shopify_taxonomy import resolve_authentic_vendor, resolve_luxury_bag_silhouette

def format_luxury_bag_description_html(prod):
    vendor = resolve_authentic_vendor(prod)
    title = prod.get("title", "Luxury Bag")
    sil = resolve_luxury_bag_silhouette(prod) or "Designer Handbag"
    specs = prod.get("specifications") or {}
    
    # 1. Extract and sanitize specs
    raw_material = specs.get("Material") or specs.get("Main Material") or specs.get("Major Material") or ""
    # Clean material if it's just repeating the title
    if raw_material.lower() == title.lower() or "signature canvas" in title.lower() and not raw_material:
        material = "Signature Coated Canvas & Smooth Leather"
    elif raw_material:
        material = str(raw_material).strip()
    else:
        material = "Premium Leather"
        
    lining = specs.get("Lining") or specs.get("Lining Material") or ""
    hardware = specs.get("Hardware") or specs.get("Hardware Finish") or ""
    closure = specs.get("Closure") or ""
    dims = specs.get("Bag Dimensions") or specs.get("Dimension") or specs.get("Dimensions") or ""
    handle_drop = specs.get("Handle Drop") or specs.get("HandleDrop") or ""
    strap_drop = specs.get("Shoulder Strap Drop") or specs.get("Strap Drop") or ""
    carrying = specs.get("Carrying Method") or specs.get("Carrying Style") or ""
    pockets = specs.get("Inner Pockets") or specs.get("Pockets") or ""
    capacity = specs.get("Capacity") or ""
    
    # Scan DetailsBullets (common in Michael Kors)
    bullets = specs.get("DetailsBullets") or []
    if isinstance(bullets, list):
        for b in bullets:
            b_str = str(b).strip()
            b_low = b_str.lower()
            if any(h in b_low for h in ["hardware", "gold-tone", "silver-tone", "gunmetal"]) and not hardware:
                hardware = b_str
            elif any(c in b_low for c in ["closure", "zip fastening", "magnetic snap", "flap"]) and not closure:
                closure = b_str
            elif "lining:" in b_low and not lining:
                lining = b_str.replace("Lining:", "").strip()
            elif "handle drop:" in b_low and not handle_drop:
                handle_drop = b_str.replace("Handle drop:", "").strip()
            elif any(s in b_low for s in ["adjustable strap:", "strap drop:"]) and not strap_drop:
                strap_drop = b_str
            elif any(p in b_low for p in ["interior details:", "exterior details:"]) and not pockets:
                pockets = b_str
                
    # 2. Extract or synthesize product summary
    raw_desc = prod.get("description_html") or prod.get("descriptionHtml") or ""
    summary_match = re.search(r'<p class="product-summary">([\s\S]*?)</p>', raw_desc)
    existing_summary = summary_match.group(1).strip() if summary_match else ""
    
    if existing_summary and len(existing_summary) > 20:
        summary_text = existing_summary
    else:
        summary_text = (
            f"The {title} by {vendor} exemplifies refined modern luxury and quintessential craftsmanship. "
            f"Masterfully rendered in {material}, this versatile {sil.lower()} balances timeless elegance with effortless everyday utility."
        )

    # 3. Clean up display specs
    clean_specs = []
    def _add_spec(lbl, val):
        if val and str(val).strip() and str(val).strip().lower() not in ("none", "n/a", "unknown", "null"):
            clean_specs.append((lbl, str(val).strip()))
            
    _add_spec("Brand", vendor)
    _add_spec("Silhouette", sil)
    _add_spec("Material", material)
    _add_spec("Lining", lining)
    _add_spec("Hardware Finish", hardware)
    _add_spec("Closure", closure)
    _add_spec("Carrying Method", carrying)
    _add_spec("Organization", pockets)
    _add_spec("Device & Phone Fit", capacity)

    spec_rows = []
    for lbl, val in clean_specs:
        spec_rows.append(
            f'<tr style="border-bottom: 1px solid #f0f0f0;">'
            f'<td style="padding: 8px 12px; font-weight: 600; width: 38%; color: #4b5563;">{lbl}</td>'
            f'<td style="padding: 8px 12px; color: #111827;">{val}</td>'
            f'</tr>'
        )
    spec_table_html = "\n".join(spec_rows)

    # 4. Accordion measurement rows (strictly omit N/A)
    dim_rows = []
    def _add_dim(lbl, val):
        if val and str(val).strip() and str(val).strip().lower() not in ("none", "n/a", "unknown", "null"):
            dim_rows.append(
                f'<tr style="border-bottom: 1px solid #f3f4f6;">'
                f'<td style="padding: 6px 10px; font-weight: 600; width: 45%; color: #374151;">{lbl}</td>'
                f'<td style="padding: 6px 10px; color: #111827;">{str(val).strip()}</td>'
                f'</tr>'
            )
            
    _add_dim("Exterior Dimensions", dims)
    _add_dim("Handle Drop", handle_drop)
    _add_dim("Shoulder / Crossbody Strap Drop", strap_drop)
    _add_dim("Capacity Profile", capacity)

    dim_table_html = "\n".join(dim_rows) if dim_rows else (
        '<tr><td style="padding: 6px 10px; color: #6b7280;" colspan="2">Standard luxury sizing profile. Accommodates daily essentials.</td></tr>'
    )

    return f'''<div class="luxury-bag-overview" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a;">
  <p class="product-summary" style="font-size: 14px; line-height: 1.6; color: #374151; margin-bottom: 20px;">{summary_text}</p>

  <div class="bag-highlights" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px;">
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Silhouette</div>
      <div style="font-size: 13px; font-weight: 600; color: #111827; margin-top: 2px;">{sil}</div>
    </div>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Material</div>
      <div style="font-size: 13px; font-weight: 600; color: #111827; margin-top: 2px;">{material[:28]}</div>
    </div>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Hardware</div>
      <div style="font-size: 13px; font-weight: 600; color: #111827; margin-top: 2px;">{hardware[:28] if hardware else 'Luxury Custom'}</div>
    </div>
  </div>

  <div class="bag-specifications" style="margin-top: 24px;">
    <h3 style="font-size: 15px; font-weight: 700; color: #111827; margin-bottom: 12px; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;">Product Specifications</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.5;">
      <tbody>
{spec_table_html}
      </tbody>
    </table>
  </div>

  <details class="size-guide-accordion" style="margin: 24px 0 16px; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;">
    <summary style="font-weight: 600; cursor: pointer; font-size: 14px; color: #111827;">📏 Bag Dimensions &amp; Fit Guide</summary>
    <div style="margin-top: 12px;">
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <tbody>
{dim_table_html}
        </tbody>
      </table>
    </div>
  </details>

  <div class="authenticity-guarantee" style="margin-top: 16px; padding: 12px 16px; background: #fdfbf7; border: 1px solid #f3ebd8; border-radius: 8px; font-size: 12px; color: #785e28;">
    <strong>The Rare Avenue Authenticity Guarantee:</strong> 100% genuine luxury designer piece sourced directly from authentic manufacturer collections, accompanied by original documentation and verified authenticity guarantee.
  </div>
</div>'''

catalog = get_luxury_bag_products()
for brand in ["coach", "jwpei", "michaelkors"]:
    sample = catalog[brand][0]
    html = format_luxury_bag_description_html(sample)
    print(f"=== {brand.upper()} SAMPLE RENDER ===")
    print("Title:", sample.get("title"))
    print(html[:600])
    print("...\n")
