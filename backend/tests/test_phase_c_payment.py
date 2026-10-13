"""Payment handoff, review, and stock safety checks for Phase C."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.queries.reservations import get_inventory_summary
from app.services.orders import (
    CreateOrderDTO, OrderItemDTO, cancel_order, confirm_supplier_acceptance,
    mark_expired_bank_orders_for_review, place_order, preview_bank_instructions,
    record_payment_instructions_sent, resolve_payment_review, upload_payment_receipt,
    verify_bank_payment,
)
from tests.test_payment_separation import _setup_catalog
from tests.test_owner_sessions import sign_in, ORIGIN


def _bank_order(db):
    variant, supplier_variant, _, user = _setup_catalog(db, on_hand=2)
    order = place_order(db, CreateOrderDTO(
        customer_name='SAMPLE Phase C', customer_phone='03001234567',
        shipping_address_line1='Sample Road', shipping_city='Lahore',
        shipping_province='Punjab', payment_method='bank_transfer',
        items=[OrderItemDTO(variant_id=variant.id, quantity=1)],
    ))
    db.flush()
    return order, supplier_variant, user


def test_unconfigured_transfer_is_rejected_at_service_and_capability(db_session, client):
    variant, _, _, _ = _setup_catalog(db_session)
    assert settings.permitted_payment_methods == ['cod']
    assert client.get('/api/v1/storefront/capabilities').json()['payment_methods'] == ['cod']
    with pytest.raises(ValueError, match='unavailable'):
        place_order(db_session, CreateOrderDTO(
            customer_name='SAMPLE Customer', customer_phone='03001234567',
            shipping_address_line1='Sample Road', shipping_city='Lahore',
            shipping_province='Punjab', payment_method='bank_transfer',
            items=[OrderItemDTO(variant_id=variant.id, quantity=1)],
        ))


def test_handoff_requires_confirmation_and_does_not_restart_deadline(db_session, configured_bank, monkeypatch):
    order, _, user = _bank_order(db_session)
    with pytest.raises(ValueError, match='Confirm the supplier'):
        record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=user.id,
                                         channel='sms', reference='message-1')
    with pytest.raises(ValueError, match='after bank instructions'):
        upload_payment_receipt(db_session, order_id=order.id, receipt_image_url='https://example.com/proof.png')
    assert order.payment_deadline_at is None
    confirm_supplier_acceptance(db_session, order_id=order.id)
    preview = preview_bank_instructions(db_session, order.id)
    assert preview['already_sent_at'] is None
    assert order.payment_deadline_at is None
    sent = record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=user.id,
                                            channel='sms', reference='message-1')
    first_deadline = sent.payment_deadline_at
    assert first_deadline - sent.payment_instructions_sent_at == timedelta(hours=4)
    assert sent.payment_status == 'pending'
    monkeypatch.setattr(settings, 'bank_name', 'Different Bank')
    assert preview_bank_instructions(db_session, order.id)['bank_name'] == 'Standard Chartered Bank'
    record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=user.id,
                                     channel='email', reference='resend-2')
    assert sent.payment_deadline_at == first_deadline
    assert sent.payment_instructions_channel == 'sms'


def test_expired_payment_requires_review_and_preserves_stock(db_session, configured_bank):
    order, supplier_variant, user = _bank_order(db_session)
    confirm_supplier_acceptance(db_session, order_id=order.id)
    record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=user.id,
                                     channel='whatsapp', reference='message-1')
    order.payment_deadline_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()
    with pytest.raises(ValueError, match='review'):
        verify_bank_payment(db_session, order_id=order.id, verified_by_user_id=user.id)
    with pytest.raises(ValueError, match='review'):
        cancel_order(db_session, order_id=order.id)
    assert len(mark_expired_bank_orders_for_review(db_session)) == 1
    assert mark_expired_bank_orders_for_review(db_session) == []
    assert get_inventory_summary(db_session, supplier_variant.id).available == 1
    with pytest.raises(ValueError, match='Review requires'):
        resolve_payment_review(db_session, order_id=order.id, actor_user_id=user.id,
                               resolution='release_unpaid', note='No funds received', funds_checked=False)
    resolved = resolve_payment_review(db_session, order_id=order.id, actor_user_id=user.id,
                                      resolution='payment_received', note='Cleared bank funds checked',
                                      funds_checked=True)
    assert resolved.payment_status == 'verified'
    assert resolved.payment_review_status == 'resolved_paid'
    assert resolved.order_status == 'confirmed'
    assert get_inventory_summary(db_session, supplier_variant.id).available == 1
    with pytest.raises(ValueError, match='refund'):
        cancel_order(db_session, order_id=order.id)


def test_expired_unpaid_review_releases_only_after_explicit_decision(db_session, configured_bank):
    order, supplier_variant, user = _bank_order(db_session)
    confirm_supplier_acceptance(db_session, order_id=order.id)
    record_payment_instructions_sent(db_session, order_id=order.id, actor_user_id=user.id,
                                     channel='sms', reference='message-2')
    order.payment_deadline_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()
    mark_expired_bank_orders_for_review(db_session)
    assert get_inventory_summary(db_session, supplier_variant.id).available == 1
    resolved = resolve_payment_review(db_session, order_id=order.id, actor_user_id=user.id,
                                      resolution='release_unpaid', note='Bank and pending funds checked',
                                      funds_checked=True)
    assert resolved.order_status == 'cancelled'
    assert resolved.payment_review_status == 'released_unpaid'
    assert get_inventory_summary(db_session, supplier_variant.id).available == 2


def test_owner_handoff_and_review_api_requires_session_and_explicit_funds_check(
        db_session, client, sample_owner, configured_bank):
    order, _, _ = _bank_order(db_session)
    path = f'/api/v1/admin/orders/{order.id}'
    assert client.get(path + '/payment-instructions-preview').status_code == 401
    csrf = sign_in(client).json()['csrf_token']
    headers = {'Origin': ORIGIN, 'X-CSRF-Token': csrf}
    assert client.get(path + '/payment-instructions-preview').status_code == 400
    confirm_supplier_acceptance(db_session, order_id=order.id)
    assert client.get(path + '/payment-instructions-preview').json()['order_number'] == order.order_number
    payload = {'confirmed_sent': True, 'channel': 'sms', 'reference': 'message-123'}
    assert client.post(path + '/instructions-sent', json=payload).status_code == 403
    assert client.post(path + '/instructions-sent', headers=headers,
                       json={**payload, 'confirmed_sent': False}).status_code == 422
    sent = client.post(path + '/instructions-sent', headers=headers, json=payload)
    assert sent.status_code == 200, sent.text
    assert sent.json()['payment_instructions_sent_at']
    assert sent.json()['payment_deadline_at']
    assert sent.json()['bank_instructions']['iban'] == 'PK36SCBL0000001123456702'
    assert order.payment_instructions_sent_by_user_id == sample_owner.user_id
    order.payment_deadline_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()
    checked = client.post('/api/v1/admin/orders/review-expired', headers=headers)
    assert checked.status_code == 200 and checked.json()['review_count'] == 1
    assert client.post(path + '/verify-payment', headers=headers).status_code == 400
    review_payload = {'funds_checked': True, 'resolution': 'release_unpaid',
                      'note': 'Cleared and pending bank funds checked'}
    assert client.post(path + '/payment-review', headers=headers,
                       json={**review_payload, 'funds_checked': False}).status_code == 422
    resolved = client.post(path + '/payment-review', headers=headers, json=review_payload)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()['payment_review_status'] == 'released_unpaid'
    assert order.payment_reviewed_by_user_id == sample_owner.user_id


def test_payment_verification_and_cancellation_cannot_both_commit(test_engine, configured_bank):
    with Session(test_engine) as db:
        order, supplier_variant, user = _bank_order(db)
        order_id, variant_id, user_id = order.id, supplier_variant.id, user.id
        db.commit()

    barrier = Barrier(2)

    def run(action):
        with Session(test_engine) as db:
            barrier.wait(timeout=5)
            try:
                if action == 'verify':
                    verify_bank_payment(db, order_id=order_id, verified_by_user_id=user_id)
                else:
                    cancel_order(db, order_id=order_id)
                db.commit()
                return 'committed'
            except ValueError:
                db.rollback()
                return 'rejected'

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ('verify', 'cancel')))
    assert sorted(results) == ['committed', 'rejected']
    with Session(test_engine) as db:
        from app.models.orders import Order
        settled = db.get(Order, order_id)
        available = get_inventory_summary(db, variant_id).available
        assert (settled.payment_status, settled.order_status, available) in {
            ('verified', 'placed', 1), ('pending', 'cancelled', 2),
        }
