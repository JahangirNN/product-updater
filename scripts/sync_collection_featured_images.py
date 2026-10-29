import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_auth import execute_shopify_graphql

COLLECTION_IMAGES = {
    "coach": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/cek80_svpwh_a0_0019e6a5-86fa-418c-a982-765d1346b62b.jpg?v=1790852580",
        "alt": "COACH Caitlin Shoulder Bag In Signature Canvas"
    },
    "michael-kors": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/30S6SETT2V-198-0239_1-tif_3e551b5b-e8da-4713-be92-afdeabca5d66.jpg?v=1790671872",
        "alt": "Michael Kors Scarlett Medium Textured Tote Bag"
    },
    "jw-pei": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/2T33-46-FRONT_e944b954-bdcc-411a-a243-1c8fb0bc8622.jpg?v=1790757835",
        "alt": "JW PEI Abacus Embroidered Floral Mini Top Handle Bag"
    },
    "tissot": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/tissot-chemin-des-tourelles-automatic-mens-watch-t0994081103800-t0994081103800.jpg?v=1790662044",
        "alt": "Tissot Chemin Des Tourelles Automatic Men's Watch"
    },
    "seiko": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/seiko-chronograph-quartz-blue-dial-mens-watch-ssb377.jpg?v=1791027195",
        "alt": "Seiko Chronograph Quartz Blue Dial Men's Watch"
    },
    "citizen": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/citizen-promaster-skyhawk-u830-analogdigital-mens-watch-jv200655h.jpg?v=1790662045",
        "alt": "Citizen Promaster Skyhawk U830 Analog-Digital Men's Watch"
    },
    "movado": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/movado-series-800-chronograph-blue-dial-mens-watch-2600141.jpg?v=1790662045",
        "alt": "Movado Series 800 Chronograph Blue Dial Men's Watch"
    },
    "versace": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/versace-hellenyium-automatic-black-dial-mens-watch-veqca0624.jpg?v=1790662043",
        "alt": "Versace Hellenyium Automatic Black Dial Men's Watch"
    },
    "on-running": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/2235e51c-7086-40ac-9117-b7e1ba819544.jpg?v=1791091884",
        "alt": "On Running Cloudpulse Next Athletic Sneaker"
    },
    "hoka": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/97895463-5c61-4f78-9c7a-7ab9d57ab505_b9e67aee-2b90-4f23-86ff-bbbc8f921785.jpg?v=1791171218",
        "alt": "HOKA Mach 7 Running Shoe"
    },
    "salomon": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/1391d60a-6d03-4f36-89ca-7db6780cbfc8_1796a7b8-75f7-448c-8a4c-c6ea68df2635.jpg?v=1791171199",
        "alt": "Salomon XA Pro 3D Sneaker"
    },
    "wallets-leather-goods": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/cx161_imxaq_a0_bd879fb3-43de-4dde-9b07-d712696081d5.jpg?v=1790852586",
        "alt": "Double Zip Wallet In Signature Canvas"
    },
    "womens-sunglasses": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/MK-1178-2717-2717_1-tif.jpg?v=1790661827",
        "alt": "Sea Island Luxury Sunglasses"
    },
    "mens-sunglasses": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/MK-9046-0020-0001_1-tif_a541d1a9-7998-493b-866f-f93fbd42b2e3.jpg?v=1790661828",
        "alt": "Avenue Men's Sunglasses"
    },
    "totes": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/30T6G51T9B-251-0201_1-tif.jpg?v=1790661818",
        "alt": "Henly Large Signature Logo and Textured Tote"
    },
    "crossbody-bags": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/32F6GJ6C5L-230-0230_1-tif_5a4b18d0-d6f7-4580-9e64-a50fa8164daf.jpg?v=1790661828",
        "alt": "Jet Set Small Pebbled Leather Smartphone Crossbody"
    },
    "designer-bags": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/cek80_svpwh_a0_0019e6a5-86fa-418c-a982-765d1346b62b.jpg?v=1790852580",
        "alt": "Caitlin Shoulder Bag In Signature Canvas"
    },
    "premium-footwear": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/IQ0292_060_P1.jpg?v=1791105407",
        "alt": "Nike Air Force 1 '07 LV8 Casual Shoes"
    },
    "luxury-watches": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/tissot-chemin-des-tourelles-automatic-mens-watch-t0994081103800-t0994081103800.jpg?v=1790662044",
        "alt": "Tissot Chemin Des Tourelles Swiss Automatic"
    },
    "ready-to-ship": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/IQ0292_060_P1.jpg?v=1791105407",
        "alt": "Ready to Ship Collection"
    },
    "instant-ship": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/IQ0292_060_P1.jpg?v=1791105407",
        "alt": "Instant Ship Collection"
    },
    "womens-handbags": {
        "url": "https://cdn.shopify.com/s/files/1/0759/1457/6038/files/cek80_svpwh_a0_0019e6a5-86fa-418c-a982-765d1346b62b.jpg?v=1790852580",
        "alt": "Women's Designer Handbags"
    }
}

update_mutation = """
mutation UpdateCollectionImage($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection {
      id
      handle
      image {
        url
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

get_col_query = """
query GetCol($handle: String!) {
  collectionByHandle(handle: $handle) {
    id
    handle
  }
}
"""

for handle, meta in COLLECTION_IMAGES.items():
    res, _, err = execute_shopify_graphql(get_col_query, {"handle": handle})
    col = res.get("collectionByHandle") if res else None
    if not col:
        print(f"Skipping {handle}: not found")
        continue
    cid = col["id"]
    variables = {
        "input": {
            "id": cid,
            "image": {
                "src": meta["url"],
                "altText": meta["alt"]
            }
        }
    }
    up_res, _, up_err = execute_shopify_graphql(update_mutation, variables)
    errs = up_res.get("data", {}).get("collectionUpdate", {}).get("userErrors", []) if up_res else []
    if errs:
        print(f"Failed {handle}: {errs}")
    else:
        print(f"SUCCESS {handle}: updated image")
