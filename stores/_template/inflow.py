"""
Store Inflow Normalizer: [Store Name]
Pure functions to transform raw Firecrawl output into canonical product format.
No classes, pure functional composition.
"""
from typing import Any, Dict, List, Optional


def parse_product_payload(raw_data: Dict[str, Any], group_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Transform raw Firecrawl markdown/JSON into a standardized canonical product dictionary.
    
    Args:
        raw_data: Dictionary returned by Firecrawl scrape.
        group_name: Optional category/product group override (e.g. 'sports_shoes').
        
    Returns:
        Canonical product dictionary ready for local JSON storage.
    """
    # 1. Basic Identity
    title = clean_title(raw_data.get("title", ""))
    sku = extract_sku(raw_data)
    brand = raw_data.get("brand") or "[Store Name]"
    
    # 2. Pricing & Currency
    price_info = parse_pricing(raw_data)
    
    # 3. Variants (Color, Size, Stock)
    variants = parse_variants(raw_data)
    
    # 4. Media & Galleries
    images = clean_image_urls(raw_data.get("images", []))
    
    # 5. Enrichment Details
    details = parse_product_details(raw_data)
    
    return {
        "source_store": "[store_slug]",
        "product_group": group_name or "general",
        "source_sku": sku,
        "source_url": raw_data.get("url", ""),
        "title": title,
        "brand": brand,
        "current_price": price_info["current_price"],
        "original_price": price_info["original_price"],
        "currency": price_info["currency"],
        "availability": "in_stock" if any(v.get("in_stock") for v in variants) else "out_of_stock",
        "images": images,
        "variants": variants,
        "description": details.get("description", ""),
        "bullet_points": details.get("bullet_points", []),
        "material": details.get("material"),
        "care_instructions": details.get("care_instructions", []),
        "country_of_origin": details.get("country_of_origin"),
        "specifications": details.get("specifications", {}),
    }


def clean_title(title: str) -> str:
    """Sanitize and strip redundant marketing noise from title."""
    return title.strip()


def extract_sku(raw_data: Dict[str, Any]) -> str:
    """Extract model/style code from raw attributes or URL."""
    return str(raw_data.get("sku") or "").strip()


def parse_pricing(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract current price, MSRP, and convert currency if needed."""
    return {
        "current_price": float(raw_data.get("price") or 0.0),
        "original_price": float(raw_data.get("original_price") or 0.0) or None,
        "currency": "INR",
    }


def parse_variants(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse variant options (colors, sizes) and individual availability."""
    return raw_data.get("variants") or []


def clean_image_urls(image_list: List[str]) -> List[str]:
    """Filter out thumbnails and keep high-resolution image URLs."""
    return [img for img in image_list if img.startswith("http")]


def parse_product_details(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract materials, care instructions, origin, and bullet points."""
    return {
        "description": raw_data.get("description", ""),
        "bullet_points": raw_data.get("bullet_points", []),
        "material": raw_data.get("material"),
        "care_instructions": raw_data.get("care_instructions", []),
        "country_of_origin": raw_data.get("country_of_origin"),
        "specifications": raw_data.get("specifications", {}),
    }
