# M9: final local acceptance and handoff

Completed 2026-10-15. M0–M9 satisfy the local owner/catalog/media/checkout-lab milestone. Your persistent development owner/data remain intact. Normal development and the checkout lab are healthy; the temporary media acceptance source is stopped with its volumes retained. Production/public ordering remain outside this milestone.

## Changes and results

- Added final acceptance using the existing commerce suite, with mobile checkout, real keyboard focus, scrolling/touch controls, deliberate offline retry, partial/final COD settlement, replacement RTO and purchased-product archive/history checks.
- Fixed completed replacement-RTO inspection remaining actionable. The existing shipment inspection timestamp/reconciliation state now reaches the return response; the dashboard hides completed/legacy inspection actions and shows completion. Existing stock services remain authoritative. Backend/frontend regressions cover the response and action visibility.
- Clarified that customer return receipt is recorded once; positive partial receipt and later inspection retain the existing service rules.
- Stacked report cards on small screens, verified in actual mobile Chrome screenshots.
- Updated Vite 5 to patched Vite 7.3.7 and esbuild 0.28.2. Registry audit changed from one moderate/one high finding to **zero npm advisories**, including development dependencies. Native frontend runtime requirements are documented from [Vite's migration guide](https://v7.vite.dev/guide/migration#node-js-support); Docker uses compatible Node 22. The committed lockfile pins the verified dependency tree.
- Added the [owner handoff](m9_owner_handoff.md), refreshed summary/deployment/agent guidance and marked old database-pause documents as historical.

| Verification actually executed | Result / evidence |
| --- | --- |
| Focused catalog/import tests | 18 passed |
| Final full backend suite | 260 passed; one existing AnyIO deprecation warning; `.local/m9-backend-final.xml` |
| Replacement API regression | 5 exchange-flow tests passed; full suite also passed after the fix |
| Frontend tests | 108 passed; production build passed on Vite 7 |
| Commerce/mobile/archive Chrome | 145 checks; `m9_browser_verification.json` |
| Authoring/media/gallery/cart Chrome rerun on Vite 7 | 83 checks; `m9_catalog_browser_verification.json` |
| Network/console | No unexpected JS or network failures; expected 401/404 checks and one deliberately offline checkout-session failure are recorded separately |
| Migration | Isolated upgrade, guarded nonempty downgrade refusal, safe downgrade/re-upgrade and Alembic comparison passed; `m9_migration_verification.json`; no new application migration |
| Restart/persistence | Archived product/media/poster checksums, five order states and exact stock/holds survive lab restart; `m9_runtime_verification.json` |
| Containment/data | Main website/direct API order creation return 503; protected owner routes reject anonymous access; owner remains enabled; no development sample catalog/orders; `m9_development_verification.json` |
| Dependencies | Zero npm advisories after patching; `m9_dependency_verification.json` |
| Containers | Development, production and checkout-lab images build; normal and lab stacks healthy |

The final archive check compares complete original order evidence, customer returns and financial summaries before/after dashboard archival. Public slug/stable-ID paths return 404 and the card disappears, while private customer tracking continues. Replacement RTO stock increases only after inspection, and the completed action disappears. The final runtime snapshot preserves physical/held/available stock of **20/1/19** and **19/0/19** for the two SAMPLE variants after those operations.

Screenshots are under the browser reports' `.local/...` artifact paths. Desktop authoring/report and mobile checkout/gallery/report screenshots were inspected. Private access codes and credentials are excluded. Earlier M3 matched backup/restore evidence remains referenced in the storage runbook; M9 reran restart persistence and migration checks rather than claiming a new backup restore.

## Repeat the final browser checks

Start normal development first and wait for it to be healthy, then run these sequentially:

```powershell
docker compose -f compose.media-check.yml up --build --wait -d
docker compose -f compose.checkout-lab.yml up --build --wait -d
backend\.venv\Scripts\python.exe backend/scripts/verify_m4_browser.py --phase-m6
backend\.venv\Scripts\python.exe backend/scripts/verify_m9_browser.py
backend\.venv\Scripts\python.exe backend/scripts/verify_m8_runtime.py --phase-m9
docker compose -f compose.media-check.yml stop
```

Do not restart either environment during the browser session-isolation checks. Each run uses fresh SAMPLE fixtures in test databases; no real customer/account data is copied. Runtime verification follows a successful M9 browser report. Owner startup, first-product, import, payment and backup instructions are in the handoff guide.

The remaining work is business configuration and any separately requested product improvements or public launch/deployment. No further numbered phase is automatically started.
