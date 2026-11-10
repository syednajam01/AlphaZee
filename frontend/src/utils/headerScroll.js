export function createHeaderScroll(initialY = 0) {
  let last = Math.max(0, initialY), extreme = last, direction = 0;
  let state = last <= 12 ? 'top' : 'expanded';
  return {
    reset(y = 0) {
      last = extreme = Math.max(0, y); direction = 0;
      return (state = last <= 12 ? 'top' : 'expanded');
    },
    update(y, maxY = Infinity, locked = false) {
      const next = Math.max(0, Math.min(y, Math.max(0, maxY)));
      if (locked || next <= 12) return this.reset(next);
      const delta = next - last; last = next;
      if (!delta) return state;
      const sign = Math.sign(delta);
      if (sign !== direction) { direction = sign; extreme = next - delta; }
      const travelled = Math.abs(next - extreme);
      if (sign > 0 && next >= 32 && travelled >= 6) state = 'compact';
      else if (sign < 0 && travelled >= 6) state = 'expanded';
      else if (state === 'top') state = 'expanded';
      return state;
    },
  };
}
