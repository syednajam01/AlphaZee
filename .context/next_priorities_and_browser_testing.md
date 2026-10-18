# What to prioritize next, and how to test AlphaZee

Prepared 2026-10-18. Recommendations use the current code, [readiness assessment](production_readiness_summary.md) and existing acceptance scripts. This task writes guidance; it does not rerun tests or change checkout/deployment.

## My recommendation

**Start with a baseline test of the buying journey, fix serious failures, then make mobile shopping and checkout your main product focus.** Prepare Azure staging alongside that work. Close the remaining commercial/backend launch gaps before accepting public orders or spending on ads.

You do not need to build every optional feature first. Your core commerce implementation is substantial. However, attractive screens cannot compensate for an order that fails, unclear delivery charges, inaccurate stock or a fulfillment process you cannot operate. Equally, a technically correct backend does not prove that customers understand the interface.

A better UX can reduce avoidable abandonment; it cannot guarantee purchases. Product appeal, price, availability, trust, delivery terms and the relevance of the visitor also matter. Checkout research supports prioritizing cost clarity and recoverable errors over decoration: [Baymard's checkout findings](https://baymard.com/research-articles/current-state-of-checkout-ux).

## Recommended order

| Priority | Work now | Finish when |
| --- | --- | --- |
| 1. Establish the baseline | Personally complete the customer and owner test paths below. Log defects and separate broken behavior from confusing behavior and cosmetic issues. | Both payment journeys are understood; every blocking failure has a reproducible report. |
| 2. Settle rules that affect the screens | Choose free versus charged shipping, supported delivery areas, mixed-vendor fulfillment, return/exchange terms and vendor payment bookkeeping. | You can state the exact customer total, fulfillment promise and vendor amount owed. |
| 3. Improve the purchase journey | Mobile product details → variant choice → cart → checkout → confirmation/tracking. Fix friction discovered in testing; use consistent forms, dialogs and feedback. | Potential customers can complete representative tasks without coaching, including fixing a mistake. |
| 4. Close launch gaps and validate staging | Implement a deliberate production checkout release; resolve required shipping/vendor accounting gaps; configure Azure, HTTPS, persistent storage, backups/restore and monitoring. Repeat acceptance on the deployed version. | A production-like rehearsal passes and the business can fulfill, settle and refund an order. |
| 5. Launch a controlled pilot | Start with a small catalog and order volume you can handle. Verify measurement, support and actual deliveries, then try limited paid acquisition. | Orders, courier receipts, returns, vendor payments and advertising costs reconcile well enough to assess the business. |

Priorities 2–4 can overlap. Do not delay UX work for vendor portals, reviews, a card gateway, advanced animations or automated courier integrations. Manual bank confirmation and COD are valid for your chosen model. A maintained external vendor-payment ledger can be an explicit initial choice; it must still be reconciled.

Current constraints: shipping defaults to zero; there is no vendor payout ledger; original fulfillment uses one shipment rather than independent vendor parcels; public checkout is closed. These are decisions/gaps to resolve, not evidence that every implemented feature needs rewriting.

## Where frontend/HCI effort should go

1. **Product confidence:** accurate pictures, useful size guidance, material/care, clear price/availability, visible selected size/color and understandable delivery/return terms. Match the landing product and offer to what an ad promises.
2. **Purchase controls:** an obvious add-to-cart action, editable cart, visible final charges, clearly distinguished COD/bank instructions and a submit button usable with the phone keyboard open.
3. **Feedback and recovery:** field-specific errors, preserved input, progress/disabled states during submission, honest stock-change messages and a safe retry after a network failure. Confirmation must explain what happens next and how to retain private order access.
4. **Accessibility and performance:** visible keyboard focus, labels, readable contrast/text, responsive layouts, manageable media and usable slow-network states. Avoid visual polish that makes these worse.

Improve owner operations after customer blockers: you must still be able to locate the order, confirm the supplier, verify funds, dispatch, reconcile cash and process returns accurately.

## Browser testing: three complementary layers

- **Automated regression:** proves specified behaviors repeatedly; the repository has terminal-driven real Chrome scripts.
- **Manual acceptance:** you inspect actual rendering, touch/keyboard behavior and business outcomes in supported browsers.
- **Usability sessions:** potential customers attempt tasks without help; this reveals confusion the automated scripts cannot detect.

Previously recorded M9 evidence is 260 backend tests, 108 frontend tests and 228 Chrome checks. It is a useful baseline, not a new result, cross-browser certification or proof of usability.

## 1. Prepare the safe environment

Run from `F:\AlphaZee` with Docker Desktop running:

```powershell
docker compose --env-file .env.docker.local up --build --wait -d
docker compose -f compose.checkout-lab.yml up --build --wait -d
```

Use **http://127.0.0.1:13001** for SAMPLE customer orders and `/admin` for the separate lab owner. Provision your own lab login interactively if necessary:

```powershell
docker compose -f compose.checkout-lab.yml exec api python scripts/provision_owner.py YOUR_LAB_USERNAME
```

Do not use the development `syed123` account as a lab credential. Use separate browser profiles for owner/customer testing. Populate a few SAMPLE products with two variants, managed media, supplier costs and chosen stock; follow the [owner handoff](m9_owner_handoff.md) and [lab catalog-copy guide](m8_checkout_lab_runbook.md). All money is simulated. Never transfer funds using lab instructions, reset the main database or remove its volumes.

Normal development at http://localhost:13000 remains browse/admin only: order creation returning 503 there is expected. Do not interpret that as a failed lab checkout.

## 2. Run the existing automated browser checks

These Windows runners require local Node 22.12+, frontend dependencies, `backend\.venv`, backend dependencies, Pillow and Python `websockets` with `websockets.sync.client`. Chrome is currently hardcoded at `C:\Program Files\Google\Chrome\Application\chrome.exe`. Check imports with:

```powershell
backend\.venv\Scripts\python.exe -c "import sqlalchemy, PIL; from websockets.sync.client import connect; print('Browser dependencies available')"
npm.cmd --prefix frontend ci
```

If an import fails, install the missing dependencies into that venv before continuing. Run each command separately and stop on failure. Normal development must remain healthy for the isolation checks:

```powershell
docker compose -f compose.media-check.yml up --build --wait -d
Test-Path .local/m3-media-check/runtime-prepared.json
```

The manifest currently exists in this workspace. On a **fresh, unprepared isolated media stack only**, prepare fixtures once:

```powershell
docker compose -f compose.media-check.yml exec -T api python scripts/verify_m3_media_runtime.py --prepare
```

Do not rerun preparation when already prepared; it deliberately refuses. If retained evidence and volumes disagree, diagnose them rather than deleting data. Then run sequentially:

```powershell
backend\.venv\Scripts\python.exe backend/scripts/verify_m4_browser.py --phase-m6
backend\.venv\Scripts\python.exe backend/scripts/verify_m9_browser.py
backend\.venv\Scripts\python.exe backend/scripts/verify_m8_runtime.py --phase-m9
docker compose -f compose.media-check.yml stop
```

The first runner starts and closes its own temporary frontend on port 13003; leave that port free. It covers catalog/media/storefront/cart. M9 covers lab checkout, bank/COD, returns/exchanges, mobile/offline recovery, archive history and session isolation. The runtime command must immediately follow a successful M9 browser run; it restarts lab services and checks the latest fixture's persistence. Do not restart services or manually alter those fixtures during the sequence.

For the additional M7 owner expiry-review/original-RTO scenarios, run this separately after the sequence above:

```powershell
docker compose -f compose.media-check.yml -f compose.operations-check.yml up --build --wait -d
backend\.venv\Scripts\python.exe backend/scripts/verify_m7_browser.py
docker compose -f compose.media-check.yml -f compose.operations-check.yml stop
```

Results overwrite their phase JSON reports in `.context/`: `m6_browser_verification.json`, `m9_browser_verification.json`, `m9_runtime_verification.json` and optionally `m7_browser_verification.json`. Timestamped screenshots live under `.local/m6-browser/`, `.local/m9-browser/` and `.local/m7-browser/`. Inspect timestamps, assertions and errors, not merely whether a report file exists. Preserve prior evidence separately if comparing runs. Rerunning M6 does not automatically refresh the historical M9 catalog-report copy.

These scripts create fresh SAMPLE records and automate prompts; they are not a human usability test. UI selector changes during redesign may require updating runners after checking whether the failure is an actual regression. Refer to the [existing acceptance checklist](owner_catalog_browser_checklist.md) for coverage details.

## 3. Perform your own manual acceptance

Use desktop Chrome and Firefox, actual Android Chrome and iPhone Safari where available. Device emulation is useful, but is not an actual phone/browser test. Check roughly 360–390px mobile widths, tablet and desktop. Mark unavailable devices **not tested**. A phone's `127.0.0.1` points to the phone, not your PC; the current lab is loopback-only. Use a deliberately configured protected staging environment for real-device purchase tests; do not casually expose the local lab publicly.

| Test path | What must be true |
| --- | --- |
| Browse → product → variant → cart | Correct media, price, size/color, availability and quantity; cart edits and refresh preserve the right items. |
| COD checkout → confirmation → private tracking | Correct total, one order despite double-click/retry, usable access instructions, correct owner order and stock hold. |
| Bank checkout → supplier confirmation → instruction handoff → proof → verification → dispatch | Proof alone does not permit dispatch; owner verification does. Customer sees accurate next steps. |
| Invalid/missing fields, coupon failure and unavailable stock | Clear actionable errors; other entered information remains; no phantom success/order. |
| Offline/slow response, back/refresh, close/reopen and retry | No stuck overlay, lost entered data without explanation, duplicate order or duplicate stock deduction. |
| Owner fulfillment and settlement | Supplier acceptance first; dispatch deducts stock once; delivery alone does not mean COD reached your bank; partial/final receipts reconcile. |
| Cancel, expiry review, return, refund and exchange/RTO | Eligible cancellation releases holds once; overdue funds require review; receipt alone never restocks; inspection controls sellable stock; refunds paid separately. |
| Archive purchased product | Public sale disappears; existing private tracking, purchased snapshots, returns and reports survive. |
| Login/logout, direct admin URL and customer access | Anonymous users see no owner data; customer code/session controls tracking; revoked/logout sessions are rejected. |
| Mobile and accessibility | No clipped controls; keyboard does not hide essential actions; Tab/Shift+Tab/Enter/Escape work appropriately; focus is visible/restored; 200% zoom remains usable. |

In DevTools, inspect Console and Network; use slow-network throttling and Offline briefly, then restore normal networking. Investigate unexpected errors and failed API requests. Intentional security denials and deliberate offline failures are expected only in their test scenarios. For each order, compare customer display, owner record, inventory and financial evidence. Do not judge success from a toast alone. [W3C's Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/) supplies a practical accessibility starting point, not a complete audit.

## 4. Test with potential customers

Start with a small round, for example five people resembling your intended buyers, then fix findings and repeat. This is qualitative discovery, not a statistically reliable conversion forecast. Ask them to think aloud and give goals rather than button instructions:

- “Find an item in your size and work out its total delivered cost.”
- “Place a SAMPLE COD order, correcting one address mistake.”
- “Explain how bank transfer works and when you expect dispatch.”
- “Find the order again and discover how to request a size exchange.”

Observe without coaching. Record task completion, assistance, hesitation, misunderstandings and exact points of abandonment. Ask what felt unclear or untrustworthy. Use SAMPLE details and obtain permission before recording. This follows [NN/g's task-based testing guidance](https://www.nngroup.com/articles/task-scenarios-usability-testing/).

## Defects, release decisions and ads

Use one log row per finding:

`ID | build/date | environment/device/browser | steps | expected | actual | severity | redacted evidence | fix/retest result`

**P0:** privacy exposure, wrong money/stock, duplicate orders or broken checkout: fix before release. **P1:** essential task requires help, has no recovery or fails on a target device: fix before paid traffic. **P2:** visual inconsistencies and nonessential convenience: schedule after blockers. Retest the fix and neighboring flows.

Before ads, validate a funnel measurement plan: landing/product view → add to cart → checkout start → server-confirmed order. UTM attribution exists; Meta Pixel/Conversions API and the complete event funnel are not established by the current evidence and need separate implementation/verification. Do not send personal details or private order codes to analytics. Verify one order is counted once after retries. Track delivered orders, cancellations/RTO, refunds and margin after advertising/vendor/courier costs; a COD order placed is not cash earned. Begin with a budget you deliberately choose, learn from the funnel and scale only when fulfillment and economics support it.

Your immediate next task should be **baseline browser acceptance plus a ranked issue list**, followed by a focused mobile buying-journey redesign. Keep the remaining launch checklist visible while doing that work.
