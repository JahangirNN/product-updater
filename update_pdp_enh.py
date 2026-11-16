import os

p = r"C:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\snippets\luxury-pdp-enhancements.liquid"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

target = """      if (stickyBtn) {
        stickyBtn.addEventListener('click', function(e) {
          e.preventDefault();
          mainBuyBtn.click();
        });
      }"""

replacement = """      if (stickyBtn) {
        stickyBtn.addEventListener('click', function(e) {
          e.preventDefault();
          mainBuyBtn.click();
        });
      }

      // Live synchronize sticky buy bar price & variant with selected variant
      var vp = document.querySelector('variant-picker');
      if (vp) {
        vp.addEventListener('change', function(e) {
          var target = e.target;
          if (target && target.dataset) {
            var pText = target.dataset.variantPrice;
            var vTitle = target.value;
            if (pText) {
              var sPrice = document.querySelector('.luxury-sticky-buy-bar__price');
              if (sPrice) sPrice.textContent = pText;
            }
            if (vTitle) {
              var sVar = document.querySelector('.luxury-sticky-buy-bar__variant');
              if (sVar) sVar.textContent = '· ' + vTitle;
            }
          }
        });
      }"""

c_norm = c.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

if target_norm in c_norm:
    c_norm = c_norm.replace(target_norm, replacement_norm, 1)
    print("Updated luxury-pdp-enhancements.liquid sticky buy bar sync")
else:
    print("Could not find target in luxury-pdp-enhancements.liquid")

with open(p, "w", encoding="utf-8") as f:
    f.write(c_norm)
