"""
Shopify Declarative Smart Collection Manifest & Provisioner
Defines and provisions luxury department, category, and brand showroom collections
using automated ruleSet filters. Idempotent: queries existing collections by handle
to avoid duplication. Pure functions only, zero classes (ADR 0002, ADR 0020).
"""
import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_auth import execute_shopify_graphql
from storage.logger import log_info, log_success, log_warning, log_error

COLLECTIONS_MANIFEST: List[Dict[str, Any]] = [
    # --- Instant Dispatch & Ready to Ship ---
    {
        "title": "Ready to Ship",
        "handle": "ready-to-ship",
        "descriptionHtml": "<p>In-stock luxury designer pieces ready to ship immediately — authentic, verified, and delivered with express dispatch.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Ready to Ship"},
                {"column": "TAG", "relation": "EQUALS", "condition": "instant-ship"}
            ]
        }
    },

    # --- Master Categories ---
    {
        "title": "Luxury Watches",
        "handle": "luxury-watches",
        "descriptionHtml": "<p>Discover our curated collection of authentic Swiss and Japanese luxury timepieces.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Watches"}
            ]
        }
    },
    {
        "title": "Designer Bags",
        "handle": "designer-bags",
        "descriptionHtml": "<p>Explore our exclusive edit of luxury handbags, shoulder bags, crossbody bags, and totes.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Designer Bags"}
            ]
        }
    },
    {
        "title": "Luxury Bags & Leather Goods",
        "handle": "luxury-bags",
        "descriptionHtml": "<p>Discover our curated collection of luxury handbags, totes, crossbody bags, and finely crafted leather goods from COACH, JW PEI, and Michael Kors.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Luxury Bags"}
            ]
        }
    },
    {
        "title": "Women's Luxury Bags",
        "handle": "womens-bags",
        "descriptionHtml": "<p>Explore our coveted selection of women's designer handbags, statement totes, shoulder bags, and luxury leather accessories.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Luxury Bags"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"}
            ]
        }
    },
    {
        "title": "Crossbody & Messenger Bags",
        "handle": "crossbody-bags",
        "descriptionHtml": "<p>Hands-free luxury: iconic crossbody bags, camera bags, belt bags, and utilitarian messengers.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Crossbody & Messenger Bags"}
            ]
        }
    },
    {
        "title": "Luxury Totes & Carryalls",
        "handle": "totes",
        "descriptionHtml": "<p>Spacious, structured, and versatile luxury totes crafted from premium leathers and signature canvases.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Totes"}
            ]
        }
    },
    {
        "title": "Wallets & Leather Goods",
        "handle": "wallets-leather-goods",
        "descriptionHtml": "<p>Designer wallets, cardholders, wristlets, and small leather goods crafted with impeccable attention to detail.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Wallets & Small Leather Goods"}
            ]
        }
    },
    {
        "title": "Premium Footwear",
        "handle": "premium-footwear",
        "descriptionHtml": "<p>Elevate your footwear with iconic performance runners and designer sneakers.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Premium Footwear"}
            ]
        }
    },
    {
        "title": "Wallets & Accessories",
        "handle": "wallets-accessories",
        "descriptionHtml": "<p>Finely crafted wallets, cardholders, belts, and luxury everyday essentials.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Wallets & Accessories"}
            ]
        }
    },
    {
        "title": "Designer Sunglasses & Eyewear",
        "handle": "designer-eyewear",
        "descriptionHtml": "<p>Discover our curated collection of luxury designer sunglasses and statement eyewear, featuring 100% UV protection and signature craftsmanship.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Sunglasses"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Sunglasses"}
            ]
        }
    },

    # --- Master Gender Department Collections ---
    {
        "title": "Women's Collection",
        "handle": "women",
        "descriptionHtml": "<p>Explore our complete women's luxury edit featuring designer handbags, fine horology, and statement accessories.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women's"}
            ]
        }
    },
    {
        "title": "Men's Collection",
        "handle": "men",
        "descriptionHtml": "<p>Explore our complete men's luxury edit featuring fine horology, designer leather goods, and premium accessories.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Men"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men's"}
            ]
        }
    },

    # --- Gender Sub-Categories ---
    {
        "title": "Men's Watches",
        "handle": "mens-watches",
        "descriptionHtml": "<p>Distinguished timepieces for men, engineered with precision and timeless elegance.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Watches"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men's"}
            ]
        }
    },
    {
        "title": "Women's Watches",
        "handle": "womens-watches",
        "descriptionHtml": "<p>Exquisite timepieces for women blending luxury jewelry craftsmanship with horological precision.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Watches"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women's"}
            ]
        }
    },
    {
        "title": "Women's Handbags",
        "handle": "womens-handbags",
        "descriptionHtml": "<p>Statement handbags, luxury totes, and shoulder bags crafted for discerning women.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Designer Bags"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"}
            ]
        }
    },
    {
        "title": "Men's Bags",
        "handle": "mens-bags",
        "descriptionHtml": "<p>Functional and sophisticated luxury bags, backpacks, and crossbodies for men.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Designer Bags"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men"}
            ]
        }
    },
    {
        "title": "Women's Wallets & Small Leather Goods",
        "handle": "womens-wallets",
        "descriptionHtml": "<p>Coveted designer women's wallets, wristlets, cardholders, and luxury leather accessories from Michael Kors and COACH.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Wallets & Small Leather Goods"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"}
            ]
        }
    },
    {
        "title": "Men's Wallets & Small Leather Goods",
        "handle": "mens-wallets",
        "descriptionHtml": "<p>Distinguished men's leather wallets, slim billfolds, card cases, and MagSafe accessories engineered with precision.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Wallets & Small Leather Goods"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men"}
            ]
        }
    },
    {
        "title": "Men's Shoes",
        "handle": "mens-shoes",
        "descriptionHtml": "<p>Premium sneakers, performance trail runners, and athletic shoes for men.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Premium Footwear"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men"}
            ]
        }
    },
    {
        "title": "Women's Shoes",
        "handle": "womens-shoes",
        "descriptionHtml": "<p>Iconic silhouettes, running shoes, and luxury lifestyle footwear for women.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TAG", "relation": "EQUALS", "condition": "Premium Footwear"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"}
            ]
        }
    },
    {
        "title": "Women's Sunglasses",
        "handle": "womens-sunglasses",
        "descriptionHtml": "<p>Discover our curated collection of luxury women's designer sunglasses and statement frames.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Sunglasses"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Women"}
            ]
        }
    },
    {
        "title": "Men's Sunglasses",
        "handle": "mens-sunglasses",
        "descriptionHtml": "<p>Explore our distinctive edit of luxury men's designer sunglasses engineered for style, precision, and complete UV protection.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Sunglasses"},
                {"column": "TAG", "relation": "EQUALS", "condition": "Men"}
            ]
        }
    },

    # --- Brand Showrooms: Handbags & Accessories ---
    {
        "title": "JW PEI",
        "handle": "jw-pei",
        "descriptionHtml": "<p>Sustainable vegan leather bags celebrated by fashion icons globally.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "JW PEI"}
            ]
        }
    },
    {
        "title": "COACH",
        "handle": "coach",
        "descriptionHtml": "<p>Timeless American leather goods, signature canvas bags, and heritage accessories.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "COACH"}
            ]
        }
    },
    {
        "title": "Michael Kors",
        "handle": "michael-kors",
        "descriptionHtml": "<p>Chic, jet-set luxury handbags, totes, and designer accessories.</p>",
        "ruleSet": {
            "appliedDisjunctively": True,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Michael Kors"},
                {"column": "VENDOR", "relation": "EQUALS", "condition": "MICHAEL Michael Kors"}
            ]
        }
    },

    # --- Brand Showrooms: Footwear ---
    {
        "title": "Salomon",
        "handle": "salomon",
        "descriptionHtml": "<p>Technical trail runners and iconic gorpcore performance sneakers (XT-6, ACS Pro).</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Salomon"}
            ]
        }
    },
    {
        "title": "On Running",
        "handle": "on-running",
        "descriptionHtml": "<p>Swiss-engineered CloudTec cushioning for road running and luxury all-day movement.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "On"}
            ]
        }
    },
    {
        "title": "HOKA",
        "handle": "hoka",
        "descriptionHtml": "<p>Maximalist performance road and trail running shoes built for supreme comfort.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "HOKA"}
            ]
        }
    },
    {
        "title": "Nike",
        "handle": "nike",
        "descriptionHtml": "<p>Authentic Nike icons: Air Force 1, Dunk Low, Air Max, and modern classics.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Nike"}
            ]
        }
    },
    {
        "title": "Jordan",
        "handle": "jordan",
        "descriptionHtml": "<p>Iconic Air Jordan retros, high-top court legends, and premium basketball sneakers.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Jordan"}
            ]
        }
    },
    {
        "title": "adidas",
        "handle": "adidas",
        "descriptionHtml": "<p>Heritage terrace sneakers (Samba, Gazelle, Campus) and modern sportstyle.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "adidas"}
            ]
        }
    },
    {
        "title": "ASICS",
        "handle": "asics",
        "descriptionHtml": "<p>GEL-cushioned technical runners and sought-after retro lifestyle sneakers.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "ASICS"}
            ]
        }
    },

    # --- Brand Showrooms: Watches ---
    {
        "title": "Versace",
        "handle": "versace",
        "descriptionHtml": "<p>Bold Italian luxury watches featuring the iconic Medusa and Greek Key motifs.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Versace"}
            ]
        }
    },
    {
        "title": "Tissot",
        "handle": "tissot",
        "descriptionHtml": "<p>Masterful Swiss horology featuring PRX, Seastar, and Powermatic 80 movements.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Tissot"}
            ]
        }
    },
    {
        "title": "Seiko",
        "handle": "seiko",
        "descriptionHtml": "<p>Renowned Japanese craftsmanship across Prospex, Presage, and 5 Sports lines.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Seiko"}
            ]
        }
    },
    {
        "title": "Citizen",
        "handle": "citizen",
        "descriptionHtml": "<p>Light-powered Eco-Drive technology, Tsuyosa automatics, and Promaster divers.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Citizen"}
            ]
        }
    },
    {
        "title": "Movado",
        "handle": "movado",
        "descriptionHtml": "<p>Minimalist luxury defined by the single Museum Dial dot symbolizing the sun at high noon.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Movado"}
            ]
        }
    },
    {
        "title": "Ferragamo",
        "handle": "ferragamo",
        "descriptionHtml": "<p>Florentine elegance and impeccable Swiss craftsmanship with signature Gancini details.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "VENDOR", "relation": "EQUALS", "condition": "Ferragamo"}
            ]
        }
    },
    {
        "title": "Michael Kors Watches",
        "handle": "michael-kors-watches",
        "descriptionHtml": "<p>Glamorous runway timepieces featuring Lexington, Bradshaw, and Runway designs.</p>",
        "ruleSet": {
            "appliedDisjunctively": False,
            "rules": [
                {"column": "TYPE", "relation": "EQUALS", "condition": "Watches"},
                {"column": "TITLE", "relation": "CONTAINS", "condition": "Michael Kors"}
            ]
        }
    }
]


def fetch_all_store_collections() -> Dict[str, Dict[str, Any]]:
    query = """
    query getAllCollections($cursor: String) {
      collections(first: 100, after: $cursor) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            title
            handle
            productsCount {
              count
            }
          }
        }
      }
    }
    """
    collections_by_handle: Dict[str, Dict[str, Any]] = {}
    cursor = None

    while True:
        data, ext, err = execute_shopify_graphql(query, variables={"cursor": cursor})
        if err or not data:
            log_error(f"Failed to fetch existing collections: {err}")
            break

        c_data = data.get("collections", {})
        edges = c_data.get("edges", [])
        for e in edges:
            node = e.get("node", {})
            h = node.get("handle")
            if h:
                collections_by_handle[h] = node

        page_info = c_data.get("pageInfo", {})
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    return collections_by_handle


def provision_collection(spec: Dict[str, Any], existing_collections: Optional[Dict[str, Dict[str, Any]]] = None) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    handle = spec.get("handle", "")
    if existing_collections and handle in existing_collections:
        return True, existing_collections[handle], "already_exists"

    mutation = """
    mutation createSmartCollection($input: CollectionInput!) {
      collectionCreate(input: $input) {
        collection {
          id
          title
          handle
          productsCount {
            count
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    input_payload = {
        "title": spec["title"],
        "handle": spec["handle"],
        "descriptionHtml": spec.get("descriptionHtml", ""),
        "ruleSet": spec.get("ruleSet")
    }

    data, ext, err = execute_shopify_graphql(mutation, variables={"input": input_payload})
    if err or not data:
        return False, None, f"GraphQL Error: {err}"

    res = data.get("collectionCreate", {})
    u_errors = res.get("userErrors", [])
    if u_errors:
        err_msg = "; ".join(f"{e.get('field')}: {e.get('message')}" for e in u_errors)
        return False, None, f"UserErrors: {err_msg}"

    node = res.get("collection")
    return True, node, "created"


def provision_all_collections() -> Dict[str, Any]:
    log_info("[COLLECTIONS] Fetching existing collections...")
    existing = fetch_all_store_collections()
    log_info(f"[COLLECTIONS] Found {len(existing)} existing collections on Shopify.")

    results = {
        "existing_count": len(existing),
        "created": [],
        "already_present": [],
        "failed": []
    }

    for spec in COLLECTIONS_MANIFEST:
        title = spec["title"]
        handle = spec["handle"]
        success, node, status = provision_collection(spec, existing)
        
        if success:
            if status == "created":
                log_success(f"[COLLECTIONS CREATED] '{title}' (/collections/{handle}) -> {node.get('id')}")
                results["created"].append({"title": title, "handle": handle, "id": node.get("id")})
                existing[handle] = node
            else:
                results["already_present"].append({"title": title, "handle": handle, "id": node.get("id")})
        else:
            log_error(f"[COLLECTIONS FAILED] '{title}': {status}")
            results["failed"].append({"title": title, "handle": handle, "error": status})

    log_info(f"[COLLECTIONS] Finished provisioning. Created: {len(results['created'])}, Existing: {len(results['already_present'])}, Failed: {len(results['failed'])}")
    return results


if __name__ == "__main__":
    provision_all_collections()
