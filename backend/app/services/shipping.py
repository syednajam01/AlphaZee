"""Server-side fee quotes. Unconfigured rules never become accidental business terms."""
from sqlalchemy import select
from app.models.store_settings import StoreSettings
from app.config import settings


def quote_shipping(db, subtotal_minor, city, province):
    rules = db.scalar(select(StoreSettings).order_by(StoreSettings.version.desc()).with_for_update(read=True))
    if not rules or not rules.shipping_rules_configured:
        if not settings.is_production:
            return 0, {'configured': False, 'mode': 'local_sample', 'fee_minor': 0}
        raise ValueError('Delivery rules are awaiting store confirmation. Please contact support.')
    coverage = rules.shipping_coverage_area.strip()
    destinations = {v.strip().casefold() for v in coverage.split(',')}
    if coverage.casefold() != 'all pakistan' and not ({city.casefold(), province.casefold()} & destinations):
        raise ValueError('Delivery is not currently available for this city or province.')
    fee = rules.standard_shipping_fee_minor
    if rules.free_shipping_threshold_minor is not None and subtotal_minor >= rules.free_shipping_threshold_minor:
        fee = 0
    return fee, {'configured': True, 'version': rules.version, 'coverage': coverage,
        'flat_fee_minor': rules.standard_shipping_fee_minor,
        'free_threshold_minor': rules.free_shipping_threshold_minor, 'fee_minor': fee,
        'threshold_basis': 'catalog_subtotal_before_discount'}
