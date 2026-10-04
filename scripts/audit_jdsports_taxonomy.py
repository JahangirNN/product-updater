import os
import sys
import glob
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.shopify_taxonomy import resolve_gender, generate_taxonomy_tags, resolve_product_type, resolve_authentic_vendor

files = glob.glob("storage/db/jdsports/products/*.json")
gender_counts = {}
kids_leaks_in_men = 0
kids_leaks_in_women = 0
men_leaks_in_women = 0
women_leaks_in_men = 0

forbidden_for_kids = {"men", "mens", "men's", "women", "womens", "women's", "ladies"}
forbidden_for_men = {"women", "womens", "women's", "ladies", "kids", "kids'", "youth"}
forbidden_for_women = {"men", "mens", "men's", "kids", "kids'", "youth"}

for f in files:
    with open(f, "r", encoding="utf-8") as fp:
        d = json.load(fp)
    g = resolve_gender(d)
    gender_counts[g] = gender_counts.get(g, 0) + 1
    v = resolve_authentic_vendor(d)
    pt = resolve_product_type(d)
    tags = [t.lower() for t in generate_taxonomy_tags(d, v, pt, g)]

    if g == "Kids":
        if any(t in forbidden_for_kids for t in tags):
            kids_leaks_in_men += 1
    elif g == "Men":
        if any(t in forbidden_for_men for t in tags):
            men_leaks_in_women += 1
    elif g == "Women":
        if any(t in forbidden_for_women for t in tags):
            women_leaks_in_men += 1

print("--- Taxonomy Audit on JD Sports (476 products) ---")
print(f"Genders: {gender_counts}")
print(f"Kids leaking into Men/Women tags: {kids_leaks_in_men}")
print(f"Men leaking into Women/Kids tags: {men_leaks_in_women}")
print(f"Women leaking into Men/Kids tags: {women_leaks_in_men}")
