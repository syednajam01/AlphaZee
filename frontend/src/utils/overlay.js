// One active dialog at a time. Closed roots are hidden and inert, including
// descendants whose CSS might otherwise override inherited visibility.
let activeOverlay = null;

export function createOverlay({ element, backdrop = null, onClose = () => {}, onEscape = null }) {
  let opener = null;
  let previousOverflow = '';
  const surfaces = backdrop ? [element, backdrop] : [element];

  function setOpen(open) {
    surfaces.forEach(surface => {
      surface.hidden = !open;
      surface.inert = !open;
      surface.setAttribute('aria-hidden', String(!open));
      if (open) surface.classList.add('is-open');
      else surface.classList.remove('is-open');
    });
  }

  function focusableElements() {
    return [...element.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')]
      .filter(node => !node.disabled && !node.hidden && node.tabIndex !== -1
        && (node.getClientRects?.().length ?? 1) > 0);
  }

  function onKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      if (!onEscape?.()) close();
    } else if (event.key === 'Tab') {
      const elements = focusableElements();
      const first = elements[0];
      const last = elements.at(-1);
      if (!first) { event.preventDefault(); element.focus?.(); return; }
      if (event.shiftKey && (document.activeElement === first || !element.contains(document.activeElement))) {
        event.preventDefault(); last.focus?.();
      } else if (!event.shiftKey && (document.activeElement === last || !element.contains(document.activeElement))) {
        event.preventDefault(); first.focus?.();
      }
    }
  }

  function open() {
    if (activeOverlay === controller) return;
    activeOverlay?.close();
    opener = document.activeElement;
    previousOverflow = document.body.style.overflow || '';
    setOpen(true);
    activeOverlay = controller;
    document.body.style.overflow = 'hidden';
    document.body?.classList?.add('has-overlay');
    document.addEventListener?.('keydown', onKeyDown);
    (focusableElements()[0] || element).focus?.();
  }

  function close() {
    const wasOpen = activeOverlay === controller;
    setOpen(false);
    if (!wasOpen) return;
    activeOverlay = null;
    document.removeEventListener?.('keydown', onKeyDown);
    document.body.style.overflow = previousOverflow;
    document.body?.classList?.remove('has-overlay');
    onClose();
    if (opener?.isConnected !== false) opener?.focus?.();
  }

  element.setAttribute('tabindex', '-1');
  element.setAttribute('aria-modal', 'true');
  setOpen(false);
  const controller = { open, close };
  return controller;
}
