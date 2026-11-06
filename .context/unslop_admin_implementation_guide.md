# Antigravity: unslop the AlphaZee admin portal

The owner requested parallel work: Codex owns the **customer storefront**; you own **admin only**. Vendor work is deferred. Preserve the existing working tree and application/data contracts.

## Read and apply the installed skill

Read `.agent/AGENTS.md`, `.agent/skills/unslop/SKILL.md`, then its `references/signs.md`, `tokens.md`, `refs.md` and `visuals.md`. Inspect the referenced dashboard image before styling. This is a local repository copy of [unslop by Damir Sokolovsky (@heydamir)](https://github.com/heydamir/unslop), **CC BY 4.0**; preserve its attribution. Original installed Codex location: `C:/Users/SyedNajam's PC/.codex/skills/unslop`. If your IDE does not discover it, read/apply the file directly rather than claiming installation failed.

Follow its sequence: audit → five-line direction → spacing → color → icons → copy → type → layout → details → visuals → motion → verification/report. The owner has already said to implement; document your direction before editing and proceed. Paid image generation/story video are unnecessary for this admin task. Do not replace real data with plausible invented figures.

## Scope and coordination

You may edit `frontend/src/components/AdminDashboard.js`, `AdminConsole.js`, `AdminPreview.js`, `components/admin/*`, and `styles/admin.css`, plus relevant admin tests. Scope styles under actual admin root classes. Codex owns `Hero.js`, storefront components, `app.js`, and storefront styles. **Do not edit shared tokens/reset/main stylesheet, API contracts, storefront or vendor files without coordinating a concrete dependency.** Use admin-local variables. Keep existing sidebar scroll/hover fixes.

Use `/admin` on `http://localhost:13000` for visual inspection. Test mutations on the separate lab `http://127.0.0.1:13001/admin` with clearly labeled fixtures. Never reset owner credentials, insert fixtures into development, remove volumes, expose private values, or open checkout as part of styling. Account, Origin/CSRF, financial and inventory rules remain enforced.

## Direction to derive, not copy blindly

- Product: an owner-operated clothing shop's workspace for catalog, fulfillment, vendor stock and money.
- Character: exact, composed, practical.
- World: a shop's order book and stockroom, not a marketing landing page.
- Moments: the selected product photo and one financial/operational view whose figures mean something.
- Signature: consistently aligned order references, quantities and PKR amounts.

Preserve actual logo, brand accent and configured light/dark preferences. Graphite/white neutral chrome, one restrained accent, semantic statuses with labels. No gradients, glows, emoji headings, generic greeting banners, decorative charts or badge clusters. Keep existing section order and functionality; improve proportions/grouping rather than rebuilding the application.

## Concrete work

1. **Baseline:** capture login, overview, catalog/media editor, orders/detail, inventory/shortage, supplier finance, expenses/reports and settings. Audit each visible defect with selector/file. Decide heavy versus light treatment per screen; do not redesign good controls for novelty.
2. **Shell:** fluid workspace, roughly 240–280px desktop sidebar, coherent compact navigation, visible page context, useful mobile navigation, stable selected states. No overflowing sidebar or hidden logout; keep horizontal scrolling inside genuinely wide tables. Preserve accessible 44px touch targets even where the skill's compact desktop examples are smaller.
3. **Information:** quiet page titles, short sentence-case labels, consistent 4px spacing, three text roles and aligned tabular figures. Clear filter/period/timezone/freshness labels; preserve filter/export agreement. Money uses existing exact PKR format; no rounding underlying paisas.
4. **Tasks:** make primary next action obvious on order/catalog screens. Preserve draft/publish, dirty/save, loading/error/retry, upload progress, media-role assignment and stale-edit protection. Confirm consequential operations with the actual identity/amount. Do not make every button equally prominent.
5. **Finance/stock:** show delivery, payment and settlement as separate concepts. Physical, held, available, shortage and owned-return stock must remain distinct. Never rename contribution as profit, delivery as remittance or a refund liability as cash paid. Keep audit/reversal evidence discoverable.
6. **Craft:** retain required status badges quietly, unify icon stroke/size, remove ornamental card shadows/lift/scale and transition-all. Use restrained neutral surfaces/borders, readable contrast, nested radii and visible focus. Data visualizations only for real supported series; do not add charts merely to make the dashboard attractive.

## Browser gate and outputs

Render baseline, completed passes, and one corrective comparison—keep the skill's three visual review cycles per screen, while running necessary functional checks. At 1440×900 and 390×844 inspect screenshots yourself; include 1366×768, keyboard Tab/Escape, actual 200% browser zoom, reduced motion, loading/empty/error and two-tab stale edits. Contrast-check text/actions in light and dark themes. Confirm no global/storefront/vendor style leakage.

Perform real lab UI journeys: create/edit/publish a product and its media; inspect order and permitted next action; count stock/resolve a genuine shortage; record a controlled supplier payment/expense and reconcile report/export; save/reset personal preferences. Use existing tests for deeper commerce coverage. Do not claim a screenshot or DOM presence proves the mutation worked.

Run frontend tests/build and relevant admin regressions. Record browser/network errors, before/after screenshots, measured layout issues, actual outcomes and remaining gaps. Never claim physical mobile/screen-reader testing from emulation or DOM attributes.

Write `.context/unslop_admin_progress.md` and `.context/unslop_admin_report.md`. Include the five-line direction, audit items resolved, nine pass notes, changed files, tests, evidence paths under `.local/unslop-admin/<run>/`, and deferred work. Do not overwrite earlier acceptance reports. Keep unslop attribution in the report. Completion is an improved, working admin interface; vendor remains for a later task.
