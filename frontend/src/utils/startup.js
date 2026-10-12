export function startStorefront(loadApp, doc = document) {
  async function start() {
    try {
      const { initApp } = await loadApp();
      initApp();
    } catch (error) {
      console.error('Storefront startup failed:', error);
      const app = doc.getElementById('app');
      if (!app) return;
      app.innerHTML = '<section class="catalog-status-box is-error" role="alert"><h1>Unable to open the store</h1><p>Please reload to try again. Your saved cart is kept.</p><button type="button" class="btn btn-primary" id="retry-store-startup">Reload store</button></section>';
      app.querySelector('#retry-store-startup').addEventListener('click', () => doc.defaultView.location.reload());
    }
  }
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start, { once: true });
  else return start();
}
