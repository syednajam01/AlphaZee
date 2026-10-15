from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class StrictCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=1)


class MediaLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    role: Literal['primary', 'gallery', 'hero_image', 'hero_video', 'hero_poster'] = 'gallery'
    variant_id: int | None = Field(default=None, strict=True, ge=1)
    display_order: int = Field(default=0, strict=True, ge=0, le=10000)
    alt_text: str = Field(default='', max_length=1000)


class ProductMediaCommand(StrictCommand):
    items: list[MediaLink] = Field(max_length=100)


class CollectionMediaCommand(StrictCommand):
    asset_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class PosterCommand(StrictCommand):
    poster_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
