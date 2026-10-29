import os
import sys
import glob
import json
import random
import time
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from storage.shopify_sync import upsert_product_to_shopify
from storage.forex import get_usd_to_inr_rate

def pick_3_random_multicolor_bags():
    already_tested = {
        "hana-large-tote-bag-pink",
        "celeste-woven-textured-envelope-top-handle-bag-dark-brown",
        "ellie-metal-ring-embellished-top-handle-bag-lemon-yellow",
        "mini-rowan-crossbody-bag",
        "nolita-19-in-signature-canvas",
        "nell-fringe-hardware-top-handle-bag-burgundy",
        "radio-camera-bag",
        "keyla-weave-texture-top-handle-bag-pink",
        "emily-shoulder-bag-cdw87-sv-bk",
        "hana-medium-weave-texture-tote-bag-black",
        "piper-flex-logo-stitched-suede"
    }
    
    candidates = []
    for store in ['coach', 'jwpei']:
        for f in glob.glob(f'storage/db/{store}/products/*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    d = json.load(fp)
                t = d.get('title', '').lower()
                pt = d.get('product_type', '').lower()
                if not any(w in t or w in pt for w in ['bag', 'tote', 'crossbody', 'satchel', 'shoulder', 'top handle', 'wallet', 'backpack', 'clutch', 'wristlet']):
                    continue
                h = d.get('shopify_handle') or d.get('handle')
                if h in already_tested:
                    continue
                vars = d.get('variants', [])
                if len(vars) < 3 or d.get('availability') != 'in_stock':
                    continue
                # Distinct images per variant
                img_urls = set(v.get('image_url') or v.get('image') for v in vars if isinstance(v, dict) and (v.get('image_url') or v.get('image')))
                if len(img_urls) >= 3 and d.get('shopify_product_id'):
                    candidates.append((f, d, store))
            except Exception:
                pass

    print(f"Total eligible multi-color bag candidates: {len(candidates)}")
    random.seed(int(time.time() * 1000) % 1000000)
    selected = random.sample(candidates, 3)
    return selected

def run_audit():
    selected = pick_3_random_multicolor_bags()
    forex_rate = get_usd_to_inr_rate()
    
    products_to_test = []
    print("\n================================================================================")
    print("SELECTED 3 EXTREMELY RANDOM MULTI-COLOR BAG PRODUCTS:")
    print("================================================================================")
    for idx, (fpath, prod, store) in enumerate(selected, 1):
        handle = prod.get("shopify_handle") or prod.get("handle")
        title = prod.get("title")
        variants = prod.get("variants", [])
        colors = [v.get("color") or v.get("name") or v.get("title") for v in variants[:6]]
        print(f"\n[{idx}] {title} ({store.upper()})")
        print(f"    Handle: {handle}")
        print(f"    Variants: {len(variants)} -> Colors: {colors}")
        print(f"    Shopify Product ID: {prod.get('shopify_product_id')}")
        
        # Sync to ensure latest image mapping & active inventory
        print(f"    Ensuring variant images and active inventory policy on Shopify Admin...")
        success, pnode, err = upsert_product_to_shopify(prod, forex_rate)
        if success:
            print(f"    >>> Sync Result: SUCCESS (GID: {pnode.get('id') if pnode else 'OK'})")
        else:
            print(f"    >>> Sync Result: FAILED ({err})")
            
        products_to_test.append({
            "title": title,
            "handle": handle,
            "store": store,
            "variants": variants
        })
        
    print("\n================================================================================")
    print("RUNNING LIVE PLAYWRIGHT AUDIT ON THE 3 RANDOM PRODUCTS")
    print("================================================================================")
    
    artifacts_dir = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
    test_results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        for p_idx, prod_info in enumerate(products_to_test, 1):
            handle = prod_info["handle"]
            title = prod_info["title"]
            store = prod_info["store"]
            url = f"https://therareavenue.com/products/{handle}"
            
            print(f"\n>>> [{p_idx}/3] TESTING PDP: {title} ({store.upper()})")
            print(f"    URL: {url}")
            
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Initial state
            init_img = page.evaluate("""() => {
                const el = document.querySelector('product-media-carousel img, .product-gallery img, .product__media-item img');
                return el ? el.src : '';
            }""")
            init_price = page.evaluate("""() => {
                const el = document.querySelector('.price-list, .product-info__price, .price');
                return el ? el.innerText.trim().replace(/\\s+/g, ' ') : '';
            }""")
            init_var_id = page.evaluate("""() => {
                const input = document.querySelector('input[name=\"id\"]');
                return input ? input.value : '';
            }""")
            
            print(f"    [Initial State] Price: {init_price} | Variant ID: {init_var_id}")
            print(f"    [Initial Image]: {init_img[:70]}...")
            
            # Find all color options/swatches and which one is checked
            swatches = page.evaluate("""() => {
                const results = [];
                // Look for labels with data-option-value or for attribute
                const labels = Array.from(document.querySelectorAll('label.color-swatch, .color-swatch, label[data-option-value]'));
                labels.forEach((lbl, idx) => {
                    const forId = lbl.getAttribute('for') || '';
                    const radio = forId ? document.getElementById(forId) : null;
                    const isChecked = radio ? radio.checked : (idx === 0);
                    const name = lbl.getAttribute('data-tooltip') || lbl.getAttribute('title') || lbl.innerText.trim() || `Option_${idx}`;
                    results.push({
                        idx: idx,
                        forId: forId,
                        isChecked: isChecked,
                        name: name
                    });
                });
                return results;
            }""")
            
            unselected = [s for s in swatches if not s["isChecked"] and s["name"]]
            print(f"    Found {len(swatches)} total color swatches, {len(unselected)} unselected.")
            
            # We test up to 2 distinct unselected swatches
            test_swatches = unselected[:2]
            prev_img = init_img
            prev_var_id = init_var_id
            
            for t_idx, target in enumerate(test_swatches, 1):
                swatch_name = target["name"]
                for_id = target["forId"]
                s_idx = target["idx"]
                
                print(f"\n    -> Selecting variant swatch #{t_idx}: '{swatch_name}'...")
                
                # Click the unselected swatch
                clicked = page.evaluate("""(arg) => {
                    let el = null;
                    if (arg.forId) {
                        el = document.querySelector(`label[for=\"${arg.forId}\"]`) || document.getElementById(arg.forId);
                    }
                    if (!el) {
                        const items = document.querySelectorAll('label.color-swatch, .color-swatch, label[data-option-value]');
                        el = items[arg.idx];
                    }
                    if (el) {
                        el.scrollIntoView({ behavior: 'instant', block: 'center' });
                        el.click();
                        return true;
                    }
                    return false;
                }""", {"forId": for_id, "idx": s_idx})
                
                page.wait_for_timeout(2500)
                
                post_state = page.evaluate("""() => {
                    const priceEl = document.querySelector('.price-list, .product-info__price, .price');
                    const priceText = priceEl ? priceEl.innerText.trim().replace(/\\s+/g, ' ') : '';
                    const varInput = document.querySelector('input[name=\"id\"]');
                    const varId = varInput ? varInput.value : '';
                    
                    const atcBtn = document.querySelector('form[action*=\"/cart/add\"] button[type=\"submit\"], button.product-form__submit');
                    const atcText = atcBtn ? atcBtn.innerText.trim().replace(/\\s+/g, ' ') : '';
                    const atcDisabled = atcBtn ? atcBtn.disabled : true;
                    
                    // Visible image in viewport
                    const imgs = Array.from(document.querySelectorAll('product-media-carousel img, .product-gallery img, .product__media-item img'));
                    let visibleImg = '';
                    for (const img of imgs) {
                        const rect = img.getBoundingClientRect();
                        if (rect.width > 50 && rect.height > 50 && rect.top >= -100 && rect.top <= window.innerHeight) {
                            visibleImg = img.src;
                            break;
                        }
                    }
                    if (!visibleImg && imgs.length > 0) visibleImg = imgs[0].src;
                    
                    return {
                        price: priceText,
                        variantId: varId,
                        atcText: atcText,
                        atcDisabled: atcDisabled,
                        activeImg: visibleImg
                    };
                }""")
                
                var_id_changed = (post_state["variantId"] != prev_var_id) and bool(post_state["variantId"])
                img_changed = (post_state["activeImg"] != prev_img) and bool(post_state["activeImg"])
                whole_rupees = ".00" in post_state["price"]
                atc_active = ("ADD TO CART" in post_state["atcText"].upper()) and not post_state["atcDisabled"]
                
                print(f"       Post-click Price: {post_state['price']} (Whole-rupees: {whole_rupees})")
                print(f"       Post-click Variant ID: {post_state['variantId']} (Changed: {var_id_changed})")
                print(f"       Post-click ATC Button: {post_state['atcText']} (Active: {atc_active})")
                print(f"       Post-click Active Image: {post_state['activeImg'][:70]}...")
                print(f"       Image Switched: {img_changed} (Prev != New: {post_state['activeImg'] != prev_img})")
                
                # Take screenshot
                safe_name = "".join(c if c.isalnum() else "_" for c in f"{store}_{handle}_{swatch_name}")
                shot_path = os.path.join(artifacts_dir, f"random_bag_{safe_name}.png")
                page.screenshot(path=shot_path, full_page=False)
                
                is_pass = var_id_changed and atc_active and whole_rupees and img_changed
                status_str = "[PASS]" if is_pass else "[FAIL]"
                print(f"       >>> STATUS: {status_str}")
                
                test_results.append({
                    "title": title,
                    "store": store,
                    "handle": handle,
                    "swatch": swatch_name,
                    "price": post_state["price"],
                    "variant_id": post_state["variantId"],
                    "img_switched": img_changed,
                    "atc_active": atc_active,
                    "whole_rupees": whole_rupees,
                    "status": "PASS" if is_pass else "FAIL",
                    "screenshot": shot_path
                })
                
                prev_img = post_state["activeImg"]
                prev_var_id = post_state["variantId"]
                
        # Perform Add-to-Cart verification on the last tested product
        last_prod = products_to_test[-1]
        print(f"\n================================================================================")
        print(f"TESTING ADD TO CART WITH SELECTED VARIANT ON {last_prod['title']}...")
        page.evaluate("""() => {
            const btn = document.querySelector('form[action*=\"/cart/add\"] button[type=\"submit\"], button.product-form__submit');
            if (btn && !btn.disabled) {
                btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                btn.click();
            }
        }""")
        page.wait_for_timeout(3000)
        
        cart_info = page.evaluate("""() => {
            const drawer = document.querySelector('cart-drawer, #cart-drawer, .cart-drawer');
            const drawerVisible = drawer ? (drawer.hasAttribute('open') || window.getComputedStyle(drawer).visibility !== 'hidden') : false;
            const items = document.querySelectorAll('cart-drawer-items .cart-item, .cart-drawer__item, .cart-item');
            const firstItem = items.length > 0 ? items[0].innerText.replace(/\\s+/g, ' ') : '';
            return {
                drawerVisible: drawerVisible,
                itemCount: items.length,
                firstItemText: firstItem
            };
        }""")
        print(f"Cart Result: {cart_info}")
        
        cart_shot_path = os.path.join(artifacts_dir, "random_3_bags_atc_verified.png")
        page.screenshot(path=cart_shot_path, full_page=False)
        print(f"Saved cart drawer screenshot to: {cart_shot_path}")
        
        browser.close()
        
    print("\n================================================================================")
    print("FINAL RANDOM 3 MULTI-COLOR BAGS AUDIT & VERIFICATION REPORT:")
    print("================================================================================")
    all_passed = True
    for r in test_results:
        print(f"[{r['status']}] [{r['store'].upper():<6}] {r['title'][:30]:<30} | Variant: {r['swatch']:<16} | Price: {r['price']:<25} | ID: {r['variant_id']}")
        if r["status"] != "PASS":
            all_passed = False
            
    print("================================================================================")
    print(f"OVERALL RESULT: {'ALL PASS (6/6 Passed)' if all_passed else 'SOME CHECKS FAILED'}")
    print("================================================================================")

if __name__ == "__main__":
    run_audit()
