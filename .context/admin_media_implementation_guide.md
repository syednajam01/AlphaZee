# AlphaZee: admin-managed media and collections

Owner specification, 2026-10-19. For Antigravity: finish the currently running acceptance pass and save its results first. Then implement phases MM0–MM5 sequentially, verifying each before advancing. Preserve concurrent changes. This guide supersedes earlier hero autoplay restrictions: muted automatic playback is required for the homepage hero only; product-gallery videos remain user-initiated.

Read `.agent/AGENTS.md`, `.context/b1_followup_and_browser_handoff.md` and the latest `.context/frontend_redesign_progress.md`. Keep public checkout closed and use the isolated lab for sample uploads/orders. Do not change commercial promises, owner credentials, existing stock/order rules or production data. No framework migration is required for this task.

## Exact owner experience

| Area | Required behavior and admin controls |
| --- | --- |
| Homepage hero | A responsive horizontal video area. Admin uploads/selects videos, selects posters, orders slides, enables/disables them and saves. The active video starts muted, plays to its end, then transitions to the next; the last returns to the first. A single video repeats. No fixed timer may cut a video short. |
| Collections | Collections act like flat folders, e.g. Winter Collection. Admin creates/edits them, creates a product inside one, adds an existing unassigned product, or moves a product between collections. Keep one collection per product initially; nested folders and simultaneous multi-collection membership are outside this request. |
| Product gallery | Admin uploads multiple images/videos, changes order, edits alt text, assigns posters to videos and removes/replaces attachments. No artificial “one video only” restriction: a few photos plus one video is the owner's preference, not a schema rule. All applicable gallery assets appear on the product URL. Preserve variant-specific media. |
| Listing images | Explicit admin selectors: **Card front image** and **Card hover/back image** from that product's uploaded images. These selections are independent of gallery order. Desktop hover shows the selected back image; leaving restores front. Both remain accessible in the product gallery. Touch opens the product on the first tap. |

The owner must configure these through visible admin controls without SQL, source edits, pasted media URLs or changing environment files. Save feedback, validation, unsaved-change protection and persistence across reload/container restart are required.

## Current implementation: reuse versus gaps

- `components/admin/CatalogWorkspace.js` already handles collections, product collection selection (“Choose later”), product media attachment/reorder, primary image, hero image/video/poster, and hero inclusion/order. Reuse its authenticated/versioned API patterns.
- `components/Hero.js` sets `muted`, `playsInline` and `loop=true` on videos. It contains a six-second timer helper with no invocation found in the inspected file. Neither this nor looping individual videos implements end-driven sequencing.
- `components/FeaturedProducts.js` guesses a secondary image from optional fields/media. Backend role constraints currently allow only `primary`, `gallery`, `hero_image`, `hero_video`, `hero_poster`; there is no explicit card-hover role/control. Check public list serializers, not just detail responses.
- `schemas/media.py` caps the replacement attachment list at 100. Uploads also have file-size/format/duration limits. Do not promise literal unlimited storage or silently drop files beyond a cap.
- Draft products can be unassigned; published products currently require an active collection in service and DB validation. Preserve that rule: an unassigned draft can be assigned and then published. Do not silently invent a collection or weaken publication checks.

Paths above are under `frontend/src/` or `backend/app/`. Also read `utils/productMedia.js`, `ProductGallery.js`, `ProductPage.js`, `ProductModal.js`, `CollectionsSection.js` if present; backend media/catalog models, schemas, services, serializers, migrations and existing media/auth tests. Find actual filenames before editing.

## MM0 — map contracts and record baseline

Record what works, what is missing and the chosen changes in `.context/admin_media_progress.md`. Inspect pending code changes before building on them. List existing upload limits in user-friendly units and distinguish total assets, product attachments and upload batch size. Inventory all public card renderers, including related products and collection-filtered lists.

Acceptance: map each requested admin action to its current or proposed control/API; save baseline screenshots and current test/build results. Do not mark behavior implemented merely because a field exists.

## MM1 — explicit media selection and playlist contracts

Reuse durable media assets; do not duplicate uploaded files. Use existing `primary` for card front and an explicit image-only hover reference/role. Enforce same-product association, readiness, type and safe deletion/replacement. Include both selected URLs/IDs in listing responses; deduplicate repeated assets in the gallery. Keep gallery order independent of front/back selection. Audit every role consumer, including lab export/import and publication validation.

Provide an ordered hero-playlist contract backed by managed assets. Prefer dedicated slide records so the owner can upload a brand video without creating a fake product. Include stable identity, video, poster, display order and enabled state; optional product/collection destination and copy can reuse existing catalog links. Preserve existing product hero configuration through an explicit compatibility/backfill strategy; one active playlist must determine presentation, not two competing systems.

For “any number,” support growing galleries through incremental/paginated attachment operations rather than an ever-larger replace-all request. Retain documented upload/resource safeguards and explicit errors. Test beyond the current 100-attachment boundary using isolated fixtures; changing a UI label or merely raising a constant is insufficient. No one-video cap.

Acceptance: additive migrations tested in a disposable DB, existing data preserved, authorization/CSRF/version conflicts checked, role/type validation covered, old catalog rendering compatible, and exact limits documented. No applied migration history edits.

## MM2 — complete admin controls and collection workflows

Add a clear “Homepage hero” editor with add/upload, poster selection, reorder, enabled toggle, preview and Save. Product editing shows front/back image selectors with thumbnails and a gallery manager with multiple uploads, progress, retry, order and remove. Video posters must be selectable without leaving an unclear half-saved state. Removing selected media must require a replacement or explicitly clear the selection with visible consequences.

Collection editor must offer “Create product here” and “Add existing product”; show current members and searchable unassigned products. Product editor retains collection selection/move. Show draft/published state and why publication is blocked. Moving a product preserves its ID, slug, variants, media, inventory and purchased history. A collection archive/deactivation must explain existing publication consequences.

Acceptance through actual browser actions: create Winter Collection → create product inside it → create unassigned draft → assign it → move it → save/reload. Upload several images and two videos; set/reorder gallery/front/back/posters; reload and confirm persisted selections. Check rejected uploads, interrupted upload retry and concurrent-edit conflicts.

## MM3 — hero playback state machine

Use the active video's `ended` event to advance once; for multiple videos do not set per-video looping. Reset the next video to its start, play it muted/inline, wrap last→first. Single-video mode loops correctly. Only the active video plays; inactive videos must not all download eagerly.

Provide visible accessible pause/resume and previous/next controls, including pause for a single video. User pause persists through visibility changes. Pause when offscreen, on a hidden tab or when leaving home; clean up listeners on rebuild/navigation. Resume only when appropriate. Respect reduced motion/data-saving with a poster and explicit Play. Browsers may block autoplay: handle rejected playback with usable Play/retry, never a blank hero or an infinite retry loop. On media failure, offer retry/skip; if every video fails, stop on a useful poster state.

Use a landscape frame on desktop and a bounded horizontal frame on mobile. Reserve dimensions; support admin preview/focal-point adjustment if cropping is used. Avoid stretched garments, obstructed controls and excessive page height.

Acceptance: real short clips of different lengths prove A-end→B-end→A, plus single-video loop, pause/resume, manual next, autoplay rejection, failure, tab switching, leaving home and reduced motion. Save playback timing/event evidence, not just a screenshot of a video element.

## MM4 — listing hover and full gallery parity

All listing contexts use the explicit front/back selections. Fine-pointer hover crossfades to back and mouse leave restores front; missing or failed back image retains front. No videos autoplay on cards. Keyboard/touch users can reach both images in the product gallery; touch navigation needs one tap. Hover must never select an unrelated gallery asset or hero poster by accident.

Verify gallery order, front/back deduplication, variant scoping, video posters, explicit playback and pause on route/slide exit. Inspect `variantImage()` consumers: the helper currently returns a URL string; consumers must not read `.url` from that string and lose the selected variant's image in the cart. Verify listing/detail/cart image consistency with distinct fixtures.

Acceptance: select deliberately non-adjacent images for front/back, reorder other gallery images, and prove hover remains unchanged. Test home catalog, collection results and related products, plus single-image products, unavailable back assets and mobile navigation.

## MM5 — integration, persistence and owner handoff

Run relevant frontend/backend tests, build and dev/lab/production packaging checks. Verify browser results against the newly built image. Restart the relevant test containers without deleting volumes and confirm saved playlist, collection membership, images, posters and ordering persist. Verify auth, checkout isolation and existing product URL/cart/stock behavior remain intact.

Publish `.context/admin_media_acceptance_report.md`: phase status, changed files/migrations, commands/results, actual limits, per-case PASS/FAIL/NOT TESTED, redacted screenshot/video paths under `.local/admin-media/<run>/`, and known gaps. Keep “implemented,” “terminal-tested” and “browser-verified” separate. Update the earlier redesign brief only where this new specification supersedes it.

Finish with a short owner walkthrough: **create collection → create/assign product → upload gallery → choose front/back → set video poster → configure hero playlist → publish → verify storefront**. Functional testing can use clearly marked lab assets now. Final crop, quality and content acceptance waits for the owner's real photos/videos; do not insert synthetic products into development or claim that final approval is complete.
