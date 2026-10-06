export const storeConfig = {
  name: 'AlphaZee',
  tagline: 'Modern Apparel & Curated Essentials',
  currency: 'PKR',
  currencySymbol: 'Rs. ',
  shippingInfo: {
    standardTime: '3–5 business days nationwide',
    standardRate: 'Calculated at checkout',
    podNote: 'Originals are crafted on demand (2–4 days production + 3 days transit)',
  },
  reassurance: [
    {
      id: 'delivery',
      title: 'Reliable Nationwide Delivery',
      desc: 'Tracked shipping across Pakistan with verified courier partners.',
      icon: 'truck'
    },
    {
      id: 'payments',
      title: 'Secure Payments',
      desc: 'Direct bank transfer and verified online payment gateways.',
      icon: 'shield-check'
    },
    {
      id: 'support',
      title: 'Direct WhatsApp Support',
      desc: 'Human assistance for sizing, tracking, and custom inquiries.',
      icon: 'message-circle'
    }
  ],
  faqs: [
    {
      q: 'How long does delivery take?',
      a: 'In-stock supplier items ship within 24 hours and typically arrive within 3–5 business days across Pakistan. Made-to-order AlphaZee Originals take 2–4 days for crafting before courier handover.'
    },
    {
      q: 'How can I pay for my order?',
      a: 'We accept direct bank transfers, debit/credit cards, and verified local payment methods. All payments are encrypted and securely processed.'
    },
    {
      q: 'What is the return & exchange policy?',
      a: 'Unworn items with original tags can be exchanged within 7 days of delivery. For size exchanges, contact our support team on WhatsApp.'
    },
    {
      q: 'How do I choose the correct size?',
      a: 'Each apparel product features an exact size specification chart in inches. If you are between sizes, we recommend sizing up.'
    }
  ],
  footerLinks: {
    shop: [
      { label: 'All Products', href: '#shop' },
      { label: 'Collections', href: '#collections' },
      { label: 'New Arrivals', href: '#featured' },
    ],
    customerCare: [
      { label: 'Contact on WhatsApp', href: 'https://wa.me/yourwhatsapp' },
      { label: 'Track Your Order', href: '#track' },
      { label: 'Shipping & Delivery', href: '#reassurance' },
      { label: 'Returns & Exchange', href: '#faq' },
    ],
    legal: [
      { label: 'Privacy Policy', href: '#privacy' },
      { label: 'Terms of Service', href: '#terms' },
      { label: 'Admin Console (Preview)', href: '#admin' },
    ]
  }
};
