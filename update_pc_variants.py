import os

p = r"C:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\snippets\product-card-variants.liquid"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Update color button
target_btn = """                  <button
                    type="button"
                    class="luxury-card__color-btn{% if forloop.first %} is-active{% endif %}"
                    data-variant-id="{{ variant.id }}"
                    data-img-src="{{ var_img | image_url: width: 600 }}"
                    data-img-srcset="{{ var_img | image_url: width: 400 }} 400w, {{ var_img | image_url: width: 600 }} 600w, {{ var_img | image_url: width: 800 }} 800w"
                    data-variant-url="{{ variant.url | default: product.url }}"
                    title="{{ color_val | escape }}"
                    aria-label="{{ color_val | escape }}"
                  >"""

new_btn = """                  <button
                    type="button"
                    class="luxury-card__color-btn{% if forloop.first %} is-active{% endif %}"
                    data-variant-id="{{ variant.id }}"
                    data-price="{{ variant.price | money_without_trailing_zeros | replace: '.00', '' }}"
                    data-price-raw="{{ variant.price }}"
                    data-compare-at="{% if variant.compare_at_price > variant.price %}{{ variant.compare_at_price | money_without_trailing_zeros | replace: '.00', '' }}{% endif %}"
                    data-compare-at-raw="{{ variant.compare_at_price | default: 0 }}"
                    data-img-src="{{ var_img | image_url: width: 600 }}"
                    data-img-srcset="{{ var_img | image_url: width: 400 }} 400w, {{ var_img | image_url: width: 600 }} 600w, {{ var_img | image_url: width: 800 }} 800w"
                    data-variant-url="{{ variant.url | default: product.url }}"
                    title="{{ color_val | escape }}"
                    aria-label="{{ color_val | escape }}"
                  >"""

# Normalize CRLF
c_norm = c.replace("\r\n", "\n")
target_btn_norm = target_btn.replace("\r\n", "\n")
new_btn_norm = new_btn.replace("\r\n", "\n")

if target_btn_norm in c_norm:
    c_norm = c_norm.replace(target_btn_norm, new_btn_norm, 1)
    print("Replaced color button data attributes")
else:
    print("Could not find target_btn in product-card-variants.liquid")

# 2. Update size pill
target_pill = """                <a
                  href="{{ target_variant.url | default: product.url }}"
                  class="luxury-card__size-pill{% unless size_available %} is-sold-out{% endunless %}"
                  data-variant-id="{{ target_variant.id }}"
                  title="{% if size_available %}{{ display_size }}{% else %}{{ display_size }} (Sold Out){% endif %}"
                  {% unless size_available %}tabindex="-1" aria-disabled="true"{% endunless %}
                >"""

new_pill = """                <a
                  href="{{ target_variant.url | default: product.url }}"
                  class="luxury-card__size-pill{% unless size_available %} is-sold-out{% endunless %}"
                  data-variant-id="{{ target_variant.id }}"
                  data-price="{{ target_variant.price | money_without_trailing_zeros | replace: '.00', '' }}"
                  data-price-raw="{{ target_variant.price }}"
                  data-compare-at="{% if target_variant.compare_at_price > target_variant.price %}{{ target_variant.compare_at_price | money_without_trailing_zeros | replace: '.00', '' }}{% endif %}"
                  data-compare-at-raw="{{ target_variant.compare_at_price | default: 0 }}"
                  title="{% if size_available %}{{ display_size }}{% else %}{{ display_size }} (Sold Out){% endif %}"
                  {% unless size_available %}tabindex="-1" aria-disabled="true"{% endunless %}
                >"""

target_pill_norm = target_pill.replace("\r\n", "\n")
new_pill_norm = new_pill.replace("\r\n", "\n")

if target_pill_norm in c_norm:
    c_norm = c_norm.replace(target_pill_norm, new_pill_norm, 1)
    print("Replaced size pill data attributes")
else:
    print("Could not find target_pill in product-card-variants.liquid")

with open(p, "w", encoding="utf-8") as f:
    f.write(c_norm)
print("Saved product-card-variants.liquid")
