const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

// Minimal DOM mock for Node test runner
export function createMockElement(tagName) {
  const el = {
    tagName: tagName.toUpperCase(),
    className: '',
    id: '',
    style: {},
    dataset: {},
    children: [],
    _listeners: {},
    _innerHTML: '',
    _textContent: '',
    hidden: false,
    inert: false,
    disabled: false,
    focus() { globalThis.document.activeElement = this; },
    scrollIntoView() { this.scrolledIntoView = true; },
    getClientRects() { return this.hidden ? [] : [{}]; },
    contains(target) { return target === this || this.children.some(child => child.contains(target)); },
    removeEventListener(type, listener) {
      this._listeners[type] = (this._listeners[type] || []).filter(fn => fn !== listener);
    },
    click() {
      if (!this.disabled && !this.inert) this.dispatchEvent({ type: 'click', target: this, preventDefault() {} });
    },

    setAttribute(name, val) {
      if (name === 'disabled') { this.disabled = true; return; }
      if (name === 'style') {
        if (typeof val === 'string') {
          val.split(';').forEach(rule => {
            const [prop, v] = rule.split(':');
            if (prop && v) this.style[prop.trim()] = v.trim();
          });
        }
        return;
      }
      this[name] = val;
    },
    getAttribute(name) {
      return this[name] || null;
    },
    appendChild(child) {
      this.children.push(child);
      child.parentElement = this;
      return child;
    },
    prepend(child) {
      this.children.unshift(child);
      child.parentElement = this;
      return child;
    },
    addEventListener(event, fn) {
      if (!this._listeners[event]) this._listeners[event] = [];
      this._listeners[event].push(fn);
    },
    dispatchEvent(event) {
      const fns = this._listeners[event.type || event] || [];
      fns.forEach(fn => fn(event));
    },
    classList: {
      _classes: new Set(),
      add(cls) { this._classes.add(cls); },
      remove(cls) { this._classes.delete(cls); },
      contains(cls) { return this._classes.has(cls); },
      toggle(cls, force) {
        const add = force ?? !this._classes.has(cls);
        if (add) this._classes.add(cls); else this._classes.delete(cls);
        return add;
      },
    },

    querySelector(selector) {
      const results = this.querySelectorAll(selector);
      return results.length > 0 ? results[0] : null;
    },

    querySelectorAll(selector) {
      const descendant = selector.match(/^([#.][\w-]+)\s+(.+)$/);
      if (descendant) return this.querySelectorAll(descendant[1]).flatMap(node => node.querySelectorAll(descendant[2]));
      if (selector.includes(',')) return [...new Set(selector.split(',').flatMap(part => this.querySelectorAll(part.trim())))];
      const compound = selector.match(/^([a-z]+)(\[.+\])$/);
      if (compound) return this.querySelectorAll(compound[2]).filter(node => node.tagName.toLowerCase() === compound[1]);
      const matches = [];

      function search(node) {
        if (!node) return;
        if (selector.startsWith('#')) {
          const id = selector.slice(1);
          if (node.id === id) matches.push(node);
        } else if (selector.startsWith('.')) {
          const cls = selector.slice(1);
          if (node.className && node.className.split(/\s+/).includes(cls)) {
            matches.push(node);
          }
        } else if (selector.startsWith('[')) {
          const attrMatch = selector.match(/\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/);
          if (attrMatch) {
            const attr = attrMatch[1];
            const val = attrMatch[2];
            if (attr.startsWith('data-')) {
              const key = attr.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
              if (val !== undefined) {
                if (node.dataset && node.dataset[key] === val) matches.push(node);
              } else if (node.dataset && node.dataset[key] !== undefined) {
                matches.push(node);
              }
            } else if (val !== undefined) {
              if (node[attr] === val || node.getAttribute?.(attr) === val) matches.push(node);
            } else if (node[attr] !== undefined || node.getAttribute?.(attr) !== null) {
              matches.push(node);
            }
          }
        } else if (node.tagName && node.tagName.toLowerCase() === selector.toLowerCase()) {
          matches.push(node);
        }

        if (Array.isArray(node.children)) {
          for (const child of node.children) {
            search(child);
          }
        }
      }

      if (this.children) {
        for (const child of this.children) {
          search(child);
        }
      }
      return matches;
    },
  };

  Object.defineProperty(el, 'innerHTML', {
    get() { return this._innerHTML; },
    set(html) {
      this._innerHTML = html;
      this.children = [];
      parseHtmlIntoChildren(html, this);
    }
  });

  Object.defineProperty(el, 'textContent', {
    get() {
      if (this.children.length === 0) return this._textContent || this._innerHTML.replace(/<[^>]*>/g, '');
      return this.children.map(c => c.textContent || '').join('');
    },
    set(txt) {
      this._textContent = txt;
      this._innerHTML = txt;
      this.children = [];
    }
  });

  return el;
}

function parseHtmlIntoChildren(html, root) {
  if (typeof html !== 'string') return;
  const stack = [root];
  const tokenRegex = /<!--[\s\S]*?-->|<(\/)?([a-z0-9-]+)([^>]*)>|([^<]+)/gi;
  let match;

  while ((match = tokenRegex.exec(html)) !== null) {
    if (match[0].startsWith('<!--')) continue;

    const isClosing = match[1] === '/';
    const tagName = match[2];
    const attrsStr = match[3];
    const textContent = match[4];

    if (textContent) {
      const top = stack[stack.length - 1];
      if (top) {
        top._textContent = (top._textContent || '') + textContent;
      }
      continue;
    }

    if (isClosing) {
      const lower = tagName.toLowerCase();
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].tagName.toLowerCase() === lower) {
          stack.splice(i);
          break;
        }
      }
    } else {
      const el = createMockElement(tagName);
      if (attrsStr) {
        const attrRegex = /([a-z0-9_-]+)(?:=(?:"([^"]*)"|'([^']*)'|(\S+)))?/gi;
        let attrMatch;
        while ((attrMatch = attrRegex.exec(attrsStr)) !== null) {
          const name = attrMatch[1].toLowerCase();
          const val = attrMatch[2] ?? attrMatch[3] ?? attrMatch[4] ?? '';
          if (name === 'class') {
            el.className = val;
            val.split(/\s+/).filter(Boolean).forEach(c => el.classList.add(c));
          } else if (name === 'id') {
            el.id = val;
          } else if (name.startsWith('data-')) {
            const dataKey = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
            el.dataset[dataKey] = val;
          }
          el.setAttribute(name, val);
        }
      }

      const top = stack[stack.length - 1];
      if (top) top.appendChild(el);

      if (!VOID_TAGS.has(tagName.toLowerCase())) {
        stack.push(el);
      }
    }
  }
}

