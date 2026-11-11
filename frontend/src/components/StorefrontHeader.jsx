import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { cart } from '../utils/cart.js';
import { capabilities } from '../utils/capabilities.js';
import { fetchPublicStoreSettings } from '../utils/api.js';
import { LOGO_ASSETS } from './BrandLogo.js';
import { createHeaderScroll } from '../utils/headerScroll.js';

const links = [['#featured', 'Shop'], ['#collections', 'Collections'], ['#track', 'Track Order'], ['#reassurance', 'About & Delivery'], ['#faq', 'FAQ']];
function Icon({ type }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {type === 'catalog' ? <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></> : type === 'cart' ? <><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18M8 10a4 4 0 0 0 8 0"/></> : <path d="M3 6h18M3 12h18M3 18h18"/>}
  </svg>;
}

export function StorefrontHeader({ host, onCart, onMenu, onCatalog, onTrack }) {
  const [mode, setMode] = useState('top');
  const [count, setCount] = useState(() => cart.getState().count);
  const [caps, setCaps] = useState(() => capabilities.getState());
  const [settings, setSettings] = useState(null);
  const [active, setActive] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const panel = useRef(null), announcement = useRef(null);
  const controller = useRef(createHeaderScroll());
  const compact = mode === 'compact';

  useEffect(() => cart.subscribe(state => setCount(state.count)), []);
  useEffect(() => capabilities.subscribe(setCaps), []);
  useEffect(() => {
    let alive = true;
    fetchPublicStoreSettings().then(value => { if (alive) setSettings(value); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    if (!settings) return;
    const root = document.documentElement;
    if (settings.font_family) root.style.setProperty('--font-family', settings.font_family);
    const radius = { none: '0px', sm: '4px', md: '8px', lg: '16px', full: '999px' }[settings.border_radius];
    if (radius) { root.style.setProperty('--radius-btn', radius); root.style.setProperty('--radius-control', radius); }
    root.dataset.storeSpacing = settings.spacing_density || 'comfortable';
  }, [settings]);

  useLayoutEffect(() => {
    const measure = () => {
      const height = panel.current?.offsetHeight || 72;
      host.style.height = `${height}px`;
      host.style.setProperty('--nav-announcement-height', `${announcement.current?.offsetHeight || 0}px`);
      document.documentElement.style.setProperty('--storefront-header-height', `${height}px`);
    };
    measure();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(measure);
    observer?.observe(panel.current);
    window.addEventListener('resize', measure);
    return () => { observer?.disconnect(); window.removeEventListener('resize', measure); document.documentElement.style.removeProperty('--storefront-header-height'); };
  }, [host, settings, caps.testMode]);
  useLayoutEffect(() => { host.dataset.navState = mode; }, [host, mode]);

  useEffect(() => {
    let frame = 0;
    const locked = () => document.body.classList.contains('has-overlay') || host.contains(document.activeElement) && document.activeElement.matches(':focus-visible');
    const reset = () => setMode(controller.current.reset(window.scrollY));
    const scroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        setMode(controller.current.update(window.scrollY, document.documentElement.scrollHeight - window.innerHeight, locked()));
      });
    };
    const route = event => { setActive(event.detail); reset(); };
    const overlays = new MutationObserver(() => {
      setMenuOpen(document.getElementById('mobile-nav-drawer')?.classList.contains('is-open') === true);
      reset();
    });
    overlays.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    host.addEventListener('focusin', reset); host.addEventListener('alphazee:header-route', route);
    window.addEventListener('scroll', scroll, { passive: true });
    for (const event of ['resize', 'pageshow', 'hashchange']) window.addEventListener(event, reset);
    reset();
    return () => {
      cancelAnimationFrame(frame); overlays.disconnect();
      host.removeEventListener('focusin', reset); host.removeEventListener('alphazee:header-route', route);
      window.removeEventListener('scroll', scroll);
      for (const event of ['resize', 'pageshow', 'hashchange']) window.removeEventListener(event, reset);
    };
  }, [host]);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(entries => {
      if (window.location.pathname !== '/') return;
      const visible = entries.filter(entry => entry.isIntersecting).at(-1);
      if (visible) setActive(`#${visible.target.id}`);
    }, { rootMargin: '-20% 0px -65% 0px', threshold: 0 });
    const observe = () => {
      observer.disconnect();
      for (const id of ['featured', 'collections', 'reassurance', 'faq']) {
        const section = document.getElementById(id);
        if (section) observer.observe(section);
      }
    };
    const changes = new MutationObserver(observe);
    const main = document.getElementById('main-content');
    if (main) changes.observe(main, { childList: true });
    observe();
    return () => { changes.disconnect(); observer.disconnect(); };
  }, []);

  const banner = settings?.announcement_banner_enabled !== false && settings?.announcement_banner_text;
  const bannerText = caps.testMode ? `AlphaZee SAMPLE / TEST: ${banner || 'no real orders'}` : banner;
  return <>
    <div id="header-logo-slot" className="brand-logo-container">
      <a href="/" data-nav="/" className="brand-logo-link storefront-header-logo" aria-label="AlphaZee home" title="AlphaZee home" onClick={() => { if (typeof window !== 'undefined' && window.scrollY > 0) { window.scrollTo({ top: 0, behavior: 'smooth' }); } }}>
        <img className="brand-logo-img logo-variant-wordmark" src={LOGO_ASSETS.wordmark} width="125" height="42" alt=""/>
        <img className="brand-logo-img logo-variant-combined" src={LOGO_ASSETS.combined} width="165" height="55" alt=""/>
        <img className="brand-logo-img logo-variant-compact" src={LOGO_ASSETS.symbol} width="36" height="36" alt=""/>
      </a>
    </div>
    <div ref={panel} className="header-panel" inert={compact} aria-hidden={compact}>
      <div ref={announcement} className="announcement-bar" role="region" aria-label="Store announcement" style={{ display: bannerText ? 'block' : 'none', backgroundColor: settings?.accent_color || undefined }}>
        {settings?.announcement_banner_link?.startsWith('#') ? <a href={settings.announcement_banner_link}>{bannerText}</a> : <span>{bannerText}</span>}
      </div>
      <div className="container"><div className="header-inner">
        <div className="header-brand-space" aria-hidden="true"/>
        <nav className="nav-desktop" aria-label="Primary navigation">
          {links.map(([href, label]) => <a key={href} href={href} id={href === '#track' ? 'nav-track-order' : undefined} className={`nav-link${active === href ? ' is-active' : ''}`} aria-current={active === href ? 'page' : undefined} onClick={href === '#track' ? event => { event.preventDefault(); onTrack?.(); } : undefined}>{label}</a>)}
        </nav>
        <div className="header-actions">
          <button type="button" className="header-action-btn" id="btn-browse-catalog" aria-label="Browse catalog" title="Browse catalog" onClick={onCatalog}><Icon type="catalog"/></button>
          <button type="button" className="header-action-btn" id="btn-cart" aria-label="Open shopping cart" onClick={onCart}><Icon type="cart"/><span className="cart-count-badge" id="header-cart-count" style={{ display: count ? 'flex' : 'none' }}>{count > 99 ? '99+' : count}</span></button>
          <button type="button" className="header-action-btn menu-toggle-btn" id="btn-mobile-menu" aria-label="Toggle mobile menu" aria-expanded={menuOpen} aria-controls="mobile-nav-drawer" onClick={onMenu}><Icon type="menu"/></button>
        </div>
      </div></div>
    </div>
  </>;
}
