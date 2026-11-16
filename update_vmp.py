import os

p = r"C:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\snippets\variant-main-picker.liquid"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Update radio button loop to resolve matched_var and attach live price attributes
target_input_block = """            {%- for product_option_value in product_option.values -%}
              {% if product_option_value.size > longest_value and option_id_attribute %}
                {% assign longest_value = product_option_value.size %}
              {% endif %}
              <label
                class="variant-option__button-label{% if variant_style == 'swatch' %} variant-option__button-label--has-swatch{% endif %}"
              >
                <input
                  type="radio"
                  name="{{ product_option.name | escape }}-{{ block.id }}-{{ product_resource.id }}"
                  value="{{ product_option_value | escape }}"
                  aria-label="{{ product_option_value.name | escape }}{% if product_option_value.available == false %} - {{ 'products.product.sold_out' | t }}{% endif %}"
                  {% if product_option_value.available == false %}
                    aria-disabled="true"
                  {% endif %}
                  data-previous-checked="false"
                  data-fieldset-index="{{ fieldset_index }}"
                  data-input-index="{{ forloop.index0 }}"
                  data-input-id="{{ product_option.position }}-{{ forloop.index0 }}"
                  data-option-name="{{ product_option.name | escape }}"
                  data-option-value-id="{{ product_option_value.id }}"
                  data-option-available="{{ product_option_value.available }}"
                  data-connected-product-url="{{ product_option_value.product_url }}"
                  {% if product_option_value.variant.id %}
                    data-variant-id="{{ product_option_value.variant.id }}"
                  {% endif %}
                  {% if product_option_value.selected %}
                    data-current-checked="true"
                    checked
                  {% else %}
                    data-current-checked="false"
                  {% endif %}
                >"""

new_input_block = """            {%- for product_option_value in product_option.values -%}
              {% liquid
                assign matched_var = nil
                for v in product_resource.variants
                  if v[swatch_opt_key] == product_option_value.name or v.options contains product_option_value.name
                    assign matched_var = v
                    if v.available
                      break
                    endif
                  endif
                endfor
                if matched_var == nil
                  assign matched_var = product_option_value.variant
                endif
              %}
              {% if product_option_value.size > longest_value and option_id_attribute %}
                {% assign longest_value = product_option_value.size %}
              {% endif %}
              <label
                class="variant-option__button-label{% if variant_style == 'swatch' %} variant-option__button-label--has-swatch{% endif %}"
              >
                <input
                  type="radio"
                  name="{{ product_option.name | escape }}-{{ block.id }}-{{ product_resource.id }}"
                  value="{{ product_option_value | escape }}"
                  aria-label="{{ product_option_value.name | escape }}{% if product_option_value.available == false %} - {{ 'products.product.sold_out' | t }}{% endif %}"
                  {% if product_option_value.available == false %}
                    aria-disabled="true"
                  {% endif %}
                  data-previous-checked="false"
                  data-fieldset-index="{{ fieldset_index }}"
                  data-input-index="{{ forloop.index0 }}"
                  data-input-id="{{ product_option.position }}-{{ forloop.index0 }}"
                  data-option-name="{{ product_option.name | escape }}"
                  data-option-value-id="{{ product_option_value.id }}"
                  data-option-available="{{ product_option_value.available }}"
                  data-connected-product-url="{{ product_option_value.product_url }}"
                  {% if matched_var %}
                    data-variant-id="{{ matched_var.id }}"
                    data-variant-price="{{ matched_var.price | money_without_trailing_zeros | replace: '.00', '' }}"
                    data-variant-price-raw="{{ matched_var.price }}"
                    data-variant-compare-price="{% if matched_var.compare_at_price > matched_var.price %}{{ matched_var.compare_at_price | money_without_trailing_zeros | replace: '.00', '' }}{% endif %}"
                    data-variant-compare-raw="{{ matched_var.compare_at_price | default: 0 }}"
                  {% elsif product_option_value.variant.id %}
                    data-variant-id="{{ product_option_value.variant.id }}"
                  {% endif %}
                  {% if product_option_value.selected %}
                    data-current-checked="true"
                    checked
                  {% else %}
                    data-current-checked="false"
                  {% endif %}
                >"""

c_norm = c.replace("\r\n", "\n")
target_input_norm = target_input_block.replace("\r\n", "\n")
new_input_norm = new_input_block.replace("\r\n", "\n")

if target_input_norm in c_norm:
    c_norm = c_norm.replace(target_input_norm, new_input_norm, 1)
    print("Replaced radio input block in variant-main-picker.liquid")
else:
    print("Could not find target_input_block in variant-main-picker.liquid")

# 2. Add complete product variants JSON and client-side synchronizer
target_script_block = """      <script type="application/json">
        {{ product_resource.selected_or_first_available_variant | json }}
      </script>"""

new_script_block = """      <script type="application/json" id="LuxuryProductVariantsData-{{ product_resource.id }}">
        [
          {%- for variant in product_resource.variants -%}
            {
              "id": {{ variant.id }},
              "title": {{ variant.title | json }},
              "price": {{ variant.price }},
              "formatted_price": "{{ variant.price | money_without_trailing_zeros | replace: '.00', '' }}",
              "compare_at_price": {{ variant.compare_at_price | default: 0 }},
              "formatted_compare_at_price": "{% if variant.compare_at_price > variant.price %}{{ variant.compare_at_price | money_without_trailing_zeros | replace: '.00', '' }}{% endif %}",
              "available": {{ variant.available | json }},
              "options": {{ variant.options | json }},
              "option1": {{ variant.option1 | json }},
              "option2": {{ variant.option2 | json }},
              "option3": {{ variant.option3 | json }}
            }{%- unless forloop.last -%},{%- endunless -%}
          {%- endfor -%}
        ]
      </script>
      <script type="application/json">
        {{ product_resource.selected_or_first_available_variant | json }}
      </script>"""

target_script_norm = target_script_block.replace("\r\n", "\n")
new_script_norm = new_script_block.replace("\r\n", "\n")

if target_script_norm in c_norm:
    c_norm = c_norm.replace(target_script_norm, new_script_norm, 1)
    print("Added LuxuryProductVariantsData JSON to variant-main-picker.liquid")
else:
    print("Could not find target_script_block in variant-main-picker.liquid")

# 3. Add client-side synchronizer script at bottom of snippet
client_sync_script = """
<script>
  (function() {
    function updatePDPVariantPrice(variant) {
      if (!variant) return;

      // 1. Format prices
      var priceFormatted = variant.formatted_price || ("Rs. " + Math.round(variant.price / 100).toLocaleString('en-IN'));
      var hasCompare = variant.compare_at_price && variant.compare_at_price > variant.price;
      var compareFormatted = hasCompare ? (variant.formatted_compare_at_price || ("Rs. " + Math.round(variant.compare_at_price / 100).toLocaleString('en-IN'))) : '';

      // 2. Update main price container on PDP
      var priceContainers = document.querySelectorAll('product-price [ref="priceContainer"], product-price, .product-price');
      priceContainers.forEach(function(priceContainer) {
        var priceBdi = priceContainer.querySelector('.price bdi, span.price, bdi');
        if (priceBdi) {
          priceBdi.textContent = priceFormatted;
        }
        var compareEl = priceContainer.querySelector('.compare-at-price');
        if (hasCompare) {
          if (!compareEl) {
            compareEl = document.createElement('span');
            compareEl.className = 'price-item__group price-item--regular compare-at-price';
            compareEl.innerHTML = '<span class="visually-hidden">Regular price&nbsp;</span><bdi></bdi>';
            priceContainer.insertBefore(compareEl, priceContainer.firstChild);
          }
          var compareBdi = compareEl.querySelector('bdi') || compareEl;
          compareBdi.textContent = compareFormatted;
          compareEl.style.display = '';
        } else if (compareEl) {
          compareEl.style.display = 'none';
        }
      });

      // 3. Update Savings Badge
      var savingsRow = document.querySelector('.luxury-pdp-savings-row');
      var savingsBadge = document.querySelector('.luxury-pdp-savings-badge');
      if (hasCompare) {
        var savingsAmount = variant.compare_at_price - variant.price;
        var savingsPercent = Math.round((savingsAmount / variant.compare_at_price) * 100);
        var savingsFormatted = "Rs. " + Math.round(savingsAmount / 100).toLocaleString('en-IN');
        if (savingsBadge) {
          savingsBadge.textContent = 'Save ' + savingsPercent + '% (' + savingsFormatted + ' off)';
        }
        if (savingsRow) savingsRow.style.display = 'flex';
      } else if (savingsRow) {
        savingsRow.style.display = 'none';
      }

      // 4. Update Sticky Quick-Buy Bar
      var stickyPrice = document.querySelector('.luxury-sticky-buy-bar__price');
      if (stickyPrice) {
        stickyPrice.textContent = priceFormatted;
      }
      var stickyVariant = document.querySelector('.luxury-sticky-buy-bar__variant');
      if (stickyVariant && variant.title && variant.title !== 'Default Title') {
        stickyVariant.textContent = '· ' + variant.title;
      }

      // 5. Update form variant ID
      var formVariantInputs = document.querySelectorAll('form[action*="/cart/add"] input[name="id"], .buy-buttons input[name="id"]');
      formVariantInputs.forEach(function(inp) {
        inp.value = variant.id;
      });
    }

    function bindVariantPickerListeners() {
      var vp = document.querySelector('variant-picker');
      if (!vp) return;

      var variants = [];
      var dataScript = vp.querySelector('script[id^="LuxuryProductVariantsData-"]') || document.querySelector('script[id^="LuxuryProductVariantsData-"]');
      if (dataScript) {
        try {
          variants = JSON.parse(dataScript.textContent);
        } catch(e) {
          console.warn('Could not parse variants JSON', e);
        }
      }

      vp.addEventListener('change', function(e) {
        var selectedValues = [];
        vp.querySelectorAll('fieldset').forEach(function(fs) {
          var checked = fs.querySelector('input:checked');
          if (checked) selectedValues.push(checked.value.trim());
        });
        vp.querySelectorAll('select').forEach(function(sel) {
          if (sel.value) selectedValues.push(sel.value.trim());
        });

        if (variants.length > 0 && selectedValues.length > 0) {
          var match = variants.find(function(v) {
            return selectedValues.every(function(val) {
              return v.options && v.options.indexOf(val) !== -1;
            });
          });
          if (match) {
            updatePDPVariantPrice(match);
            return;
          }
        }

        var target = e.target;
        if (target && target.dataset && target.dataset.variantPrice) {
          updatePDPVariantPrice({
            id: target.dataset.variantId,
            title: target.value,
            price: parseInt(target.dataset.variantPriceRaw || '0', 10),
            formatted_price: target.dataset.variantPrice,
            compare_at_price: parseInt(target.dataset.variantCompareRaw || '0', 10),
            formatted_compare_at_price: target.dataset.variantComparePrice
          });
        }
      });

      // Hook into Shopify StandardEvents.productSelect for server fetch synchronization
      var closestSection = vp.closest('.shopify-section');
      if (closestSection) {
        closestSection.addEventListener('shopify:events:productSelect', function(ev) {
          if (ev && ev.detail && ev.detail.resource) {
            updatePDPVariantPrice(ev.detail.resource);
          }
        });
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', bindVariantPickerListeners);
    } else {
      bindVariantPickerListeners();
    }
    document.addEventListener('shopify:section:load', bindVariantPickerListeners);
  })();
</script>
"""

c_norm = c_norm + "\n" + client_sync_script

with open(p, "w", encoding="utf-8") as f:
    f.write(c_norm)
print("Updated variant-main-picker.liquid successfully")
