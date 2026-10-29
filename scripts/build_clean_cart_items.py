import os

debug_file = r"c:\workspace\dropship-scraper-portable-20260905\product-updater\debug_theme_files\assets__component-cart-items.js"
target_file = r"c:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\assets\component-cart-items.js"

with open(debug_file, "r", encoding="utf-8") as f:
    code = f.read()

target = """      const body = JSON.stringify({
        line: line,
        quantity: quantity,
        sections: Array.from(sectionsToUpdate).join(','),
        sections_url: window.location.pathname,
      });

      cartTotal?.shimmer();

      const lineId = this.refs.cartItemRows[line - 1]?.dataset.key ?? '';
      this.dispatchEvent(
        new CartLinesUpdateEvent({
          action: config.action === 'change' && quantity > 0 ? 'update' : 'remove',
          context: 'cart',
          lines: [{ id: lineId, quantity }],
          promise: deferredUpdatePromise.promise,
        })
      );

      const response = await fetch(`${Theme.routes.cart_change_url}`, fetchConfig('json', { body }));"""

replacement = """      const targetRow = this.querySelector(`tr[data-line-index="${line}"]`) ||
                        this.querySelector(`tr[data-line="${line}"]`) ||
                        this.querySelector(`input[data-cart-line="${line}"]`)?.closest('.cart-items__table-row') ||
                        this.refs.cartItemRows?.find(r => r.dataset?.lineIndex == line || r.dataset?.line == line) ||
                        this.refs.cartItemRows?.[line - 1];

      const parentKey = targetRow?.dataset?.key;
      const certKey = targetRow?.dataset?.attachedCertKey;

      let fetchUrl;
      let body;

      if (certKey && parentKey) {
        fetchUrl = `${Theme?.routes?.cart_update_url || '/cart/update'}.js`;
        body = JSON.stringify({
          updates: {
            [parentKey]: quantity,
            [certKey]: quantity,
          },
          sections: Array.from(sectionsToUpdate).join(','),
          sections_url: window.location.pathname,
        });
      } else {
        fetchUrl = `${Theme.routes.cart_change_url}`;
        body = JSON.stringify({
          line: line,
          quantity: quantity,
          sections: Array.from(sectionsToUpdate).join(','),
          sections_url: window.location.pathname,
        });
      }

      cartTotal?.shimmer();

      const lineId = parentKey || this.refs.cartItemRows[line - 1]?.dataset.key ?? '';
      const lines = [{ id: lineId, quantity }];
      if (certKey) {
        lines.push({ id: certKey, quantity });
      }
      this.dispatchEvent(
        new CartLinesUpdateEvent({
          action: config.action === 'change' && quantity > 0 ? 'update' : 'remove',
          context: 'cart',
          lines,
          promise: deferredUpdatePromise.promise,
        })
      );

      const response = await fetch(fetchUrl, fetchConfig('json', { body }));"""

assert target in code, "Target string not found in debug component-cart-items.js"
new_code = code.replace(target, replacement)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(new_code)

print("Successfully generated horizon_clean_theme/assets/component-cart-items.js")
