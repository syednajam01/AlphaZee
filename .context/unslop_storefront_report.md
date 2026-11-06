# AlphaZee storefront unslop

Implemented 2026-11-06. Method: [unslop by Damir Sokolovsky (@heydamir)](https://github.com/heydamir/unslop), CC BY 4.0. Original skill installed globally; repository copy: `.agent/skills/unslop/SKILL.md`. See its `PROVENANCE.md` for source/checksum. The skill is discoverable by Codex from the next turn and was read/applied directly for this run.

## Direction

- **Product:** selected clothing and accessories for a younger generation.
- **Character:** assured, tactile, direct.
- **World:** a clothing label and a well-edited shop.
- **Moments:** uploaded hero media and the actual product photography.
- **Signature:** quiet label-style captions with consistent price alignment.

Owner already authorized implementation; the skill's direction pause was skipped under its explicit "already said to just do it" exception. No paid image generation, fabricated product photography, or story video was used. Existing brand/logo and Manrope/Newsreader families were retained.

## Audit and treatment

The hero needed substantial work: its copy/actions were visually hidden, the first screen repeated 16 cards in a continuous animation, video was blurred/darkened, and decorative borders/shadows competed with the media. Product/collection sections had a usable structure needing polish, not a framework rewrite. Several fallback strings claimed specific manufacturing, fabrics or garment properties unsupported by catalog facts. Generic dark "coming soon" artwork and ornamental hover movement reinforced the template appearance.

The scope stayed customer-facing. Existing Header.js and scratch changes present at task start were preserved. Admin work is delegated through `.context/unslop_admin_implementation_guide.md`; vendor is deferred. No accounts, prices, stock, policies, uploaded originals or database records were changed.

## Nine passes applied

| Pass | Result |
| --- | --- |
| Spacing | One scoped storefront layer establishes section rhythm, card gutters, filter spacing and grouped purchase controls using the existing grid |
| Color | Paper/ink neutrals with brand green reserved for actions/selection; product photos carry the color; no blurred hue wash in the hero |
| Icons | Hero playback/navigation now use consistent line SVGs; storefront stroke treatment is consistent; no decorative replacement badges |
| Copy | Visible title/actions; removed unverified local-manufacturing/heavyweight claims; collection, catalog, footer and empty-cart copy describe selection/shopping |
| Type | Newsreader display titles, quieter 400/500 hierarchy, sentence-case labels and tabular prices, without replacing the real logo |
| Layout | Desktop hero has readable copy beside a full unblurred media stage; mobile stacks in reading order; collection captions move beneath images |
| Details | Plain cards/borders, compact controls and a neutral storefront-only unavailable-photo asset; inactive hero slides are inert/hidden from assistive navigation |
| Visuals | Existing uploaded images/video remain authoritative; hero rail uses unique images instead of repeated clones; no invented media or feature data |
| Motion | Removed the infinite card marquee, lift/scale decoration and blanket promoted layers in scoped rules; intentional muted video playlist/pause/advance remains |

Hero mapping no longer treats a collection slide's internal slide ID as a product ID. Inactive video stays unloaded until selected. Existing timing, single-video loop, multi-slide advancement and visibility pause remain covered by tests. Section order and commerce behavior remain intact.

## Files and integration

`frontend/src/styles/storefront.css` scopes the design to the `.storefront` app root; `main.css` imports it. Existing base styles remain reusable, with no global token/reset rewrite. `app.js` adds the storefront scope. Component edits: `Hero.js`, `Collections.js`, `FeaturedProducts.js`, `ReassuranceFooter.js`, `CartDrawer.js`. New static asset: `frontend/public/images/storefront-empty.svg`. Admin/vendor roots do not get the storefront class.

Updated hero/collection tests follow intentional copy changes. Added behavior assertions for hidden-slide keyboard isolation and inactive video loading, retaining the existing media playback assertions.

## Verification and limits

Three visual review cycles: `.local/unslop-storefront/before/`, `after/`, `final/`. Screenshots were inspected, not counted as automatic acceptance. The original mobile product capture caught a loading skeleton; subsequent captures wait for the actual product title. Do not use that skeleton as a completed product before/after comparison.

Final browser/CDP checks cover 1440×900, 390×844, 360×640 and 768×1024: home/product routes, no horizontal overflow, hero pause/next, one interactive active slide, gallery next, lightbox open/close, empty cart and lower-page captures. Final JSON reports no browser exceptions or HTTP errors. Product stage bottoms were 646, 514, 426 and 566px respectively, within their viewports. Hero cards fell from 16 repeated items to 2 unique items for the current fixture. Sources and gallery associations were preserved.

Lower-page screenshots can capture ongoing smooth scroll; they are not proof that every footer row was visually audited. Final neutral placeholder/empty-cart wording received terminal regression/build checks after the main visual cycle. Physical devices, screen-reader audio, real desktop zoom and new cloud checkout were not verified in this run. No measured Core Web Vitals improvement is claimed. Existing catalog test records/missing photos remain; final brand art direction needs real product media.

Final checks: **138/138 frontend tests passed** (11.54s), final Vite build passed (7.44s), production web-image build passed, and isolated lab web-image build passed. The new neutral asset is served on port 13000 with HTTP 200. No backend tests were needed for this presentation-only change. Earlier copy-sensitive failures were corrected without removing interaction assertions. Production was built, not deployed.

## Next handoff

Feed Antigravity `.context/unslop_admin_implementation_guide.md`. It must read the local skill/references, preserve shared storefront files, use real browser evidence, and produce `.context/unslop_admin_report.md`. Vendor redesign stays outside this task. The shop still needs actual launch content and the separately documented cloud acceptance before real customer orders.
