# Phase D/E stock transition rules

`inventory_balances.on_hand` counts sellable units physically at the supplier/shop. An active reservation hold reduces availability while the item is still on hand. A dispatched parcel is no longer on hand and is not an active hold. Each physical movement records a stock event in the same transaction, keyed to its source.

| Event | Reservation | Physical on hand | Active hold | Shipment allocation | Order |
| --- | --- | ---: | ---: | --- | --- |
| Checkout | none → held | 0 | +quantity | none | placed |
| Supplier acceptance | held → confirmed | 0 | 0 | none | confirmed |
| Dispatch | confirmed → dispatched | −quantity once | −quantity | created for exact reservation/quantity | dispatched |
| Delivery | dispatched → fulfilled | 0 | 0 | same allocation, delivered | delivered |
| Pre-dispatch cancellation | held/confirmed → cancelled | 0 | −quantity | none | cancelled |
| RTO initiation/receipt | dispatched/fulfilled unchanged | 0 | 0 | returned/received quantities recorded | rto |
| RTO inspection | disposition recorded | +sellable delta only | 0 | sellable/damaged/unresolved bounded by received | rto |
| Customer return receipt | fulfilled unchanged | 0 | 0 | received quantity quarantined | delivered/rto |
| Customer return inspection | fulfilled unchanged | +sellable delta only | 0 | sellable/damaged/unresolved bounded by received | delivered/rto |

Dispatch requires complete supplier-confirmed allocations and cleared bank funds when applicable. Delivery requires a previously dispatched shipment allocation; it cannot create or repair earlier events. RTO and customer return restocks always target the historical supplier variant recorded by the dispatched reservation. Damaged and unresolved units never increase sellable stock. Duplicate status callbacks or inspection submissions create no additional stock movement.

Legacy shipments predate explicit allocations and dispatch deductions. The additive migration flags them for owner stock reconciliation instead of assuming physical stock was or was not already adjusted. New dispatch is unaffected. Historical records require an explicit reconciliation decision before stock-affecting continuation; ambiguous multi-shipment records remain blocked for manual mapping.
