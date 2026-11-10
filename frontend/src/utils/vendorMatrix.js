const sizeOrder = ['XXXS', 'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '2XL', 'XXXL', '3XL', '4XL', '5XL'];
export const MAX_VENDOR_COUNT = 2147483647;

export function parseVendorCount(value) {
  if (!/^\d+$/.test(String(value))) return null;
  const count = Number(value);
  return Number.isSafeInteger(count) && count <= MAX_VENDOR_COUNT ? count : null;
}

export function groupVendorStock(items) {
  const groups = new Map();
  for (const item of items) {
    const color = item.color || null;
    const key = JSON.stringify([String(item.product_id), color]);
    if (!groups.has(key)) groups.set(key, { key, title: item.product_title, color: color || 'Standard', thumbnail: item.thumbnail_url, items: [] });
    groups.get(key).items.push(item);
  }
  for (const group of groups.values()) group.items.sort((a, b) => {
    const rank = value => { const index = sizeOrder.indexOf(String(value || '').toUpperCase()); return index < 0 ? sizeOrder.length : index; };
    return rank(a.size) - rank(b.size) || String(a.size || '').localeCompare(String(b.size || ''), undefined, { numeric: true }) || a.variant_id - b.variant_id;
  });
  return [...groups.values()];
}

// Drafts survive page/search/refresh, but versions are never silently rebased.
export class VendorCountDrafts {
  constructor() { this.entries = new Map(); }
  clear() { this.entries.clear(); }
  reset(id) { this.entries.delete(id); }
  get(id) { return this.entries.get(id); }
  pending(ids = null) {
    return [...this.entries.values()].filter(draft => draft.dirty && (!ids || ids.includes(draft.item.variant_id)));
  }
  reconcile(items) {
    for (const item of items) {
      const draft = this.get(item.variant_id);
      if (!draft) continue;
      if (draft.dirty && item.version !== draft.baseVersion) {
        draft.needsReview = true; draft.status = 'conflict';
        draft.message = 'Stock changed elsewhere. Review the recorded count, then use latest to discard this edit.';
      } else if (!draft.dirty && item.version !== draft.baseVersion) {
        this.reset(item.variant_id); continue;
      }
      draft.item = { ...item };
    }
  }
  edit(item, value) {
    let draft = this.get(item.variant_id);
    if (!draft?.dirty) draft = { item: { ...item }, baseVersion: item.version, needsReview: false };
    if (parseVendorCount(value) === item.allocated_on_hand && !draft.needsReview) { this.reset(item.variant_id); return; }
    Object.assign(draft, { value: String(value), dirty: true, status: draft.needsReview ? 'conflict' : 'edited', message: '', requestRef: globalThis.crypto?.randomUUID?.() });
    this.entries.set(item.variant_id, draft);
  }
  snapshot(ids) {
    const changes = ids ? ids.map(id => this.get(id)).filter(draft => draft?.dirty) : this.pending();
    return changes.map(draft => ({ ...draft, item: { ...draft.item }, count: parseVendorCount(draft.value) }));
  }
  saving(id) { const draft = this.get(id); if (draft) draft.status = 'saving'; }
  acknowledge(id, result) {
    const draft = this.get(id);
    if (!draft) return;
    draft.item = { ...draft.item, ...result };
    draft.baseVersion = result.version; draft.dirty = false; draft.needsReview = false;
    draft.status = result.shortage_detected ? 'reported' : 'saved';
    draft.message = result.shortage_detected ? `Shortage reported: ${draft.value} units. Recorded stock stays ${result.allocated_on_hand}; customer holds are preserved.` : 'Saved';
    if (!result.shortage_detected) draft.value = String(result.allocated_on_hand);
  }
  fail(id, error) {
    const draft = this.get(id);
    if (!draft) return;
    draft.status = error.status === 409 ? 'conflict' : 'error';
    draft.needsReview = error.status === 409;
    draft.message = error.status === 409 ? 'Stock changed elsewhere. Refresh, review the recorded count, then use latest before editing again.' : `Not saved: ${error.message || 'Please retry'}`;
  }
}
