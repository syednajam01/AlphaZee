"""Managed public catalog assets; payment evidence never enters these tables."""
from datetime import datetime, timezone
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.catalog import Product, Collection


class MediaAsset(Base):
    __tablename__ = 'media_assets'
    __table_args__ = (
        CheckConstraint("kind IN ('image', 'video')", name='ck_media_kind'),
        CheckConstraint("state IN ('ready', 'deleted')", name='ck_media_state'),
        CheckConstraint('byte_size > 0 AND width > 0 AND height > 0', name='ck_media_dimensions'),
        CheckConstraint('duration_ms IS NULL OR duration_ms BETWEEN 1 AND 120000', name='ck_media_duration'),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(50), unique=True)
    original_name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))
    content_type: Mapped[str] = mapped_column(String(30))
    byte_size: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(10), default='ready')
    edit_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'))
    poster_id: Mapped[str | None] = mapped_column(ForeignKey('media_assets.id', ondelete='RESTRICT'))
    poster: Mapped['MediaAsset | None'] = relationship(remote_side='MediaAsset.id')
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('user_accounts.id', ondelete='RESTRICT'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ProductMedia(Base):
    __tablename__ = 'product_media'
    __table_args__ = (
        CheckConstraint("role IN ('primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster', 'hover_image')", name='ck_product_media_role'),
        CheckConstraint("variant_id IS NULL OR role = 'gallery'", name='ck_product_media_variant_role'),
        CheckConstraint('display_order >= 0', name='ck_product_media_order'),
        Index('uq_product_media_link', 'product_id', 'asset_id', 'role', 'variant_id', unique=True, postgresql_nulls_not_distinct=True),
        Index('uq_product_media_single_role', 'product_id', 'role', unique=True, postgresql_where=text("role != 'gallery'")),
        Index('ix_product_media_asset', 'asset_id'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('products.id', ondelete='RESTRICT'))
    asset_id: Mapped[str] = mapped_column(ForeignKey('media_assets.id', ondelete='RESTRICT'))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey('variants.id', ondelete='RESTRICT'))
    role: Mapped[str] = mapped_column(String(20))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    alt_text: Mapped[str] = mapped_column(Text, default='')
    asset: Mapped[MediaAsset] = relationship()
    product: Mapped['Product'] = relationship(back_populates='media_links')


class HeroSlide(Base):
    __tablename__ = 'hero_slides'
    __table_args__ = (
        CheckConstraint('display_order >= 0', name='ck_hero_slide_order'),
        CheckConstraint('video_asset_id IS NOT NULL OR image_asset_id IS NOT NULL OR poster_asset_id IS NOT NULL', name='ck_hero_slide_media'),
        Index('ix_hero_slides_order', 'display_order'),
        Index('ix_hero_slides_enabled', 'is_enabled'),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_asset_id: Mapped[str | None] = mapped_column(ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True)
    poster_asset_id: Mapped[str | None] = mapped_column(ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True)
    image_asset_id: Mapped[str | None] = mapped_column(ForeignKey('media_assets.id', ondelete='RESTRICT'), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default=text('0'))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text('true'))
    target_product_id: Mapped[str | None] = mapped_column(ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    target_collection_id: Mapped[str | None] = mapped_column(ForeignKey('collections.id', ondelete='SET NULL'), nullable=True)
    edit_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now())

    video: Mapped[MediaAsset | None] = relationship(foreign_keys=[video_asset_id])
    poster: Mapped[MediaAsset | None] = relationship(foreign_keys=[poster_asset_id])
    image: Mapped[MediaAsset | None] = relationship(foreign_keys=[image_asset_id])
    product: Mapped['Product | None'] = relationship(foreign_keys=[target_product_id])
    collection: Mapped['Collection | None'] = relationship(foreign_keys=[target_collection_id])

