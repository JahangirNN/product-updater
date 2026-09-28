"""
Shopify Universal Taxonomy, Schema Normalizer & Category Classifier
Standardizes all products across all 7 dropship stores into compliant Shopify ProductSetInput payloads.
Enforces:
  1. Zero Retailer Leakage (ADR 0005, ADR 0020)
  2. Whole-Rupee INR Forex Math (ADR 0006)
  3. Multi-Category Sizing & Variant Harmony (ADR 0015, ADR 0016)
  4. Luxury Department & Brand Showroom Taxonomy (ADR 0020)
Pure functions only, zero classes.
"""
import os
import sys
import re
from typing import Dict, Any, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.forex import get_usd_to_inr_rate


def resolve_authentic_vendor(prod: Dict[str, Any]) -> str:
    """
    Resolve authentic luxury brand name, strictly eliminating any supplier retailer leaks.
    """
    store = (prod.get("source_store") or prod.get("store") or "").lower()
    raw_vendor = (prod.get("vendor") or prod.get("brand") or "").strip()
    title = prod.get("title", "")
    specs = prod.get("specifications") or {}
    url = (prod.get("source_url") or "").lower()
    text = f"{raw_vendor} {title} {url}".lower()

    # 1. JW PEI
    if store == "jwpei" or "jw pei" in text or "jwpei" in text:
        return "JW PEI"

    # 2. Coach
    if store == "coach" or "coach" in text:
        return "COACH"

    # 3. Michael Kors
    if store == "michaelkors" or "michael kors" in text or "michael michael kors" in text:
        return "MICHAEL Michael Kors" if "michael michael kors" in raw_vendor.lower() else "Michael Kors"

    # 4. Nordstrom running shoes (Salomon, On, HOKA)
    if store == "nordstrom" or raw_vendor.lower() == "nordstrom":
        if any(w in text for w in ["hoka", "clifton", "bondi", "mach", "arahi", "speedgoat", "tor summit", "transport", "challenger", "solimar", "gaviota", "mafate", "ora recovery", "skyward", "stinson"]):
            return "HOKA"
        if any(w in text for w in ["salomon", "xt-6", "xt-4", "acs pro", "speedcross", "xa pro", "tepiaz", "xt-slate", "xt-whisper", "neuva", "infini"]):
            return "Salomon"
        if any(w in text for w in ["on ", "cloud", "the roger", "roger wildcard", "roger clubhouse"]):
            return "On"
        spec_brand = specs.get("Brand")
        if spec_brand and spec_brand not in ("NORDSTROM", "Nordstrom", "The Rare Avenue"):
            return spec_brand
        return "On"

    # 5. Foot Locker & JD Sports (Nike, adidas, ASICS, Jordan)
    if store in ("footlocker", "jdsports"):
        if any(w in text for w in ["asics", "gel-"]):
            return "ASICS"
        if any(w in text for w in ["adidas", "samba", "gazelle", "campus"]):
            return "adidas"
        if "jordan" in text:
            return "Jordan"
        if "salomon" in text:
            return "Salomon"
        if "hoka" in text:
            return "HOKA"
        return "Nike"

    # 6. Jomashop Luxury Watches
    if store == "jomashop" or prod.get("product_type") == "Watches":
        for b in ["Versace", "Tissot", "Citizen", "Movado", "Seiko", "Ferragamo", "Michael Kors"]:
            if b.lower() in text:
                return b
        if raw_vendor and raw_vendor.lower() not in ("jomashop", "unknown"):
            return raw_vendor
        return "Luxury Timepieces"

    # Default fallback - clean supplier names
    if raw_vendor and raw_vendor.lower() not in ("jomashop", "nordstrom", "footlocker", "finishline", "jdsports", "unknown"):
        return raw_vendor
    return "The Rare Avenue"


def resolve_gender(prod: Dict[str, Any]) -> str:
    """Classify product gender into Men, Women, or Unisex with title-dominant priority."""
    title = str(prod.get("title", "")).strip().lower()
    raw_g = str(prod.get("gender") or (prod.get("specifications") or {}).get("Gender") or "").strip().lower()
    url = str(prod.get("source_url", "")).strip().lower()

    # 1. Product title is the single most authoritative customer-facing indicator
    is_women_title = bool(re.search(r"\b(women|womens|women\'s|ladies|lady)\b", title))
    is_men_title = bool(re.search(r"\b(men|mens|men\'s)\b", title))

    if is_women_title and not is_men_title:
        return "Women"
    if is_men_title and not is_women_title:
        return "Men"
    if re.search(r"\bunisex|gender inclusive\b", title):
        return "Unisex"

    # 2. Check structured attributes / specifications
    if re.search(r"\b(women|womens|women\'s|ladies|lady)\b", raw_g):
        return "Women"
    if re.search(r"\b(men|mens|men\'s)\b", raw_g):
        return "Men"
    if re.search(r"\bunisex|gender inclusive\b", raw_g):
        return "Unisex"

    # 3. Fallback to URL only if title and specs are completely silent
    if re.search(r"\b(women|womens|women\'s|ladies|lady)\b", url):
        return "Women"
    if re.search(r"\b(men|mens|men\'s)\b", url):
        return "Men"
    if re.search(r"\bunisex|gender inclusive\b", url):
        return "Unisex"

    return "Women" if prod.get("source_store") == "jwpei" else "Men"


def resolve_luxury_bag_silhouette(prod: Dict[str, Any]) -> Optional[str]:
    """
    Classify bags into clear luxury silhouettes (ADR 0020, ADR 0023):
    1. Backpacks
    2. Wallets & Small Leather Goods
    3. Totes
    4. Crossbody & Messenger Bags
    5. Shoulder Bags
    6. Clutches & Evening Bags
    7. Satchels & Top Handles
    Returns None if the product is not a bag / leather goods item.
    """
    store = (prod.get("source_store") or prod.get("store") or "").lower()
    raw_pt = str(prod.get("product_type") or "").strip()
    title = str(prod.get("title", "")).strip()
    text = f"{raw_pt} {title}".lower()

    if store == "jomashop" or bool(re.search(r"\bwatches?\b", raw_pt.lower())) or raw_pt in ("Sunglasses", "Shoes", "Sneakers", "Sandals", "Boots", "Flats"):
        return None
    if store == "coach" and raw_pt == "Shoes & Footwear":
        return None
    if store == "michaelkors" and (raw_pt in ("Sandals", "Sneakers", "Sunglasses", "Shoes", "Flats", "Belts", "Boots", "Apparel") or prod.get("source_sku") in ("MK0017", "MK0018")):
        return None
    if store not in ("coach", "jwpei", "michaelkors") and not any(k in text for k in ["bag", "tote", "crossbody", "wallet", "backpack", "clutch", "satchel", "pouch"]):
        return None

    # 1. Backpacks
    if bool(re.search(r"\b(backpacks?|rucksacks?)\b", text)) or (bool(re.search(r"\bpack\b", text)) and "package" not in text):
        return "Backpacks"

    # 2. Wallets & Small Leather Goods
    if any(w in text for w in ["wallet", "billfold", "card case", "cardholder", "coin purse", "money clip", "passcase", "key ring", "lanyard", "passport", "small goods"]):
        return "Wallets & Small Leather Goods"

    # 3. Totes
    if any(w in text for w in ["tote", "carryall", "shopper", "cabas"]):
        return "Totes"

    # 4. Crossbody & Messenger Bags
    if any(w in text for w in ["crossbody", "messenger", "camera bag", "belt bag", "waist pack", "sling", "hip pack", "saddle"]):
        return "Crossbody & Messenger Bags"

    # 5. Shoulder Bags
    if any(w in text for w in ["shoulder", "hobo", "baguette", "swinger", "teri", "flap"]):
        return "Shoulder Bags"

    # 6. Clutches & Evening Bags
    if any(w in text for w in ["clutch", "evening", "minaudière", "minaudiere", "wristlet", "pochette", "pouch", "vanity", "travel kit"]):
        return "Clutches & Evening Bags"

    # 7. Satchels & Top Handles
    if any(w in text for w in ["satchel", "top handle", "top-handle", "barrel", "dome", "bowler", "briefcase", "brief", "rowan", "bucket", "duffle"]):
        return "Satchels & Top Handles"

    if store == "jwpei":
        return "Satchels & Top Handles"
    if "handbag" in text or "bag" in text:
        return "Satchels & Top Handles"
    return "Shoulder Bags"


def resolve_product_type(prod: Dict[str, Any]) -> str:
    """Normalize raw product type into luxury customer-facing taxonomy."""
    store = (prod.get("source_store") or prod.get("store") or "").lower()
    raw_pt = str(prod.get("product_type") or "").strip()
    title = str(prod.get("title", "")).lower()
    text = f"{raw_pt} {title}".lower()

    if store == "jomashop" or (bool(re.search(r"\bwatches?\b", text)) and "watch hunger stop" not in text):
        return "Watches"

    # Check luxury bag silhouette first for bag stores / bag products
    bag_sil = resolve_luxury_bag_silhouette(prod)
    if bag_sil:
        return bag_sil

    # Footwear
    if any(w in text for w in ["shoe", "sneaker", "runner", "trainer", "footwear", "slide", "sandal", "boot", "loafer", "mule"]):
        if any(w in text for w in ["sandal", "slide"]) and "sandalwood" not in text:
            return "Sandals"
        if any(w in text for w in ["boot", "bootie"]):
            return "Boots"
        if any(w in text for w in ["flat", "loafer", "mule"]):
            return "Flats"
        if any(w in text for w in ["sneaker", "trainer", "runner", "athletic"]):
            return "Sneakers"
        return "Shoes"

    # Handbags & Small Goods
    if any(w in text for w in ["wallet", "billfold", "card case", "cardholder", "wristlet"]):
        return "Wallets & Small Leather Goods"
    if "belt" in text and "belt bag" not in text:
        return "Belts"
    if "backpack" in text:
        return "Backpacks"
    if "sunglasses" in text or "eyewear" in text:
        return "Sunglasses"
    if any(w in text for w in ["tote", "carryall", "shopper"]):
        return "Totes"
    if any(w in text for w in ["crossbody", "camera bag"]):
        return "Crossbody & Messenger Bags"
    if any(w in text for w in ["shoulder", "hobo", "swinger", "teri"]):
        return "Shoulder Bags"
    if any(w in text for w in ["satchel", "top handle", "top-handle", "rowan", "bucket"]):
        return "Satchels & Top Handles"
    if any(w in text for w in ["clutch", "evening"]):
        return "Clutches & Evening Bags"
    if any(w in text for w in ["bag", "pouch", "vanity"]):
        return "Satchels & Top Handles"

    if store == "jwpei":
        return "Satchels & Top Handles"
    if raw_pt and not raw_pt.startswith(("JH", "2T", "8T", "4B", "7C", "5S")):
        return raw_pt
    return "Accessories"


def generate_taxonomy_tags(prod: Dict[str, Any], vendor: str, product_type: str, gender: str) -> List[str]:
    """Generate high-precision tags for automated Shopify Smart Collections."""
    tags = list(prod.get("tags") or [])
    
    # Clean out any old retailer supplier tags
    tags = [t for t in tags if not any(leak in t.lower() for leak in ["jomashop", "nordstrom", "footlocker", "finishline", "jdsports"])]

    # 1. Master Category Tags & Silhouettes
    bag_sil = resolve_luxury_bag_silhouette(prod)
    if bag_sil or product_type in ("Totes", "Shoulder Bags", "Crossbody & Messenger Bags", "Satchels & Top Handles", "Clutches & Evening Bags", "Backpacks", "Wallets & Small Leather Goods", "Handbags", "Tote Bags", "Crossbody Bags", "Top Handle Bags", "Wallets"):
        sil = bag_sil or product_type
        tags.extend(["Designer Bags", "Luxury Bags", sil])
        
        # Add silhouette aliases and facet tags
        if sil == "Totes":
            tags.extend(["Tote Bags", "Totes", "Handbags"])
        elif sil == "Shoulder Bags":
            tags.extend(["Shoulder Bags", "Handbags"])
        elif sil == "Crossbody & Messenger Bags":
            tags.extend(["Crossbody Bags", "Messenger Bags", "Crossbody & Messenger Bags", "Handbags"])
        elif sil == "Satchels & Top Handles":
            tags.extend(["Top Handle Bags", "Satchels", "Satchels & Top Handles", "Handbags"])
        elif sil == "Clutches & Evening Bags":
            tags.extend(["Clutches", "Evening Bags", "Clutches & Evening Bags", "Handbags"])
        elif sil == "Backpacks":
            tags.extend(["Backpacks", "Handbags"])
        elif sil == "Wallets & Small Leather Goods":
            tags.extend(["Wallets", "Wallets & Accessories", "Wallets & Small Leather Goods", "Accessories", "Small Leather Goods"])
    elif product_type == "Watches":
        tags.extend(["Watches", "Luxury Watches"])
    elif product_type in ("Shoes", "Sneakers", "Sandals", "Boots", "Flats"):
        tags.extend(["Footwear", "Shoes", "Premium Footwear", product_type])
    elif product_type in ("Wallets", "Belts", "Sunglasses", "Accessories"):
        tags.extend(["Accessories", "Wallets & Accessories", product_type])

    # 2. Gender Department Tags
    if gender == "Men":
        tags = [t for t in tags if not any(g in t.lower() for g in ["women", "ladies", "unisex"])]
        tags.extend(["Men", "Men's", "Gender:Men", "Gender:Men's"])
    elif gender == "Women":
        tags = [t for t in tags if not any(g in t.lower() for g in ["men", "unisex"])]
        tags.extend(["Women", "Women's", "Gender:Women", "Gender:Women's", "Ladies"])
    else:
        tags.extend(["Unisex", "Gender:Unisex", "Men", "Men's", "Women", "Women's"])

    # 3. Brand Showroom Tags
    tags.extend([f"Brand:{vendor}", vendor])
    if vendor == "COACH":
        tags.append("Coach")
    elif vendor in ("Michael Kors", "MICHAEL Michael Kors"):
        tags.extend(["Michael Kors", "MICHAEL Michael Kors"])

    # 4. Sizing Category for Shoes
    sizing_cat = prod.get("sizing_category")
    if sizing_cat:
        tags.append(sizing_cat)

    return sorted(list(set(tags)))


def resolve_options_and_variants(
    prod: Dict[str, Any],
    forex_rate: float,
    source_price: float,
    compare_source: Optional[float]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Format Shopify ProductOptions and ProductVariants with whole-rupee INR math.
    """
    variants_raw = prod.get("variants") or []
    product_type = resolve_product_type(prod)
    source_sku = prod.get("source_sku") or prod.get("id") or ""
    
    # 1. Single or No-Variant fallback (e.g. Bags with One Size)
    if not variants_raw or not isinstance(variants_raw, list) or len(variants_raw) == 0:
        inr_price = float(round(source_price * forex_rate))
        compare_str = None
        if compare_source and float(compare_source) > source_price:
            compare_str = f"{float(round(float(compare_source) * forex_rate)):.2f}"
            
        sku_val = f"RARE-{source_sku}" if not source_sku.startswith("RARE-") else source_sku
        option_name = "Title"
        return (
            [{"name": "Title", "values": [{"name": "Default Title"}]}],
            [{
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": f"{inr_price:.2f}",
                "compareAtPrice": compare_str,
                "sku": sku_val,
                "inventoryPolicy": "DENY"
            }]
        )

    # 2. Detect Option Name
    first_var = variants_raw[0] if isinstance(variants_raw[0], dict) else {}
    first_opt_val = (first_var.get("option_values") or [{}])[0] if isinstance(first_var.get("option_values"), list) and len(first_var.get("option_values")) > 0 else {}
    opt_val_name = first_opt_val.get("option_name")
    
    bag_sil = resolve_luxury_bag_silhouette(prod)
    
    if product_type == "Watches":
        primary_option = "Case Diameter"
    elif product_type in ("Shoes", "Sneakers", "Sandals", "Boots", "Flats"):
        primary_option = "Size"
    elif opt_val_name and opt_val_name.strip() in ("Color", "Colour", "Size", "Style", "Material"):
        primary_option = "Color" if opt_val_name.strip() in ("Color", "Colour") else opt_val_name.strip()
    elif any(v.get("color") for v in variants_raw if isinstance(v, dict)) or any(
        isinstance(v.get("option_values"), list) and any(ov.get("option_name") in ("Color", "Colour") for ov in v.get("option_values", []))
        for v in variants_raw if isinstance(v, dict)
    ):
        primary_option = "Color"
    elif any(v.get("size") for v in variants_raw if isinstance(v, dict)) or any(
        isinstance(v.get("option_values"), list) and any(ov.get("option_name") == "Size" for ov in v.get("option_values", []))
        for v in variants_raw if isinstance(v, dict)
    ):
        primary_option = "Size"
    elif bag_sil:
        primary_option = "Color"
    else:
        primary_option = "Option"

    # Extract distinct option values and deduplicate variants by option value name
    seen_variants: Dict[str, Dict[str, Any]] = {}

    for v in variants_raw:
        if not isinstance(v, dict):
            continue
            
        # Determine size/color value
        val_name = ""
        if v.get("option_values") and isinstance(v["option_values"], list):
            val_name = v["option_values"][0].get("name", "")
        if not val_name:
            val_name = v.get("size") or v.get("title") or v.get("color") or "Default"

        # Trim long strings
        val_name = str(val_name).strip()[:40]
        if not val_name:
            val_name = "Default"
            
        if val_name not in seen_variants:
            seen_variants[val_name] = v
        else:
            # If current variant is in stock and existing is not, prioritize current
            if seen_variants[val_name].get("availability") != "in_stock" and v.get("availability") == "in_stock":
                seen_variants[val_name] = v

    variant_inputs = []
    for val_name, v in seen_variants.items():
        v_source_price = float(v.get("source_price") or source_price)
        v_inr_price = float(round(v_source_price * forex_rate))
        
        v_compare_source = v.get("source_compare_at_price") or compare_source
        v_compare_str = None
        if v_compare_source and float(v_compare_source) > v_source_price:
            v_compare_str = f"{float(round(float(v_compare_source) * forex_rate)):.2f}"

        v_sku = v.get("sku") or source_sku or ""
        if v_sku and not v_sku.startswith("RARE-"):
            v_sku = f"RARE-{v_sku}"

        v_img = v.get("image_url") or v.get("image") or (v.get("images") or [None])[0]
        v_barcode = v.get("barcode") or v.get("upc") or v.get("ean")

        var_dict = {
            "optionValues": [
                {
                    "optionName": primary_option,
                    "name": val_name
                }
            ],
            "price": f"{v_inr_price:.2f}",
            "compareAtPrice": v_compare_str,
            "sku": v_sku,
            "inventoryPolicy": "DENY"
        }
        if v_img and isinstance(v_img, str) and v_img.startswith("http"):
            var_dict["file"] = {
                "originalSource": v_img,
                "contentType": "IMAGE"
            }
        if v_barcode:
            var_dict["barcode"] = str(v_barcode).strip()

        variant_inputs.append(var_dict)

    product_options = [
        {
            "name": primary_option,
            "values": [{"name": opt} for opt in sorted(list(seen_variants.keys()))]
        }
    ]

    return product_options, variant_inputs


def format_luxury_watch_description_html(prod: Dict[str, Any]) -> str:
    """
    Format a world-class luxury watch product description HTML with:
      1. Highlights Grid (Movement, Case Diameter, Water Resistance, Crystal)
      2. Grouped Technical Specifications Table (Zero Retailer Leaks)
      3. Interactive Wrist Sizing Guide Accordion
      4. The Rare Avenue Authenticity & Warranty Guarantee
    """
    specs = prod.get("specifications") or {}
    vendor = resolve_authentic_vendor(prod)
    
    movement = specs.get("Movement") or "Precision Horology"
    case_diam = specs.get("Case Diameter") or specs.get("Case Size") or (prod.get("variants") or [{}])[0].get("size") or "Standard"
    water_res = specs.get("Water Resistance") or "Splash Resistant"
    crystal = specs.get("Crystal") or "Sapphire Crystal"
    
    # Priority ordered specification fields to display
    display_fields = [
        ("Brand", specs.get("Brand") or vendor),
        ("Series / Collection", specs.get("Series") or specs.get("Collection Name")),
        ("Model Reference", specs.get("Model")),
        ("Gender", specs.get("Gender")),
        ("Movement", movement),
        ("Engine / Caliber", specs.get("Engine")),
        ("Power Reserve", specs.get("Power Reserve")),
        ("Case Diameter", case_diam),
        ("Case Thickness", specs.get("Case Thickness")),
        ("Case Material", specs.get("Case Material")),
        ("Case Shape", specs.get("Case Shape")),
        ("Case Back", specs.get("Case Back")),
        ("Dial Color", specs.get("Dial Color")),
        ("Dial Markers", specs.get("Dial Markers")),
        ("Hands", specs.get("Hands")),
        ("Bezel", specs.get("Bezel") or specs.get("Bezel Material")),
        ("Crystal", crystal),
        ("Band Material", specs.get("Band Material")),
        ("Band Type", specs.get("Band Type")),
        ("Band Color", specs.get("Band Color")),
        ("Band Width", specs.get("Band Width")),
        ("Clasp Type", specs.get("Clasp")),
        ("Water Resistance", water_res),
        ("Calendar / Functions", specs.get("Calendar") or specs.get("Functions")),
        ("Origin Label", specs.get("Watch Label")),
        ("Warranty", "2-Year International Luxury Warranty"),
        ("Packaging", "Original Brand Presentation Box & Papers")
    ]
    
    # Build clean table rows
    spec_rows = []
    for label, val in display_fields:
        if val and str(val).strip() and str(val).lower() not in ("none", "n/a", "unknown"):
            # Sanitize any accidental leak
            clean_val = str(val).replace("Jomashop", "The Rare Avenue").replace("jomashop", "The Rare Avenue")
            spec_rows.append(
                f'<tr style="border-bottom: 1px solid #f0f0f0;">'
                f'<td style="padding: 8px 12px; font-weight: 600; width: 38%; color: #4b5563;">{label}</td>'
                f'<td style="padding: 8px 12px; color: #111827;">{clean_val}</td>'
                f'</tr>'
            )
            
    spec_table_html = "\n".join(spec_rows)

    return f'''<div class="luxury-watch-overview" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a1a1a;">
  <div class="watch-highlights" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px;">
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Movement</div>
      <div style="font-size: 14px; font-weight: 600; color: #111827; margin-top: 2px;">{movement}</div>
    </div>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Case Diameter</div>
      <div style="font-size: 14px; font-weight: 600; color: #111827; margin-top: 2px;">{case_diam}</div>
    </div>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Water Resistance</div>
      <div style="font-size: 14px; font-weight: 600; color: #111827; margin-top: 2px;">{water_res}</div>
    </div>
    <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px;">
      <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; font-weight: 600;">Crystal</div>
      <div style="font-size: 14px; font-weight: 600; color: #111827; margin-top: 2px;">{crystal}</div>
    </div>
  </div>

  <div class="watch-specifications" style="margin-top: 24px;">
    <h3 style="font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 12px; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;">Technical Specifications</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.5;">
      <tbody>
{spec_table_html}
      </tbody>
    </table>
  </div>

  <details class="size-guide-accordion" style="margin: 24px 0 16px; padding: 12px 16px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff;">
    <summary style="font-weight: 600; cursor: pointer; font-size: 14px; color: #111827;">📏 Watch Sizing &amp; Case Dimension Guide</summary>
    <div style="margin-top: 12px;">
      <p style="font-size: 12px; color: #6b7280; margin-bottom: 8px;">Standard wrist circumference &amp; case diameter matching guide:</p>
      <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
        <thead>
          <tr style="background-color: #f3f4f6; color: #374151;">
            <th style="padding: 6px 10px; text-align: left;">Case Diameter</th>
            <th style="padding: 6px 10px; text-align: left;">Recommended Wrist Size</th>
            <th style="padding: 6px 10px; text-align: left;">Fit Profile</th>
          </tr>
        </thead>
        <tbody>
          <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 6px 10px; font-weight: 600;">28 mm – 34 mm</td><td style="padding: 6px 10px;">5.0" – 6.0" (12.5 – 15.0 cm)</td><td style="padding: 6px 10px;">Petite / Delicate</td></tr>
          <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 6px 10px; font-weight: 600;">36 mm – 38 mm</td><td style="padding: 6px 10px;">6.0" – 6.75" (15.0 – 17.0 cm)</td><td style="padding: 6px 10px;">Classic / Dress</td></tr>
          <tr style="border-bottom: 1px solid #f3f4f6;"><td style="padding: 6px 10px; font-weight: 600;">40 mm – 42 mm</td><td style="padding: 6px 10px;">6.75" – 7.5" (17.0 – 19.0 cm)</td><td style="padding: 6px 10px;">Contemporary Standard</td></tr>
          <tr><td style="padding: 6px 10px; font-weight: 600;">43 mm – 46 mm</td><td style="padding: 6px 10px;">7.5" – 8.5" (19.0 – 21.5 cm)</td><td style="padding: 6px 10px;">Sport / Bold Diver</td></tr>
        </tbody>
      </table>
    </div>
  </details>

  <div class="authenticity-guarantee" style="margin-top: 16px; padding: 12px 16px; background: #fdfbf7; border: 1px solid #f3ebd8; border-radius: 8px; font-size: 12px; color: #785e28;">
    <strong>The Rare Avenue Authenticity Guarantee:</strong> 100% genuine luxury timepiece supplied in original manufacturer packaging with complete documentation and backed by our comprehensive 2-Year International Luxury Warranty.
  </div>
</div>'''


def format_luxury_bag_description_html(prod: Dict[str, Any]) -> str:
    """
    Format a world-class luxury bag product description HTML with:
      1. Refined editorial overview / product summary
      2. Key Highlights Grid (Silhouette, Material, Hardware Finish)
      3. Grouped Technical Specifications Table (Zero Retailer Leaks, No N/A rows)
      4. Interactive Size, Proportions & Fit Guide Accordion
      5. The Rare Avenue Authenticity & Craftsmanship Guarantee
    """
    vendor = resolve_authentic_vendor(prod)
    title = prod.get("title", "Luxury Bag")
    sil = resolve_luxury_bag_silhouette(prod) or "Designer Handbag"
    specs = prod.get("specifications") or {}
    
    # 1. Extract and sanitize specs
    raw_material = specs.get("Material") or specs.get("Main Material") or specs.get("Major Material") or ""
    if raw_material and raw_material.strip().lower() != title.strip().lower() and not raw_material.strip().lower().startswith("http"):
        material = str(raw_material).strip()
    elif "signature canvas" in title.lower():
        material = "Signature Coated Canvas & Smooth Leather"
    elif "leather" in title.lower():
        material = "Refined Calf Leather"
    elif "suede" in title.lower():
        material = "Premium Suede Leather"
    elif "canvas" in title.lower():
        material = "Durable Luxury Canvas"
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

    # 3. Clean up display specs (strictly omit N/A rows)
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


def prepare_product_set_payload(prod: Dict[str, Any], forex_rate: Optional[float] = None) -> Dict[str, Any]:
    """
    Format any catalog product into a fully compliant Shopify ProductSetInput payload.
    """
    if forex_rate is None:
        forex_rate = get_usd_to_inr_rate()

    title = prod.get("title", "Luxury Item")
    vendor = resolve_authentic_vendor(prod)
    gender = resolve_gender(prod)
    product_type = resolve_product_type(prod)
    handle = prod.get("shopify_handle") or prod.get("handle")
    bag_sil = resolve_luxury_bag_silhouette(prod)
    
    if product_type == "Watches":
        desc_html = format_luxury_watch_description_html(prod)
    elif bag_sil or product_type in ("Totes", "Shoulder Bags", "Crossbody & Messenger Bags", "Satchels & Top Handles", "Clutches & Evening Bags", "Backpacks", "Wallets & Small Leather Goods", "Handbags"):
        desc_html = format_luxury_bag_description_html(prod)
    else:
        desc_html = prod.get("descriptionHtml") or prod.get("description_html") or ""

    # Pricing
    source_price = float(prod.get("source_price") or prod.get("price_current") or 0.0)
    compare_source = prod.get("source_compare_at_price") or prod.get("compare_at_price_source")

    # Tags
    tags = generate_taxonomy_tags(prod, vendor, product_type, gender)

    # Options & Variants
    options, variants = resolve_options_and_variants(prod, forex_rate, source_price, compare_source)

    # Collect all image URLs: ensure all variant images are included so Shopify can link them
    all_img_urls = []
    seen_img_urls = set()

    # 1. Variant specific images first
    for v in variants:
        v_file = v.get("file")
        if v_file and isinstance(v_file, dict):
            v_src = v_file.get("originalSource")
            if v_src and isinstance(v_src, str) and v_src.startswith("http") and v_src not in seen_img_urls:
                all_img_urls.append(v_src)
                seen_img_urls.add(v_src)

    # 2. Product gallery images
    for img_url in prod.get("images", []):
        if img_url and isinstance(img_url, str) and img_url.startswith("http") and img_url not in seen_img_urls:
            all_img_urls.append(img_url)
            seen_img_urls.add(img_url)

    # Media CDN files
    media_files = []
    for img_url in all_img_urls:
        media_files.append({
            "originalSource": img_url,
            "contentType": "IMAGE"
        })

    is_in_stock = (prod.get("availability") == "in_stock")

    payload = {
        "title": title,
        "vendor": vendor,
        "productType": product_type,
        "descriptionHtml": desc_html,
        "tags": tags,
        "status": "ACTIVE" if is_in_stock else "DRAFT",
        "productOptions": options,
        "variants": variants
    }

    if media_files:
        payload["files"] = media_files

    if prod.get("shopify_product_id"):
        payload["id"] = prod["shopify_product_id"]
    elif handle:
        payload["handle"] = handle

    return payload
