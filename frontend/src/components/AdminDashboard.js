import { createAdminConsoleModal } from './AdminConsole.js';

const sections = new Set(['overview', 'products', 'collections', 'media', 'inventory',
  'suppliers', 'orders', 'returns', 'coupons', 'reports']);

export function adminSection(pathname) {
  const path = pathname.replace(/\/+$/, '');
  if (path === '/admin') return 'overview';
  const section = path.slice('/admin/'.length);
  return path.startsWith('/admin/') && sections.has(section) ? section : 'not-found';
}

export function initAdminDashboard() {
  const root = document.getElementById('app');
  let currentPath = window.location.pathname;
  let index = 0;
  let restoringHistory = false;
  window.history.replaceState({ ...window.history.state, adminIndex: index }, '', currentPath);
  const internalTab = section => section === 'reports' ? 'analytics' : section;
  const dashboard = createAdminConsoleModal({ page: true,
    initialTab: internalTab(adminSection(currentPath)),
    onNavigate(tab) {
      const section = tab === 'analytics' ? 'reports' : tab;
      const path = section === 'overview' ? '/admin' : `/admin/${section}`;
      window.history.pushState({ adminIndex: ++index }, '', path);
      currentPath = path;
      dashboard.selectTab(tab, { checkDirty: false });
    },
  });
  root.innerHTML = '';
  root.appendChild(dashboard.element);
  document.title = 'AlphaZee — Owner dashboard';
  const popstate = event => {
    if (restoringHistory) { restoringHistory = false; return; }
    if (!dashboard.canLeave()) {
      const targetIndex = event.state?.adminIndex;
      if (Number.isInteger(targetIndex) && targetIndex !== index) {
        restoringHistory = true;
        window.history.go(index - targetIndex);
      }
      else window.history.replaceState({ adminIndex: index }, '', currentPath);
      return;
    }
    currentPath = window.location.pathname;
    index = event.state?.adminIndex ?? index;
    dashboard.selectTab(internalTab(adminSection(currentPath)), { checkDirty: false });
  };
  window.addEventListener('popstate', popstate);
  dashboard.ready = dashboard.open();
  const destroy = dashboard.destroy;
  dashboard.destroy = () => { window.removeEventListener('popstate', popstate); destroy(); };
  return dashboard;
}
