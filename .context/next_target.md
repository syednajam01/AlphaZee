# Antigravity: second browser pass and report correction

Workspace: F:\AlphaZee. Follow-up to the 2026-10-18 first pass. This task supersedes the earlier browser handoff.

## Goal and reading order

Finish unsupported checks and produce an accurate report. The first pass contains useful fresh regression results, but its blanket PASS conclusion is unsupported. Resolve uncertainty; do not redesign or fix the application.

Read `.agent/AGENTS.md`, `.context/antigravity_browser_acceptance_report.md` and this file. Consult `.context/m9_owner_handoff.md` for operations, `.context/owner_catalog_browser_checklist.md` for coverage and `.context/next_priorities_and_browser_testing.md` for testing guidance. Inspect relevant code only as needed.

## First-pass mistakes to correct

1. The cited M9 original COD fixture was TWO units at PKR 123.45, total 246.90, settled as 100.00 + 146.90. Your timeline claimed one unit, PKR 2,500 and receipts 1,500 + 1,000. Dispatch courier COST was 1.25, distinct from customer shipping. Sources: `backend/scripts/prepare_m8_source.py`, `verify_m8_browser.py` and your checkout screenshot. Use actual observations for each order; do not copy example amounts into new results.
2. The saved `.context/m9_runtime_verification.json` leaves the bank order CONFIRMED with stock held. It does not establish bank dispatch/delivery. Complete those steps on a new order.
3. Customer access codes are long random tokens, not six digits (`backend/app/services/order_access.py`). `pending_payment` is not an order_status: order, payment and shipment states are separate.
4. Broad PASS rows hide untested subcases. One Tab assertion does not prove focus wrapping, Shift+Tab, Escape or zoom. Mobile emulation is not actual iPhone/Safari evidence.
5. Missing address autocomplete is a UX observation; a province dropdown is a proposal, not proven misrouting. Badge animation is optional polish. Card-alignment claims need reproducible visual evidence; existing CSS already uses flex/auto-margin alignment.
6. Historical M6/M9 reports were overwritten despite instructions. Preserve current evidence now. Record actual git dirty-state; do not claim a clean tree without checking.
7. Distinguish capabilities GET (200 with checkout_enabled=false) from orders POST rejection (503); they are not one response.

## Safe environment

Normal http://localhost:13000 (API 18000) stays checkout-CLOSED. Preserve owner `syed123`, development records and existing edits. Lab http://127.0.0.1:13001 and `/admin` (API 18001) is independent, SAMPLE-only and checkout-open. Verify readiness/capabilities. No public exposure, production deployment, real transfers, credential resets, raw database modifications or volume deletion.

If necessary, start from root:

    docker compose --env-file .env.docker.local up --build --wait -d
    docker compose -f compose.checkout-lab.yml up --build --wait -d

Create new uniquely named SAMPLE fixtures via the lab dashboard: collection/product, two variants, image/video/poster, supplier/cost and chosen stock. Do not mutate earlier run fixtures. Use separate customer/owner browser contexts and separate orders for incompatible lifecycle branches.

Provision a new lab owner using documented `provision_owner.py`, or inspect guarded `backend/scripts/lab_runtime.py --provision` (sample_m8_<8 lowercase hex>, password on stdin). Keep secrets in memory, never arguments/screenshots/reports. Expiry simulation may use existing guarded `lab_runtime.py --expire ORDER_UUID` only for your handed-off bank order named `SAMPLE M8 ...`; disclose the manipulation. Do not shorten application timers.

## Execute using browser controls

UI forms/buttons are the primary evidence. Read-only API/Network inspection may corroborate persistence, not replace UI interaction. If an action is unavailable, record that state; server rejection remains NOT TESTED unless independently observed. Do not bypass guards to force success.

Do not rerun all automated suites as a substitute. If a targeted rerun is needed, preserve its existing output before execution and distinguish fresh from inherited evidence.

Create an individual result for each ID below. Split compound cases into subrows if outcomes differ:

| IDs | Required checks |
| --- | --- |
| B01–B04 | New bank checkout; supplier acceptance/read-only preview; explicit handoff and proof still pending; premature dispatch unavailable/rejected, then funds verification, dispatch AND delivery. Record separate order/payment/shipment states. |
| C01–C03 | New COD placement/acceptance/dispatch/delivery; exact partial and final receipts; duplicate/excess settlement rejection. Compare stock and amounts at each step. |
| R01–R04 | Customer refund request/approval and separate rejection; receipt without restock; mixed sellable/damaged inspection; liability and partial/final refund payments with overpayment/repeat prevention. |
| X01–X04 | Exchange/replacement reservation; original receipt/inspection before dispatch; replacement delivery; ORIGINAL shipment RTO and separate REPLACEMENT RTO, with receipt quarantine and single inspection restock. Separate incompatible branches. |
| E01–E03 | Eligible cancellation releases once; bank expiry flag/review/release through UI after documented simulation; merely viewing does not release stock. |
| A01–A04 | Invalid/valid login/logout denial; deep links/refresh/back; wrong customer code in fresh context; expiry/revocation if feasible without changing app policy, otherwise NOT TESTED. |
| P01–P04 | Dashboard catalog/media/variant/supplier/stock authoring; corrupt upload/retry and duplicate validation; actual TWO-TAB stale-save conflict retaining input; purchased archive preserves private order/return/report evidence. |
| F01–F04 | Invalid coupon/missing fields; sold-out/unpublished cart recovery; double-click and slow/offline retry without duplicate order/hold; refresh/back/dialog close/reopen and input recovery. Claim lost-response/concurrent last-unit coverage only if induced. |
| H01–H04 | Desktop and 360/390px emulation; Tab/Shift+Tab wrapping, visible/restored focus and Escape; actual 200% browser zoom/reflow; errors/loading/empty/media with screenshots of clipping/overflow. Explicitly list unavailable real browsers/devices. |

Existing automation can support a case, but is not a new interactive PASS. For failures, capture Console/Network observations; separate deliberate denials/offline failures from unexpected ones. Continue independent cases when dependencies fail.

For each order record actual PKR totals, quantities, cost, receipts/refunds and before/after physical/held/available stock. Lab-wide reports contain other fixtures: use baseline/deltas, not assumed global totals. Do not manufacture a neat reconciliation if values disagree.

## Deliverables and completion

Preserve the original report unchanged. Write `.context/antigravity_browser_acceptance_report_v2.md`; redacted evidence goes in `.local/antigravity-browser/<new-run-id>/`. Update incrementally.

Include:
1. Verdict VERIFIED WITHIN LISTED SCOPE / PARTIAL / BLOCKED, counts and limitations.
2. Correction table: old claim, corrected fact/source and whether retested.
3. Date/time, revision/dirty-state, exact browser version/viewport/zoom, environment, setup/files changed and fixture IDs.
4. Every ID/subcase: PASS / FAIL / BLOCKED / NOT TESTED; method (new UI / read-only corroboration / inherited automation), steps, expected/observed result and exact evidence path. No implied passes.
5. Per-order timelines with exact money/stock. Exclude passwords, access codes, cookies, CSRF, personal data and raw secret-bearing HARs.
6. Reproducible P0 money/privacy/order blockers, P1 essential-task/recovery failures, P2 cosmetic findings; separate optional suggestions and hypotheses.
7. Known launch gaps, remaining human-only tests, commands/results, retained fixtures, final service state and ranked next work.

Known gaps remain: public checkout closed, zero-default shipping, no vendor payout ledger, single original shipment, unfinished policy links and unverified Azure/Meta funnel. Do not implement these during testing.

If tooling blocks a case, explain precisely, mark it and continue; do not delegate the whole pass back to the owner. No claim of complete production readiness or invented customer feedback. Finish with the v2 report link, counts and three key findings.

Afterward Codex reviews the evidence, reproduces important issues, fixes confirmed blockers and plans mobile buying-journey improvements. Real-customer usability and actual-device/staging checks remain separate.
