"""Automated tests for VF6: Configurable Storefront Settings, Policy Publication & Admin Preferences."""
import secrets
import pytest
from starlette.testclient import TestClient

from sqlalchemy import delete
from app.database import SessionLocal
from app.main import app
from app.models.auth import OwnerLoginBucket
from app.models.store_settings import StoreSettings, StoreSettingsAuditLog, OwnerPreference
from app.services.owners import provision_owner


@pytest.fixture
def db(db_session):
    return db_session


@pytest.fixture
def client(db_session, monkeypatch):
    from app.database import get_db
    from app.dependencies.checkout import require_checkout_enabled
    from sqlalchemy.orm import sessionmaker
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_checkout_enabled] = lambda: None
    # Legacy helpers use SessionLocal; route them to this same guarded test transaction.
    import sys
    module = sys.modules[__name__]
    from contextlib import contextmanager
    @contextmanager
    def scoped_session():
        yield db_session
    monkeypatch.setattr(module, 'SessionLocal', scoped_session)
    try:
        with TestClient(app, base_url='http://localhost:3000') as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def _create_owner(db, username=None):
    token = secrets.token_hex(4)
    uname = f"{username}_{token}" if username else f"owner_vf6_{token}"
    pwd = f"OwnerPass123_{token}"
    provision_owner(db, uname, pwd, reset_password=True, allow_short_local=True)
    db.commit()
    return uname, pwd


def _login_owner(client, username, password):
    with SessionLocal() as db:
        db.execute(delete(OwnerLoginBucket))
        db.commit()
    res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        headers={"Origin": "http://localhost:3000"},
    )
    assert res.status_code == 200, res.text
    return res.json()["csrf_token"]


def test_public_store_settings_unauthenticated(client):
    """Public endpoint /api/v1/store/settings is unauthenticated and safe."""
    res = client.get("/api/v1/store/settings")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "brand_name" in data
    assert "announcement_banner_enabled" in data
    assert "announcement_banner_text" in data
    assert "accent_color" in data
    assert "font_family" in data
    assert "standard_shipping_fee_minor" in data
    # Invariant: internal operational thresholds and audit IDs must not be leaked to public
    assert "low_stock_threshold" not in data
    assert "stock_staleness_threshold_days" not in data
    assert "version" not in data
    assert "updated_by_user_id" not in data


def test_admin_settings_requires_owner_auth(client, db):
    """Admin settings routes strictly reject unauthenticated requests."""
    res = client.get("/api/v1/admin/settings")
    assert res.status_code == 401

    uname, pwd = _create_owner(db)
    _login_owner(client, uname, pwd)

    res = client.get("/api/v1/admin/settings")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "low_stock_threshold" in data
    assert "version" in data
    assert data["version"] >= 1


def test_update_store_settings_and_audit_log(client, db):
    """Owner updates branding and shipping settings; version increments and audit log is recorded."""
    token = secrets.token_hex(4)
    uname, pwd = _create_owner(db)
    csrf = _login_owner(client, uname, pwd)

    initial_res = client.get("/api/v1/admin/settings")
    v_start = initial_res.json()["version"]

    new_brand = f"AlphaZee Haute {token}"
    new_banner = f"Free express shipping {token}"
    update_payload = {
        "brand_name": new_brand,
        "tagline": "Curated Contemporary Silhouettes",
        "announcement_banner_enabled": True,
        "announcement_banner_text": new_banner,
        "announcement_banner_link": "#featured",
        "accent_color": "#1e3a8a",
        "font_family": "Outfit, sans-serif",
        "border_radius": "lg",
        "spacing_density": "spacious",
        "standard_shipping_fee_minor": 25000,
        "free_shipping_threshold_minor": 500000,
        "low_stock_threshold": 5,
        "stock_staleness_threshold_days": 10,
        "change_reason": f"Spring Refresh {token}",
    }

    res = client.put(
        "/api/v1/admin/settings",
        json=update_payload,
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["brand_name"] == new_brand
    assert data["tagline"] == "Curated Contemporary Silhouettes"
    assert data["accent_color"] == "#1e3a8a"
    assert data["font_family"] == "Outfit, sans-serif"
    assert data["border_radius"] == "lg"
    assert data["spacing_density"] == "spacious"
    assert data["standard_shipping_fee_minor"] == 25000
    assert data["free_shipping_threshold_minor"] == 500000
    assert data["low_stock_threshold"] == 5
    assert data["stock_staleness_threshold_days"] == 10
    assert data["version"] == v_start + 1

    # Verify public endpoint immediately reflects the updated settings
    pub_res = client.get("/api/v1/store/settings")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["brand_name"] == new_brand
    assert pub_data["announcement_banner_text"] == new_banner
    assert pub_data["accent_color"] == "#1e3a8a"
    assert pub_data["standard_shipping_fee_minor"] == 25000
    assert pub_data["free_shipping_threshold_minor"] == 500000

    # Verify audit log was recorded
    audit_res = client.get("/api/v1/admin/settings/audit-logs")
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) > 0
    latest_log = logs[0]
    assert latest_log["version"] == data["version"]
    assert "brand_name" in latest_log["changed_fields"]
    assert latest_log["change_reason"] == f"Spring Refresh {token}"


def test_settings_validation_rejects_invalid_values(client, db):
    """Validation rejects invalid hex colors, fonts, negative fees, and unknown fields."""
    uname, pwd = _create_owner(db)
    csrf = _login_owner(client, uname, pwd)

    # 1. Invalid hex color
    res = client.put(
        "/api/v1/admin/settings",
        json={"accent_color": "not-a-hex-color"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code in {400, 422}

    # 2. Unsupported font
    res = client.put(
        "/api/v1/admin/settings",
        json={"font_family": "Comic Sans MS"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code in {400, 422}

    # 3. Negative shipping fee
    res = client.put(
        "/api/v1/admin/settings",
        json={"standard_shipping_fee_minor": -100},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code in {400, 422}

    # 4. Unknown attribute (extra forbidden)
    res = client.put(
        "/api/v1/admin/settings",
        json={"malicious_secret_key": "some_value"},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code in {400, 422}


def test_policy_draft_and_publish_lifecycle(client, db):
    """Draft policies are not shown publicly until explicitly published."""
    uname, pwd = _create_owner(db)
    csrf = _login_owner(client, uname, pwd)

    # Ensure clean initial draft state for test isolation
    client.post(
        "/api/v1/admin/settings/policies/delivery/publish",
        json={"publish": False},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )

    token = secrets.token_hex(4)
    policy_text = f"All domestic orders are delivered within 3-5 business days via tracked courier services ({token})."

    # Step 1: Save draft delivery policy
    res = client.put(
        "/api/v1/admin/settings",
        json={"delivery_policy_content": policy_text},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    assert res.json()["delivery_policy_status"] == "draft"

    # Step 2: Public endpoint must still return None for draft policy
    pub_res = client.get("/api/v1/store/settings")
    assert pub_res.status_code == 200
    assert pub_res.json()["delivery_policy"] is None

    # Step 3: Publish the delivery policy
    pub_action_res = client.post(
        "/api/v1/admin/settings/policies/delivery/publish",
        json={"publish": True},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert pub_action_res.status_code == 200
    assert pub_action_res.json()["delivery_policy_status"] == "published"
    assert pub_action_res.json()["delivery_policy_published_at"] is not None

    # Step 4: Public endpoint now shows the published policy
    pub_res2 = client.get("/api/v1/store/settings")
    assert pub_res2.status_code == 200
    assert pub_res2.json()["delivery_policy"] == policy_text

    # Step 5: Unpublish policy back to draft
    unpub_res = client.post(
        "/api/v1/admin/settings/policies/delivery/publish",
        json={"publish": False},
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert unpub_res.status_code == 200
    assert unpub_res.json()["delivery_policy_status"] == "draft"

    # Step 6: Public endpoint returns None again
    pub_res3 = client.get("/api/v1/store/settings")
    assert pub_res3.json()["delivery_policy"] is None


def test_per_owner_preferences_isolation(client, db):
    """Owner A and Owner B have independent interface preferences; reset restores defaults."""
    owner_a_name, owner_a_pwd = _create_owner(db, "owner_a_prefs")
    owner_b_name, owner_b_pwd = _create_owner(db, "owner_b_prefs")

    # Owner A logs in and customizes preferences
    csrf_a = _login_owner(client, owner_a_name, owner_a_pwd)
    res_a = client.put(
        "/api/v1/admin/preferences",
        json={
            "theme": "dark",
            "table_density": "compact",
            "default_date_range": "today",
            "nav_order": ["analytics", "orders", "inventory", "settings"],
            "dashboard_layout": {
                "cards": [
                    {"id": "sales", "visible": True},
                    {"id": "inventory", "visible": False},
                ]
            },
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_a},
    )
    assert res_a.status_code == 200
    pref_a = res_a.json()
    assert pref_a["theme"] == "dark"
    assert pref_a["table_density"] == "compact"
    assert pref_a["default_date_range"] == "today"

    # Owner B logs in: preferences must be independent and default to system/comfortable
    client_b = TestClient(app, base_url="http://localhost:3000")
    _login_owner(client_b, owner_b_name, owner_b_pwd)
    res_b = client_b.get("/api/v1/admin/preferences")
    assert res_b.status_code == 200
    pref_b = res_b.json()
    assert pref_b["theme"] == "system"
    assert pref_b["table_density"] == "comfortable"
    assert pref_b["default_date_range"] == "this_month"

    # Owner A resets preferences to factory default
    reset_res = client.post(
        "/api/v1/admin/preferences/reset",
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_a},
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["theme"] == "system"
    assert reset_data["table_density"] == "comfortable"
    assert reset_data["default_date_range"] == "this_month"


def test_faq_items_and_support_configuration(client, db):
    """Owner can update support channels and FAQ items, and public store settings reflect them."""
    owner_name, pwd = _create_owner(db, "owner_faq_test")
    csrf = _login_owner(client, owner_name, pwd)

    # 1. Fetch current settings
    cur = client.get("/api/v1/admin/settings").json()
    version = cur["version"]

    custom_faqs = [
        {
            "id": "faq_1",
            "question": "Can I exchange for another size?",
            "answer": "Yes, exchanges are permitted within 7 days of delivery.",
            "category": "Returns",
            "is_enabled": True,
            "display_order": 0,
        },
        {
            "id": "faq_2",
            "question": "Secret upcoming question",
            "answer": "Not visible yet",
            "category": "General",
            "is_enabled": False,
            "display_order": 1,
        },
    ]

    # 2. Update support channels and FAQ items
    update_res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": version,
            "support_email": "care@alphazee.tech",
            "support_phone": "+923001234567",
            "support_hours": "Mon-Sat: 10am-7pm PKT",
            "faq_items": custom_faqs,
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert update_res.status_code == 200, update_res.text
    updated = update_res.json()
    assert updated["support_email"] == "care@alphazee.tech"
    assert updated["support_phone"] == "+923001234567"
    assert len(updated["faq_items"]) == 2

    # 3. Public endpoint returns only enabled FAQs and support contacts
    pub_res = client.get("/api/v1/store/settings").json()
    assert pub_res["support_email"] == "care@alphazee.tech"
    assert pub_res["support_phone"] == "+923001234567"
    assert len(pub_res["faq_items"]) == 1
    assert pub_res["faq_items"][0]["id"] == "faq_1"


def test_collections_page_headings_configuration(client, db):
    """Owner can update collections page title and subtitle, reflected in public store settings."""
    owner_name, pwd = _create_owner(db, "owner_col_head_test")
    csrf = _login_owner(client, owner_name, pwd)

    # 1. Check default values on public endpoint
    pub = client.get("/api/v1/store/settings").json()
    assert pub["collections_page_title"] == "All Collections"
    assert pub["collections_page_subtitle"] == "Explore our complete range of curated wardrobe edits."

    # 2. Update via admin settings
    cur = client.get("/api/v1/admin/settings").json()
    v = cur["version"]
    res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": v,
            "collections_page_title": "Curated Collections",
            "collections_page_subtitle": "Discover our seasonal drops and bespoke capsule wardrobes.",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    adm = res.json()
    assert adm["collections_page_title"] == "Curated Collections"
    assert adm["collections_page_subtitle"] == "Discover our seasonal drops and bespoke capsule wardrobes."

    # 3. Public endpoint now serves the updated headings
    pub_updated = client.get("/api/v1/store/settings").json()
    assert pub_updated["collections_page_title"] == "Curated Collections"
    assert pub_updated["collections_page_subtitle"] == "Discover our seasonal drops and bespoke capsule wardrobes."


def test_products_page_headings_configuration(client, db):
    """Owner can update products page title and subtitle, reflected in public store settings."""
    owner_name, pwd = _create_owner(db, "owner_prod_head_test")
    csrf = _login_owner(client, owner_name, pwd)

    # 1. Check default values on public endpoint
    pub = client.get("/api/v1/store/settings").json()
    assert pub["products_page_title"] == "All Products"
    assert pub["products_page_subtitle"] == "Find a piece that feels like you. Explore our complete catalog."

    # 2. Update via admin settings
    cur = client.get("/api/v1/admin/settings").json()
    v = cur["version"]
    res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": v,
            "products_page_title": "Catalog & Wardrobe",
            "products_page_subtitle": "Explore our full archive of premium essentials and signature cuts.",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    adm = res.json()
    assert adm["products_page_title"] == "Catalog & Wardrobe"
    assert adm["products_page_subtitle"] == "Explore our full archive of premium essentials and signature cuts."

    # 3. Public endpoint now serves the updated headings
    pub_updated = client.get("/api/v1/store/settings").json()
    assert pub_updated["products_page_title"] == "Catalog & Wardrobe"
    assert pub_updated["products_page_subtitle"] == "Explore our full archive of premium essentials and signature cuts."


def test_homepage_and_faq_headings_configuration(client, db):
    """Owner can update homepage section headings and FAQ headers, reflected in public store settings and audit logs."""
    owner_name, pwd = _create_owner(db, "owner_hp_faq_test")
    csrf = _login_owner(client, owner_name, pwd)

    # 1. Verify defaults
    pub = client.get("/api/v1/store/settings").json()
    assert pub["homepage_collections_title"] == "Shop by collection"
    assert pub["homepage_collections_subtitle"] == "A place for every part of your wardrobe."
    assert pub["homepage_products_title"] == "The current edit"
    assert pub["homepage_products_subtitle"] == "A curated selection of our latest pieces."
    assert pub["faq_section_title"] == "Before you order"
    assert pub["faq_section_subtitle"] == "A few useful answers, all in one place."

    # 2. Update via admin settings
    cur = client.get("/api/v1/admin/settings").json()
    v = cur["version"]
    res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": v,
            "homepage_collections_title": "Curated Seasonal Capsules",
            "homepage_collections_subtitle": "Exclusive capsules handpicked for every occasion.",
            "homepage_products_title": "Editor's Choice Pieces",
            "homepage_products_subtitle": "Hand-stitched luxury apparel and latest runway drops.",
            "faq_section_title": "Order Inquiries & Answers",
            "faq_section_subtitle": "Everything you need to know about our craftsmanship and delivery.",
            "change_reason": "Configure custom storefront section copy",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    adm = res.json()
    assert adm["homepage_collections_title"] == "Curated Seasonal Capsules"
    assert adm["homepage_collections_subtitle"] == "Exclusive capsules handpicked for every occasion."
    assert adm["homepage_products_title"] == "Editor's Choice Pieces"
    assert adm["homepage_products_subtitle"] == "Hand-stitched luxury apparel and latest runway drops."
    assert adm["faq_section_title"] == "Order Inquiries & Answers"
    assert adm["faq_section_subtitle"] == "Everything you need to know about our craftsmanship and delivery."

    # 3. Public endpoint serves updated values
    pub_updated = client.get("/api/v1/store/settings").json()
    assert pub_updated["homepage_collections_title"] == "Curated Seasonal Capsules"
    assert pub_updated["homepage_collections_subtitle"] == "Exclusive capsules handpicked for every occasion."
    assert pub_updated["homepage_products_title"] == "Editor's Choice Pieces"
    assert pub_updated["homepage_products_subtitle"] == "Hand-stitched luxury apparel and latest runway drops."
    assert pub_updated["faq_section_title"] == "Order Inquiries & Answers"
    assert pub_updated["faq_section_subtitle"] == "Everything you need to know about our craftsmanship and delivery."

    # 4. Audit log records the snapshot
    audit = client.get("/api/v1/admin/settings/audit-logs?limit=5", headers={"Origin": "http://localhost:3000"}).json()
    assert len(audit) > 0
    latest_entry = audit[0]
    assert latest_entry["change_reason"] == "Configure custom storefront section copy"
    assert "homepage_collections_title" in latest_entry["changed_fields"]
    assert "faq_section_title" in latest_entry["changed_fields"]


def test_storefront_reassurance_items_crud_and_audit(client, db):
    """Owner can update storefront reassurance badges, reflected in public store settings and audit logs."""
    owner_name, pwd = _create_owner(db, "owner_reassurance_test")
    csrf = _login_owner(client, owner_name, pwd)

    # 1. Verify defaults on public endpoint
    pub = client.get("/api/v1/store/settings").json()
    assert "reassurance_items" in pub
    assert len(pub["reassurance_items"]) == 3
    assert pub["reassurance_items"][0]["icon"] == "truck"
    assert pub["reassurance_items"][1]["icon"] == "shield-check"
    assert pub["reassurance_items"][2]["icon"] == "message-circle"

    # 2. Update reassurance items via admin settings
    cur = client.get("/api/v1/admin/settings").json()
    v = cur["version"]
    new_items = [
        {
            "id": "delivery",
            "icon": "truck",
            "title": "Express Nationwide Dispatch",
            "description": "Next-day courier dispatch across all major cities in Pakistan.",
        },
        {
            "id": "returns",
            "icon": "refresh-cw",
            "title": "7-Day Seamless Returns",
            "description": "Hassle-free exchanges and returns with original tags attached.",
        },
        {
            "id": "quality",
            "icon": "award",
            "title": "Artisanal Craftsmanship",
            "description": "100% long-staple combed cotton tailored to exact standards.",
        },
    ]

    res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": v,
            "reassurance_items": new_items,
            "change_reason": "Configure custom brand reassurance badges",
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert res.status_code == 200, res.text
    adm = res.json()
    assert len(adm["reassurance_items"]) == 3
    assert adm["reassurance_items"][1]["icon"] == "refresh-cw"
    assert adm["reassurance_items"][1]["title"] == "7-Day Seamless Returns"

    # 3. Public endpoint serves updated reassurance badges
    pub_updated = client.get("/api/v1/store/settings").json()
    assert len(pub_updated["reassurance_items"]) == 3
    assert pub_updated["reassurance_items"][1]["icon"] == "refresh-cw"
    assert pub_updated["reassurance_items"][1]["title"] == "7-Day Seamless Returns"
    assert pub_updated["reassurance_items"][2]["icon"] == "award"

    # 4. Audit log records the reassurance change
    audit = client.get("/api/v1/admin/settings/audit-logs?limit=5", headers={"Origin": "http://localhost:3000"}).json()
    assert len(audit) > 0
    latest_entry = audit[0]
    assert latest_entry["change_reason"] == "Configure custom brand reassurance badges"
    assert "reassurance_items" in latest_entry["changed_fields"]

    # 5. Validation rejection on invalid reassurance item
    cur2 = client.get("/api/v1/admin/settings").json()
    v2 = cur2["version"]
    bad_res = client.put(
        "/api/v1/admin/settings",
        json={
            "expected_version": v2,
            "reassurance_items": [{"id": "bad", "icon": "", "title": ""}],
        },
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf},
    )
    assert bad_res.status_code == 422





