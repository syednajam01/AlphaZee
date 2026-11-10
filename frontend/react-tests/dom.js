import { JSDOM } from 'jsdom';

export function installDom() {
  const dom = new JSDOM('<!doctype html><html><body><div id="app"></div></body></html>', { url: 'http://localhost/', pretendToBeVisual: true });
  for (const key of ['window', 'document', 'HTMLElement', 'Element', 'Node', 'CustomEvent', 'MutationObserver']) globalThis[key] = key === 'window' ? dom.window : dom.window[key];
  globalThis.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window);
  globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window);
  dom.window.scrollTo = () => {};
  dom.window.matchMedia = () => ({ matches: false });
  dom.window.HTMLElement.prototype.scrollIntoView = function () { this.scrolledIntoView = true; };
  return { dom, doc: dom.window.document, app: dom.window.document.getElementById('app') };
}
