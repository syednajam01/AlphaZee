# AlphaZee Design Guide

## Purpose and priorities
Build a mobile-first e-commerce MVP for supplier products and original print-on-demand (POD) products. Follow this file for visual and interaction decisions; keep the project's existing stack and architecture. Priority: latest explicit user request, then this guide, then existing component conventions. Implement only the requested scope.

The approved direction is a sharp product image over a softly blurred video of the same product, with horizontal featured-product slides. Colours, typography and sections below are proposed defaults until the owner changes them. Product categories, audience, prices and supplier policies are not yet confirmed; never invent them.

## Visual system
Aim for a bold, clean storefront with a cinematic hero and calm shopping sections.

| Token | Default |
| --- | --- |
| Page / cards | Warm white `#F7F7F2` / white `#FFFFFF` |
| Text / secondary text | `#171717` / `#595959` |
| Accent | Deep green `#145C44`; white button text |
| Borders | `#DEDED7` |
| Hero | Dark imagery, white text, contrast overlay |
| Font | Inter if available, otherwise system sans-serif |
| Type | Body 16px; section titles 28–40px; hero title 36–64px responsive |
| Spacing | 4, 8, 12, 16, 24, 32, 48, 64, 96px |
| Layout | Content max-width 1280px; gutters 16px mobile / 32px desktop |
| Shape | 8px buttons, 12px cards; subtle shadows only |

Use the supplied AZ/AlphaZee logo without distortion. Prefer a compact horizontal lockup in the header and the AZ symbol for small placements. Use a reversed logo on dark surfaces. If usable assets are missing, use a plain AlphaZee text placeholder rather than redrawing the logo. Keep product photography consistent; avoid dashboard styling, decorative gradients and excessive animation.

## Homepage, in order

### 1. Header
Logo left; Shop, Collections and Contact navigation; search and cart right. On mobile use a menu button and compact controls. Keep header text readable over the hero using a dark backing; switch to a solid surface when scrolling. Announcements appear only for verified offers.

### 2. Featured-product hero
- Full-width layered composition: background product video, soft blur and dark overlay, then a crisp product image and readable copy above it. Blur only the background. The product is the visual focus.
- Desktop: foreground product image near the centre-left; short title, one-sentence benefit, verified price and “Shop this product” beside it. A subtle AZ motif may decorate unused space.
- Mobile: image first, short copy and button beneath, all over the same background. Use content-driven height; do not crop the product or force the section to fit one screen.
- Use `object-fit: cover` for background media and `contain` for the foreground image. Keep meaningful product details visible.
- Support up to three manually selected products. Each slide changes the image, matching video, copy and product link together. With one product, hide carousel controls.
- Horizontal transition: about 350ms. Optional auto-advance every 8 seconds, with visible pause/play, previous/next buttons and position indicators. Pause on hover, keyboard focus, manual interaction and when offscreen. Support swipe without blocking vertical scrolling.
- Video is muted, looping and inline. Show an optimised poster immediately and retain it if playback fails. Include a clearly labelled motion control that pauses both video and slide rotation.
- Reduced-motion preference: use the poster, disable auto-advance and remove sliding animation. Also prefer the poster when data-saving preferences are available.

### 3. Shop by collection
Show 2–4 real launch collections with clear images and names. Organise around what customers buy, not supplier logistics. Do not display empty categories.

### 4. Featured products
Show 4–8 launch products in a two-column mobile / four-column desktop grid. Cards contain consistent-ratio images, name, PKR price and an honest availability label. Products with options use “Choose options”. Avoid fabricated bestseller badges, reviews or crossed-out prices.

### 5. AlphaZee Originals
When POD products are ready, feature one collection with a strong image, short explanation and collection link. Explain made-to-order production time on the product page. Omit this section until assets and products exist.

### 6. Shopping reassurance and footer
Show confirmed delivery, payment and return information, followed by a short FAQ. Footer includes Contact/WhatsApp, shipping, returns, privacy and terms links. Never promise COD, free delivery or returns without confirmation.

## Essential shopping screens
- **Collection:** title, relevant filters, sorting, product grid and useful empty state.
- **Product:** gallery, price, stock, size/colour options, size guide where relevant, delivery estimate, shipping cost or calculation explanation, return terms and prominent Add to cart. Distinguish POD production time from transit time.
- **Cart/checkout:** editable quantities, guest checkout, essential customer fields, available payment methods and complete total before submission. Explain separate shipments where applicable.
- **Confirmation:** order reference, items, total and accurate next steps. Never show success before the order is saved.

## Implementation checks
Reuse shared header, buttons, product cards and spacing tokens. Use semantic elements, visible keyboard focus, labelled controls, sufficient contrast and at least 44px touch targets. Decorative video is hidden from assistive technology; product images have meaningful alt text.

Keep the hero fast: compress media, load only the active video, stop hidden playback, reserve image dimensions and lazy-load below-fold images. Do not make content visibility depend on video loading. Avoid autoplay audio, scroll hijacking and continuous decorative motion.

Check mobile at 360px and desktop at 1440px: no horizontal overflow, readable text, uncropped foreground product, working navigation and usable carousel controls. Verify video failure and reduced-motion fallbacks. Clearly identify preview data; never invent live business claims. Keep advanced analytics and admin interfaces outside this storefront design scope.
