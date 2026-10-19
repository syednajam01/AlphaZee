export const storeConfig = {
  name: 'AlphaZee',
  tagline: 'Modern Apparel & Curated Essentials',
  currency: 'PKR',
  currencySymbol: 'Rs. ',
  shippingInfo: {
    standardTime: 'Delivery timing and coverage will be published before public ordering opens',
    dispatchTime: 'Dispatch timing will be published before public ordering opens',
    standardRate: 'Public delivery charges are not yet published',
    returnPolicy: 'Return and exchange terms will be published before public ordering opens',
    courierNotice: 'Delivery coverage is not yet published',
  },
  policies: {
    delivery: null,
    returns: null,
    privacy: null,
  },
  reassurance: [
    {
      id: 'delivery',
      title: 'Delivery Information',
      desc: 'Delivery coverage, charges and timing will be published before public ordering opens.',
      icon: 'truck'
    },
    {
      id: 'payments',
      title: 'Manual Verification',
      desc: 'Enabled payment options appear at checkout. Bank transfers require confirmation of received funds before dispatch.',
      icon: 'shield-check'
    },
    {
      id: 'support',
      title: 'Direct Support',
      desc: 'Support contact details will be published before public ordering opens.',
      icon: 'message-circle'
    }
  ],
  faqs: [
    {
      q: 'How long does delivery take?',
      a: 'Delivery coverage and dispatch/transit estimates will be published before public ordering opens.'
    },
    {
      q: 'How can I pay for my order?',
      a: 'Enabled options appear at checkout. For bank transfer, instructions follow supplier confirmation, and received funds must be verified before dispatch. Public ordering is not open yet.'
    },
    {
      q: 'What is the return & exchange policy?',
      a: 'Return eligibility, time limits and exchange charges will be published before public ordering opens.'
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
      { label: 'Privacy Policy', href: null },
      { label: 'Terms of Service', href: null },
      { label: 'Return Policy', href: null },
      { label: 'Owner Console', href: '/admin' },
    ]
  }
};

