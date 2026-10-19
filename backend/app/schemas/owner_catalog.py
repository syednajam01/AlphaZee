"""Owner-only catalog commands; public serializers remain separate."""
from typing import Annotated, Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
import uuid
from app.schemas.media import MediaLink

Minor = Annotated[int, Field(strict=True, ge=0, le=2147483647)]


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')


class VariantEdit(Command):
    id: int | None = Field(default=None, gt=0)
    sku: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=100)
    price_minor: Minor | None = None
    is_active: bool = False
    availability: Literal['available', 'unavailable', 'unknown'] = 'unknown'

    @field_validator('sku', 'size', 'color', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() or None if isinstance(value, str) else value


class ProductFields(Command):
    title: str | None = Field(default=None, max_length=300)
    slug: str | None = Field(default=None, max_length=100)
    collection_id: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=20000)
    short_description: str | None = Field(default=None, max_length=2000)
    material: str | None = Field(default=None, max_length=5000)
    care: str | None = Field(default=None, max_length=5000)
    sizing: str | None = Field(default=None, max_length=5000)
    badge: str | None = Field(default=None, max_length=100)
    is_hero: bool = False
    hero_order: int | None = Field(default=None, ge=0, le=2147483647)
    hero_benefit: str | None = Field(default=None, max_length=2000)
    stock_management_source: Literal['alphazee_managed', 'vendor_managed'] | None = 'alphazee_managed'
    vendor_id: uuid.UUID | None = None
    variants: list[VariantEdit] | None = Field(default=None, max_length=200)

    @field_validator('title', 'collection_id', 'description', 'short_description', 'material', 'care', 'sizing', 'badge', 'hero_benefit', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator('slug')
    @classmethod
    def slug_format(cls, value):
        if value is None or not value.strip():
            return None
        value = value.strip().lower()
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', value):
            raise ValueError('Use lowercase letters/numbers separated by hyphens')
        return value


class ProductCreate(ProductFields):
    pass


class ProductUpdate(ProductFields):
    expected_version: int = Field(gt=0)
    media: list[MediaLink] | None = Field(default=None, max_length=100)


class VersionCommand(Command):
    expected_version: int = Field(gt=0)


class CollectionCreate(Command):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    display_order: int = Field(default=0, ge=0, le=2147483647)
    is_active: bool = True
    image_media_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')

    _slug = field_validator('slug')(ProductFields.slug_format.__func__)

    @field_validator('name')
    @classmethod
    def name_format(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Name is required')
        return value

    @field_validator('slug')
    @classmethod
    def slug_required(cls, value):
        if not value:
            raise ValueError('Slug is required')
        return value


class CollectionUpdate(Command):
    expected_version: int = Field(gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    display_order: int | None = Field(default=None, ge=0, le=2147483647)
    is_active: bool | None = None
    image_media_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')

    @field_validator('name', 'slug', 'display_order', 'is_active')
    @classmethod
    def not_null(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError('This field cannot be cleared')
        return value.strip() if isinstance(value, str) else value

    _slug = field_validator('slug')(ProductFields.slug_format.__func__)


class CollectionPosition(VersionCommand):
    id: str = Field(min_length=1, max_length=100)


class CollectionReorder(Command):
    items: list[CollectionPosition] = Field(min_length=1, max_length=1000)
