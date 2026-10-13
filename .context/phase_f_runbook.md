# Phase F financial operations

Phase F uses PKR minor units (100 paisas = PKR 1) and an all-time, current-state report. It is an operational reconciliation, not a dated tax or general-ledger export. Refresh the owner Analytics tab after recording settlement or refund evidence. No browser verification was performed at the owner's request.

## COD settlement

Only a delivered COD shipment can receive a settlement entry. Open **COD Settlement** on its owner order row; the dialog shows gross COD, bank receipts, deductions, outstanding balance, and prior references. Enter the new bank receipt amount and a unique reference. For a deduction, select outbound shipping, RTO shipping, or another documented charge, then supply a positive amount, unique invoice/reference, and evidence note. Outbound and RTO deductions cannot exceed their respective recorded courier charges. Multiple receipts and deductions are retained as separate append-only rows; the database rejects updates and deletion of financial evidence. The order-ID endpoint targets only the original shipment.

The outstanding amount is gross collected COD minus cumulative bank receipts minus documented deductions. A positive outstanding amount is **partial**; when the courier marks its last payout final, it is **disputed** until resolved. A zero balance is **remitted**, even when the bank receipt is less than gross COD because documented courier charges were deducted. Duplicate references and a total above gross COD are rejected. A deduction of a courier fee changes settlement balance but does not create a second courier expense: the original shipment cost already records that expense. An `other_deduction` is an additional cost in estimated contribution.

Historical payout snapshots with a positive amount are imported as receipt entries with a `legacy-remittance-<shipment id>` reference and their old reference in the note. Review these against bank records; the migration does not invent deductions or cash. An imported short payout remains partial or disputed, never automatically settled.

## Refund payment

Completing a bank-refund return creates an approved refund liability and sales reversal; it does not mean money was sent. Use **Record Paid Refund** only after sending money, entering the actual amount and unique payment reference. Multiple partial payments can close one liability. The total cannot exceed the approved refund. The payment record is append-only; the customer return details expose paid amounts, outstanding amount, and references. A legacy `refund_reference` supplied at return completion is ignored; only the payment endpoint records executed refund evidence.

## Report definitions

All figures are minor-unit integers internally. **Order value** is the current total of non-cancelled orders. **Delivered sales** includes delivered original orders and delivered replacement charges. **Bank customer payments** count verified bank transfers, even if shipment is pending; an unpaid or undelivered order is not delivered sales. **COD collected** is delivered shipment COD, held by the courier until bank receipt. **Business cash after refunds** is verified bank customer payments plus recorded courier cash receipts minus executed refund payments. **Courier-held COD** is collected COD minus receipts and deductions. **Refund outstanding** is completed bank-refund liabilities minus executed payments.

**Net sales** is delivered sales minus completed bank-refund sales reversals. **COGS** includes delivered original product costs and delivered replacement costs, less the product cost of inspected sellable completed returns. Damaged units do not reverse COGS. **Courier expenses** come from shipment outbound/RTO costs once. **Estimated contribution** is net sales minus COGS, courier expenses, and other documented deductions; it excludes overhead, tax, chargebacks, and unrecorded fees. The legacy API key `gross_profit_minor` carries this estimated contribution for compatibility.

Deploy with `alembic upgrade head` before starting the updated API. Migrations `b83f20d6a451` and `c94e31f7d562` add financial evidence tables, import historical payout snapshots, normalize legacy partial states, and protect evidence from updates/deletes.
