import './styles/main.css';
import { startStorefront } from './utils/startup.js';

if (import.meta.env.VITE_CHECKOUT_LAB === 'true') {
  const notice = document.createElement('div');
  notice.setAttribute('role', 'status');
  notice.className = 'checkout-lab-notice';
  notice.textContent = 'SAMPLE CHECKOUT LAB — simulated orders and payment verification only. Do not transfer real money.';
  document.body.prepend(notice);

  const updateNoticeHeight = () => {
    const h = notice.offsetHeight || 0;
    document.documentElement.style.setProperty('--lab-notice-height', `${h}px`);
  };
  updateNoticeHeight();
  window.addEventListener('resize', updateNoticeHeight);
  if (typeof ResizeObserver !== 'undefined') {
    new ResizeObserver(updateNoticeHeight).observe(notice);
  }
}

// Remote typography must not hold up a usable local store/dashboard.
const fonts = document.getElementById('brand-fonts');
if (fonts?.sheet) fonts.media = 'all';
else fonts?.addEventListener('load', () => { fonts.media = 'all'; }, { once: true });

startStorefront(() => {
  const path = window.location.pathname;
  if (path === '/admin' || path.startsWith('/admin/')) {
    return import('./components/AdminDashboard.js').then(module => ({ initApp: module.initAdminDashboard }));
  }
  if (path === '/vendor' || path.startsWith('/vendor/')) {
    return import('./components/VendorPortal.js').then(module => ({ initApp: module.initVendorPortal }));
  }
  return import('./app.js');
});
