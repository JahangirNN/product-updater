import os

p = r"C:\workspace\dropship-scraper-portable-20260905\product-updater\horizon_clean_theme\snippets\product-card.liquid"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

target = """    // Handle color thumbnail click/hover to swap product card image
    function swapCardImage(btn) {
      const card = btn.closest('product-card, .product-card');
      if (!card) return;
      const imgSrc = btn.dataset.imgSrc;
      const imgSrcset = btn.dataset.imgSrcset;
      const varUrl = btn.dataset.variantUrl;
      const varId = btn.dataset.variantId;

      if (imgSrc) {
        // Target active card gallery image
        const targetImg = card.querySelector('card-gallery img, .product-media__image, slideshow-slide:not([hidden]) img, img');
        if (targetImg) {
          targetImg.src = imgSrc;
          if (imgSrcset) targetImg.srcset = imgSrcset;
        }
      }

      // Update active swatch state in this card
      card.querySelectorAll('.luxury-card__color-btn').forEach(function(b) {
        b.classList.remove('is-active');
      });
      btn.classList.add('is-active');

      // Update card links to maintain variant selection
      if (varUrl) {
        card.querySelectorAll('a.product-card__link, a[ref="cardGalleryLink"], a[ref="productTitleLink"]').forEach(function(a) {
          a.href = varUrl;
        });
      }
    }"""

replacement = """    // Handle color thumbnail click/hover to swap product card image & update live variant price
    function swapCardImage(btn) {
      const card = btn.closest('product-card, .product-card');
      if (!card) return;
      const imgSrc = btn.dataset.imgSrc;
      const imgSrcset = btn.dataset.imgSrcset;
      const varUrl = btn.dataset.variantUrl;
      const varId = btn.dataset.variantId;
      const priceText = btn.dataset.price;
      const comparePriceText = btn.dataset.compareAt;

      // 1. Swap active card gallery image
      if (imgSrc) {
        const targetImg = card.querySelector('card-gallery img, .product-media__image, slideshow-slide:not([hidden]) img, img');
        if (targetImg) {
          targetImg.src = imgSrc;
          if (imgSrcset) targetImg.srcset = imgSrcset;
        }
      }

      // 2. Live Dynamic Price Update for Variant
      if (priceText) {
        const priceContainer = card.querySelector('[ref="priceContainer"], product-price, .price-container');
        if (priceContainer) {
          const mainPriceEl = priceContainer.querySelector('.price bdi, span.price, bdi');
          if (mainPriceEl) {
            mainPriceEl.textContent = priceText;
          }
          let compareEl = priceContainer.querySelector('.compare-at-price');
          if (comparePriceText) {
            if (!compareEl) {
              compareEl = document.createElement('span');
              compareEl.className = 'price-item__group price-item--regular compare-at-price';
              compareEl.innerHTML = '<span class="visually-hidden">Regular price&nbsp;</span><bdi></bdi>';
              priceContainer.insertBefore(compareEl, priceContainer.firstChild);
            }
            const compareBdi = compareEl.querySelector('bdi') || compareEl;
            compareBdi.textContent = comparePriceText;
            compareEl.style.display = '';
          } else if (compareEl) {
            compareEl.style.display = 'none';
          }
        }
      }

      // 3. Update active swatch state in this card
      card.querySelectorAll('.luxury-card__color-btn').forEach(function(b) {
        b.classList.remove('is-active');
      });
      btn.classList.add('is-active');

      // 4. Update card links to maintain variant selection
      if (varUrl) {
        card.querySelectorAll('a.product-card__link, a[ref="cardGalleryLink"], a[ref="productTitleLink"]').forEach(function(a) {
          a.href = varUrl;
        });
      }
    }"""

c_norm = c.replace("\r\n", "\n")
target_norm = target.replace("\r\n", "\n")
replacement_norm = replacement.replace("\r\n", "\n")

if target_norm in c_norm:
    c_norm = c_norm.replace(target_norm, replacement_norm, 1)
    print("Replaced swapCardImage with dynamic price update in product-card.liquid")
else:
    print("Could not find target in product-card.liquid")

with open(p, "w", encoding="utf-8") as f:
    f.write(c_norm)
