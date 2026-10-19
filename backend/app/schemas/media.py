from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class StrictCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=1)


class MediaLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    role: Literal['primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster', 'hover_image'] = 'gallery'
    variant_id: int | None = Field(default=None, strict=True, ge=1)
    display_order: int = Field(default=0, strict=True, ge=0, le=10000)
    alt_text: str = Field(default='', max_length=1000)


class ProductMediaCommand(StrictCommand):
    items: list[MediaLink] = Field(max_length=500)


class CollectionMediaCommand(StrictCommand):
    asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class PosterCommand(StrictCommand):
    poster_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class AttachMediaCommand(StrictCommand):
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    role: Literal['primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster', 'hover_image'] = 'gallery'
    variant_id: int | None = Field(default=None, strict=True, ge=1)
    display_order: int | None = Field(default=None, strict=True, ge=0)
    alt_text: str = Field(default='', max_length=1000)


class DetachMediaCommand(StrictCommand):
    link_id: int | None = Field(default=None, strict=True, ge=1)
    asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    role: str | None = None


class ReorderMediaCommand(StrictCommand):
    link_ids: list[int] = Field(min_length=1)


class SetRolesCommand(StrictCommand):
    primary_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    hover_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class HeroSlideCreateCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str | None = Field(default=None, max_length=200)
    benefit: str | None = Field(default=None, max_length=2000)
    video_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    poster_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    image_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    display_order: int = Field(default=0, ge=0)
    is_enabled: bool = True
    target_product_id: str | None = None
    target_collection_id: str | None = None


class HeroSlideUpdateCommand(StrictCommand):
    title: str | None = Field(default=None, max_length=200)
    benefit: str | None = Field(default=None, max_length=2000)
    video_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    poster_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    image_asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    display_order: int | None = Field(default=None, ge=0)
    is_enabled: bool | None = None
    target_product_id: str | None = None
    target_collection_id: str | None = None


class HeroSlideReorderCommand(StrictCommand):
    slide_ids: list[str] = Field(min_length=1)
