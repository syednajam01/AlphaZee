"""Services for Vendor Stock Portal & Authentication (VS2-VS3)."""
from datetime import datetime, timezone
import re
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.catalog import Product, Variant
from app.models.inventory import InventoryBalance, StockEvent, StockReservation, SupplierVariant
from app.models.suppliers import Supplier, SupplierMembership, UserAccount
from app.models.vendor_portal import VendorStockShortage, VendorUser
from app.queries.inventory import StaleInventoryError, adjust_inventory, get_active_supplier_variant
from app.queries.stock_rules import holding_predicate
from app.services.passwords import hash_password
from app.services.vendor_session_store import revoke_vendor_user_sessions


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Owner Administration of Vendor Users ---

def provision_vendor_user(
    db: Session,
    vendor_id: uuid.UUID,
    username: str,
    password: str,
    *,
    allow_short_local: bool = False,
) -> VendorUser:
    """Create or update a vendor stock user for an active supplier."""
    vendor = db.get(Supplier, vendor_id)
    if not vendor:
        raise ValueError("Supplier not found.")
    if vendor.supplier_type != "external_vendor":
        raise ValueError("Cannot provision vendor login for internal or non-vendor suppliers.")

    clean_username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.@-]{3,100}", clean_username):
        raise ValueError("Username must contain 3 to 100 letters, digits, _, ., @ or -.")

    password_hash = hash_password(password, allow_short_local=allow_short_local)

    # Check if VendorUser already exists with this username
    existing_user = db.scalar(
        select(VendorUser).where(VendorUser.username == clean_username).with_for_update()
    )
    if existing_user:
        if existing_user.vendor_id != vendor_id:
            raise ValueError(f"Username '{clean_username}' is already in use by another shop.")
        existing_user.password_hash = password_hash
        existing_user.is_active = True
        existing_user.updated_at = _utcnow()
        revoke_vendor_user_sessions(db, existing_user.id)
        db.flush()
        return existing_user

    # Create associated UserAccount for unified audit references
    user_account = UserAccount(
        auth_subject=f"vendor:{clean_username}",
        display_name=f"{vendor.name} ({clean_username})",
        is_active=True,
    )
    db.add(user_account)
    db.flush()

    # Create VendorUser
    vendor_user = VendorUser(
        user_id=user_account.id,
        vendor_id=vendor_id,
        username=clean_username,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(vendor_user)

    # Ensure SupplierMembership exists
    membership = db.get(SupplierMembership, (user_account.id, vendor_id))
    if not membership:
        membership = SupplierMembership(
            user_id=user_account.id,
            supplier_id=vendor_id,
            active=True,
        )
        db.add(membership)
    else:
        membership.active = True

    db.flush()
    return vendor_user


def reset_vendor_password(
    db: Session,
    vendor_user_id: uuid.UUID,
    password: str,
    *,
    allow_short_local: bool = False,
) -> VendorUser:
    """Reset vendor password and revoke active sessions."""
    vendor_user = db.get(VendorUser, vendor_user_id)
    if not vendor_user:
        raise ValueError("Vendor user not found.")
    vendor_user.password_hash = hash_password(password, allow_short_local=allow_short_local)
    vendor_user.updated_at = _utcnow()
    revoke_vendor_user_sessions(db, vendor_user.id)
    db.flush()
    return vendor_user


def toggle_vendor_user_status(
    db: Session,
    vendor_user_id: uuid.UUID,
    is_active: bool,
) -> VendorUser:
    """Enable or disable vendor login access."""
    vendor_user = db.get(VendorUser, vendor_user_id)
    if not vendor_user:
        raise ValueError("Vendor user not found.")
    vendor_user.is_active = is_active
    vendor_user.updated_at = _utcnow()
    if not is_active:
        revoke_vendor_user_sessions(db, vendor_user.id)
    # Also update user_account
    user_acc = db.get(UserAccount, vendor_user.user_id)
    if user_acc:
        user_acc.is_active = is_active
    db.flush()
    return vendor_user


def list_vendor_users(db: Session, vendor_id: uuid.UUID) -> List[VendorUser]:
    """List all user accounts for a specific vendor."""
    stmt = (
        select(VendorUser)
        .where(VendorUser.vendor_id == vendor_id)
        .order_by(VendorUser.created_at.asc())
    )
    return list(db.scalars(stmt))


# --- Vendor Stock Portal Read & Update Operations ---

def get_vendor_stock_list(
    db: Session,
    vendor_id: uuid.UUID,
    *,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[dict], int]:
    """
    Fetch paginated variants assigned to this vendor.
    Excludes wholesale costs, customer retail prices, margins, and customer data.
    """
    base_query = (
        select(
            Variant,
            Product,
            SupplierVariant,
            InventoryBalance,
        )
        .join(Product, Product.id == Variant.product_id)
        .join(
            SupplierVariant,
            and_(
                SupplierVariant.variant_id == Variant.id,
                SupplierVariant.active.is_(True),
                SupplierVariant.supplier_id == vendor_id,
            ),
        )
        .outerjoin(InventoryBalance, InventoryBalance.supplier_variant_id == SupplierVariant.id)
        .where(
            Product.status != "archived",
            or_(
                Product.vendor_id == vendor_id,
                SupplierVariant.supplier_id == vendor_id,
            ),
        )
    )

    if search:
        s = f"%{search.strip().lower()}%"
        base_query = base_query.where(
            or_(
                func.lower(Product.title).like(s),
                func.lower(Variant.sku).like(s),
                func.lower(Variant.color).like(s),
                func.lower(Variant.size).like(s),
            )
        )

    # Count total
    total_count = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0

    # Execute paginated query
    query = base_query.order_by(Product.title.asc(), Variant.sku.asc()).offset(offset).limit(limit)
    rows = db.execute(query).all()

    items = []
    for var, prod, sv, balance in rows:
        on_hand = balance.on_hand if balance else 0
        version = balance.version if balance else 0
        last_updated = balance.last_counted_at if balance else None

        # Calculate held reservations
        held_stmt = (
            select(func.coalesce(func.sum(StockReservation.quantity), 0))
            .where(
                StockReservation.supplier_variant_id == sv.id,
                holding_predicate(),
            )
        )
        held = int(db.scalar(held_stmt) or 0)
        available = max(0, on_hand - held)

        items.append({
            "variant_id": var.id,
            "product_id": prod.id,
            "product_title": prod.title,
            "product_slug": prod.slug,
            "thumbnail_url": prod.hero_image_url if hasattr(prod, "hero_image_url") else None,
            "variant_sku": var.sku,
            "size": var.size,
            "color": var.color,
            "allocated_on_hand": on_hand,
            "held_quantity": held,
            "available_quantity": available,
            "version": version,
            "last_updated_at": last_updated,
        })

    return items, total_count


def update_vendor_counted_quantity(
    db: Session,
    vendor_id: uuid.UUID,
    vendor_user: VendorUser,
    variant_id: int,
    counted_quantity: int,
    expected_version: int,
    reason: str,
    note: Optional[str] = None,
    request_ref: Optional[str] = None,
) -> dict:
    """
    Atomically update physical count allocated by vendor to AlphaZee.
    If counted_quantity < held_reservations, records a shortage alert and returns shortage details
    WITHOUT overwriting or cancelling customer reservations.
    """
    # 1. Verify variant belongs to this vendor
    sv = db.scalar(
        select(SupplierVariant)
        .join(Variant, Variant.id == SupplierVariant.variant_id)
        .join(Product, Product.id == Variant.product_id)
        .where(
            SupplierVariant.variant_id == variant_id,
            SupplierVariant.active.is_(True),
            SupplierVariant.supplier_id == vendor_id,
        )
    )
    if not sv:
        raise ValueError("Variant not assigned to this vendor or linkage is inactive.")

    variant = db.get(Variant, variant_id)
    product = db.get(Product, variant.product_id)
    if product and product.status == "archived":
        raise ValueError("Cannot update inventory for an archived product.")

    # 2. Lock balance row
    balance = db.scalar(
        select(InventoryBalance)
        .where(InventoryBalance.supplier_variant_id == sv.id)
        .with_for_update()
    )
    if not balance:
        raise ValueError("Inventory balance record not found.")

    if balance.version != expected_version:
        # Calculate current held
        held = int(db.scalar(
            select(func.coalesce(func.sum(StockReservation.quantity), 0))
            .where(StockReservation.supplier_variant_id == sv.id, holding_predicate())
        ) or 0)
        raise StaleInventoryError(
            f"Inventory version conflict. Current version is {balance.version}, physical count {balance.on_hand}, held {held}."
        )

    # 3. Check committed holds
    held_reservations = int(db.scalar(
        select(func.coalesce(func.sum(StockReservation.quantity), 0))
        .where(StockReservation.supplier_variant_id == sv.id, holding_predicate())
    ) or 0)

    # 4. Shortage detection: counted_quantity < held_reservations
    if counted_quantity < held_reservations:
        shortage = VendorStockShortage(
            variant_id=variant_id,
            vendor_id=vendor_id,
            vendor_user_id=vendor_user.id,
            reported_count=counted_quantity,
            held_reservations=held_reservations,
            physical_on_hand_snapshot=balance.on_hand,
            status="open",
            notes=note or f"Reported count ({counted_quantity}) below holds ({held_reservations}) via {reason}",
        )
        db.add(shortage)
        db.flush()
        return {
            "variant_id": variant_id,
            "allocated_on_hand": balance.on_hand,
            "held_quantity": held_reservations,
            "available_quantity": max(0, balance.on_hand - held_reservations),
            "version": balance.version,
            "shortage_detected": True,
            "message": f"Reported count ({counted_quantity}) is below committed holds ({held_reservations}). Shortage alert recorded for owner review; existing reservations are preserved.",
        }

    # 5. Normal absolute count update using adjust_inventory
    detailed_note = f"Vendor count update [{reason}]: {note or ''}".strip()
    event = adjust_inventory(
        db,
        supplier_variant_id=sv.id,
        actor_user_id=vendor_user.user_id,
        new_on_hand=counted_quantity,
        reason="manual_count",
        expected_version=expected_version,
        notes=detailed_note,
        last_counted_at=_utcnow(),
        source_ref=request_ref,
    )
    db.flush()

    new_available = max(0, counted_quantity - held_reservations)
    return {
        "variant_id": variant_id,
        "allocated_on_hand": counted_quantity,
        "held_quantity": held_reservations,
        "available_quantity": new_available,
        "version": balance.version,
        "shortage_detected": False,
        "message": "Allocated count successfully updated.",
    }


def report_vendor_shortage(
    db: Session,
    vendor_id: uuid.UUID,
    vendor_user: VendorUser,
    variant_id: int,
    reported_count: int,
    note: Optional[str] = None,
) -> VendorStockShortage:
    """Explicitly report a stock shortage for owner resolution."""
    sv = db.scalar(
        select(SupplierVariant).where(
            SupplierVariant.variant_id == variant_id,
            SupplierVariant.active.is_(True),
            SupplierVariant.supplier_id == vendor_id,
        )
    )
    if not sv:
        raise ValueError("Variant not assigned to this vendor.")

    balance = db.scalar(
        select(InventoryBalance).where(InventoryBalance.supplier_variant_id == sv.id)
    )
    on_hand = balance.on_hand if balance else 0

    held = int(db.scalar(
        select(func.coalesce(func.sum(StockReservation.quantity), 0))
        .where(StockReservation.supplier_variant_id == sv.id, holding_predicate())
    ) or 0)

    shortage = VendorStockShortage(
        variant_id=variant_id,
        vendor_id=vendor_id,
        vendor_user_id=vendor_user.id,
        reported_count=reported_count,
        held_reservations=held,
        physical_on_hand_snapshot=on_hand,
        status="open",
        notes=note,
    )
    db.add(shortage)
    db.flush()
    return shortage


def get_vendor_update_history(
    db: Session,
    vendor_id: uuid.UUID,
    limit: int = 30,
) -> Tuple[List[dict], int]:
    """Fetch recent audit events for variants supplied by this vendor."""
    stmt = (
        select(StockEvent, Variant, Product, UserAccount)
        .join(SupplierVariant, SupplierVariant.id == StockEvent.supplier_variant_id)
        .join(Variant, Variant.id == SupplierVariant.variant_id)
        .join(Product, Product.id == Variant.product_id)
        .outerjoin(UserAccount, UserAccount.id == StockEvent.actor_user_id)
        .where(SupplierVariant.supplier_id == vendor_id)
        .order_by(StockEvent.occurred_at.desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    history = []
    for ev, var, prod, user in rows:
        history.append({
            "event_id": ev.id,
            "variant_id": var.id,
            "product_title": prod.title,
            "variant_sku": var.sku,
            "actor_username": user.display_name if user else "System",
            "previous_on_hand": ev.previous_on_hand,
            "new_on_hand": ev.new_on_hand,
            "delta": ev.delta,
            "reason": ev.reason,
            "notes": ev.notes,
            "occurred_at": ev.occurred_at,
        })
    return history, len(history)


# --- Owner Shortage Management ---

def list_open_shortages(
    db: Session,
    vendor_id: Optional[uuid.UUID] = None,
) -> List[VendorStockShortage]:
    """List open shortages requiring owner operational review."""
    stmt = select(VendorStockShortage).where(VendorStockShortage.status == "open")
    if vendor_id:
        stmt = stmt.where(VendorStockShortage.vendor_id == vendor_id)
    stmt = stmt.order_by(VendorStockShortage.reported_at.desc())
    return list(db.scalars(stmt))


def resolve_shortage(
    db: Session,
    shortage_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    resolution_action: str,
    resolution_note: str,
) -> VendorStockShortage:
    """Mark a reported shortage resolved or cancelled with recorded owner note."""
    if resolution_action not in {"resolved", "cancelled"}:
        raise ValueError("Invalid resolution action.")

    shortage = db.get(VendorStockShortage, shortage_id)
    if not shortage:
        raise ValueError("Shortage record not found.")

    shortage.status = resolution_action
    shortage.resolved_at = _utcnow()
    shortage.resolved_by_user_id = owner_user_id
    shortage.resolution_note = resolution_note
    db.flush()
    return shortage
