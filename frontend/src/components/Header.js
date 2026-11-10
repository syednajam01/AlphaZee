import { createElement } from 'react';
import { createRoot } from 'react-dom/client';
import { StorefrontHeader } from './StorefrontHeader.jsx';

// The router owns this host; React exclusively owns the contents.
export function createHeader(actions = {}) {
  const host = document.createElement('header');
  host.className = 'site-header';
  host.id = 'site-header';
  const root = createRoot(host);
  host.setActiveNav = target => host.dispatchEvent(new CustomEvent('alphazee:header-route', { detail: target }));
  host.destroy = () => root.unmount();
  root.render(createElement(StorefrontHeader, { host, ...actions }));
  return host;
}
