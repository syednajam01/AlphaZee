"""Read-only owner navigation, stable order search and cash/sales definitions."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from app.models.orders import Order
from app.models.inventory import StockEvent, StockReservation
from app.services.orders import cancel_order, verify_bank_payment, CreateOrderDTO, OrderItemDTO, place_order
from tests.test_orders_integration import _setup_store_catalog
from tests.test_owner_stock import order

pytestmark=pytest.mark.usefixtures('configured_bank')


def test_owner_search_pagination_stable_and_no_implicit_writes(admin_client,db_session):
    variant,_,_= _setup_store_catalog(db_session,100)
    rows=[order(db_session,variant,1) for _ in range(23)]
    stamp=datetime(2026,1,1,tzinfo=timezone.utc)
    for index,row in enumerate(rows): row.placed_at=stamp; row.order_number=f'SAMPLE-M7-{index:03d}'
    db_session.flush()
    seen=[]
    for page in range(1,6):
        response=admin_client.get('/api/v1/admin/orders',params={'q':'SAMPLE-M7-','page_size':5,'page':page})
        assert response.status_code==200,response.text
        data=response.json();assert data['total']==23
        seen += [row['id'] for row in data['orders']]
    assert seen==sorted(str(row.id) for row in rows)
    assert len(set(seen))==23
    assert admin_client.get('/api/v1/admin/orders',params={'q':'%'}).json()['total']==0
    assert admin_client.get('/api/v1/admin/orders',params={'q':'_' }).json()['total']==0
    assert admin_client.get('/api/v1/admin/orders',params={'q':'x'*101}).status_code==422
    cancel_order(db_session,order_id=rows[0].id);db_session.flush()
    result=admin_client.get('/api/v1/admin/orders',params={'q':'SAMPLE-M7-','order_status':'cancelled'}).json()
    assert result['total']==1 and result['orders'][0]['id']==str(rows[0].id)
    assert db_session.scalar(select(func.count(StockReservation.id)).where(StockReservation.stage=='held'))==22


def test_overview_reuses_cash_and_delivered_sales_definitions(admin_client,db_session,sample_owner):
    variant,_,_= _setup_store_catalog(db_session,10)
    before=admin_client.get('/api/v1/admin/overview').json()
    bank=place_order(db_session,CreateOrderDTO(customer_name='SAMPLE M7 bank',customer_phone='03001234567',
        shipping_address_line1='SAMPLE street',shipping_city='Lahore',shipping_province='Punjab',
        payment_method='bank_transfer',items=[OrderItemDTO(variant.id,1)]))
    verify_bank_payment(db_session,order_id=bank.id,verified_by_user_id=sample_owner.user_id);db_session.flush()
    overview=admin_client.get('/api/v1/admin/overview').json()
    assert overview['gross_revenue_minor']==before['gross_revenue_minor']
    assert overview['cash_received_minor']==before['cash_received_minor']+variant.price_minor
    state=(bank.order_status,bank.payment_review_status,db_session.scalar(select(func.count(StockEvent.id))))
    for _ in range(2):
        report=admin_client.get('/api/v1/admin/analytics/profit-loss')
        assert report.status_code==200,report.text
        assert admin_client.get('/api/v1/admin/orders',params={'order_id':str(bank.id)}).status_code==200
        assert admin_client.get('/api/v1/admin/returns').status_code==200
    db_session.refresh(bank)
    assert state==(bank.order_status,bank.payment_review_status,db_session.scalar(select(func.count(StockEvent.id))))
    assert overview['cash_received_minor']==report.json()['business_cash_received_minor']
    assert overview['estimated_contribution_minor']==report.json()['gross_profit_minor']
