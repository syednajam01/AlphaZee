# AlphaZee — Featured Hanger Hero Implementation Handout
Decision brief • 6 November 2026

## Goal
Replace the current homepage hero's featured-media presentation with an interactive boutique clothing rail inspired by the attached reference video. Put selected featured products on hangers in sharp focus over an admin-selected, softly blurred image or looping video. Keep the rest of the homepage, collections and normal product listings intact. “Articles” means products here, not blog articles.

## Reference observations and limits
The roughly 12.6-second recording shows:
- Several garments hanging along one horizontal rail.
- Focus moving between garments: the focused garment faces forward and appears more prominent; neighbours remain narrower/angled.
- A selected garment moving into a close view, with the other garments softened behind it.
- Product information and controls beneath the selected item.
- Colour changes and a front/back view change later in the recording.

The recording does not reveal the original source code, rendering technique, exact animation values, or every input trigger. Treat hover-to-preview and click-to-select below as the proposed AlphaZee behaviour. Do not claim the reference's original implementation is known. Match its visible choreography, not its unrelated branding, ticker or page layout.

## Start inside the existing project
Inspect AGENTS.md, the current hero component, product/media models, existing featured-item ordering, admin authentication and media-upload pipeline. Reuse the existing Next.js/TypeScript frontend and actual backend patterns found in the repository. Extend the existing hero configuration where practical; avoid parallel competing sources of truth. Work on a feature branch. Implement the feature, not just a plan.

Use the supplied video and current hero screenshot as visual references. If these attachments are absent from your IDE context, use this handout as the baseline and clearly identify the missing visual reference.

## Hero composition
1. Background layer: full-bleed admin-selected photo or muted, looping, inline video with a poster image. Apply a restrained blur and contrast overlay only to this layer; slightly oversize it so blurred edges never show.
2. Foreground layer: a visible horizontal rail, convincing hangers and garment cutouts, with consistent hook positions, lighting and soft shadows.
3. Information layer: focused product name, live catalogue price and a clear View Product button. Keep navigation and controls legible.
4. Preserve AlphaZee typography and brand colours. Remove temporary preview copy from the finished hero. Keep the rail visually dominant without crowding it with large promotional text.
5. Desktop: show several garments with breathing room. Mobile: show one dominant garment and partial neighbours, with information below. Keep the full garment visible and avoid horizontal page overflow.

## Interaction and motion
Use one explicit state model: idle rack → previewed product → selected close view → return to rack.
- Fine-pointer hover or keyboard focus previews a garment: smoothly turn it toward the viewer, bring it slightly forward and separate adjacent hangers enough to avoid collisions.
- Pointer exit restores the prior resting selection unless a product is selected. Keyboard controls must remain predictable.
- Click/tap selects a garment and smoothly brings it into the close view within the hero; reveal its details and optional colour/front-back controls. Provide an obvious Back to rack control.
- View Product navigates to the existing product page. Merely hovering must never navigate.
- On touch, allow horizontal browsing with swipe plus visible previous/next controls. A first tap selects; the explicit CTA opens the product. Preserve vertical page scrolling and distinguish drag from tap.
- Keep the hook visually anchored during garment swing. Use subtle, damped rotation that settles rather than endless wobble.
- Move the garment, hanger and shadow as coordinated pieces. Focus changes must be interruptible: a rapid new selection continues from current visual values without snapping or queuing old animations.
- Preserve item identity between rack and close view to avoid image remount flashes.
- Suggested starting targets, to tune against the video: 300–500 ms preview changes; 550–800 ms close-view transitions; 150–250 ms detail fades. These are design targets, not measured reference timings.
- Do not autoplay garment selection by default. Background video may play independently. Add a visible pause control for ongoing background motion.
- Reduced-motion mode uses a static background and minimal fades, without swings or animated rotation.

## Asset strategy: essential to fidelity
Normal rectangular catalogue photos will not reproduce this effect.
- Each featured garment needs a clean, high-resolution transparent cutout with consistent framing and alignment. Store hero-specific assets separately from normal product-gallery images.
- Support either a cutout that includes its hanger or a garment-only cutout plus a shared hanger. Record the mode and hook/neck anchor coordinates so hangers are never duplicated and garments never appear detached.
- Allow admin scale/vertical offset adjustments within sensible limits.
- Optional front/back and colour-specific assets must correspond to real catalogue variants. Hide unavailable controls.
- A flat image rotated in CSS is only a 2.5D approximation; it cannot reveal real cloth depth or an unseen back. Never mirror a front image and call it the back. A convincing side profile requires side-angle imagery or a proper textured 3D model.
- Start with transparent images and transform-based animation if supplied assets support the intended quality. If that cannot match the reference, explain the precise limitation and prepare an optional 3D asset path. Do not add a heavy 3D engine without a justified visual need.
- Never fabricate product artwork, variant appearance or stock. Use clearly marked development placeholders only when necessary, and report missing production assets.

## Admin panel: complete end-to-end control
Add or extend a Hero / Featured Rack area inside the existing protected admin:
- Enable/disable the rack and choose existing catalogue products.
- Reorder products, remove them from the hero without deleting them, and toggle each item's visibility.
- Upload/replace hero cutouts and optional front/back/colour assets; edit hook alignment, scale, offset and alt text.
- Upload/select hero background image or video, poster and optional mobile background; adjust crop/focal point, blur and overlay strength.
- Offer desktop/mobile preview, validation errors and a clear save/publish action. Preview unpublished changes without changing the live hero.
- Obtain title, price, product URL, variants and availability from the catalogue rather than duplicating commercial data in hero settings.
- Reuse existing server-side authorization and upload validation, including actual file-type and size checks.
- Persist the configuration in the database, include required migrations, and invalidate/revalidate cached hero data after publish. It must survive reloads and server restarts.
- Inactive/deleted products must never remain publicly featured. For sold-out products, show their actual status and avoid misleading purchase prompts.
- Handle 0, 1 and many featured products: fall back to the existing hero when empty; disable browsing controls for one item. Start with a manageable presentation of around 5–7 items; keep larger sets navigable.

Suggested logical data, adapted to existing schema:
Hero settings: enabled, background media, poster/mobile media, focal point, blur, overlay.
Hero item: product reference, enabled, sort order, cutout/hanger mode, alignment and optional variant-view asset mappings.
Reuse existing media records and catalogue relationships wherever possible.

## Smoothness, resilience and accessibility
- Prefer existing animation tooling. Animate transform and opacity; avoid layout-changing width/left updates or full React rerenders on every pointer move.
- Reserve hero and image dimensions to prevent layout jumps. Load the first visible garment promptly, decode adjacent assets before transitions and defer distant assets.
- Avoid downloading every full-resolution image or video immediately. Use responsive image sizes and a compressed video with a poster fallback.
- Keep continuous large-area blur effects restrained. Pause background video when offscreen or the tab is hidden; provide static fallback if autoplay fails.
- Use actual links/buttons with visible focus, accessible product labels and keyboard previous/next/selection/return controls. Escape exits the close view. Avoid hover-only interactions.
- A loading or failed asset must not leave an invisible interactive product. Show a usable fallback and keep product navigation available.
- Aim for stable 60 fps on representative devices; measure rather than promise identical smoothness on every device.

## Required validation and delivery
Verify desktop and mobile layouts, touch and keyboard controls, rapid direction changes, interrupted transitions, reduced motion, failed media, empty/one/many products and long product names.
Verify admin select → reorder → upload → preview → publish → public hero, persistence after reload, cache refresh and inactive-product handling. Run relevant existing checks and meaningful tests for ordering, permissions and publishing.
Record a short interaction demo and compare it with the reference: anchored hangers, smooth focus changes, settled motion and clear foreground/background separation. Report actual tested browsers/devices and performance limitations.
Deliver the implementation, migrations, brief admin usage notes, exact missing assets and validation results. Preserve normal shopping flows. Do not merge to main or deploy without authorization.

