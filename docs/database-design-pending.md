# AlphaZee — Database & Commerce Decisions Pending Owner Alignment

Owner: Syed Najam. Milestone: Database Design Discussion Preparation.

---

> **Notice**: The database design is currently under discussion. None of the items below are implemented or assumed in the code. All schema changes remain paused until explicit owner approval.

The following commercial, operational, and database questions are prepared for our database specification discussion:

---

## 1. Customer Accounts & Identity
- **Question**: Should initial orders support guest checkout exclusively, or should customer accounts (passwords / OTP) be required?
- **Trade-offs**: Guest checkout maximizes conversion on Pakistan mobile devices; accounts allow order tracking history and faster repeat checkout.
- **Proposed Direction**: Start with guest checkout using verified phone numbers; associate future account creation by phone number retrospectively.

## 2. Supplier Fulfillment & Multi-Supplier Orders
- **Question**: When a customer orders items sourced from two different local suppliers:
  - Do we hold items until consolidated into a single parcel?
  - Or do we dispatch two split shipments with separate courier tracking numbers?
- **Trade-offs**: Consolidated delivery has one shipping fee for the customer but adds fulfillment latency and intermediate handling. Split shipments deliver faster but incur double courier fees.

## 3. Shipping Charges & Economics
- **Question**: How should courier fees be charged to the customer?
  - Flat rate across Pakistan (e.g. PKR 200)?
  - Tiered by destination city (within Karachi/Lahore vs other cities)?
  - Free shipping threshold (e.g. orders over PKR 5,000)?
- **Database Impact**: Order record must snapshot exact customer shipping fee, carrier quote, and free-shipping discount applied.

## 4. Supplier Costs & Agreed Price Snapshots
- **Question**: Where and how are agreed supplier wholesale costs stored and updated?
- **Requirement**: Each order line item must record the purchase-time supplier cost alongside the retail selling price so accurate gross margin is preserved even if supplier prices change later.

## 5. Order, Payment, Shipment, and Settlement Statuses
The business requires distinct state tracking across four operational lifecycles:
1. **Order Status**: `submitted` $\rightarrow$ `confirmed` $\rightarrow$ `processing` $\rightarrow$ `fulfilled` $\rightarrow$ `cancelled`.
2. **Payment Status**:
   - For COD: `pending_delivery` $\rightarrow$ `collected_by_courier` $\rightarrow$ `remitted_to_bank`.
   - For Bank Transfer: `awaiting_transfer` $\rightarrow$ `funds_verified_by_owner` $\rightarrow$ `refunded`.
3. **Shipment Status**: `unfulfilled` $\rightarrow$ `dispatched` $\rightarrow$ `in_transit` $\rightarrow$ `out_for_delivery` $\rightarrow$ `delivered` $\rightarrow$ `returned_to_origin (RTO)`.
4. **Courier Settlement**: Tracking when the courier company actually remits cash collected from COD deliveries into the AlphaZee business bank account (often 7–14 days in Pakistan).

## 6. COD Remittance & RTO (Return to Origin) Charges
- **Question**: How do we account for failed deliveries (RTO)?
  - In Pakistan ecommerce, COD failure rates (RTO) can range from 10% to 25%.
  - Courier services still charge delivery fees (plus return fees) on RTO orders.
- **Database Impact**: Financial reports must distinguish lost inventory from returned inventory and log courier charges incurred on RTO parcels.

## 7. Returns, Exchanges, and Refunds
- **Question**: What is the policy for customer-initiated returns or size exchanges?
  - Who covers courier fees for size exchanges?
  - Are refunds issued via bank transfer or store credit vouchers?
- **Database Impact**: Return requests must record reason, condition on receipt, inspection outcome, and refund transaction references.

## 8. Purchase-Time Immutability & Snapshots
- **Requirement**: Order history must never break if a catalog product or variant is archived, edited, or price-adjusted.
- **Items to Snapshot**:
  - Full variant SKU and human-readable title (e.g. "Heavyweight Boxy Tee - M / Chalk White").
  - Unit price charged to customer (in paisas).
  - Wholesale cost owed to supplier (in paisas).
  - Customer shipping name, phone number, and delivery address.

## 9. Profit Calculation & Missing Expense Tracking
- **Requirement**: Profit reporting must account for:
  - Gross sales minus discounts.
  - Cost of Goods Sold (supplier costs).
  - Outbound courier fees and RTO courier fees.
  - Packaging materials (mailer bags, tags, boxes).
  - Clear disclosure of missing advertising (Meta/TikTok ads) and operating costs.

## 10. Administrator Permissions & Audit Logs
- **Question**: Who accesses the owner management console?
  - Single owner login vs role-based access for future fulfillment helpers.
- **Database Impact**: Future admin operations need server-side authentication tokens and action audit logs (e.g. who confirmed an order or verified a bank transfer).

## 11. Bank Transfer Receipt Uploads & Private Storage
- **Requirement**: Receipts uploaded by customers must never be publicly readable on the internet.
- **Architecture**: Store image files in private Azure Blob Storage with short-lived shared access signatures (SAS) accessible only by the owner during verification.

## 12. Marketing Attribution & UTM Tracking
- **Question**: Should order records store marketing attribution parameters (`utm_source`, `utm_medium`, `utm_campaign`, `referrer`)?
- **Value**: Enables measuring ad spend ROI across Meta, TikTok, and influencer campaigns.
