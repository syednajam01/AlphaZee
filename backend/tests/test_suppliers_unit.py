"""
test_suppliers_unit.py — Unit tests for supplier models and validation.

These tests inspect ORM definitions, validation logic, and constraint definitions
without requiring a live database connection.
"""

import uuid
import pytest

from app.models.suppliers import Supplier, SupplierMembership, UserAccount


def test_user_account_model_instantiation():
    user = UserAccount(
        auth_subject="auth0|123456",
        display_name="Syed Najam",
        is_active=True,
    )
    assert user.auth_subject == "auth0|123456"
    assert user.display_name == "Syed Najam"
    assert user.is_active is True
    assert "auth0|123456" in repr(user)


def test_supplier_status_validates_allowed_values():
    s_active = Supplier(name="Karachi Fabric Co", slug="karachi-fabric", status="active")
    assert s_active.status == "active"

    s_inactive = Supplier(name="Lahore Mills", slug="lahore-mills", status="inactive")
    assert s_inactive.status == "inactive"

    s_suspended = Supplier(name="Rawalpindi Garments", slug="rwp-garments", status="suspended")
    assert s_suspended.status == "suspended"


def test_supplier_status_rejects_invalid_values():
    with pytest.raises(ValueError, match="Invalid supplier status"):
        Supplier(name="Bad Supplier", slug="bad-sup", status="deleted")

    with pytest.raises(ValueError, match="Invalid supplier status"):
        Supplier(name="Bad Supplier", slug="bad-sup", status="ACTIVE")


def test_supplier_membership_instantiation():
    user_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    sm = SupplierMembership(
        user_id=user_id,
        supplier_id=supplier_id,
        active=True,
    )
    assert sm.user_id == user_id
    assert sm.supplier_id == supplier_id
    assert sm.active is True
    assert repr(sm).startswith("<SupplierMembership")
