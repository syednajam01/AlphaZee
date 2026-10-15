import './styles/main.css';
import { startStorefront } from './utils/startup.js';

if (import.meta.env.VITE_CHECKOUT_LAB === 'true') {
  const notice = document.createElement('div');
  notice.setAttribute('role', 'status');
  notice.className = 'checkout-lab-notice';
  notice.textContent = 'SAMPLE CHECKOUT LAB — simulated orders and payment verification only. Do not transfer real money.';
  document.body.prepend(notice);
}

// Remote typography must not hold up a usable local store/dashboard.
const fonts = document.getElementById('brand-fonts');
if (fonts?.sheet) fonts.media = 'all';
else fonts?.addEventListener('load', () => { fonts.media = 'all'; }, { once: true });

startStorefront(() => window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin/')
  ? import('./components/AdminDashboard.js').then(module => ({ initApp: module.initAdminDashboard }))
  : import('./app.js'));
