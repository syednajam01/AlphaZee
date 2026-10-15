import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import require_owner_session
from app.queries.catalog_stock import hold_details, variant_stock

router = APIRouter(prefix='/admin', tags=['Owner stock'], dependencies=[Depends(require_owner_session)])


@router.get('/catalog/variants/{variant_id}/stock')
def stock(variant_id: int, db: Session = Depends(get_db)):
    result = variant_stock(db, variant_id)
    if result is None: raise HTTPException(404, 'Variant not found')
    return result


@router.get('/inventory/{supplier_variant_id}/holds')
def holds(supplier_variant_id: uuid.UUID, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    result = hold_details(db, supplier_variant_id, page, page_size)
    if result is None: raise HTTPException(404, 'Supplier variant not found')
    return result
