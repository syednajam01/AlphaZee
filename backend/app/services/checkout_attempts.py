"""Opaque checkout browser identity and canonical request fingerprints."""
import hashlib
import json
import re
import secrets

from fastapi import HTTPException, Request, Response

from app.config import settings
from app.models.orders import normalize_pakistan_phone

COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def checkout_cookie_name():
    if settings.checkout_lab:
        return 'alphazee_lab_checkout_session'
    return '__Host-alphazee_checkout' if settings.is_production else 'alphazee_checkout_session'


def checkout_session_hash(token: str) -> str:
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def mint_checkout_session(request: Request, response: Response):
    token = request.cookies.get(checkout_cookie_name(), '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        token = secrets.token_urlsafe(32)
        response.set_cookie(checkout_cookie_name(), token, max_age=COOKIE_MAX_AGE,
                            httponly=True, secure=settings.is_production,
                            samesite='strict', path='/')
    return {'ready': True}


def require_checkout_session(request: Request) -> str:
    token = request.cookies.get(checkout_cookie_name(), '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise HTTPException(428, 'Start a checkout session before placing an order.')
    return checkout_session_hash(token)


def fingerprint_order(data) -> str:
    """Normalize customer input before hashing; omit the attempt key itself."""
    def clean(value):
        return value.strip() if isinstance(value, str) else value

    quantities = {}
    for item in data.items:
        quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity
    canonical = {
        'customer_name': clean(data.customer_name),
        'customer_phone': normalize_pakistan_phone(data.customer_phone),
        'customer_email': clean(data.customer_email),
        'shipping_address_line1': clean(data.shipping_address_line1),
        'shipping_address_line2': clean(data.shipping_address_line2),
        'shipping_city': clean(data.shipping_city),
        'shipping_province': clean(data.shipping_province),
        'shipping_postal_code': clean(data.shipping_postal_code),
        'payment_method': clean(data.payment_method),
        'shipping_fee_minor': data.shipping_fee_minor,
        'coupon_code': clean(data.coupon_code).upper() if data.coupon_code else None,
        'utm_source': clean(data.utm_source),
        'utm_medium': clean(data.utm_medium),
        'utm_campaign': clean(data.utm_campaign),
        'customer_notes': clean(data.customer_notes),
        'items': sorted(quantities.items()),
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
