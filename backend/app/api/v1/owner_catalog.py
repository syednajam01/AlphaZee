"""Owner-protected catalog API. No stock writes or public authoring endpoints."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.dependencies.auth import require_owner_session
from app.models.catalog import Product, Collection, Variant
from app.schemas.owner_catalog import ProductCreate, ProductUpdate, VersionCommand, CollectionCreate, CollectionUpdate, CollectionReorder
from app.services import owner_catalog as service

router = APIRouter(prefix='/admin', tags=['Owner catalog'], dependencies=[Depends(require_owner_session)])


def persist(db, operation, serializer):
    try:
        obj = operation()
        db.flush()
        response = serializer(obj)
        db.commit()
        return response
    except service.CatalogError as error:
        db.rollback()
        raise HTTPException(error.status, error.detail) from None
    except IntegrityError as error:
        db.rollback()
        name = getattr(getattr(error.orig, 'diag', None), 'constraint_name', '') or ''
        if 'sku' in name: field, code = 'variants.sku', 'duplicate_sku'
        elif 'slug' in name: field, code = 'slug', 'duplicate_slug'
        elif 'size_color' in name: field, code = 'variants', 'duplicate_variant_options'
        else: field, code = 'catalog', 'catalog_constraint'
        status = 409 if code.startswith('duplicate') else 422
        raise HTTPException(status, {'code': code, 'message': 'This value conflicts with a catalog rule.',
            'fields': [{'field': field, 'code': code, 'message': 'Use a unique, valid value.'}]}) from None


@router.get('/products')
def list_products(db: Session = Depends(get_db), search: str = Query(default='', max_length=200),
                  status: Literal['draft', 'published', 'archived'] | None = None,
                  collection_id: str | None = Query(default=None, max_length=100),
                  page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    query = select(Product)
    if search.strip():
        term = search.strip()
        query = query.where(or_(Product.title.icontains(term, autoescape=True), Product.slug.icontains(term, autoescape=True),
                               Product.variants.any(Variant.sku.icontains(term, autoescape=True))))
    if status: query = query.where(Product.status == status)
    if collection_id: query = query.where(Product.collection_id == collection_id)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    products = db.scalars(query.options(selectinload(Product.variants), selectinload(Product.collection), selectinload(Product.media_links))
                         .order_by(Product.created_at.desc(), Product.id).offset((page-1)*page_size).limit(page_size)).all()
    return {'products': [service.product_response(p) for p in products], 'total': total, 'page': page, 'page_size': page_size}


@router.post('/products', status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return persist(db, lambda: service.create_product(db, payload), service.product_response)


@router.get('/products/{product_id}')
def product_detail(product_id: str, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None: raise HTTPException(404, 'Product not found')
    return service.product_response(product)


@router.post('/products/{product_id}')
def update_product(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    return persist(db, lambda: service.edit_product(db, product_id, payload), service.product_response)


@router.post('/products/{product_id}/{action}')
def product_transition(product_id: str, action: Literal['publish', 'unpublish', 'archive', 'restore'],
                       payload: VersionCommand, db: Session = Depends(get_db)):
    return persist(db, lambda: service.transition(db, product_id, payload, action), service.product_response)


@router.get('/collections')
def collections(db: Session = Depends(get_db)):
    rows = db.scalars(select(Collection).order_by(Collection.display_order, Collection.id)).all()
    return {'collections': [service.collection_response(c) for c in rows], 'total': len(rows)}


@router.post('/collections', status_code=201)
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    return persist(db, lambda: service.create_collection(db, payload), service.collection_response)


@router.post('/collections/reorder')
def reorder_collections(payload: CollectionReorder, db: Session = Depends(get_db)):
    return persist(db, lambda: service.reorder_collections(db, payload),
                   lambda rows: {'collections': [service.collection_response(c) for c in sorted(rows, key=lambda c: c.display_order)]})


@router.post('/collections/{collection_id}')
def update_collection(collection_id: str, payload: CollectionUpdate, db: Session = Depends(get_db)):
    return persist(db, lambda: service.edit_collection(db, collection_id, payload), service.collection_response)
