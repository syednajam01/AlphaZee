import pytest
from app.models.media import MediaAsset, HeroSlide, ProductMedia
from app.models.catalog import Product, Collection
from app.schemas.media import (
    HeroSlideCreateCommand, HeroSlideUpdateCommand,
    SetRolesCommand, MediaFramingCommand, CollectionMediaCommand
)
from app.services import media as media_service
from app.services import owner_catalog as catalog_service
from app.api.v1.catalog import list_hero_slides, list_collections, _build_product_summary


def create_dummy_image(db, name="test.jpg", focal_x=50, focal_y=50, zoom_scale=1.0):
    import uuid
    from app.models.suppliers import UserAccount
    owner = db.query(UserAccount).first()
    if not owner:
        owner = UserAccount(auth_subject="test_owner", display_name="Test Owner")
        db.add(owner)
        db.flush()
    key = uuid.uuid4().hex + ".jpg"
    from app.services import media_storage
    file = media_storage.object_path(key)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb')

    asset = MediaAsset(
        id=uuid.uuid4().hex,
        storage_key=key,
        original_name=name,
        kind="image",
        content_type="image/jpeg",
        byte_size=1024,
        checksum="dummy" * 8,
        width=1200,
        height=800,
        state="ready",
        focal_x=focal_x,
        focal_y=focal_y,
        zoom_scale=zoom_scale,
        creator_id=owner.id,
    )
    db.add(asset)
    db.flush()
    return asset


def test_hero_slide_framing_lifecycle(db_session):
    img = create_dummy_image(db_session, "banner.jpg", focal_x=45, focal_y=35, zoom_scale=1.1)
    
    # 1. Create HeroSlide with explicit framing
    cmd = HeroSlideCreateCommand(
        title="Framed Banner",
        image_asset_id=img.id,
        focal_x=42,
        focal_y=28,
        zoom_scale=1.15,
        is_enabled=True,
    )
    slide = media_service.create_hero_slide(db_session, cmd)
    assert slide.focal_x == 42
    assert slide.focal_y == 28
    assert slide.zoom_scale == 1.15

    # 2. Update HeroSlide framing
    upd_cmd = HeroSlideUpdateCommand(
        expected_version=slide.edit_version,
        focal_x=55,
        focal_y=20,
        zoom_scale=1.25,
    )
    updated = media_service.update_hero_slide(db_session, slide.id, upd_cmd)
    assert updated.focal_x == 55
    assert updated.focal_y == 20
    assert updated.zoom_scale == 1.25

    # 3. Check public API representation
    public_slides = list_hero_slides(db_session)
    matching = [s for s in public_slides if s.id == slide.id]
    assert len(matching) == 1
    assert matching[0].focal_x == 55
    assert matching[0].focal_y == 20
    assert matching[0].zoom_scale == 1.25


def test_product_card_roles_framing(db_session):
    front_img = create_dummy_image(db_session, "front.jpg", focal_x=50, focal_y=30)
    hover_img = create_dummy_image(db_session, "hover.jpg", focal_x=50, focal_y=40)

    # Create dummy product
    col = Collection(id="col-framing-test", name="Framing Col", slug="framing-col")
    db_session.add(col)
    prod = Product(
        id="prod-framing-test",
        title="Framed Trenchcoat",
        slug="framed-trenchcoat",
        collection_id=col.id,
        status="draft",
        is_active=True,
        is_hero=False,
    )
    db_session.add(prod)
    db_session.flush()

    # Set roles with custom framing
    roles_cmd = SetRolesCommand(
        expected_version=prod.edit_version,
        primary_asset_id=front_img.id,
        primary_focal_x=48,
        primary_focal_y=22,
        primary_zoom_scale=1.1,
        hover_asset_id=hover_img.id,
        hover_focal_x=52,
        hover_focal_y=25,
        hover_zoom_scale=1.05,
    )
    res = media_service.set_product_roles(db_session, prod.id, roles_cmd)
    
    # Check media links
    primary_link = next(l for l in prod.media_links if l.role == 'primary')
    hover_link = next(l for l in prod.media_links if l.role == 'hover_image')
    assert primary_link.focal_x == 48
    assert primary_link.focal_y == 22
    assert primary_link.zoom_scale == 1.1
    assert hover_link.focal_x == 52
    assert hover_link.focal_y == 25
    assert hover_link.zoom_scale == 1.05

    # Check product summary serialization for storefront
    summary = _build_product_summary(prod)
    assert summary.focal_x == 48
    assert summary.focal_y == 22
    assert summary.zoom_scale == 1.1
    assert summary.hover_focal_x == 52
    assert summary.hover_focal_y == 25
    assert summary.hover_zoom_scale == 1.05


def test_collection_framing_lifecycle(db_session):
    img = create_dummy_image(db_session, "col.jpg", focal_x=50, focal_y=50)
    col = Collection(
        id="col-frame-check",
        name="Check Col",
        slug="check-col",
        focal_x=50,
        focal_y=50,
        zoom_scale=1.0,
    )
    db_session.add(col)
    db_session.flush()

    # Assign media with framing
    cmd = CollectionMediaCommand(
        expected_version=col.edit_version,
        asset_id=img.id,
        focal_x=40,
        focal_y=30,
        zoom_scale=1.2,
    )
    media_service.set_collection_media(db_session, col.id, cmd)
    assert col.focal_x == 40
    assert col.focal_y == 30
    assert col.zoom_scale == 1.2


def test_media_asset_default_framing(db_session):
    img = create_dummy_image(db_session, "asset.jpg", focal_x=50, focal_y=50, zoom_scale=1.0)
    cmd = MediaFramingCommand(
        expected_version=img.edit_version,
        focal_x=60,
        focal_y=35,
        zoom_scale=1.3,
    )
    updated = media_service.update_media_framing(db_session, img.id, cmd)
    assert updated.focal_x == 60
    assert updated.focal_y == 35
    assert updated.zoom_scale == 1.3
    
    # Public representation contains updated focal coordinates
    pub = media_service.public_asset(updated)
    assert pub['focal_x'] == 60
    assert pub['focal_y'] == 35
    assert pub['zoom_scale'] == 1.3

