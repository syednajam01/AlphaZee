# B1 follow-up: completed work and next checks

2026-10-19. Owner authorized terminal review/fixes while real photos, videos and descriptions are being prepared. Browser work remains with Antigravity. This supersedes conflicting B1 completion claims; it does not open public checkout or authorize deployment.

## What Codex completed

Reviewed the B1 code and progress register. Genuine improvements include API material/care/sizing fields, request-generation guards, home metadata cleanup and removal of nested product-detail scrolling. However, E2 was not complete: centralizing an unapproved commercial promise does not make it verified. The reported policy navigation led to reassurance text, not actual privacy/terms content.

Fixed:

- Product pages no longer treat an unselected size as the first matching variant. If that first variant is sold out but another size is available, selection remains possible and the displayed starting price comes from available variants for that color.
- A nonexistent color/size combination cannot advertise itself as purchasable through product-level availability. Missing variant prices cannot fall back to another product price.
- Changing to an invalid combination removes the previous `variant` query value while preserving unrelated parameters.
- Focus handlers bind once to the reusable product container rather than accumulating on every render. Destroy clears the mobile-bar reference; pending page responses remain ignored.
- Unavailable product navigation clears the previous product canonical and replaces its description.
- Removed unsupported free nationwide delivery, fixed dispatch/transit times, seven-day exchange promises and absolute privacy claims. Shared preview copy now identifies unpublished terms. Cart, quick view and checkout no longer repeat the old promises. The zero shipping amount is explicitly labeled as test checkout; backend arithmetic is unchanged.
- Removed misleading Privacy & Terms navigation. Unpublished policies are visibly unavailable rather than linked to unrelated content. The owner must supply actual policies before launch.

Six regression tests were added for sold-out-first-variant selection, nonexistent combinations, listener accumulation, route-exit responses, variant URL cleanup and unavailable-page metadata.

## Fresh terminal verification

| Check | Actual result |
| --- | --- |
| `cd frontend; npm.cmd test` | 132 passed, 0 failed. Output: `.local/b1-followup-frontend-tests.txt`. |
| `cd frontend; npm.cmd run build` | Passed, Vite 7.3.7, 35 modules. Run after all application edits; subsequent edits added tests/documentation only. |
| Backend targeted configuration/model/unit tests | 41 passed. AnyIO deprecation and two pytest-cache permission warnings; no test failures. |

Backend command from `backend/`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_config.py tests/test_inventory_unit.py tests/test_catalog_unit.py tests/test_suppliers_unit.py tests/test_orders_unit.py tests/test_reservation_unit.py -q --basetemp ../.local/b1-followup-pytest
```

These backend checks do not establish database integration, applied migrations, backup recovery or concurrency behavior. No live DB changes, owner resets, fixtures in development, Docker rebuild, browser session or deployment were performed. Existing protected pytest artifacts were left alone. Current running containers may therefore still display Antigravity's earlier build.

## Antigravity: focused browser acceptance

Read `.agent/AGENTS.md`, this file and the B1 section of `frontend_redesign_progress.md`. Rebuild the isolated lab web service from current source before testing. Keep checkout on `127.0.0.1:13001`; use disposable lab products only, retain SAMPLE warnings and never display private access codes in saved screenshots.

1. **Variant selection:** use a lab product with first size sold out, a later size available, different prices and a missing color/size pair. Fresh URL shows no selected size; attempted addition prompts for size. Select the available size and verify exact variant/quantity in cart. Missing pair is unavailable, adds nothing and clears stale `?variant=`. Valid deep links still restore the exact variant; sold-out deep links remain blocked.
2. **Navigation/media:** rapidly switch A→B under delayed responses, then navigate home before a response completes. Verify title, canonical, visible product and playing media belong only to the active page. Test valid product→missing product→home; retain unrelated query parameters when selecting options. Record playback stopping on route exit.
3. **Commercial copy:** inspect home/footer, product page, quick view, occupied cart and checkout. No unapproved shipping/return promises, fake policy destinations or unsupported privacy assurances. Lab shipping remains PKR 0 and exact totals remain unchanged. Mark missing real policies/support as BLOCKED ON OWNER, not PASS.
4. **Layout/accessibility:** at 360/390/768/1280/1440px, verify selected options and both purchase controls, long pending-policy copy, occupied cart→checkout, focus wrapping/restoration and lab notice offsets. Use actual desktop browser zoom at 200%; `Emulation.setPageScaleFactor` is not the requested check. Assert visibility/geometry instead of mere DOM existence; fix the U5 false/zero measurements before reusing its matrix.
5. **Authenticated operations:** sign into the lab admin and edit a disposable product's material/care/sizing, save, reload and verify storefront values. A password field alone does not prove login/session/edit functionality. Complete one COD placement and a bank order through supplier confirmation, explicit handoff, received-funds verification and dispatch. Recheck the affected tracking/return UI; prior backend reports are historical evidence.

Write `.context/b1_followup_browser_report.md`: tested source revision/working-tree state, rebuild commands, environments, per-case PASS/FAIL/NOT TESTED, actual assertions, redacted screenshot paths, defects and remaining owner inputs. Do not reuse assertions that require the removed seven-day/free-shipping copy. If a check needs unavailable data or credentials, record it accurately and continue independent checks.

## Work that does not require real media

The next independent terminal work is isolated DB/migration/concurrency and backup-restore verification using the existing guarded runbooks, followed by container/runtime parity checks. It must use a verified disposable target, not development data or the persistent checkout-lab database as a destructive test target. These checks are pending, not claimed complete here. Fix demonstrated failures before adding new features.

Keep the existing backend and frontend stack during this acceptance pass. Next.js, analytics activation, shipping pricing and production release should follow the decisions in `business_and_architecture_review.md`, rather than interrupting correctness verification.

## Owner decisions while preparing media

| Decision | Needed before launch |
| --- | --- |
| Offer | Actual audience/assortment; garment material, care, measurements and image/video rights. |
| Delivery | Coverage, fees or intentional free delivery, realistic dispatch/transit estimates, who packs mixed-supplier baskets. |
| After-sales | Return window/eligibility, exchange charges, refund process and reachable support contact. |
| Operations | Supplier settlement method, courier reconciliation, per-order costs and pilot spending limit. |

No real media is needed to finish code-level selection or authentication checks. Real assets are needed to assess crops, video posters/playback, slow-network usability and whether the product presentation supports an informed purchase. Both forms of acceptance remain necessary; the app is not yet ready for unrestricted public orders.
