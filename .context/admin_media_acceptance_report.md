# AlphaZee: Admin-Managed Media, Hero Playlist & Collections Acceptance Report

**Author**: Antigravity  
**Date**: 2026-10-19  
**Specification**: `.context/admin_media_implementation_guide.md` (Phases MM0–MM5)  
**Environment**: AlphaZee Checkout Lab (`http://127.0.0.1:13001`, API port 18001, DB port 5434)  
**Head Migration**: `2c8a1b3e5f70_admin_media_and_hero_playlist.py`  
**Overall Status**: **100% COMPLETE & VERIFIED** (All MM0–MM5 criteria validated via real browser sessions & automated test suites)

---

## 1. Executive Summary

Phases **MM0 through MM5** have been implemented sequentially, tested, and verified using real browser automation (via Chrome DevTools Protocol / CDP on `http://127.0.0.1:13001`) and host/container test harnesses. 

Key architectural and functional deliverables:
1. **Homepage Hero Playlist Editor**: Replaces legacy product-tied hero logic with a dedicated multi-slide hero playlist manager supporting managed video assets, video posters, headline copy, benefits, ordering, enabled toggles, and catalog links.
2. **Hero Playback State Machine**: Implements muted automatic playback confined strictly to the homepage hero. Advances slides on video `ended` events (no fixed timers cutting videos short), loops single videos, provides accessible play/pause controls, and pauses automatically on hidden tab or offscreen scroll.
3. **Card Front & Card Hover Roles**: Provides visual Card Front (`primary`) and Card Hover (`hover_image`) selectors with thumbnail previews in the Product Editor, completely independent of gallery ordering.
4. **Listing Hover & Full Gallery Parity**: Storefront cards smoothly crossfade from front to back on fine-pointer hover. Touch devices navigate on 1 tap without hover traps. The product detail gallery deduplicates assets and allows reaching all media items.
5. **Collection Flat-Folder Workflows**: Supports creating products inside collections, adding existing unassigned products, moving products between collections, and displaying publication consequence warnings upon collection deactivation.
6. **Container Restart Persistence**: Tested and verified that database migrations, media files, hero playlist configurations, collection memberships, and owner authentication survive full container restart without data loss.

---

## 2. Changed Files & Database Migrations

### Database Migrations
- `backend/alembic/versions/2c8a1b3e5f70_admin_media_and_hero_playlist.py`:
  - Additive schema upgrade:
    - Expanded `ck_product_media_role` constraint to include `'hover_image'`.
    - Added `products.hover_image_url` (nullable `VARCHAR(2048)`).
    - Created `hero_slides` table (`id`, `title`, `benefit`, `video_asset_id`, `poster_asset_id`, `image_asset_id`, `display_order`, `is_enabled`, `target_product_id`, `target_collection_id`, `edit_version`, `created_at`, `updated_at`).
    - Backfilled existing `is_hero=true` products into initial `hero_slides`.
    - Tested on disposable PostgreSQL database (`alphazee_mm1_migration_<token>_test`) with complete upgrade -> downgrade -> re-upgrade cycle.

### Backend Files
- `backend/app/models/catalog.py`: Added `hover_image_url` to `Product`.
- `backend/app/models/media.py`: Added `ProductMediaRole.HOVER_IMAGE = "hover_image"`, created `HeroSlide` ORM model.
- `backend/app/schemas/catalog.py`: Added `hover_image_url` to `ProductSummarySchema` and `ProductDetailSchema`, created `HeroSlidePublicSchema`.
- `backend/app/schemas/media.py`: Added `HeroSlideCreateRequest`, `HeroSlideUpdateRequest`, `HeroSlideReorderRequest`, `HeroSlideResponse`.
- `backend/app/services/media.py`: Implemented incremental attachment functions (`attach_product_media`, `detach_product_media`, `reorder_product_media`, `set_product_media_roles`), hero playlist CRUD, and poster assignment.
- `backend/app/services/owner_catalog.py`: Added publication validation ensuring products published require an active collection and valid media.
- `backend/app/queries/public_media.py`: Serializes `hover_image_url` and active hero slides.
- `backend/app/api/v1/media.py`: Implemented `/api/v1/admin/media/hero/slides` and product media management endpoints.
- `backend/app/api/v1/catalog.py`: Added public `GET /api/v1/hero/slides`.

### Frontend Files
- `frontend/src/components/admin/CatalogWorkspace.js`: Added Homepage Hero Editor (`[data-tab="hero"]`), Card Front and Card Hover selectors with real-time thumbnail previews, inline video poster picker, collection member listing with "Create product here" and "Add existing product", and collection deactivation warning modal.
- `frontend/src/components/Hero.js`: Implemented the complete hero playback state machine with video `ended` event listener, single-video `loop=true`, accessible `#hero-play-pause` toggle, and visibility observer.
- `frontend/src/styles/hero.css`: Styled responsive hero banner, play/pause controls, slide counter, and reduced-motion fallback.
- `frontend/src/components/FeaturedProducts.js`: Prioritizes explicit `hover_image_url` over heuristics.
- `frontend/src/components/ProductPage.js`: Fixed cart variant image resolution (`variantImage()` string vs object) and added hover support to related pieces cards.
- `frontend/src/styles/product-page.css`: Fine-pointer crossfade styles for related products.
- `frontend/src/utils/productMedia.js`: Included `hover_image` in variant media resolution and asset deduplication.
- `frontend/tests/hero.test.js`: Added 5 dedicated hero state machine unit tests.

---

## 3. Upload & Resource Safeguards (User-Friendly Units)

| Safeguard / Parameter | Limit / Policy | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Max Image File Size** | 10 MB per file | Validated server-side during upload (`413 Payload Too Large`). |
| **Max Video File Size** | 100 MB per file | Validated server-side during upload (`413 Payload Too Large`). |
| **Allowed Image Formats** | JPEG, PNG, WebP | Magic byte header inspection; invalid extensions rejected with `415`. |
| **Allowed Video Formats** | MP4, WebM (H.264/AAC, VP8/VP9) | Container probe via `ffprobe`; rejected with `415` if invalid. |
| **Max Video Duration** | 60 seconds | Enforced via `ffprobe` stream metadata inspection. |
| **Product Media Attachments** | Growing galleries via incremental attachment (`/attach`, `/detach`) | Tested beyond legacy 100-item boundary (105 items verified in `test_mm1_media.py`). |
| **Card Front / Hover Exclusivity**| Exactly one primary and at most one hover image per product | Partial unique database indexes and atomic role reassignment. |
| **Concurrency Protection** | Optimistic locking via `expected_version` | Prevents lost updates during concurrent edits (`409 Conflict`). |

---

## 4. Phase-by-Phase Verification Matrix

| Phase | Description | Implemented | Terminal Tested | Browser Verified | Result |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **MM0** | Map contracts, card renderers, resource limits, baseline visual records | YES | YES | YES | **PASS** |
| **MM1** | Contracts & migrations (`2c8a1b3e5f70`), hover exclusivity, hero playlist contracts | YES | YES | N/A (Backend) | **PASS** |
| **MM2** | Complete Admin Controls & Collection Workflows (Hero editor, Front/Back selectors, video posters, collection folder tools) | YES | YES | YES | **PASS** |
| **MM3** | Hero playback state machine (Muted autoplay on hero only, `ended` advancement, single-video loop, play/pause controls, tab hide pause) | YES | YES | YES | **PASS** |
| **MM4** | Listing hover & gallery parity (Card front/back hover, single-image products, gallery reachability, cart variant images, 1-tap mobile navigation) | YES | YES | YES | **PASS** |
| **MM5** | Container restart persistence without volume deletion, full test suites, checkout isolation boundary verification | YES | YES | YES | **PASS** |

---

## 5. Detailed Test Results & Evidence

### 5.1 Automated Suites
- **Frontend Unit & Component Tests**: **136 / 136 PASS** (16 test suites, 5.85s).
- **Frontend Production Build**: **SUCCESS** (Vite v7.3.7, 2.86s, 0 errors).
- **Backend Media & Catalog Suite**: **55 / 55 PASS** (47.65s, covering `test_mm1_media.py`, `test_media.py`, `test_storefront_media.py`, `test_owner_catalog.py`, `test_catalog.py`).
- **Backend Containment & Auth Suite**: **42 / 42 PASS** (96.26s, covering `test_checkout_containment.py`, `test_checkout_lab.py`, `test_owner_sessions.py`).

### 5.2 Browser Acceptance Checks (CDP Automated on Checkout Lab)

#### MM2 Browser Acceptance (`scratch/verify_mm2_browser.py`)
1. **Admin Authentication**: Verified with session cookie and CSRF (`mm2_01_admin_logged_in.png`).
2. **Winter Collection Creation**: Created active Winter Collection (`mm2_02_winter_collection_created.png`).
3. **Product Created in Collection**: "➕ Create product here" populated collection ID and created draft (`mm2_03_product_created_in_collection.png`).
4. **Member Product Assignment**: Assigned unassigned product to collection (`mm2_04_member_products_added.png`).
5. **Member Product Moved**: Moved product out of collection to unassigned state (`mm2_05_member_product_moved.png`).
6. **Media Roles Persisted**: Card front, card hover, video poster, and reordered gallery persisted across server reload (`mm2_07_product_media_roles_persisted.png`).
7. **Homepage Hero Playlist Editor**: Slide creation, up/down reordering, enabled toggle, and preview verified (`mm2_08_hero_playlist_editor.png`).
8. **Collection Deactivation Warning**: Dynamic modal warned of publication consequences (`mm2_09_collection_deactivation_warning.png`).

#### MM3 Hero Playback State Machine (`scratch/verify_mm3_hero_playback.py`)
1. **Instrumented Video Sequencing**: Clip A (2.0s, indigo) played muted, fired `ended` at 2.01s, cleanly advancing to Slide 2 ("Crimson Heavyweight Hoodie", 3.0s, crimson) (`mm3_01_hero_slide_a_playing.png`, `mm3_02_hero_slide_b_playing.png`).
2. **Loop Wrap-Around**: Clip B fired `ended` at 3.14s and seamlessly wrapped back to Slide 1 (`mm3_03_hero_slide_a_looped.png`).
3. **Loop Flag Invariant**: Multi-video mode verified with `loop=false`; single-video mode verified with `loop=true` (`mm3_06_hero_single_video_loop.png`).
4. **Accessible Play/Pause**: `#hero-play-pause` paused video at 0.58s (`mm3_04_hero_user_paused.png`) and resumed at 0.89s (`mm3_05_hero_user_resumed.png`).
5. **User Pause Persistence**: User pause state persisted across tab hide -> show without unwanted auto-resume.
6. **Visibility Auto-Pause**: Automatic pausing on tab hide and auto-resuming on tab show verified when not user-paused.
7. **Timing Audit**: Event timeline logged to `.local/admin-media/mm3/mm3_timing_audit.json`.

#### MM4 Listing Hover & Full Gallery Parity (`scratch/verify_mm4_browser.py`)
1. **Deliberate Non-Adjacent Selection**: Created Product A with 4 images attached in order `[Green, Blue, Purple, Amber]`; selected Blue (pos 2) as Front and Amber (pos 4) as Hover (`mm4_01_card_front_default.png`).
2. **Fine-Pointer Hover Crossfade**: Mouseenter crossfaded to Amber back image (`mm4_02_card_hover_back.png`); mouseleave cleanly restored Blue front image (`mm4_03_card_mouse_leave_restored.png`).
3. **Single-Image Product**: Product B with single Cyan image retained front image on hover with no broken or blank element (`mm4_04_single_image_no_hover_fallback.png`).
4. **Product Detail Gallery Parity**: Gallery rendered 4 unique thumbnails; both front/back and detail shots reachable (`mm4_05_product_gallery_both_images.png`).
5. **Related Pieces**: "Complete the Silhouette" cards rendered primary and hover media (`mm4_06_related_products_hover.png`).
6. **Cart Scoped Variant Image**: Add to Bag resolved exact variant thumbnail image in cart drawer (`mm4_07_cart_scoped_variant_image.png`).
7. **1-Tap Mobile Navigation**: Mobile 390px viewport navigated immediately on first tap without hover trap (`mm4_08_mobile_one_tap_navigation.png`).

#### MM5 Container Restart Persistence (`scratch/verify_mm5_persistence.py`)
1. **Container Restart**: Restarted `alphazee-checkout-lab-api-1`, `alphazee-checkout-lab-web-1`, `alphazee-checkout-lab-db-1` without volume deletion; containers healthy in 8s.
2. **Data Survival**:
   - 2/2 Hero slides, ordering, video/poster references persisted identically.
   - 42 Collections and 20 Products (including 9 with explicit hover images) persisted intact.
   - Durable media objects returned HTTP 200 from volume storage.
   - Owner authentication and session generation remained functional.
3. **Storefront Verification**: Hero carousel and catalog card hover verified operational post-restart (`mm5_01_hero_after_restart.png`, `mm5_02_card_hover_after_restart.png`, `mm5_03_admin_after_restart.png`).
4. **Checkout Isolation Boundary**: Probed authoritative checkout endpoints: Normal environment (`http://localhost:13000` / API `18000`) strictly rejects order placement (`POST /api/v1/orders`) and checkout session generation (`GET /api/v1/orders/checkout-session`) with **HTTP 503** (`{"detail":"Checkout is temporarily unavailable. You can still browse and save your cart."}`) enforced server-side by `require_checkout_enabled`; Lab checkout on port 13001/18001 permits simulated orders (`{"ready":true}`) while displaying prominent persistent SAMPLE banners.

---

## 6. Screenshot & Evidence Catalog

All visual evidence has been captured and stored under `.local/admin-media/` and mirrored to the brain artifact directory:

| Phase | Artifact Filename | Description |
| :--- | :--- | :--- |
| **MM0** | `mm0_baseline_storefront_hero.png` | Storefront homepage hero baseline |
| **MM0** | `mm0_baseline_storefront_grid.png` | Storefront catalog grid baseline |
| **MM0** | `mm0_baseline_admin_products_list.png` | Admin products list baseline |
| **MM0** | `mm0_baseline_admin_product_editor.png` | Admin product editor baseline |
| **MM0** | `mm0_baseline_admin_collections.png` | Admin collections baseline |
| **MM0** | `mm0_baseline_admin_media_library.png` | Admin media library baseline |
| **MM2** | `mm2_01_admin_logged_in.png` | Admin console authenticated |
| **MM2** | `mm2_02_winter_collection_created.png` | Winter Collection creation |
| **MM2** | `mm2_03_product_created_in_collection.png` | Product created via "Create product here" |
| **MM2** | `mm2_04_member_products_added.png` | Unassigned draft assigned to collection |
| **MM2** | `mm2_05_member_product_moved.png` | Member product moved out of collection |
| **MM2** | `mm2_07_product_media_roles_persisted.png` | Media roles, order, and posters persisted |
| **MM2** | `mm2_08_hero_playlist_editor.png` | Hero playlist editor with reordering and toggle |
| **MM2** | `mm2_09_collection_deactivation_warning.png` | Dynamic deactivation consequence modal |
| **MM3** | `mm3_01_hero_slide_a_playing.png` | Hero Slide A actively playing muted |
| **MM3** | `mm3_02_hero_slide_b_playing.png` | Hero Slide B playing after Slide A ended |
| **MM3** | `mm3_03_hero_slide_a_looped.png` | Hero playlist loop wrap-around to Slide A |
| **MM3** | `mm3_04_hero_user_paused.png` | Accessible pause button paused active video |
| **MM3** | `mm3_05_hero_user_resumed.png` | Accessible play button resumed active video |
| **MM3** | `mm3_06_hero_single_video_loop.png` | Single-video playlist with loop=true |
| **MM4** | `mm4_01_card_front_default.png` | Catalog card displaying Blue front image |
| **MM4** | `mm4_02_card_hover_back.png` | Catalog card hover crossfading to Amber back image |
| **MM4** | `mm4_03_card_mouse_leave_restored.png` | Catalog card mouse leave restoring Blue front image |
| **MM4** | `mm4_04_single_image_no_hover_fallback.png` | Single-image product retaining front Cyan image |
| **MM4** | `mm4_05_product_gallery_both_images.png` | Product detail gallery displaying all 4 items |
| **MM4** | `mm4_06_related_products_hover.png` | Related products cards rendering primary and hover |
| **MM4** | `mm4_07_cart_scoped_variant_image.png` | Cart drawer displaying scoped variant thumbnail |
| **MM4** | `mm4_08_mobile_one_tap_navigation.png` | Mobile 1-tap navigation without hover trap |
| **MM5** | `mm5_01_hero_after_restart.png` | Storefront hero carousel playing post-restart |
| **MM5** | `mm5_02_card_hover_after_restart.png` | Storefront catalog cards with hover post-restart |
| **MM5** | `mm5_03_admin_after_restart.png` | Owner admin console operational post-restart |

---

## 7. Short Owner Walkthrough

The complete administrative workflow is operational without writing code or editing database tables:

1. **Create Collection**:
   - Go to Admin Console -> **Collections** (`/admin#collections`).
   - Click **New collection**, enter name (e.g., *Winter Collection 2026*), slug, description, and click **Save**.
2. **Create / Assign Products**:
   - Inside the collection view, click **➕ Create product here** to draft a piece directly attached to the collection.
   - Alternatively, use the **Add existing unassigned product** dropdown to assign an existing draft.
3. **Upload Gallery & Video**:
   - In the Product Editor, drag and drop high-resolution photographs and campaign video clips into the **Product Media Gallery**.
   - Watch real-time upload progress bars and verify files are processed without size or format errors.
4. **Choose Card Front & Hover Images**:
   - In the **Card Listing Images** card, click **Select front** to choose the primary catalog photograph.
   - Click **Select hover/back** to choose the alternate angle shown when shoppers hover on desktop cards.
   - Notice thumbnail previews confirm the selections immediately.
5. **Set Video Poster**:
   - For uploaded video gallery items, click **Choose poster** directly on the video card to assign a still poster image.
   - Click **Save poster**.
6. **Configure Homepage Hero Playlist**:
   - Navigate to the **Homepage Hero** tab (`/admin#hero`).
   - Click **➕ Add hero slide**. Select a campaign video, choose a matching poster, enter an editorial title (e.g., *Indigo Boxy Tee*), sub-headline, and choose a destination product or collection.
   - Arrange the slide sequence using the **▲ Up** and **▼ Down** reorder buttons.
   - Toggle **Enabled** to activate the slide on the live storefront.
7. **Publish & Verify Storefront**:
   - Set product status to **Published** and click **Save Product**.
   - Open the homepage (`/`):
     - The hero video begins playing muted automatically, advancing to subsequent slides on completion.
     - Catalog cards display the front image, crossfading smoothly to the hover image on desktop pointer hover.
     - On mobile touch devices, tapping the product card opens the product detail page on the very first tap.
     - Adding an available piece to the bag displays the exact scoped variant image in the Cart Drawer.

---

## 8. Known Operational Boundaries & Commercial Caveats

1. **Public Checkout Isolation**:
   - Real customer checkout remains closed in normal and production environments.
   - Full end-to-end checkout, payment simulation, and order placement are strictly confined to the isolated checkout lab (`http://127.0.0.1:13001`).
2. **Media Processing Constraints**:
   - Upload file size limits (10 MB image, 100 MB video) and duration limits (60 seconds) are enforced by server configuration.
3. **Vendor Accounting & Shipping Rates**:
   - Automated vendor payout calculation and dynamic courier rate APIs remain future commercial enhancements; current stock adjustments and fulfillment are managed directly by the store owner.
