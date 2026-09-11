"""
Store Inflow Normalizer: Michael Kors (Handbags, Wallets, Shoes, Sunglasses, Belts)
Transforms raw Michael Kors scraped data into canonical Shopify product format.
Pure functions only, zero classes (ADR 0004, ADR 0005, ADR 0006).
"""
import re
import html
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from storage.forex import convert_usd_to_inr

WOMEN_SHOE_SIZES = [
    {"us": "5", "uk": "3", "eu": "35.5"},
    {"us": "5.5", "uk": "3.5", "eu": "36"},
    {"us": "6", "uk": "4", "eu": "36.5"},
    {"us": "6.5", "uk": "4.5", "eu": "37"},
    {"us": "7", "uk": "5", "eu": "37.5"},
    {"us": "7.5", "uk": "5.5", "eu": "38.5"},
    {"us": "8", "uk": "6", "eu": "39"},
    {"us": "8.5", "uk": "6.5", "eu": "39.5"},
    {"us": "9", "uk": "7", "eu": "40"},
    {"us": "9.5", "uk": "7.5", "eu": "40.5"},
    {"us": "10", "uk": "8", "eu": "41"},
    {"us": "11", "uk": "9", "eu": "42"},
]

MEN_SHOE_SIZES = [
    {"us": "7", "uk": "6.5", "eu": "40"},
    {"us": "7.5", "uk": "7", "eu": "40.5"},
    {"us": "8", "uk": "7.5", "eu": "41"},
    {"us": "8.5", "uk": "8", "eu": "42"},
    {"us": "9", "uk": "8.5", "eu": "42.5"},
    {"us": "9.5", "uk": "9", "eu": "43"},
    {"us": "10", "uk": "9.5", "eu": "44"},
    {"us": "10.5", "uk": "10", "eu": "44.5"},
    {"us": "11", "uk": "10.5", "eu": "45"},
    {"us": "11.5", "uk": "11", "eu": "45.5"},
    {"us": "12", "uk": "11.5", "eu": "46"},
    {"us": "13", "uk": "12.5", "eu": "47.5"},
]

BELT_SIZES = [
    {"size": "S", "inches": "32\""},
    {"size": "M", "inches": "34\""},
    {"size": "L", "inches": "36\""},
    {"size": "XL", "inches": "38\""},
]


def clean_title(title: str) -> str:
    """Sanitize title and strip marketing noise."""
    t = title.strip()
    t = re.sub(r'^(?:wishlist|buy now|add to bag|new arrival)\s*', '', t, flags=re.IGNORECASE)
    return t.strip()


def resolve_category(title: str, handle: str, fallback_category: str) -> str:
    """Resolve true product category from keywords in title and handle."""
    text = f"{title} {handle}".lower()
    if any(w in text for w in ["sunglasses", "eyewear"]):
        return "Sunglasses"
    if any(w in text for w in ["belt"]):
        return "Belts"
    if any(w in text for w in ["wallet", "card case", "cardholder", "wristlet", "billfold", "coin purse"]):
        return "Wallets"
    if any(w in text for w in ["sneaker", "trainer"]):
        return "Sneakers"
    if any(w in text for w in ["sandal", "slide", "flip flop"]):
        return "Sandals"
    if any(w in text for w in ["flat", "loafer", "moccasin", "ballet"]):
        return "Flats"
    if any(w in text for w in ["boot", "bootie", "shoe", "oxford", "derby", "pump", "heel"]):
        return "Shoes"
    if any(w in text for w in ["bag", "tote", "crossbody", "shoulder", "satchel", "clutch", "pochette", "backpack", "messenger"]):
        return "Handbags"
    return fallback_category


def extract_color_from_title(title: str, default_color: str = "") -> str:
    """Separate color name from product title if suffixed or present."""
    if default_color:
        return default_color.strip()
    match = re.search(r'\bin\s+([A-Z\s/]+)$', title, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip().title()
    return "Standard"


def generate_size_guide_accordion(category: str, gender: str, sku: str) -> str:
    """Generate rich Shopify accordion HTML with size guide table (ADR 0006)."""
    cat_lower = category.lower()
    
    if "shoe" in cat_lower or "sneaker" in cat_lower or "flat" in cat_lower or "sandal" in cat_lower:
        is_women = "women" in gender.lower()
        sizes = WOMEN_SHOE_SIZES if is_women else MEN_SHOE_SIZES
        gender_title = "Women's" if is_women else "Men's"
        
        rows = "".join(
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\">US {s['us']}</td>"
            f"<td style=\"padding: 8px; border: 1px solid #ddd;\">UK {s['uk']}</td>"
            f"<td style=\"padding: 8px; border: 1px solid #ddd;\">EU {s['eu']}</td></tr>"
            for s in sizes
        )
        return (
            f"<details class=\"size-guide-accordion\" style=\"margin-top: 15px; border: 1px solid #eee; padding: 10px; border-radius: 4px;\">\n"
            f"  <summary style=\"font-weight: bold; cursor: pointer;\">Michael Kors {gender_title} Shoe Size Guide</summary>\n"
            f"  <table style=\"width: 100%; border-collapse: collapse; margin-top: 10px; text-align: left; font-size: 14px;\">\n"
            f"    <thead><tr style=\"background: #f8f8f8;\">"
            f"<th style=\"padding: 8px; border: 1px solid #ddd;\">US Size</th>"
            f"<th style=\"padding: 8px; border: 1px solid #ddd;\">UK Size</th>"
            f"<th style=\"padding: 8px; border: 1px solid #ddd;\">EU Size</th></tr></thead>\n"
            f"    <tbody>\n{rows}    </tbody>\n"
            f"  </table>\n"
            f"</details>"
        )
    elif "belt" in cat_lower:
        rows = "".join(
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\">{b['size']}</td>"
            f"<td style=\"padding: 8px; border: 1px solid #ddd;\">{b['inches']}</td></tr>"
            for b in BELT_SIZES
        )
        return (
            f"<details class=\"size-guide-accordion\" style=\"margin-top: 15px; border: 1px solid #eee; padding: 10px; border-radius: 4px;\">\n"
            f"  <summary style=\"font-weight: bold; cursor: pointer;\">Michael Kors Belt Size Guide</summary>\n"
            f"  <table style=\"width: 100%; border-collapse: collapse; margin-top: 10px; text-align: left; font-size: 14px;\">\n"
            f"    <thead><tr style=\"background: #f8f8f8;\">"
            f"<th style=\"padding: 8px; border: 1px solid #ddd;\">Size</th>"
            f"<th style=\"padding: 8px; border: 1px solid #ddd;\">Waist Measurement</th></tr></thead>\n"
            f"    <tbody>\n{rows}    </tbody>\n"
            f"  </table>\n"
            f"</details>"
        )
    else:
        return (
            f"<details class=\"size-guide-accordion\" style=\"margin-top: 15px; border: 1px solid #eee; padding: 10px; border-radius: 4px;\">\n"
            f"  <summary style=\"font-weight: bold; cursor: pointer;\">Product Specifications & Care</summary>\n"
            f"  <div style=\"padding: 10px; font-size: 14px; line-height: 1.6;\">\n"
            f"    <p><strong>Brand:</strong> MICHAEL Michael Kors</p>\n"
            f"    <p><strong>Style #:</strong> {sku}</p>\n"
            f"    <p><strong>Care:</strong> Wipe clean with soft, dry cloth. Store in protective dust bag.</p>\n"
            f"  </div>\n"
            f"</details>"
        )


def build_variants(
    sku: str,
    title: str,
    color_name: str,
    price_inr: int,
    source_price_usd: float,
    category: str,
    gender: str,
    featured_image: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build canonical variants and options array for Shopify compatibility."""
    cat_lower = category.lower()
    
    if "shoe" in cat_lower or "sneaker" in cat_lower or "flat" in cat_lower or "sandal" in cat_lower:
        is_women = "women" in gender.lower()
        size_chart = WOMEN_SHOE_SIZES if is_women else MEN_SHOE_SIZES
        
        variants = []
        option_values = []
        
        for s in size_chart:
            size_title = f"US {s['us']} / UK {s['uk']}"
            option_values.append({"name": size_title})
            variants.append({
                "sku": f"{sku}-{s['us']}",
                "title": f"{size_title} - {color_name}",
                "price": f"{price_inr:.2f}",
                "compare_at_price": None,
                "source_price": source_price_usd,
                "currency": "INR",
                "source_currency": "USD",
                "in_stock": True,
                "image_url": featured_image,
                "option_values": [
                    {"option_name": "Size", "name": size_title},
                    {"option_name": "Color", "name": color_name}
                ],
                "size_us": s["us"],
                "size_uk": s["uk"],
                "size_eu": s["eu"]
            })
            
        options = [
            {"name": "Size", "values": option_values},
            {"name": "Color", "values": [{"name": color_name}]}
        ]
        return variants, options

    elif "belt" in cat_lower:
        variants = []
        option_values = []
        for b in BELT_SIZES:
            size_title = f"{b['size']} ({b['inches']})"
            option_values.append({"name": size_title})
            variants.append({
                "sku": f"{sku}-{b['size']}",
                "title": f"{size_title} - {color_name}",
                "price": f"{price_inr:.2f}",
                "compare_at_price": None,
                "source_price": source_price_usd,
                "currency": "INR",
                "source_currency": "USD",
                "in_stock": True,
                "image_url": featured_image,
                "option_values": [
                    {"option_name": "Size", "name": size_title},
                    {"option_name": "Color", "name": color_name}
                ],
                "size": b["size"]
            })
        options = [
            {"name": "Size", "values": option_values},
            {"name": "Color", "values": [{"name": color_name}]}
        ]
        return variants, options

    else:
        variants = [{
            "sku": sku,
            "title": color_name or "Standard",
            "price": f"{price_inr:.2f}",
            "compare_at_price": None,
            "source_price": source_price_usd,
            "currency": "INR",
            "source_currency": "USD",
            "in_stock": True,
            "image_url": featured_image,
            "option_values": [
                {"option_name": "Color", "name": color_name or "Standard"}
            ]
        }]
        options = [
            {"name": "Color", "values": [{"name": color_name or "Standard"}]}
        ]
        return variants, options


def normalize_canonical_product(
    raw_item: Dict[str, Any],
    forex_rate: float
) -> Dict[str, Any]:
    """Transform raw Michael Kors item into canonical Shopify product dictionary."""
    sku = str(raw_item["sku"]).strip()
    title = clean_title(raw_item.get("title", ""))
    handle = raw_item.get("handle") or title.lower().replace(" ", "-")
    
    # Resolve accurate category from title/handle keywords
    raw_cat = raw_item.get("category", "Handbags")
    category = resolve_category(title, handle, raw_cat)
    gender = raw_item.get("gender", "Women")
    source_price_usd = float(raw_item.get("source_price_usd", 0.0))
    url = raw_item.get("url", "")
    
    price_inr = int(round(convert_usd_to_inr(source_price_usd, forex_rate)))
    
    color_name = extract_color_from_title(title, raw_item.get("color", ""))
    images = raw_item.get("images", [])
    featured_image = images[0] if images else None
    
    variants, options = build_variants(
        sku=sku,
        title=title,
        color_name=color_name,
        price_inr=price_inr,
        source_price_usd=source_price_usd,
        category=category,
        gender=gender,
        featured_image=featured_image
    )
    
    accordion_html = generate_size_guide_accordion(category, gender, sku)
    description_html = f"<p>{html.escape(title)} by Michael Kors. Designed with superior craftsmanship and luxury finishing.</p>\n{accordion_html}"
    
    specifications = {
        "Brand": "MICHAEL Michael Kors",
        "Category": category,
        "Gender": gender,
        "StyleNumber": sku,
        "Color": color_name,
        "SourceCurrency": "USD",
        "TargetCurrency": "INR"
    }
    
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    return {
        "source_store": "michaelkors",
        "source_sku": sku,
        "source_url": url,
        "handle": handle,
        "title": title,
        "vendor": "MICHAEL Michael Kors",
        "product_type": category,
        "gender": gender,
        "current_price": price_inr,
        "source_price": source_price_usd,
        "currency": "INR",
        "source_currency": "USD",
        "availability": "in_stock",
        "is_active": True,
        "featured_image": featured_image,
        "images": images,
        "variants": variants,
        "options": options,
        "description_html": description_html,
        "specifications": specifications,
        "groups": [category.lower(), gender.lower()],
        "last_verified_at": now_iso
    }
