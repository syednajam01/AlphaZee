# React scroll navbar — 2026-11-10

Implemented the approved navbar plan in an isolated worktree, excluding ongoing vendor/collection work.

## Delivered

- Full navbar on entry. Downward scrolling beyond 32px hides the panel and announcement; only the compact AZ monogram remains top left. Upward movement of 6px reveals navigation. The opening 12px restores the top state; tiny reversals are ignored.
- Warm glass panel, opaque fallback, compact glass logo, safe-area/lab offsets, reduced-motion and forced-colors rules. Hiding preserves the layout footprint. Announcement height is measured, including wrapped messages.
- React 19/React DOM, JSX and the compatible Vite React plugin, within existing Vite/Caddy hosting. No additional production frontend server. Existing routes, cart, capabilities and API remain authoritative.
- `Header.js` creates the root; `StorefrontHeader.jsx` owns UI/subscriptions; `headerScroll.js` handles direction. The app supplies explicit action callbacks, avoiding synchronous mounting assumptions.
- One accessible home link; hidden controls are inert and cannot intercept page clicks. Keyboard focus reveals navigation. Dialogs suspend hiding and restore their opener. Tablet uses the mobile menu below 1100px.
- Existing admin-managed announcements/typography/radius, cart badge, tracking and mobile drawer remain connected. Frames, observers and subscriptions are cleaned up on unmount.

## Local verification before push

| Check | Result |
| --- | --- |
| Full backend suite, fresh random `_test` DB | 342 passed; one existing Starlette/AnyIO deprecation warning |
| Frontend including React real-DOM tests | 147 passed on Windows and 147 in Linux/Node 22 |
| Frontend production build | Passed; app chunk approximately 108 kB gzip including React |
| Operational tests | 29 passed |
| Workflow policy and pinned actionlint | Passed |
| Real isolated PostgreSQL/media restore | Passed; synthetic Blob transport, not a new live restore claim |
| CI and VF migration verification | Passed clean upgrade and supported downgrade/re-upgrade on disposable DBs |
| Production API/frontend builds | Passed |
| Production preflight, unsafe-config rejection, exact migration CLI | Passed on disposable Compose project; temporary DB/volume removed |
| Production storefront browser smoke | Passed desktop/mobile catalog, product deep reload, admin/vendor entry |
| Production admin mobile browser smoke | Passed layout, logo, scrolling and bottom reachability |
| Navbar | Chrome/WebKit at 360/390/768/1440px, five storefront routes, long/disabled announcements, normal/reduced animation, keyboard, dialogs, position and hit testing; Chrome trusted touch swipes and wheel input passed |
| Lab frontend container | Navbar route/width checks passed with the persistent SAMPLE notice enabled |

Browser scenarios use explicit SAMPLE responses and no application writes. No production orders, stock changes or account resets were created. Evidence is under `.local/navbar-*.log` and `.local/navbar-evidence*/`; private settings are excluded from Git.

Extended browser checks found and fixed an invisible header container intercepting clicks; the regression assertion is permanent. The harness waits for async measurements and requests to settle. `ops/navbar_smoke.cjs` joins the packaging CI job. Existing mock-DOM tests remain; header/shell checks use a real DOM through the JSX-enabled `npm test` command.

React currently owns the navbar, not every portal. Browser engines were checked on this workstation; physical phones were unavailable. GitHub checks/live deployment must be confirmed after push; local results cannot guarantee Azure availability or future failures.

## Collections deployment blocker found before push

While this work was isolated, the IDE agent published `0c2a099`, including collection hover-media migration `d3f8a1c9e2b4`. Its frontend/backend/operations/packaging checks passed, but deployment run `42801220417` failed because the new migration lacked a reviewed compatibility entry. The navbar branch was rebased onto that commit; its Collections UI and product-isolation behavior were preserved. Full backend/frontend and migration/packaging checks were repeated on the combined source.

Reviewed upgrade: two nullable columns, with a nullable media foreign key; no existing column is renamed/removed or made mandatory. A rebuilt previous API image from `a1b260c` (schema code `c7f1e2a3b4d5`) successfully created, read, updated and deleted a SAMPLE collection against a freshly migrated `d3f8a1c9e2b4` database. New fields remained NULL when inserted by the previous code. The scratch database was removed afterward. On this evidence, `ops/migration-policy.json` now explicitly includes `d3f8a1c9e2b4`; the deployment guard remains active.

Before push, public production readiness still returned ready/database connected. The previously authorized SSH address timed out, so no private VM preflight result is claimed. Actual release status must be checked through Actions and the live revision markers.
