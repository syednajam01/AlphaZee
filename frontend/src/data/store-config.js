export const storeConfig = {
  name: 'AlphaZee',
  tagline: 'Modern Apparel & Curated Essentials',
  currency: 'PKR',
  currencySymbol: 'Rs. ',
  shippingInfo: {
    standardTime: '3–5 business days nationwide upon confirmation',
    dispatchTime: '24–48 hours upon confirmation',
    standardRate: 'Free nationwide delivery',
    returnPolicy: '7-day inspection and size-exchange policy upon delivery',
    courierNotice: 'Delivery nationwide via verified local courier partners',
  },
  policies: {
    delivery: 'Orders dispatch within 24–48 hours following confirmation. Nationwide transit takes 3–5 business days via verified courier partners.',
    returns: 'Every order is backed by our 7-day inspection and size-exchange policy. Inspect your items upon delivery and contact support for sizing exchanges or defect resolution.',
    privacy: 'Customer shipping details and phone numbers are used solely for order confirmation, delivery coordination, and private status recovery. They are never shared or sold.',
  },
  reassurance: [
    {
      id: 'delivery',
      title: 'Nationwide Delivery',
      desc: '3–5 business days nationwide transit via verified local courier partners.',
      icon: 'truck'
    },
    {
      id: 'payments',
      title: 'Manual Verification',
      desc: 'Cash on delivery and bank transfer, verified before shipment.',
      icon: 'shield-check'
    },
    {
      id: 'support',
      title: 'Direct Support',
      desc: 'Direct assistance for sizing inquiries and verified order tracking.',
      icon: 'message-circle'
    }
  ],
  faqs: [
    {
      q: 'How long does delivery take?',
      a: 'Orders typically dispatch within 24–48 hours and arrive in 3–5 business days nationwide once confirmed.'
    },
    {
      q: 'How can I pay for my order?',
      a: 'Cash on Delivery is supported nationwide. Bank transfer appears only when configured; instructions follow supplier confirmation, and received funds are verified before dispatch.'
    },
    {
      q: 'What is the return & exchange policy?',
      a: 'We offer a 7-day inspection and size-exchange policy upon delivery. Report any sizing adjustments or defects immediately for prompt resolution.'
    },
    {
      q: 'How do I choose the correct size?',
      a: 'Refer to the size options and published measurements on each product page before ordering.'
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
      { label: 'Privacy & Terms', href: '#policies' },
      { label: 'Return Policy', href: '#faq' },
      { label: 'Owner Console', href: '/admin' },
    ]
  }
};

