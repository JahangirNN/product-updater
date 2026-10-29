import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_DIR = os.path.join(BASE_DIR, "horizon_clean_theme")

def update_cart_summary():
    path = os.path.join(THEME_DIR, "snippets", "cart-summary.liquid")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")

    start_tag = "{%- liquid\n    assign has_checkcheck_in_cart = false"
    start_idx = content_norm.find(start_tag)
    if start_idx == -1:
        start_tag = "{%- liquid"
        # find where has_checkcheck_in_cart is
        pos = content_norm.find("has_checkcheck_in_cart")
        if pos != -1:
            start_idx = content_norm.rfind("{%- liquid", 0, pos)

    if start_idx != -1:
        end_tag = "{%- endunless -%}"
        end_idx = content_norm.find(end_tag, start_idx)
        if end_idx != -1:
            full_block = content_norm[start_idx : end_idx + len(end_tag)]
            content_norm = content_norm.replace(full_block, "").strip()
            content_norm = content_norm.replace('<div class="cart__ctas">\n\n  <button', '<div class="cart__ctas">\n  <button')
            with open(path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(content_norm.replace("\n", "\r\n"))
            print("[cart-summary.liquid] Bottom upsell box removed successfully.")
            return True

    print("[cart-summary.liquid] Block not found or already removed.")
    return True

def update_cart_products():
    path = os.path.join(THEME_DIR, "snippets", "cart-products.liquid")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_norm = content.replace("\r\n", "\n")

    # Step 1: Physical items count and empty cart
    old_empty = "  {% if cart.empty? or force_empty %}"
    new_empty = """  {% liquid
    assign physical_items_count = 0
    assign cert_items_count = 0
    for item in cart.items
      if item.variant_id == 57721101779110 or item.product.handle == 'official-checkcheck-certificate-of-authenticity' or item.title contains 'CheckCheck Certificate'
        assign cert_items_count = cert_items_count | plus: item.quantity
      else
        assign physical_items_count = physical_items_count | plus: item.quantity
      endif
    endfor
  %}
  {% if cart.empty? or force_empty or physical_items_count == 0 %}
    {% if cert_items_count > 0 and physical_items_count == 0 %}
      <script>
        (function(){ fetch('/cart/clear.js', { method: 'POST' }).then(() => { if (typeof reloadCartSections === 'function') reloadCartSections(); else window.location.reload(); }); })();
      </script>
    {% endif %}"""

    if old_empty not in content_norm:
        print("[cart-products.liquid] old_empty not found!")
        return False
    content_norm = content_norm.replace(old_empty, new_empty, 1)

    # Step 2: Update cart count span
    cart_count_pos = content_norm.find('ref="cartItemCount"')
    if cart_count_pos != -1:
        open_span = content_norm.rfind("<span", 0, cart_count_pos)
        close_span = content_norm.find("</span>", cart_count_pos) + len("</span>")
        old_span = content_norm[open_span:close_span]
        new_span = """<span
      class="visually-hidden"
      ref="cartItemCount"
      aria-hidden="true"
    >
      {{- physical_items_count -}}
    </span>"""
        content_norm = content_norm.replace(old_span, new_span, 1)
        print("[cart-products.liquid] Replaced cartItemCount span.")
    else:
        print("[cart-products.liquid] ref=cartItemCount not found!")
        return False

    # Step 3: Loop start (skip checkcheck standalone rows, find attached cert)
    loop_start_tag = '{% for item in cart.items %}'
    loop_start_idx = content_norm.find(loop_start_tag)
    row_tag_idx = content_norm.find('<tr\n                id="CartItem-{{ item.key }}"', loop_start_idx)
    if loop_start_idx != -1 and row_tag_idx != -1:
        old_loop_block = content_norm[loop_start_idx : row_tag_idx]
        new_loop_block = """{% for item in cart.items %}
              {%- liquid
                assign is_checkcheck = false
                if item.variant_id == 57721101779110 or item.product.handle == 'official-checkcheck-certificate-of-authenticity' or item.title contains 'CheckCheck Certificate'
                  assign is_checkcheck = true
                endif
              -%}
              {% if is_checkcheck %}
                {% continue %}
              {% endif %}
              {%- liquid
                assign attached_cert = null
                for other_item in cart.items
                  if other_item.variant_id == 57721101779110 or other_item.product.handle == 'official-checkcheck-certificate-of-authenticity' or other_item.title contains 'CheckCheck Certificate'
                    assign parent_id = other_item.properties['_parent_id'] | default: ''
                    assign cert_for = other_item.properties['Certified For'] | default: ''
                    assign cur_variant_id = item.variant_id | append: ''
                    if parent_id == cur_variant_id or cert_for contains item.product.title
                      assign attached_cert = other_item
                      break
                    endif
                  endif
                endfor
              -%}
              """
        content_norm = content_norm.replace(old_loop_block, new_loop_block, 1)
        print("[cart-products.liquid] Replaced loop header.")
    else:
        print("[cart-products.liquid] loop header not found!")
        return False

    # Add data-attached-cert-key to row tag
    old_row_tag = """data-key="{{ item.key }}"
              >"""
    new_row_tag = """data-key="{{ item.key }}"
                data-variant-id="{{ item.variant_id }}"
                {% if attached_cert != null %}
                  data-attached-cert-key="{{ attached_cert.key }}"
                {% endif %}
              >"""
    if old_row_tag in content_norm:
        content_norm = content_norm.replace(old_row_tag, new_row_tag, 1)
        print("[cart-products.liquid] Added data-attached-cert-key to tr.")

    # Step 4: Clean up media container
    media_start = content_norm.find('<td\n                  class="cart-items__media"')
    media_end = content_norm.find('</td>', media_start)
    old_media_block = content_norm[media_start:media_end]
    if "is_checkcheck" in old_media_block:
        # replace checkcheck conditional in media
        check_start = old_media_block.find('{% if is_checkcheck %}')
        check_else = old_media_block.find('{% else %}', check_start)
        check_endif = old_media_block.find('{% endif %}', check_else)
        normal_a = old_media_block[check_else + len('{% else %}'):check_endif].strip()
        new_media_block = old_media_block[:check_start] + normal_a + old_media_block[check_endif + len('{% endif %}'):]
        content_norm = content_norm.replace(old_media_block, new_media_block, 1)
        print("[cart-products.liquid] Cleaned up media block.")

    # Step 5: Clean up title row
    title_start = content_norm.find('<div class="cart-items__title-row">')
    title_end = content_norm.find('</div>', title_start)
    # The title block has is_checkcheck
    if title_start != -1:
        next_block = content_norm[title_start : title_start + 800]
        if "is_checkcheck" in next_block:
            # Let's cleanly replace the entire cart-items__product-info up to vendor
            info_start = content_norm.find('<div class="cart-items__product-info">')
            vendor_pos = content_norm.find('{% if item.product.vendor and block_settings.vendor %}', info_start)
            clean_product_info = """<div class="cart-items__product-info">
                    {%- liquid
                      assign cart_disclosure_unique_id = 'page-' | append: item.index
                      if context == 'drawer'
                        assign cart_disclosure_unique_id = 'drawer-' | append: item.index
                      endif
                    -%}
                    <div class="cart-items__title-row">
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
                    </div>
                    """
            content_norm = content_norm[:info_start] + clean_product_info + content_norm[vendor_pos:]
            print("[cart-products.liquid] Cleaned up title row.")

    # Step 6: Inject attached certificate inside cart-items__variants-wrapper
    var_wrapper_pos = content_norm.find('<div class="cart-items__variants-wrapper">')
    if var_wrapper_pos != -1:
        # Find the options loop end: {% endif %}\n                      {%- endif -%}
        # Find closing tag of options block
        opt_end_tag = "{%- endif -%}\n\n                      {%- liquid\n                        assign has_visible_properties"
        opt_end_idx = content_norm.find(opt_end_tag, var_wrapper_pos)
        if opt_end_idx == -1:
            opt_end_tag = "{%- endif -%}\n                      {%- liquid\n                        assign has_visible_properties"
            opt_end_idx = content_norm.find(opt_end_tag, var_wrapper_pos)

        if opt_end_idx != -1:
            cert_ui_snippet = """
                      {%- if attached_cert != null -%}
                        <div class="ra-attached-cert-box" style="margin: 0.45rem 0 0.35rem 0; padding: 0.45rem 0.65rem; background: #faf9f6; border: 1px solid rgba(16, 185, 129, 0.35); border-left: 3px solid #10b981; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;">
                          <div style="display: flex; align-items: center; gap: 0.45rem; min-width: 0;">
                            <svg width="14" height="14" viewBox="0 0 20 20" fill="none" style="flex-shrink: 0;"><path d="M10 2L4 5v5c0 4.5 2.5 8.7 6 10 3.5-1.3 6-5.5 6-10V5l-6-3z" fill="#10b981"/><path d="M7 10l2 2 4-4" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                            <div style="min-width: 0; line-height: 1.25;">
                              <div style="font-size: 0.72rem; font-weight: 700; color: #111827; letter-spacing: -0.01em;">
                                CheckCheck® Certificate <span style="color: #059669; font-weight: 600;">(+₹699{% if attached_cert.quantity > 1 %} × {{ attached_cert.quantity }}{% endif %})</span>
                              </div>
                              <div style="font-size: 0.625rem; color: #6b7280;">Physical Serialized Tag &amp; Digital COA</div>
                            </div>
                          </div>
                          <button type="button" class="ra-remove-cert-btn" onclick="removeAttachedCert('{{ attached_cert.key }}', '{{ item.key }}')" style="background: none; border: none; padding: 2px 4px; font-size: 0.6875rem; color: #9ca3af; cursor: pointer; text-decoration: underline;" title="Remove certificate from this product">
                            Remove
                          </button>
                        </div>
                      {%- else -%}
                        <div class="ra-add-cert-prompt" style="margin: 0.35rem 0 0.25rem 0;">
                          <button type="button" class="ra-add-cert-btn" onclick="addCertToProduct('{{ item.variant_id }}', '{{ item.product.title | escape }}', {{ item.quantity }})" style="display: inline-flex; align-items: center; gap: 4px; background: none; border: 1px dashed rgba(16, 185, 129, 0.45); border-radius: 4px; padding: 3px 7px; font-size: 0.6875rem; font-weight: 600; color: #047857; cursor: pointer; transition: all 0.2s ease;">
                            <svg width="11" height="11" viewBox="0 0 20 20" fill="none"><path d="M10 2L4 5v5c0 4.5 2.5 8.7 6 10 3.5-1.3 6-5.5 6-10V5l-6-3z" stroke="#10b981" stroke-width="2" fill="rgba(16,185,129,0.15)"/><path d="M10 7v6m-3-3h6" stroke="#10b981" stroke-width="2" stroke-linecap="round"/></svg>
                            <span>+ Add CheckCheck Certificate (+₹699)</span>
                          </button>
                        </div>
                      {%- endif -%}
"""
            insert_pos = opt_end_idx + len("{%- endif -%}")
            content_norm = content_norm[:insert_pos] + cert_ui_snippet + content_norm[insert_pos:]
            print("[cart-products.liquid] Inserted attached cert UI inside variants wrapper.")

    # Step 7: Clean up properties rendering so Authentication and Certified For don't show as text
    # In properties dl loop:
    prop_loop_tag = "{%- if property.last != blank and property_first_char != '_' -%}"
    prop_loop_idx = content_norm.find(prop_loop_tag)
    if prop_loop_idx != -1:
        # Check what follows
        old_prop_block = content_norm[prop_loop_idx : content_norm.find("{%- endif -%}\n                          {%- endfor -%}", prop_loop_idx)]
        new_prop_block = """{%- if property.last != blank and property_first_char != '_' and property.first != 'Authentication' and property.first != 'Certified For' -%}
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
                            """
        content_norm = content_norm[:prop_loop_idx] + new_prop_block + content_norm[prop_loop_idx + len(old_prop_block):]
        print("[cart-products.liquid] Cleaned up properties dl.")

    # Step 8: Replace remove button with atomic remove
    qty_ctrls_start = content_norm.find('<div class="cart-items__quantity-controls">')
    qty_ctrls_end = content_norm.find('</div>', content_norm.find('cart-items__remove', qty_ctrls_start)) + len('</div>')
    old_qty_ctrls = content_norm[qty_ctrls_start:qty_ctrls_end]
    new_qty_ctrls = """<div class="cart-items__quantity-controls">
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

                    {% if attached_cert != null %}
                      <button
                        class="button cart-items__remove"
                        type="button"
                        aria-label="{{ 'accessibility.remove_item' | t: title: item.title | escape }}"
                        onclick="removeProductAndCert('{{ item.key }}', '{{ attached_cert.key }}')"
                        title="Remove item and certificate"
                      >
                        {{- 'icon-delete.svg' | inline_asset_content -}}
                        <span class="visually-hidden">{{ 'accessibility.remove' | t }}</span>
                      </button>
                    {% else %}
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
    content_norm = content_norm.replace(old_qty_ctrls, new_qty_ctrls, 1)
    print("[cart-products.liquid] Updated quantity controls & atomic remove.")

    # Step 9: In cart-items__price: add + ₹699 Cert indicator
    old_price_td = """<text-component value="{{ price | strip_html }}"
                    ><bdi>{{ price }}</bdi></text-component
                  >"""
    new_price_td = """<text-component value="{{ price | strip_html }}"
                    ><bdi>{{ price }}</bdi></text-component
                  >
                  {%- if attached_cert != null -%}
                    <div style="font-size: 0.6875rem; color: #047857; font-weight: 600; margin-top: 2px;">
                      + ₹699 Cert
                    </div>
                  {%- endif -%}"""
    if old_price_td in content_norm:
        content_norm = content_norm.replace(old_price_td, new_price_td, 1)
        print("[cart-products.liquid] Added price indicator.")

    # Step 10: Append client-side sync script
    client_script = """
<script>
  async function reloadCartSections() {
    try {
      const cartItems = document.querySelectorAll('cart-items-component');
      const sectionIds = Array.from(cartItems).map(c => c.dataset.sectionId).filter(Boolean);
      if (sectionIds.length === 0) {
        window.location.reload();
        return;
      }
      const sectionsParam = sectionIds.join(',');
      const res = await fetch(`/cart?sections=${sectionsParam}`, {
        headers: { 'Accept': 'application/json' }
      });
      if (res.ok) {
        const data = await res.json();
        for (const [secId, html] of Object.entries(data)) {
          const container = document.querySelector(`[data-section-id="${secId}"]`);
          if (container) {
            const doc = new DOMParser().parseFromString(html, 'text/html');
            const newEl = doc.querySelector(`[data-section-id="${secId}"]`);
            if (newEl) {
              container.replaceWith(newEl);
            } else {
              container.innerHTML = html;
            }
          }
        }
        try {
          const cartRes = await fetch('/cart.js');
          const cartData = await cartRes.json();
          const count = cartData.items.filter(it => it.variant_id != 57721101779110).reduce((sum, it) => sum + it.quantity, 0);
          document.querySelectorAll('.cart-count, [ref="cartItemCount"]').forEach(el => el.textContent = count);
        } catch (_) {}
      } else {
        window.location.reload();
      }
    } catch (e) {
      window.location.reload();
    }
  }

  async function removeProductAndCert(itemKey, certKey) {
    try {
      const updates = {};
      updates[itemKey] = 0;
      if (certKey) updates[certKey] = 0;
      const res = await fetch('/cart/update.js', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ updates })
      });
      if (res.ok) {
        await reloadCartSections();
      }
    } catch (err) {
      console.error('Failed to remove item and cert:', err);
    }
  }

  async function removeAttachedCert(certKey, parentKey) {
    try {
      const updates = {};
      updates[certKey] = 0;
      const res = await fetch('/cart/update.js', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ updates })
      });
      if (res.ok) {
        await reloadCartSections();
      }
    } catch (err) {
      console.error('Failed to remove cert:', err);
    }
  }

  async function addCertToProduct(variantId, productTitle, quantity) {
    try {
      const res = await fetch('/cart/add.js', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
          items: [
            {
              id: 57721101779110,
              quantity: quantity || 1,
              properties: {
                'Certified For': productTitle,
                '_parent_id': String(variantId)
              }
            }
          ]
        })
      });
      if (res.ok) {
        await reloadCartSections();
      }
    } catch (err) {
      console.error('Failed to add cert:', err);
    }
  }

  if (!window._cartCertQtySyncAttached) {
    window._cartCertQtySyncAttached = true;
    document.addEventListener('change', async (e) => {
      const input = e.target.closest('.cart-items__quantity-controls input');
      if (!input) return;
      const row = input.closest('.cart-items__table-row');
      if (!row) return;
      const certKey = row.dataset.attachedCertKey;
      if (!certKey) return;
      const newQty = parseInt(input.value, 10);
      if (isNaN(newQty)) return;

      try {
        const updates = {};
        updates[certKey] = newQty;
        await fetch('/cart/update.js', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({ updates })
        });
      } catch (err) {
        console.error('Failed to sync cert qty:', err);
      }
    });
  }
</script>
"""
    content_norm += client_script

    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(content_norm.replace("\n", "\r\n"))
    print("[cart-products.liquid] Updated successfully.")
    return True

if __name__ == "__main__":
    ok1 = update_cart_summary()
    ok2 = update_cart_products()
    print("All success:", ok1 and ok2)
