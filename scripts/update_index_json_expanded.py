#!/usr/bin/env python3
"""
Updates theme/templates/index.json with the expanded luxury architecture:
15 rhythmically ordered sections featuring over 80 curated collection and product cards:
 1. slideshow (Cinematic Luxury Hero)
 2. scrolling-marquee (Typographic Brand Tape)
 3. marquee-collection-list (12-Card Infinite Horizontal Auto-Scroll Rail)
 4. silhouette-collections (6-Card Silhouette & Form Portal Rail)
 5. category-tiles (3-Card Asymmetric Editorial Media Grid)
 6. featured-collections-1 (5-Tab Curated Handbag & Ready-to-Ship Drops)
 7. department-split (50/50 The Women's Edit vs The Men's Edit)
 8. footwear-collections (4-Tab Performance & Designer Footwear Vanguard)
 9. maison-spotlight (4-Card Editorial Storytelling: COACH, JW PEI, Tissot, On Running)
10. brand-tiles (12-Maison Brand Portal Matrix)
11. featured-collections-2 (5-Tab Horological Vault: Tissot, Seiko, Citizen, Movado, Versace)
12. accessories-grid (4-Card Small Leather Goods & Curated Eyewear)
13. trust-badges (4 Authenticity & Service Guarantee Pillars)
14. newsletter (VIP Private Client Club Trunk Show)
15. brand-story (Maison Heritage & The Vault Manifesto)
"""

import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(PROJECT_ROOT, "theme", "templates", "index.json")

def build_expanded_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)

    secs = existing.get("sections", {})

    # 4. silhouette-collections (collection-list)
    secs["silhouette-collections"] = {
        "type": "collection-list",
        "blocks": {
            "col-1": {
                "type": "collection",
                "settings": {
                    "collection": "designer-bags",
                    "subheading": "Spacious Luxury",
                    "title": "Totes & Carryalls",
                    "button_text": "Explore Totes",
                    "button_link": "shopify://collections/designer-bags",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "col-2": {
                "type": "collection",
                "settings": {
                    "collection": "womens-handbags",
                    "subheading": "Everyday Ease",
                    "title": "Crossbody & Shoulder",
                    "button_text": "Shop Handbags",
                    "button_link": "shopify://collections/womens-handbags",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "col-3": {
                "type": "collection",
                "settings": {
                    "collection": "women",
                    "subheading": "Engineered Movement",
                    "title": "Performance Footwear",
                    "button_text": "Shop Footwear",
                    "button_link": "/collections/women?filter.p.tag=Footwear",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "col-4": {
                "type": "collection",
                "settings": {
                    "collection": "luxury-watches",
                    "subheading": "Horological Icons",
                    "title": "Swiss Automatics",
                    "button_text": "Shop Watches",
                    "button_link": "shopify://collections/luxury-watches",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "col-5": {
                "type": "collection",
                "settings": {
                    "collection": "wallets-leather-goods",
                    "subheading": "Fine Accessories",
                    "title": "Small Leather Goods",
                    "button_text": "Shop Wallets",
                    "button_link": "shopify://collections/wallets-leather-goods",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "col-6": {
                "type": "collection",
                "settings": {
                    "collection": "womens-sunglasses",
                    "subheading": "Designer Optics",
                    "title": "Luxury Eyewear",
                    "button_text": "Shop Eyewear",
                    "button_link": "shopify://collections/womens-sunglasses",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            }
        },
        "block_order": ["col-1", "col-2", "col-3", "col-4", "col-5", "col-6"],
        "settings": {
            "color_scheme": "scheme-1",
            "separate_section_with_border": True,
            "subheading": "Curated Silhouettes",
            "title": "Explore by Category",
            "content": "",
            "collections_per_row_desktop": 5,
            "collections_per_row_mobile": "2",
            "stack_collections": False,
            "stack_collections_mobile": False,
            "show_text_outside": False,
            "space_items": True,
            "image_size": "portrait"
        }
    }

    # 6. featured-collections-1: Update to focus on Handbags & Ready to Ship
    secs["featured-collections-1"]["settings"]["subheading"] = "Curated Designer Drops"
    secs["featured-collections-1"]["settings"]["title"] = "New Arrivals & Iconic Handbags"
    secs["featured-collections-1"]["blocks"] = {
        "collection-1": {
            "type": "collection",
            "settings": {
                "collection": "instant-ship",
                "products_count": 8,
                "title": "READY TO SHIP (24H)",
                "link_url": "shopify://collections/instant-ship",
                "link_text": "View All Ready to Ship"
            }
        },
        "collection-2": {
            "type": "collection",
            "settings": {
                "collection": "designer-bags",
                "products_count": 8,
                "title": "ICONIC HANDBAGS",
                "link_url": "shopify://collections/designer-bags",
                "link_text": "View All Luxury Bags"
            }
        },
        "collection-3": {
            "type": "collection",
            "settings": {
                "collection": "coach",
                "products_count": 8,
                "title": "COACH NEW YORK",
                "link_url": "shopify://collections/coach",
                "link_text": "Explore COACH"
            }
        },
        "collection-4": {
            "type": "collection",
            "settings": {
                "collection": "jw-pei",
                "products_count": 8,
                "title": "JW PEI STATEMENT",
                "link_url": "shopify://collections/jw-pei",
                "link_text": "Explore JW PEI"
            }
        },
        "collection-5": {
            "type": "collection",
            "settings": {
                "collection": "michael-kors",
                "products_count": 8,
                "title": "MICHAEL KORS JET SET",
                "link_url": "shopify://collections/michael-kors",
                "link_text": "Explore Michael Kors"
            }
        }
    }
    secs["featured-collections-1"]["block_order"] = [
        "collection-1",
        "collection-2",
        "collection-3",
        "collection-4",
        "collection-5"
    ]

    # 8. footwear-collections (featured-collections)
    secs["footwear-collections"] = {
        "type": "featured-collections",
        "blocks": {
            "footwear-1": {
                "type": "collection",
                "settings": {
                    "collection": "women",
                    "products_count": 8,
                    "title": "PERFORMANCE RUNNING",
                    "link_url": "/collections/women?filter.p.tag=Footwear",
                    "link_text": "View All Footwear"
                }
            },
            "footwear-2": {
                "type": "collection",
                "settings": {
                    "collection": "coach",
                    "products_count": 8,
                    "title": "COACH SNEAKERS & LOAFERS",
                    "link_url": "shopify://collections/coach",
                    "link_text": "View COACH Shoes"
                }
            },
            "footwear-3": {
                "type": "collection",
                "settings": {
                    "collection": "michael-kors",
                    "products_count": 8,
                    "title": "MICHAEL KORS FOOTWEAR",
                    "link_url": "shopify://collections/michael-kors",
                    "link_text": "View MK Shoes"
                }
            },
            "footwear-4": {
                "type": "collection",
                "settings": {
                    "collection": "instant-ship",
                    "products_count": 8,
                    "title": "READY TO SHIP (24H)",
                    "link_url": "shopify://collections/instant-ship",
                    "link_text": "View Instant Ship"
                }
            }
        },
        "block_order": ["footwear-1", "footwear-2", "footwear-3", "footwear-4"],
        "settings": {
            "color_scheme": "scheme-1",
            "separate_section_with_border": True,
            "hide_product_information": False,
            "stack_products": False,
            "products_per_row_mobile": "2",
            "products_per_row_desktop": 4,
            "horizontal_spacing_factor": 1,
            "vertical_spacing_factor": 1,
            "subheading": "Engineered Motion & Streetwear",
            "title": "Performance & Designer Footwear"
        }
    }

    # 9. maison-spotlight (multi-column)
    secs["maison-spotlight"] = {
        "type": "multi-column",
        "blocks": {
            "maison-1": {
                "type": "image_with_text",
                "settings": {
                    "collection": "coach",
                    "title": "COACH NEW YORK",
                    "heading_tag": "h4",
                    "content": "<p>American leathercraft heritage since 1941. Renowned for glove-tanned leather, iconic brass turnlocks, and archival bag forms.</p>",
                    "link_text": "Explore COACH",
                    "link_url": "shopify://collections/coach"
                }
            },
            "maison-2": {
                "type": "image_with_text",
                "settings": {
                    "collection": "jw-pei",
                    "title": "JW PEI",
                    "heading_tag": "h4",
                    "content": "<p>Sculptural modernism made with certified vegan materials. Minimalist silhouettes adored by international tastemakers.</p>",
                    "link_text": "Explore JW PEI",
                    "link_url": "shopify://collections/jw-pei"
                }
            },
            "maison-3": {
                "type": "image_with_text",
                "settings": {
                    "collection": "tissot",
                    "title": "TISSOT SUISSE",
                    "heading_tag": "h4",
                    "content": "<p>Swiss chronometry rooted in Le Locle since 1853. Precision Powermatic 80 movements and iconic integrated sport silhouettes.</p>",
                    "link_text": "Explore Tissot",
                    "link_url": "shopify://collections/tissot"
                }
            },
            "maison-4": {
                "type": "image_with_text",
                "settings": {
                    "collection": "women",
                    "title": "ON RUNNING",
                    "heading_tag": "h4",
                    "content": "<p>Swiss-engineered zero-gravity running. Patented CloudTec® cushioning and Speedboard® propulsion for supreme motion.</p>",
                    "link_text": "Explore On",
                    "link_url": "/collections/women/on"
                }
            }
        },
        "block_order": ["maison-1", "maison-2", "maison-3", "maison-4"],
        "settings": {
            "color_scheme": "scheme-1",
            "separate_section_with_border": True,
            "subheading": "Maison Spotlight",
            "title": "Craftsmanship & Heritage",
            "columns_per_row": 4,
            "stack_on_mobile": False,
            "content_alignment": "center",
            "spacing": "md"
        }
    }

    # 11. featured-collections-2: The Horological Vault
    secs["featured-collections-2"]["settings"]["subheading"] = "Horological Icons"
    secs["featured-collections-2"]["settings"]["title"] = "The Swiss & Japanese Vault"
    secs["featured-collections-2"]["blocks"] = {
        "watch-1": {
            "type": "collection",
            "settings": {
                "collection": "tissot",
                "products_count": 8,
                "title": "TISSOT SWISS",
                "link_url": "shopify://collections/tissot",
                "link_text": "View Tissot"
            }
        },
        "watch-2": {
            "type": "collection",
            "settings": {
                "collection": "seiko",
                "products_count": 8,
                "title": "SEIKO AUTOMATICS",
                "link_url": "shopify://collections/seiko",
                "link_text": "View Seiko"
            }
        },
        "watch-3": {
            "type": "collection",
            "settings": {
                "collection": "citizen",
                "products_count": 8,
                "title": "CITIZEN ECO-DRIVE",
                "link_url": "shopify://collections/citizen",
                "link_text": "View Citizen"
            }
        },
        "watch-4": {
            "type": "collection",
            "settings": {
                "collection": "movado",
                "products_count": 8,
                "title": "MOVADO MUSEUM",
                "link_url": "shopify://collections/movado",
                "link_text": "View Movado"
            }
        },
        "watch-5": {
            "type": "collection",
            "settings": {
                "collection": "versace",
                "products_count": 8,
                "title": "VERSACE MAISON",
                "link_url": "shopify://collections/versace",
                "link_text": "View Versace"
            }
        }
    }
    secs["featured-collections-2"]["block_order"] = [
        "watch-1",
        "watch-2",
        "watch-3",
        "watch-4",
        "watch-5"
    ]

    # 12. accessories-grid (collection-list)
    secs["accessories-grid"] = {
        "type": "collection-list",
        "blocks": {
            "acc-1": {
                "type": "collection",
                "settings": {
                    "collection": "wallets-leather-goods",
                    "subheading": "Fine Accessories",
                    "title": "Continental & Zip Wallets",
                    "button_text": "Explore Wallets",
                    "button_link": "shopify://collections/wallets-leather-goods",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "acc-2": {
                "type": "collection",
                "settings": {
                    "collection": "wallets-leather-goods",
                    "subheading": "Slim Silhouette",
                    "title": "Card Cases & Wristlets",
                    "button_text": "Explore Card Cases",
                    "button_link": "shopify://collections/wallets-leather-goods",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "acc-3": {
                "type": "collection",
                "settings": {
                    "collection": "womens-sunglasses",
                    "subheading": "Designer Frames",
                    "title": "Women's Sunglasses",
                    "button_text": "Explore Eyewear",
                    "button_link": "shopify://collections/womens-sunglasses",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            },
            "acc-4": {
                "type": "collection",
                "settings": {
                    "collection": "mens-sunglasses",
                    "subheading": "Aviator & Navigator",
                    "title": "Men's Luxury Eyewear",
                    "button_text": "Explore Eyewear",
                    "button_link": "shopify://collections/mens-sunglasses",
                    "button_style": "outline",
                    "overlay_color": "#000000",
                    "overlay_opacity": 30
                }
            }
        },
        "block_order": ["acc-1", "acc-2", "acc-3", "acc-4"],
        "settings": {
            "color_scheme": "scheme-1",
            "separate_section_with_border": True,
            "subheading": "Everyday Accoutrements",
            "title": "Small Leather Goods & Curated Eyewear",
            "content": "",
            "collections_per_row_desktop": 4,
            "collections_per_row_mobile": "2",
            "stack_collections": False,
            "stack_collections_mobile": False,
            "show_text_outside": False,
            "space_items": True,
            "image_size": "portrait"
        }
    }

    new_order = [
        "slideshow",
        "scrolling-marquee",
        "marquee-collection-list",
        "silhouette-collections",
        "category-tiles",
        "featured-collections-1",
        "department-split",
        "footwear-collections",
        "maison-spotlight",
        "brand-tiles",
        "featured-collections-2",
        "accessories-grid",
        "trust-badges",
        "newsletter",
        "brand-story"
    ]

    payload = {
        "sections": secs,
        "order": new_order
    }

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Successfully generated expanded index.json with {len(new_order)} sections and {len(secs)} section keys.")

if __name__ == "__main__":
    build_expanded_index()
