export const heroProducts = [
  {
    id: 'hero-1',
    productId: 'prod-heavyweight-tee',
    title: 'Heavyweight Boxy Tee',
    benefit: 'Crafted from 280 GSM combed cotton with an architectural, structured drape.',
    price: 3450,
    formattedPrice: 'PKR 3,450',
    stockStatus: 'In Stock — Ready to ship',
    category: 'essentials',
    image: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=1000&q=85',
    poster: 'https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?auto=format&fit=crop&w=1200&q=80',
    video: 'https://assets.mixkit.co/videos/preview/mixkit-young-man-in-a-white-t-shirt-smiling-41477-large.mp4',
    options: {
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Chalk White', 'Washed Black', 'Pine Green']
    }
  },
  {
    id: 'hero-2',
    productId: 'prod-hoodie-stone',
    title: 'Relaxed Fleece Hoodie',
    benefit: 'Double-layered hood with brushed 420 GSM French Terry for effortless warmth.',
    price: 6800,
    formattedPrice: 'PKR 6,800',
    stockStatus: 'In Stock — Limited batch',
    category: 'streetwear',
    image: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1000&q=85',
    poster: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=1200&q=80',
    video: 'https://assets.mixkit.co/videos/preview/mixkit-man-dancing-under-the-sun-42861-large.mp4',
    options: {
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Stone Grey', 'Midnight', 'Olive']
    }
  },
  {
    id: 'hero-3',
    productId: 'prod-oversized-sweatshirt',
    title: 'Minimalist Crewneck',
    benefit: 'Refined raglan sleeves and ribbed cuffs designed for clean, tailored layering.',
    price: 5200,
    formattedPrice: 'PKR 5,200',
    stockStatus: 'In Stock — Ready to ship',
    category: 'essentials',
    image: 'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=1000&q=85',
    poster: 'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=1200&q=80',
    video: 'https://assets.mixkit.co/videos/preview/mixkit-close-up-of-a-man-wearing-a-dark-sweater-42845-large.mp4',
    options: {
      sizes: ['S', 'M', 'L'],
      colors: ['Forest Green', 'Oatmeal']
    }
  }
];

export const productsData = [
  {
    id: 'prod-heavyweight-tee',
    title: 'Heavyweight Boxy Tee',
    price: 3450,
    formattedPrice: 'PKR 3,450',
    category: 'essentials',
    stockStatus: 'In Stock',
    badge: 'Core Basic',
    image: 'https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Chalk White', 'Washed Black', 'Pine Green']
    },
    description: 'Custom relaxed fit, 280 GSM 100% combed cotton, reinforced collar stitch that maintains shape after washing.'
  },
  {
    id: 'prod-hoodie-stone',
    title: 'Relaxed Fleece Hoodie',
    price: 6800,
    formattedPrice: 'PKR 6,800',
    category: 'streetwear',
    stockStatus: 'In Stock',
    badge: 'Heavyweight',
    image: 'https://images.unsplash.com/photo-1556905055-8f358a7a47b2?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Stone Grey', 'Midnight', 'Olive']
    },
    description: '420 GSM custom milled French Terry, oversized drop shoulder cut, kangaroo pocket with hidden stash slot.'
  },
  {
    id: 'prod-oversized-sweatshirt',
    title: 'Minimalist Crewneck',
    price: 5200,
    formattedPrice: 'PKR 5,200',
    category: 'essentials',
    stockStatus: 'In Stock',
    badge: 'Essential',
    image: 'https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      sizes: ['S', 'M', 'L'],
      colors: ['Forest Green', 'Oatmeal']
    },
    description: 'Ultra-soft interior, relaxed silhouette, reinforced rib knit hem and collar.'
  },
  {
    id: 'prod-canvas-tote',
    title: 'Heavy Duck Canvas Tote',
    price: 2400,
    formattedPrice: 'PKR 2,400',
    category: 'accessories',
    stockStatus: 'In Stock',
    badge: 'Utility',
    image: 'https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80',
    hasOptions: false,
    options: null,
    description: '16 oz industrial cotton duck canvas, interior organizer pocket, reinforced cross-stitched handles.'
  },
  {
    id: 'prod-cargo-pants',
    title: 'Structured Ripstop Trousers',
    price: 5900,
    formattedPrice: 'PKR 5,900',
    category: 'streetwear',
    stockStatus: 'In Stock',
    badge: 'Durable',
    image: 'https://images.unsplash.com/photo-1517445312882-bc9910d016b7?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      sizes: ['30', '32', '34', '36'],
      colors: ['Tactical Black', 'Desert Sage']
    },
    description: 'Military-grade ripstop fabric with adjustable ankle cinches and ergonomic knee articulation.'
  },
  {
    id: 'prod-structured-cap',
    title: 'Unstructured 6-Panel Cap',
    price: 1850,
    formattedPrice: 'PKR 1,850',
    category: 'accessories',
    stockStatus: 'In Stock',
    badge: 'Classic',
    image: 'https://images.unsplash.com/photo-1588850561407-ed78c282e89b?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      colors: ['Washed Black', 'Olive Green', 'Sand']
    },
    description: 'Low-profile washed cotton twill with brass buckle strapback adjustment.'
  },
  {
    id: 'prod-waffle-knit-longsleeve',
    title: 'Thermal Waffle Knit Longsleeve',
    price: 4200,
    formattedPrice: 'PKR 4,200',
    category: 'essentials',
    stockStatus: 'In Stock',
    badge: 'Layering',
    image: 'https://images.unsplash.com/photo-1618354691373-d851c5c3a990?auto=format&fit=crop&w=800&q=80',
    hasOptions: true,
    options: {
      sizes: ['S', 'M', 'L', 'XL'],
      colors: ['Off-White', 'Charcoal']
    },
    description: '300 GSM breathable textured thermal knit. Engineered for comfortable insulation.'
  },
  {
    id: 'prod-everyday-socks',
    title: 'Cushioned Ribbed Crew Socks (3-Pack)',
    price: 1450,
    formattedPrice: 'PKR 1,450',
    category: 'accessories',
    stockStatus: 'In Stock',
    badge: 'Essentials',
    image: 'https://images.unsplash.com/photo-1586350977771-b3b0abd50c82?auto=format&fit=crop&w=800&q=80',
    hasOptions: false,
    options: null,
    description: 'Arch compression support, reinforced heel/toe padding, combed organic cotton blend.'
  }
];
