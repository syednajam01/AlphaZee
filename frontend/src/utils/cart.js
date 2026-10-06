class CartStore {
  constructor() {
    this.storageKey = 'alphazee_cart_v1';
    this.items = this.load();
    this.listeners = new Set();
  }

  load() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  save() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.items));
    } catch (e) {
      console.warn('Failed to save cart to localStorage', e);
    }
    this.notify();
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.getState());
    return () => this.listeners.delete(listener);
  }

  notify() {
    const state = this.getState();
    this.listeners.forEach((fn) => fn(state));
  }

  getState() {
    const count = this.items.reduce((sum, item) => sum + item.quantity, 0);
    const total = this.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    return {
      items: [...this.items],
      count,
      total,
      formattedTotal: `PKR ${total.toLocaleString()}`
    };
  }

  addItem(product, options = {}, quantity = 1) {
    const itemKey = `${product.id}_${options.size || ''}_${options.color || ''}`;
    const existingIndex = this.items.findIndex(item => item.key === itemKey);

    if (existingIndex > -1) {
      this.items[existingIndex].quantity += quantity;
    } else {
      this.items.push({
        key: itemKey,
        id: product.id,
        title: product.title,
        price: product.price,
        formattedPrice: product.formattedPrice,
        image: product.image,
        options,
        quantity
      });
    }
    this.save();
  }

  updateQuantity(itemKey, delta) {
    const itemIndex = this.items.findIndex(item => item.key === itemKey);
    if (itemIndex > -1) {
      this.items[itemIndex].quantity += delta;
      if (this.items[itemIndex].quantity <= 0) {
        this.items.splice(itemIndex, 1);
      }
      this.save();
    }
  }

  removeItem(itemKey) {
    this.items = this.items.filter(item => item.key !== itemKey);
    this.save();
  }

  clear() {
    this.items = [];
    this.save();
  }
}

export const cart = new CartStore();
