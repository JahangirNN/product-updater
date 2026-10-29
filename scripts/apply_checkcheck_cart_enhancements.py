import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_DIR = os.path.join(BASE_DIR, "horizon_clean_theme")

def apply_product_form_js():
    path = os.path.join(THEME_DIR, "assets", "product-form.js")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_target = """    let fetchPromise;
    if (isCheckCheckSelected) {
      const productTitle = this.dataset.productTitle || document.querySelector('.product-title, h1.product__title, h1')?.textContent?.trim() || '';
      const bundlePayload = {
        items: [
          {
            id: Number(mainVariantId),
            quantity: itemCount,
            properties: {
              '_checkcheck_certified': 'true'
            }
          },
          {
            id: Number(CHECKCHECK_VARIANT_ID),
            quantity: itemCount,
            properties: {
              '_bundled_with': productTitle
            }
          }
        ]
      };
      if (cartItemComponentsSectionIds.length > 0) {
        bundlePayload.sections = cartItemComponentsSectionIds.join(',');
      }"""

    # Normalize newlines for matching
    content_norm = content.replace("\r\n", "\n")
    old_target_norm = old_target.replace("\r\n", "\n")

    if old_target_norm not in content_norm:
        print("[product-form.js] Target not found!")
        return False

    new_replacement = """    let fetchPromise;
    if (isCheckCheckSelected) {
      const productTitle = this.dataset.productTitle || document.querySelector('h1.product-title, .product__title h1, h1')?.textContent?.trim() || 'Selected Item';
      let selectedOptionValues = [];
      const optionInputs = form.querySelectorAll('fieldset input[type="radio"]:checked, select.variant-select option:checked, .variant-picker input[type="radio"]:checked');
      optionInputs.forEach(input => {
        const val = (input.value || input.textContent || '').trim();
        if (val && val !== 'Default Title' && !selectedOptionValues.includes(val)) {
          selectedOptionValues.push(val);
        }
      });
      const certifiedItemTitle = selectedOptionValues.length > 0 ? `${productTitle} (${selectedOptionValues.join(' / ')})` : productTitle;

      const bundlePayload = {
        items: [
          {
            id: Number(mainVariantId),
            quantity: itemCount,
            properties: {
              'Authentication': 'CheckCheck Certified (+₹699)',
              '_checkcheck_parent': 'true'
            }
          },
          {
            id: Number(CHECKCHECK_VARIANT_ID),
            quantity: itemCount,
            properties: {
              'Certified For': certifiedItemTitle,
              '_parent_id': String(mainVariantId)
            }
          }
        ]
      };
      if (cartItemComponentsSectionIds.length > 0) {
        bundlePayload.sections = cartItemComponentsSectionIds.join(',');
      }"""

    content_norm = content_norm.replace(old_target_norm, new_replacement)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("[product-form.js] Updated successfully.")
    return True


def apply_buy_buttons_liquid():
    path = os.path.join(THEME_DIR, "blocks", "buy-buttons.liquid")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")
    
    old_target = """<input type="checkbox" id="checkcheck-addon-checkbox" name="properties[_checkcheck_certified]" value="true" style="margin-top: 3px; accent-color: #10b981; width: 16px; height: 16px; cursor: pointer;">"""
    new_target = """<input type="checkbox" id="checkcheck-addon-checkbox" value="true" style="margin-top: 3px; accent-color: #10b981; width: 16px; height: 16px; cursor: pointer;">"""

    if old_target not in content_norm:
        print("[buy-buttons.liquid] Checkbox name attribute already updated or not found.")
    else:
        content_norm = content_norm.replace(old_target, new_target)
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(content_norm.replace("\n", "\r\n"))
        print("[buy-buttons.liquid] Updated successfully.")
    return True


def apply_cart_summary_liquid():
    path = os.path.join(THEME_DIR, "snippets", "cart-summary.liquid")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")
    old_target = """          const res = await fetch('/cart/add.js', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
              items: [
                {
                  id: 57721101779110,
                  quantity: 1,
                  properties: {
                    '_added_from': 'cart_drawer_upsell'
                  }
                }
              ]
            })
          });"""

    new_replacement = """          const firstProductRow = document.querySelector('.cart-items__table-row');
          let certTargetTitle = 'Order Item';
          if (firstProductRow) {
            const titleEl = firstProductRow.querySelector('.cart-items__title');
            const variantEl = firstProductRow.querySelector('.cart-items__variant dd');
            if (titleEl) {
              certTargetTitle = titleEl.textContent.trim();
              if (variantEl && variantEl.textContent.trim()) {
                certTargetTitle += ' (' + variantEl.textContent.trim() + ')';
              }
            }
          }

          const res = await fetch('/cart/add.js', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
              items: [
                {
                  id: 57721101779110,
                  quantity: 1,
                  properties: {
                    'Certified For': certTargetTitle,
                    '_added_from': 'cart_drawer_upsell'
                  }
                }
              ]
            })
          });"""

    if old_target not in content_norm:
        print("[cart-summary.liquid] Target not found!")
        return False

    content_norm = content_norm.replace(old_target, new_replacement)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("[cart-summary.liquid] Updated successfully.")
    return True


def apply_cart_products_liquid():
    path = os.path.join(THEME_DIR, "snippets", "cart-products.liquid")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")

    # 1. Detect checkcheck item at row loop
    old_row_target = """          <tbody role="rowgroup">
            {% for item in cart.items %}
              <tr
                id="CartItem-{{ item.key }}\""""

    new_row_target = """          <tbody role="rowgroup">
            {% for item in cart.items %}
              {%- liquid
                assign is_checkcheck = false
                if item.variant_id == 57721101779110 or item.product.handle == 'official-checkcheck-certificate-of-authenticity' or item.title contains 'CheckCheck Certificate'
                  assign is_checkcheck = true
                endif
              -%}
              <tr
                id="CartItem-{{ item.key }}\""""

    if old_row_target not in content_norm:
        print("[cart-products.liquid] Row target not found!")
        return False
    content_norm = content_norm.replace(old_row_target, new_row_target, 1)

    # 2. Media thumbnail for CheckCheck
    old_media_target = """                    <a
                      href="{{ item.url }}"
                      class="cart-items__media-container"
                      style="--ratio:{{ ratio }};"
                    >
                      {%- liquid
                        echo item.image | image_url: width: 250 | image_tag: class: 'cart-items__media-image border-style', style: border_override
                      -%}
                    </a>"""

    new_media_target = """                    {% if is_checkcheck %}
                      <div
                        class="cart-items__media-container checkcheck-seal-thumb"
                        style="--ratio: 1; background: #0f1211; border-radius: 8px; border: 1px solid rgba(201, 168, 118, 0.4); display: flex; align-items: center; justify-content: center; padding: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.25);"
                      >
                        <img
                          src="{{ item.image | image_url: width: 250 }}"
                          alt="Official CheckCheck Certificate of Authenticity"
                          class="cart-items__media-image"
                          style="object-fit: contain; width: 100%; height: 100%; border-radius: 4px;"
                          loading="lazy"
                        >
                      </div>
                    {% else %}
                      <a
                        href="{{ item.url }}"
                        class="cart-items__media-container"
                        style="--ratio:{{ ratio }};"
                      >
                        {%- liquid
                          echo item.image | image_url: width: 250 | image_tag: class: 'cart-items__media-image border-style', style: border_override
                        -%}
                      </a>
                    {% endif %}"""

    if old_media_target not in content_norm:
        print("[cart-products.liquid] Media target not found!")
        return False
    content_norm = content_norm.replace(old_media_target, new_media_target, 1)

    # 3. Title row for CheckCheck
    old_title_target = """                    <div class="cart-items__title-row">
                      <a
                        href="{{ item.url }}"
                        class="cart-items__title"
                        {% if item.parent_relationship.parent != null %}
                          aria-label="{{ 'accessibility.nested_product' | t: product_title: item.product.title, parent_title: item.parent_relationship.parent.title | escape }}"
                        {% endif %}
                      >
                        {{- item.product.title -}}
                      </a>
                      {%- render 'cart-disclosure-tooltip',
                        product: item.product,
                        unique_id: cart_disclosure_unique_id,
                        mode: 'trigger'
                      -%}
                    </div>"""

    new_title_target = """                    <div class="cart-items__title-row">
                      {% if is_checkcheck %}
                        <span class="cart-items__title" style="font-weight: 700; color: #111827; letter-spacing: -0.01em;">
                          Official CheckCheck Certificate of Authenticity
                        </span>
                      {% else %}
                        <a
                          href="{{ item.url }}"
                          class="cart-items__title"
                          {% if item.parent_relationship.parent != null %}
                            aria-label="{{ 'accessibility.nested_product' | t: product_title: item.product.title, parent_title: item.parent_relationship.parent.title | escape }}"
                          {% endif %}
                        >
                          {{- item.product.title -}}
                        </a>
                        {%- render 'cart-disclosure-tooltip',
                          product: item.product,
                          unique_id: cart_disclosure_unique_id,
                          mode: 'trigger'
                        -%}
                      {% endif %}
                    </div>
                    {% if is_checkcheck %}
                      <div style="display: flex; align-items: center; gap: 4px; margin-top: 3px;">
                        <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #047857; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 3px; padding: 2px 6px;">
                          <svg width="10" height="10" viewBox="0 0 20 20" fill="none"><path d="M10 2L4 5v5c0 4.5 2.5 8.7 6 10 3.5-1.3 6-5.5 6-10V5l-6-3z" fill="#10b981"/><path d="M7 10l2 2 4-4" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                          Official 3rd-Party Verification
                        </span>
                      </div>
                    {% endif %}"""

    if old_title_target not in content_norm:
        print("[cart-products.liquid] Title target not found!")
        return False
    content_norm = content_norm.replace(old_title_target, new_title_target, 1)

    # 4. Properties rendering
    old_props_target = """                      {%- if has_visible_properties -%}
                        <dl class="cart-items__properties">
                          {%- for property in item.properties -%}
                            {%- assign property_first_char = property.first | slice: 0 -%}
                            {%- if property.last != blank and property_first_char != '_' -%}
                              <div class="cart-items__property">
                                <dt>{{ property.first }}:</dt>
                                <dd>
                                  {%- if property.last contains '/uploads/' -%}
                                    <a href="{{ property.last }}">{{ property.last | split: '/' | last }}</a>
                                  {%- else -%}
                                    {{ property.last }}
                                  {%- endif -%}
                                </dd>
                              </div>
                            {%- endif -%}
                          {%- endfor -%}
                        </dl>
                      {%- endif -%}"""

    new_props_target = """                      {%- if has_visible_properties -%}
                        <dl class="cart-items__properties">
                          {%- for property in item.properties -%}
                            {%- assign property_first_char = property.first | slice: 0 -%}
                            {%- if property.last != blank and property_first_char != '_' -%}
                              {%- if property.first == 'Certified For' -%}
                                <div class="checkcheck-certified-for-box" style="margin-top: 6px; padding: 6px 10px; background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.25); border-left: 3px solid #10b981; border-radius: 4px;">
                                  <div style="font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #047857; margin-bottom: 2px; display: flex; align-items: center; gap: 4px;">
                                    <svg width="11" height="11" viewBox="0 0 20 20" fill="none"><path d="M10 2L4 5v5c0 4.5 2.5 8.7 6 10 3.5-1.3 6-5.5 6-10V5l-6-3z" fill="#10b981"/><path d="M7 10l2 2 4-4" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                    Certified Product:
                                  </div>
                                  <div style="font-size: 0.75rem; font-weight: 600; color: #111827; line-height: 1.35;">
                                    {{ property.last }}
                                  </div>
                                </div>
                              {%- elsif property.first == 'Authentication' -%}
                                <div class="checkcheck-item-authenticated-tag" style="display: inline-flex; align-items: center; gap: 5px; margin-top: 5px; padding: 3px 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 4px;">
                                  <svg width="12" height="12" viewBox="0 0 20 20" fill="none"><path d="M10 2L4 5v5c0 4.5 2.5 8.7 6 10 3.5-1.3 6-5.5 6-10V5l-6-3z" stroke="#10b981" stroke-width="2" fill="rgba(16, 185, 129, 0.15)"/><path d="M7 10l2 2 4-4" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                  <span style="font-size: 0.7rem; font-weight: 600; color: #065f46;">{{ property.last }}</span>
                                </div>
                              {%- else -%}
                                <div class="cart-items__property">
                                  <dt>{{ property.first }}:</dt>
                                  <dd>
                                    {%- if property.last contains '/uploads/' -%}
                                      <a href="{{ property.last }}">{{ property.last | split: '/' | last }}</a>
                                    {%- else -%}
                                      {{ property.last }}
                                    {%- endif -%}
                                  </dd>
                                </div>
                              {%- endif -%}
                            {%- endif -%}
                          {%- endfor -%}
                        </dl>
                      {%- endif -%}"""

    if old_props_target not in content_norm:
        print("[cart-products.liquid] Properties target not found!")
        return False
    content_norm = content_norm.replace(old_props_target, new_props_target, 1)

    # 5. Quantity controls for CheckCheck
    old_qty_target = """                  <div class="cart-items__quantity-controls">
                    {% render 'volume-pricing-info',
                      variant: item.variant,
                      unique_id: item.index,
                      quantity: item.quantity
                    %}

                    {% render 'quantity-selector',
                      product: item.product,
                      variant: item.variant,
                      in_cart_quantity: item.quantity,
                      line_index: item.index,
                      class: 'cart-primary-typography',
                      can_update_quantity: can_update_quantity
                    %}

                    <button
                      class="button cart-items__remove"
                      type="button"
                      aria-label="{{ 'accessibility.remove_item' | t: title: item.title | escape }}"
                      on:click="/onLineItemRemove/{{ item.index | plus: 1 }}"
                      {% assign can_remove = item.instructions.can_remove | default: true, allow_false: true %}
                      {% if can_remove == false %}
                        hidden
                      {% endif %}
                    >
                      {{- 'icon-delete.svg' | inline_asset_content -}}
                      <span class="visually-hidden">{{ 'accessibility.remove' | t }}</span>
                    </button>
                  </div>"""

    new_qty_target = """                  <div class="cart-items__quantity-controls">
                    {% if is_checkcheck %}
                      <span class="checkcheck-quantity-pill" style="display: inline-flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 600; color: #4b5563; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 4px; padding: 4px 10px; min-width: 50px;">
                        Qty: {{ item.quantity }}
                      </span>
                      <button
                        class="button cart-items__remove"
                        type="button"
                        aria-label="{{ 'accessibility.remove_item' | t: title: item.title | escape }}"
                        on:click="/onLineItemRemove/{{ item.index | plus: 1 }}"
                        title="Remove certificate"
                      >
                        {{- 'icon-delete.svg' | inline_asset_content -}}
                        <span class="visually-hidden">{{ 'accessibility.remove' | t }}</span>
                      </button>
                    {% else %}
                      {% render 'volume-pricing-info',
                        variant: item.variant,
                        unique_id: item.index,
                        quantity: item.quantity
                      %}

                      {% render 'quantity-selector',
                        product: item.product,
                        variant: item.variant,
                        in_cart_quantity: item.quantity,
                        line_index: item.index,
                        class: 'cart-primary-typography',
                        can_update_quantity: can_update_quantity
                      %}

                      <button
                        class="button cart-items__remove"
                        type="button"
                        aria-label="{{ 'accessibility.remove_item' | t: title: item.title | escape }}"
                        on:click="/onLineItemRemove/{{ item.index | plus: 1 }}"
                        {% assign can_remove = item.instructions.can_remove | default: true, allow_false: true %}
                        {% if can_remove == false %}
                          hidden
                        {% endif %}
                      >
                        {{- 'icon-delete.svg' | inline_asset_content -}}
                        <span class="visually-hidden">{{ 'accessibility.remove' | t }}</span>
                      </button>
                    {% endif %}
                  </div>"""

    if old_qty_target not in content_norm:
        print("[cart-products.liquid] Quantity target not found!")
        return False
    content_norm = content_norm.replace(old_qty_target, new_qty_target, 1)

    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("[cart-products.liquid] Updated successfully.")
    return True

if __name__ == "__main__":
    ok1 = apply_product_form_js()
    ok2 = apply_buy_buttons_liquid()
    ok3 = apply_cart_summary_liquid()
    ok4 = apply_cart_products_liquid()
    print("All success:", ok1 and ok2 and ok3 and ok4)
