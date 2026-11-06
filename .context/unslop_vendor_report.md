# Vendor portal redesign

Implemented 2026-11-06. Preview: http://127.0.0.1:13001/vendor (isolated checkout lab). Normal frontend also reads the updated source. No vendor accounts, inventory or financial records were changed.

## Design direction

- Product: a stock workspace for vendor shop staff.
- Character: calm, exact, helpful.
- World: a shop stock ledger, with warm neutral surfaces and AlphaZee green.
- Moments: actual product thumbnails and prominent stock counts.
- Signature: three aligned counts—your stock, customer holds, available online.

Applied [Unslop by Damir Sokolovsky (@heydamir)](https://github.com/heydamir/unslop), CC BY 4.0; local skill: `.agent/skills/unslop/SKILL.md`.

## What changed

The nine passes covered spacing, color, icons, copy, type, layout, details, visuals and motion. Replaced gradients, glow, emoji labels and oversized decorative badges with quiet surfaces, consistent spacing, readable typography, restrained green actions, real branding and visible keyboard focus. Product thumbnails use the existing safe media URL helper and an empty-media fallback.

Login, stock overview, product cards, search, empty/error/loading states, count and shortage dialogs, and history now share the same design. Mobile inputs use 16px type; buttons have 44px targets. History scrolls inside its own table region. Dialogs scroll within the screen, lock the background, trap Tab, support Escape and restore focus. Reduced-motion settings are respected.

Count guidance explicitly explains that selling one of three means entering **2**, including held units in the physical total. Success uses inline feedback; failed submissions retain their form. Duplicate pending submissions are blocked. Stale-version errors require closing and refreshing. Below-hold warnings preserve the existing backend shortage workflow. Search retains focus and cursor position; request generations prevent stale stock results replacing newer results. Session-expiry and history callbacks avoid restoring closed private views. Summary labels distinguish matching variant totals from page-specific stock sums.

Added previous/next navigation for inventories larger than 50 variants. Fixed three pre-existing API contract mismatches discovered during browser checks:

1. Session restore now calls `/vendor/auth/session`, replacing the nonexistent `/auth/me` endpoint.
2. Stock pages translate to the backend's `offset` and `limit` parameters.
3. Shortage submissions include the schema-required `variant_id` alongside count and note.

## Files

- `frontend/src/components/VendorPortal.js`: layout and interactions.
- `frontend/src/styles/vendor_portal.css`: scoped vendor design.
- `frontend/src/utils/api.js`: vendor-only contract fixes.
- `frontend/tests/vendor-api.test.js`: regression coverage for those contracts and CSRF propagation.

No backend authorization, pricing, customer privacy, reservation, financial or checkout rules were changed. Concurrent admin/storefront edits were preserved.

## Verification and limits

- Frontend suite: **139 passed**, zero failures.
- Production Vite build: passed.
- Lab frontend image: rebuilt and web container refreshed; backend/database containers unchanged.
- Headless Chrome: login, stock and dialogs at 1440×900, 768×1024, 390×844 and 360×640; no page horizontal overflow. Checked absolute count 3→2 with expected version, history, Escape, Tab wrapping, focus restoration, below-hold warning, retained input on 409, shortage payload and empty search.
- Evidence/scripts: `.local/unslop-vendor/{before,after,final}/`, `capture.py`, `fixture.js`; final results in `final/checks.json`. Local artifacts are ignored by Git.

Authenticated design checks use explicitly SAMPLE browser-only responses, with no database writes. They establish UI behavior, not a new real-account end-to-end stock acceptance. Anonymous session checks use the live lab endpoint; an unauthenticated 401 is expected. Early captures exposed the old 404 URL, fixed in this change. Before production rollout, sign in with an existing vendor, reload to confirm session restoration, and perform an owner-approved count/shortage test against designated test inventory. Real device/screen-reader acceptance remains separate.
