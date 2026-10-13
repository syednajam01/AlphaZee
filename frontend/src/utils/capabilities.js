import { fetchStorefrontCapabilities } from './api.js';

export const CHECKOUT_UNAVAILABLE = 'Checkout is temporarily unavailable. You can still browse and save your cart.';

export function createCapabilitiesStore(fetchCapabilities = fetchStorefrontCapabilities) {
  let state = { checkoutEnabled: false, testMode: false, paymentMethods: ['cod'] };
  let pending = null;
  const listeners = new Set();
  function publish(next) {
    state = Object.freeze(next);
    listeners.forEach(listener => listener(state));
  }
  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
    refresh() {
      if (pending) return pending;
      publish({ checkoutEnabled: false, testMode: false, paymentMethods: ['cod'] });
      pending = Promise.resolve().then(fetchCapabilities).then(data => {
        const enabled = data?.checkout_enabled === true && data?.test_mode === true;
        const paymentMethods = Array.isArray(data?.payment_methods)
          ? data.payment_methods.filter(method => method === 'cod' || method === 'bank_transfer') : ['cod'];
        publish({ checkoutEnabled: enabled, testMode: enabled, paymentMethods });
      }).catch(() => {
        publish({ checkoutEnabled: false, testMode: false, paymentMethods: ['cod'] });
      }).finally(() => { pending = null; });
      return pending;
    },
  };
}

export const capabilities = createCapabilitiesStore();
