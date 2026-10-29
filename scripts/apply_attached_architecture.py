import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from storage.shopify_auth import execute_shopify_graphql

THEME_DIR = os.path.join(BASE_DIR, "horizon_clean_theme")
SNIPPET_PATH = os.path.join(THEME_DIR, "snippets", "cart-products.liquid")

# 1. Fetch clean remote version first
query = """
query getThemeFile {
  theme(id: "gid://shopify/OnlineStoreTheme/198751387814") {
    files(filenames: ["snippets/cart-products.liquid"]) {
      nodes {
        filename
        body {
          ... on OnlineStoreThemeFileBodyText {
            content
          }
        }
      }
    }
  }
}
"""
res = execute_shopify_graphql(query)
data = res[0]
node = data["data"]["theme"]["files"]["nodes"][0] if "data" in data else data["theme"]["files"]["nodes"][0]
content = node["body"]["content"].replace("\r", "")

# Remove alternating empty lines if present
lines = content.split("\n")
if len(lines) > 4 and all(lines[i] == '' for i in range(1, len(lines), 2)):
    lines = [lines[i] for i in range(0, len(lines), 2)]
content = "\n".join(lines)

# Strip existing client_script if present
if "<script>\n  async function reloadCartSections()" in content:
    content = content[:content.find("<script>\n  async function reloadCartSections()")].strip()

# Strip any previous ra-attached-cert-box injection if present
# (fresh base)

text = content

# 1. Update physical_items_count and empty cart check
old_empty = "{% if cart.empty? or force_empty %}"
new_empty = """{% liquid
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

if old_empty in text:
    text = text.replace(old_empty, new_empty, 1)

# 2. Update cartItemCount visually-hidden span
old_count = "{{- cart.item_count -}}"
new_count = "{{- physical_items_count -}}"
if old_count in text:
    text = text.replace(old_count, new_count, 1)

# 3. Update table loop start
loop_start = "{% for item in cart.items %}"
row_tag_start = '<tr\n                id="CartItem-{{ item.key }}"'
l_idx = text.find(loop_start)
r_idx = text.find(row_tag_start, l_idx)
if l_idx != -1 and r_idx != -1:
    new_loop_header = """{% for item in cart.items %}
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
    text = text[:l_idx] + new_loop_header + text[r_idx:]

# Add data-attached-cert-key to row tag
old_tr_attrs = """data-key="{{ item.key }}"
              >"""
new_tr_attrs = """data-key="{{ item.key }}"
                data-variant-id="{{ item.variant_id }}"
                {% if attached_cert != null %}
                  data-attached-cert-key="{{ attached_cert.key }}"
                {% endif %}
              >"""
if old_tr_attrs in text:
    text = text.replace(old_tr_attrs, new_tr_attrs, 1)

# 4. Clean up media block
media_start = text.find('<td\n                  class="cart-items__media"')
if media_start != -1:
    media_end = text.find('</td>', media_start)
    media_block = text[media_start:media_end]
    if "{% if is_checkcheck %}" in media_block:
        s = media_block.find("{% if is_checkcheck %}")
        e = media_block.find("{% else %}", s)
        fi = media_block.find("{% endif %}", e)
        normal_a = media_block[e + len("{% else %}"):fi].strip()
        clean_media_block = media_block[:s] + normal_a + media_block[fi + len("{% endif %}"):]
        text = text[:media_start] + clean_media_block + text[media_end:]

# 5. Clean up title block
info_start = text.find('<div class="cart-items__product-info">')
if info_start != -1:
    vendor_pos = text.find('{% if item.product.vendor and block_settings.vendor %}', info_start)
    if vendor_pos != -1:
        clean_info = """<div class="cart-items__product-info">
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
        text = text[:info_start] + clean_info + text[vendor_pos:]

# 6. Insert attached certificate inside cart-items__variants-wrapper
if "ra-attached-cert-box" not in text:
    vw_start = text.find('<div class="cart-items__variants-wrapper">')
    dl_end = text.find('</dl>\n                      {%- endif -%}', vw_start)
    if dl_end != -1:
        insert_pos = dl_end + len('</dl>\n                      {%- endif -%}')
        cert_box_html = """

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
                      {%- endif -%}"""
        text = text[:insert_pos] + cert_box_html + text[insert_pos:]

# 7. Clean properties list
prop_condition = "{%- if property.last != blank and property_first_char != '_' -%}"
p_idx = text.find(prop_condition)
if p_idx != -1:
    end_prop = text.find('{%- endif -%}\n                          {%- endfor -%}', p_idx)
    if end_prop != -1:
        clean_prop_inner = """{%- if property.last != blank and property_first_char != '_' and property.first != 'Authentication' and property.first != 'Certified For' -%}
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
        text = text[:p_idx] + clean_prop_inner + text[end_prop:]

# 8. Quantity controls and atomic removal
qty_start = text.find('<div class="cart-items__quantity-controls">')
if qty_start != -1:
    btn_remove_end = text.find('</div>', text.find('cart-items__remove', qty_start)) + len('</div>')
    clean_qty = """<div class="cart-items__quantity-controls">
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
    text = text[:qty_start] + clean_qty + text[btn_remove_end:]

# 9. In cart-items__price: add + ₹699 indicator
if "+ ₹699 Cert" not in text:
    price_pos = text.find('<text-component value="{{ price | strip_html }}"')
    if price_pos != -1:
        price_end = text.find('</text-component>', price_pos) + len('</text-component>')
        price_append = """
                  {%- if attached_cert != null -%}
                    <div style="font-size: 0.6875rem; color: #047857; font-weight: 600; margin-top: 2px;">
                      + ₹699 Cert
                    </div>
                  {%- endif -%}"""
        text = text[:price_end] + price_append + text[price_end:]

# 10. Robust Client-Side Script
client_script = """
<script>
  async function reloadCartSections() {
    if (window.location.pathname.endsWith('/cart') || window.location.pathname.endsWith('/cart/')) {
      window.location.reload();
      return;
    }
    try {
      const res = await fetch(window.location.href);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const newItems = doc.querySelector('cart-items-component, .cart-items__wrapper');
      const currentItems = document.querySelector('cart-items-component, .cart-items__wrapper');
      if (newItems && currentItems) {
        currentItems.replaceWith(newItems);
      }
      const newSummary = doc.querySelector('.cart__summary, .cart-drawer__summary');
      const currentSummary = document.querySelector('.cart__summary, .cart-drawer__summary');
      if (newSummary && currentSummary) {
        currentSummary.replaceWith(newSummary);
      }
      const cartRes = await fetch('/cart.js');
      const cartData = await cartRes.json();
      const count = cartData.items.filter(it => it.variant_id != 57721101779110).reduce((sum, it) => sum + it.quantity, 0);
      document.querySelectorAll('.cart-count, [ref="cartItemCount"]').forEach(el => el.textContent = count);
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
text += client_script

with open(SNIPPET_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(text)

print("Saved clean cart-products.liquid successfully.")
