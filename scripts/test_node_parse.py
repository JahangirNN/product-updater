import subprocess

debug_file = r"c:\workspace\dropship-scraper-portable-20260905\product-updater\debug_theme_files\assets__component-cart-items.js"
with open(debug_file, "r", encoding="utf-8") as f:
    orig = f.read()

target = "const response = await fetch(`${Theme.routes.cart_change_url}`, fetchConfig('json', { body }));"

replacement = """const targetRow = this.querySelector('tr[data-line-index=\"' + line + '\"]') ||
                        this.querySelector('tr[data-line=\"' + line + '\"]') ||
                        this.querySelector('input[data-cart-line=\"' + line + '\"]')?.closest('.cart-items__table-row') ||
                        this.refs.cartItemRows?.find(r => r.dataset?.lineIndex == line || r.dataset?.line == line) ||
                        this.refs.cartItemRows?.[line - 1];
      const parentKey = targetRow?.dataset?.key;
      const certKey = targetRow?.dataset?.attachedCertKey;
      let reqBody = body;
      let fetchUrl = `${Theme.routes.cart_change_url}`;
      if (certKey && parentKey) {
        fetchUrl = `${Theme?.routes?.cart_update_url || '/cart/update'}.js`;
        const updates = {};
        updates[parentKey] = quantity;
        updates[certKey] = quantity;
        reqBody = JSON.stringify({
          updates: updates,
          sections: Array.from(sectionsToUpdate).join(','),
          sections_url: window.location.pathname
        });
      }
      const response = await fetch(fetchUrl, fetchConfig('json', { body: reqBody }));"""

assert target in orig, "Target string not found!"
cand = orig.replace(target, replacement)
res = subprocess.run(["node", "--input-type=module", "-c"], input=cand, encoding="utf-8", capture_output=True)
print("Result code:", res.returncode)
if res.returncode == 0:
    print("SUCCESS! Valid JavaScript with ZERO errors!")
    target_file = r"c:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\assets\component-cart-items.js"
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(cand)
    print("Wrote to horizon_clean_theme/assets/component-cart-items.js successfully!")
else:
    print("Stderr:\n", res.stderr)
