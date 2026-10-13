"""Real, separate-session PostgreSQL contention on one COD shipment."""
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.finance import CourierSettlementEntry
from app.models.shipments import Shipment
from app.services.finance import FinanceError, record_settlement


@pytest.fixture
def delivered_cod_shipment(test_engine):
    number = f'AZ-SETTLEMENT-{uuid.uuid4().hex[:8]}'
    with test_engine.begin() as conn:
        order_id = conn.scalar(text('''INSERT INTO orders
            (order_number, customer_name, customer_phone, shipping_address_line1,
             shipping_city, shipping_province, payment_method, payment_status,
             subtotal_minor, total_minor, order_status)
            VALUES (:number, 'SAMPLE Settlement', '03001112222', 'SAMPLE Street',
                    'Lahore', 'Punjab', 'cod', 'verified', 100000, 100000, 'delivered')
            RETURNING id'''), {'number': number})
        shipment_id = conn.scalar(text('''INSERT INTO shipments
            (order_id, courier_code, tracking_number, status, cod_amount_minor,
             cod_remittance_status, delivered_at)
            VALUES (:order_id, 'manual', :number, 'delivered', 100000,
                    'pending_remittance', now()) RETURNING id'''),
            {'order_id': order_id, 'number': number})
    try:
        yield shipment_id, number
    finally:
        # Separate-session checks commit by design; remove only this fixture's rows.
        with test_engine.begin() as conn:
            conn.execute(text('DELETE FROM courier_settlement_entries WHERE shipment_id=:id'),
                         {'id': shipment_id})
            conn.execute(text('DELETE FROM shipments WHERE id=:id'), {'id': shipment_id})
            conn.execute(text('DELETE FROM orders WHERE id=:id'), {'id': order_id})


def test_simultaneous_partial_receipts_cannot_exceed_collected_cod(test_engine, delivered_cod_shipment):
    shipment_id, number = delivered_cod_shipment

    barrier = threading.Barrier(2)

    def worker(index: int):
        with Session(test_engine) as db:
            barrier.wait(timeout=10)
            try:
                record_settlement(db, shipment_id=shipment_id, amount_minor=70000,
                                  reference=f'SAMPLE-RACE-{number}-{index}', deductions=[])
                db.commit()
                return 'recorded'
            except FinanceError:
                db.rollback()
                return 'rejected'

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, range(2)))
    assert sorted(outcomes) == ['recorded', 'rejected']
    with Session(test_engine) as db:
        entries = db.scalars(select(CourierSettlementEntry).where(
            CourierSettlementEntry.shipment_id == shipment_id)).all()
        shipment = db.get(Shipment, shipment_id)
        assert len(entries) == 1
        assert entries[0].amount_minor == 70000
        assert shipment.cod_remitted_amount_minor == 70000
        assert shipment.settlement_outstanding_minor == 30000
        assert shipment.cod_remittance_status == 'partial'
