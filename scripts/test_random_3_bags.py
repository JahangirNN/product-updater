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

def pick_3_diverse_random_bags():
    """Pick 1 Coach, 1 JW PEI, and 1 Michael Kors bag at random."""
    already_tested = {
        "hana-large-tote-bag-pink",
        "celeste-woven-textured-envelope-top-handle-bag-dark-brown",
        "ellie-metal-ring-embellished-top-handle-bag-lemon-yellow",
        "mini-rowan-crossbody-bag",
        "nolita-19-in-signature-canvas",
        "nell-fringe-hardware-top-handle-bag-burgundy"
    }
    
    selected = []
    random.seed(int(time.time() * 1000) % 1000000)
    
    for store in ["coach", "jwpei", "michaelkors"]:
        pattern = os.path.join(PROJECT_ROOT, "storage", "db", store, "products", "*.json")
        candidates = []
        for f in glob.glob(pattern):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
            except Exception:
                continue
                
            handle = d.get("shopify_handle") or d.get("handle")
            pid = d.get("shopify_product_id")
            variants = d.get("variants") or []
            avail = d.get("availability")
            
            if (pid and handle not in already_tested and len(variants) >= 3 and avail == "in_stock"):
                has_imgs = any(v.get("image_url") or v.get("image") for v in variants if isinstance(v, dict))
                if has_imgs:
                    candidates.append((f, d, store))
                    
        print(f"Store {store.upper()} available multi-variant in-stock candidates: {len(candidates)}")
        if candidates:
            selected.append(random.choice(candidates))
            
    return selected

def run_tests():
    selected = pick_3_diverse_random_bags()
    forex_rate = get_usd_to_inr_rate()
    
    products_to_test = []
    print("\n================================================================================")
    print("SELECTED 3 DIVERSE RANDOM BAG PRODUCTS (1 COACH, 1 JW PEI, 1 MICHAEL KORS):")
    print("================================================================================")
    for idx, (fpath, prod, store) in enumerate(selected, 1):
        handle = prod.get("shopify_handle") or prod.get("handle")
        title = prod.get("title")
        variants = prod.get("variants", [])
        colors = [v.get("color") or v.get("name") or v.get("title") for v in variants[:6]]
        print(f"\n[{idx}] {title} ({store.upper()})")
        print(f"    Handle: {handle}")
        print(f"    Total variants: {len(variants)} -> Sample colors: {colors}")
        print(f"    Shopify Product ID: {prod.get('shopify_product_id')}")
        
        print(f"    Ensuring variant images and inventory policy are active on Shopify...")
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
    print("STARTING PLAYWRIGHT LIVE STORE AUDIT ACROSS ALL 3 BRAND BAGS")
    print("================================================================================")
    
    test_results = []
    artifacts_dir = r"C:\Users\Administrator\.gemini\antigravity\brain\8f48874f-591b-45e7-be48-696b0743b7ad"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        for p_idx, prod_info in enumerate(products_to_test, 1):
            handle = prod_info["handle"]
            title = prod_info["title"]
            store = prod_info["store"]
            url = f"https://therareavenue.com/products/{handle}"
            
            print(f"\n>>> [{p_idx}/3] TESTING PDP: {title} ({store.upper()})")
            print(f"    URL: {url}")
            
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"    Page navigation timeout/error: {e}")
                
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
            
            # Find swatches and detect which one is checked via underlying radio input
            swatches_info = page.evaluate("""() => {
                const results = [];
                // Look for radio inputs in option blocks
                const radios = Array.from(document.querySelectorAll('input[type=\"radio\"][name*=\"option\" i], input[type=\"radio\"][name*=\"color\" i]'));
                if (radios.length > 0) {
                    radios.forEach((r, idx) => {
                        const lbl = document.querySelector(`label[for=\"${r.id}\"]`);
                        const name = r.value || (lbl ? lbl.innerText.trim() : '') || `Option_${idx}`;
                        results.push({
                            idx: idx,
                            isChecked: r.checked,
                            name: name,
                            id: r.id
                        });
                    });
                } else {
                    // Fallback to swatch labels
                    const labels = Array.from(document.querySelectorAll('.color-swatch, label[data-option-value]'));
                    labels.forEach((lbl, idx) => {
                        const isChecked = lbl.classList.contains('is-selected') || (idx === 0);
                        const name = lbl.getAttribute('data-tooltip') || lbl.getAttribute('title') || lbl.innerText.trim() || `Swatch_${idx}`;
                        results.push({
                            idx: idx,
                            isChecked: isChecked,
                            name: name,
                            id: lbl.getAttribute('for') || ''
                        });
                    });
                }
                return results;
            }""")
            
            unselected = [s for s in swatches_info if not s["isChecked"] and s["name"]]
            print(f"    Found {len(swatches_info)} total swatches ({len(unselected)} unselected).")
            
            # Test 2 unselected swatches
            targets = unselected[:2]
            prev_img = init_img
            prev_var_id = init_var_id
            
            for t_idx, target in enumerate(targets, 1):
                swatch_name = target["name"]
                radio_id = target["id"]
                s_idx = target["idx"]
                
                print(f"\n    -> Selecting variant swatch #{t_idx}: '{swatch_name}'...")
                
                # Click the label corresponding to this swatch
                clicked = page.evaluate("""(arg) => {
                    const id = arg.id;
                    const idx = arg.idx;
                    let targetEl = null;
                    if (id) {
                        targetEl = document.querySelector(`label[for=\"${id}\"]`) || document.getElementById(id);
                    }
                    if (!targetEl) {
                        const items = document.querySelectorAll('.color-swatch, label[data-option-value]');
                        targetEl = items[idx];
                    }
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'instant', block: 'center' });
                        targetEl.click();
                        return true;
                    }
                    return false;
                }""", {"id": radio_id, "idx": s_idx})
                
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
                shot_path = os.path.join(artifacts_dir, f"random_brand_{safe_name}.png")
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
                
        # Perform Add-to-Cart on the 3rd product
        print("\n================================================================================")
        last_prod = products_to_test[-1]
        print(f"TESTING LIVE CART ADDITION ON {last_prod['title']} ({last_prod['store'].upper()})...")
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
        
        cart_shot_path = os.path.join(artifacts_dir, "random_brands_cart_drawer.png")
        page.screenshot(path=cart_shot_path, full_page=False)
        print(f"Saved cart screenshot to: {cart_shot_path}")
        
        browser.close()
        
    print("\n================================================================================")
    print("FINAL AUDIT & VERIFICATION REPORT ACROSS ALL 3 BRAND BAGS:")
    print("================================================================================")
    all_passed = True
    for r in test_results:
        print(f"[{r['status']}] [{r['store'].upper():<11}] {r['title'][:26]:<26} | Variant: {r['swatch']:<16} | Price: {r['price']:<25} | ID: {r['variant_id']}")
        if r["status"] != "PASS":
            all_passed = False
            
    print("================================================================================")
    print(f"OVERALL RESULT: {'ALL PASS (6/6 Passed)' if all_passed else 'SOME CHECKS FAILED'}")
    print(f"Console errors: {len(console_errors)}")
    print("================================================================================")

if __name__ == "__main__":
    run_tests()
