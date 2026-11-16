import { Component } from '@theme/component';
import { onAnimationEnd } from '@theme/utilities';
import { StandardEvents, CartLinesUpdateEvent } from '@shopify/events';

function getPhysicalItemCount(cart, detail, fallback) {
  const items = (cart && Array.isArray(cart.items)) ? cart.items : (detail && Array.isArray(detail.items)) ? detail.items : null;
  if (items) {
    return items.reduce((total, item) => {
      const isCert = String(item.product_id) === '15886266794150' ||
                     String(item.variant_id) === '57721101779110' ||
                     (item.title && item.title.includes('CheckCheck')) ||
                     (item.handle === 'checkcheck-certificate') ||
                     (item.handle === 'official-checkcheck-certificate-of-authenticity');
      return isCert ? total : total + (item.quantity || 0);
    }, 0);
  }

  const lines = cart?.lines;
  if (Array.isArray(lines) && lines.length > 0) {
    return lines.reduce((total, line) => {
      const merchId = String(line.merchandise?.id || line.merchandiseId || '');
      const title = String(line.merchandise?.title || line.merchandise?.product?.title || '');
      const isCert = merchId.includes('57721101779110') ||
                     merchId.includes('15886266794150') ||
                     title.includes('CheckCheck');
      return isCert ? total : total + (line.quantity || 0);
    }, 0);
  }

  return fallback ?? 0;
}

/**
 * A custom element that displays a cart icon.
 *
 * @typedef {object} Refs
 * @property {HTMLElement} cartBubble - The cart bubble element.
 * @property {HTMLElement} cartBubbleText - The cart bubble text element.
 * @property {HTMLElement} cartBubbleCount - The cart bubble count element.
 *
 * @extends {Component<Refs>}
 */
class CartIcon extends Component {
  requiredRefs = ['cartBubble', 'cartBubbleText', 'cartBubbleCount'];

  /** @type {AbortController | null} */
  #historyCartController = null;

  /** @type {number} */
  #cartRenderRevision = 0;

  /** @type {number} */
  get currentCartCount() {
    return parseInt(this.refs.cartBubbleCount.textContent ?? '0', 10);
  }

  set currentCartCount(value) {
    this.refs.cartBubbleCount.textContent = value < 100 ? String(value) : '';
  }

  connectedCallback() {
    super.connectedCallback();

    document.addEventListener(StandardEvents.cartLinesUpdate, this.onCartUpdate);
    window.addEventListener('pageshow', this.onPageShow);
    this.ensureCartBubbleIsCorrect();

    // A full history reload can emit pageshow before this module upgrades the element.
    if (CartIcon.#getNavigationType() === 'back_forward') {
      this.#reconcileHistoryCart();
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();

    document.removeEventListener(StandardEvents.cartLinesUpdate, this.onCartUpdate);
    window.removeEventListener('pageshow', this.onPageShow);
    this.#historyCartController?.abort();
    this.#historyCartController = null;
  }

  /**
   * Handles the page show event when the page is restored from cache.
   * @param {PageTransitionEvent} event - The page show event.
   */
  onPageShow = async (event) => {
    if (!event.persisted) return;

    await this.#reconcileHistoryCart();
  };

  /**
   * Handles the cart update event.
   * @param {CartLinesUpdateEvent} event - The cart update event.
   */
  onCartUpdate = (event) => {
    event.promise
      ?.then(({ cart, detail }) => {
        let itemCount = getPhysicalItemCount(cart, detail, detail?.itemCount ?? cart?.totalQuantity ?? 0);

        this.#cartRenderRevision += 1;
        this.#historyCartController?.abort();
        this.renderCartBubble(itemCount);
      })
      .catch((error) => {
        if (error?.name !== 'AbortError') console.warn('[cart-icon] Event promise rejected:', error);
      });
  };

  /**
   * Renders the cart bubble.
   * @param {number} itemCount - The absolute number of items in the cart.
   * @param {boolean} [animate=true] - Whether to animate the bubble.
   */
  renderCartBubble = async (itemCount, animate = true) => {
    this.refs.cartBubbleCount.classList.toggle('hidden', itemCount === 0);
    this.refs.cartBubble.classList.toggle('visually-hidden', itemCount === 0);

    this.currentCartCount = itemCount;

    this.classList.toggle('header-actions__cart-icon--has-cart', itemCount > 0);

    sessionStorage.setItem(
      'cart-count',
      JSON.stringify({
        value: String(this.currentCartCount),
        timestamp: Date.now(),
      })
    );

    if (!animate || itemCount === 0) return;

    // Ensure element is visible before starting animation
    // Use requestAnimationFrame to ensure the browser sees the state change
    await new Promise((resolve) => requestAnimationFrame(resolve));

    this.refs.cartBubble.classList.add('cart-bubble--animating');
    await onAnimationEnd(this.refs.cartBubbleText);

    this.refs.cartBubble.classList.remove('cart-bubble--animating');
  };

  /**
   * Checks if the cart count is correct and prevents restoring stale pre-removal counts.
   */
  ensureCartBubbleIsCorrect = () => {
    // Ensure refs are available
    if (!this.refs.cartBubbleCount) return;

    const isCartSurface = window.location.pathname.replace(/\/+$/, '') === (window.Theme?.routes?.cart_url || '/cart').replace(/\/+$/, '');
    const isPageReload = CartIcon.#getNavigationType() === 'reload';
    const isVisuallyHidden = this.refs.cartBubble?.classList.contains('visually-hidden');

    // 1. Authoritative Surface Guard:
    // On /cart or explicit page reload, the server-rendered Liquid count is authoritative.
    // Never overwrite server-rendered count with client sessionStorage.
    if (isCartSurface || isPageReload) {
      const text = this.refs.cartBubbleCount.textContent?.trim();
      const authoritativeCount = isVisuallyHidden ? 0 : (parseInt(text || '0', 10) || 0);
      sessionStorage.setItem('cart-count', JSON.stringify({ value: String(authoritativeCount), timestamp: Date.now() }));
      return;
    }

    // 2. Empty Bubble Guard:
    if (isVisuallyHidden) {
      const sessionStorageCount = sessionStorage.getItem('cart-count');
      if (sessionStorageCount) {
        try {
          const { value, timestamp } = JSON.parse(sessionStorageCount);
          if (Date.now() - timestamp < 10000 && parseInt(value, 10) > 0) {
            // Asynchronously verify with authoritative physical cart before altering DOM
            this.#reconcileHistoryCart();
            return;
          }
        } catch (_) {}
      }
      sessionStorage.setItem('cart-count', JSON.stringify({ value: '0', timestamp: Date.now() }));
      return;
    }

    const sessionStorageCount = sessionStorage.getItem('cart-count');
    if (sessionStorageCount === null) return;

    const text = this.refs.cartBubbleCount.textContent?.trim();
    const visibleCount = parseInt(text || '0', 10) || 0;

    try {
      const { value, timestamp } = JSON.parse(sessionStorageCount);
      const storedCount = parseInt(value, 10);

      // Matches DOM count: all consistent
      if (storedCount === visibleCount) return;

      // 3. Anti-Resurrection Guard:
      // If server rendered a positive count (visibleCount > 0), and storedCount > visibleCount,
      // an item was removed or scaled down. NEVER resurrect the higher pre-removal count!
      if (storedCount > visibleCount && visibleCount > 0) {
        sessionStorage.setItem('cart-count', JSON.stringify({ value: String(visibleCount), timestamp: Date.now() }));
        this.#reconcileHistoryCart();
        return;
      }

      // 4. Stale Expiry & Asynchronous Reconciliation:
      if (Date.now() - timestamp < 10000 && storedCount >= 0) {
        this.#reconcileHistoryCart();
      } else {
        sessionStorage.setItem('cart-count', JSON.stringify({ value: String(visibleCount), timestamp: Date.now() }));
      }
    } catch (_) {
      // no-op
    }
  };

  /**
   * Reconciles history-restored markup with the authoritative cart response.
   */
  #reconcileHistoryCart = async () => {
    this.#historyCartController?.abort();
    const controller = new AbortController();
    const cartRenderRevision = this.#cartRenderRevision;
    this.#historyCartController = controller;

    try {
      const cartUrl = window.Theme?.routes?.cart_url || '/cart';
      const response = await fetch(`${cartUrl}.json`, {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
        cache: 'no-store',
        signal: controller.signal,
      });
      if (controller.signal.aborted || this.#historyCartController !== controller) return;
      if (!response.ok) throw new Error(`Cart request failed with status ${response.status}`);

      const cart = await response.json();
      if (controller.signal.aborted || this.#historyCartController !== controller) return;

      let itemCount = getPhysicalItemCount(cart, null, cart?.item_count ?? 0);
      if (!Number.isInteger(itemCount) || itemCount < 0) throw new Error('Cart response has an invalid item count');
      if (this.#cartRenderRevision !== cartRenderRevision) return;

      await this.renderCartBubble(itemCount, false);
    } catch (error) {
      if (error?.name !== 'AbortError') console.warn('[cart-icon] History reconciliation failed:', error);
    } finally {
      if (this.#historyCartController === controller) this.#historyCartController = null;
    }
  };

  /**
   * Narrows a performance entry before reading its navigation type.
   * @param {PerformanceEntry | undefined} entry
   * @returns {entry is PerformanceNavigationTiming}
   */
  static #isNavigationTiming(entry) {
    return entry?.entryType === 'navigation';
  }

  /**
   * Returns the current document's navigation type.
   */
  static #getNavigationType() {
    const navigationEntry = globalThis.performance?.getEntriesByType?.('navigation')[0];
    return CartIcon.#isNavigationTiming(navigationEntry) ? navigationEntry.type : undefined;
  }
}

if (!customElements.get('cart-icon')) {
  customElements.define('cart-icon', CartIcon);
}
