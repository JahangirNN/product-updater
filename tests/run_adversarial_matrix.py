import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.shopify_taxonomy import (
    resolve_luxury_bag_silhouette,
    is_wallet_product,
    generate_taxonomy_tags,
    resolve_authentic_vendor
)

test_titles = [
    # Bags with charms
    ("Hudson Large Tote With Bag Charm", "Totes"),
    ("Gramercy Bag Charm Bucket Bag", "Satchels & Top Handles"),
    ("Staci Flap Crossbody With Bag Charm", "Crossbody & Messenger Bags"),
    ("Margot Suede Shoulder Bag With Floral Charm", "Shoulder Bags"),
    ("Knott Medium Satchel with Charm", "Satchels & Top Handles"),
    ("Chelsea Charm Pouch", "Clutches & Evening Bags"),
    ("Staci Charm Crossbody", "Crossbody & Messenger Bags"),
    ("Tessa Tote Bag With Charm", "Totes"),
    ("Spade Flower Key Charm Crossbody", "Crossbody & Messenger Bags"),
    # Bags with fringe
    ("Margot Fringe Shoulder Bag", "Shoulder Bags"),
    ("Chelsea Fringe Medium Satchel", "Satchels & Top Handles"),
    ("Spade Flower Fringe Tote", "Totes"),
    ("Fringe Crossbody Bag", "Crossbody & Messenger Bags"),
    # Bags with rings
    ("Leather Ring Tote Bag", "Totes"),
    ("O-Ring Flap Crossbody Bag", "Crossbody & Messenger Bags"),
    ("Chelsea Double Ring Shoulder Bag", "Shoulder Bags"),
    ("Ring Handle Satchel", "Satchels & Top Handles"),
    ("Key Ring Crossbody Bag", "Crossbody & Messenger Bags"),
    # Wallets with key ring / keychain
    ("Leather Key Ring Wallet", "Wallets & Small Leather Goods"),
    ("Staci Key Ring Card Case", "Wallets & Small Leather Goods"),
    ("Spade Flower Keychain Wallet", "Wallets & Small Leather Goods"),
    ("Morgan Card Case With Key Ring", "Wallets & Small Leather Goods"),
    # Standalone accessories / charms (should be None)
    ("Spade Flower Metal Bag Charm", None),
    ("Glitter Heart Bag Charm", None),
    ("Heritage Spade Key Charm", None),
    ("Enamel Heart Keychain", None),
    ("Leather Keychain", None),
    ("Spade Flower Ring", None),
    ("Leather Cleaner", None),
    ("Fabric Protector Spray", None)
]

print(f"{'Product Title':<45} | {'Actual Silhouette':<30} | {'Expected':<30} | {'Status'}")
print("-" * 120)

failures = []
for title, expected in test_titles:
    prod = {
        "source_store": "katespade",
        "title": title,
        "product_type": "Handbags" if expected != "Wallets & Small Leather Goods" and expected is not None else ("Wallets" if expected == "Wallets & Small Leather Goods" else "Accessories")
    }
    sil = resolve_luxury_bag_silhouette(prod)
    status = "PASS" if sil == expected else "FAIL"
    if status == "FAIL":
        failures.append((title, expected, sil))
    print(f"{title:<45} | {str(sil):<30} | {str(expected):<30} | {status}")

print("-" * 120)
print(f"Total tested: {len(test_titles)} | Passed: {len(test_titles) - len(failures)} | Failed: {len(failures)}")
