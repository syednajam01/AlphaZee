export const storeConfig = {
  name: 'AlphaZee',
  tagline: 'Modern Apparel & Curated Essentials',
  currency: 'PKR',
  currencySymbol: 'Rs. ',
  shippingInfo: {
    standardTime: 'Estimated delivery: 3–5 business days nationwide upon confirmation',
    standardRate: 'Calculated at checkout',
  },
  reassurance: [
    {
      id: 'delivery',
      title: 'Nationwide Delivery',
      desc: 'Delivery across Pakistan via verified local courier partners.',
      icon: 'truck'
    },
    {
      id: 'payments',
      title: 'Manual Verification',
      desc: 'Cash on delivery and any enabled bank transfer option, verified before shipment.',
      icon: 'shield-check'
    },
    {
      id: 'support',
      title: 'Direct Support',
      desc: 'Assistance for sizing inquiries and manual order tracking updates.',
      icon: 'message-circle'
    }
  ],
  faqs: [
    {
      q: 'How long does delivery take?',
      a: 'Orders typically arrive within 3–5 business days across Pakistan once confirmed by our team.'
    },
    {
      q: 'How can I pay for my order?',
      a: 'Cash on Delivery is available. Bank transfer appears at checkout only when configured; instructions follow supplier confirmation, and received funds must be verified before dispatch.'
    },
    {
      q: 'What is the return & exchange policy?',
      a: 'Inspection upon delivery is supported. Please report any damaged or incorrect items to customer support immediately upon receipt for resolution.'
    },
    {
      q: 'How do I choose the correct size?',
      a: 'Refer to product specifications and measurements listed on each product page before ordering.'
    }
  ],
  footerLinks: {
    shop: [
      { label: 'All Products', href: '#featured' },
      { label: 'Collections', href: '#collections' },
      { label: 'New Arrivals', href: '#featured' },
    ],
    customerCare: [
      { label: 'Order Inquiries', href: '#reassurance' },
      { label: 'Track Your Order', href: '#track' },
      { label: 'Shipping & Delivery', href: '#reassurance' },
      { label: 'Customer FAQ', href: '#faq' },
    ],
    legal: [
      { label: 'Privacy Policy', href: null },
      { label: 'Terms of Service', href: null },
      { label: 'Admin Console (Preview)', href: '#admin' },
    ]
  }
};

