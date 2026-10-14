import './styles/main.css';
import { startStorefront } from './utils/startup.js';

// Remote typography must not hold up a usable local store/dashboard.
const fonts = document.getElementById('brand-fonts');
if (fonts?.sheet) fonts.media = 'all';
else fonts?.addEventListener('load', () => { fonts.media = 'all'; }, { once: true });

startStorefront(() => window.location.pathname === '/admin' || window.location.pathname.startsWith('/admin/')
  ? import('./components/AdminDashboard.js').then(module => ({ initApp: module.initAdminDashboard }))
  : import('./app.js'));
