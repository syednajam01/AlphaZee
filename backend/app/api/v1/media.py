"""Authenticated uploads/associations and controlled public immutable bytes."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import require_owner_session, OwnerPrincipal
from app.models.media import MediaAsset
from app.schemas.media import ProductMediaCommand, CollectionMediaCommand, PosterCommand, StrictCommand
from app.services import media as service
from app.services import media_storage as storage
from app.services.owner_catalog import CatalogError, product_response, collection_response
from app.api.v1.owner_catalog import persist

router = APIRouter(prefix='/admin/media', tags=['Owner media'], dependencies=[Depends(require_owner_session)])
public_router = APIRouter(tags=['Public catalog media'])
upload_slots = asyncio.Semaphore(4)


class LimitedUploadMiddleware:
    """Bound multipart bytes before parser spooling, including chunked requests."""
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'].rstrip('/') != '/api/v1/admin/media':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        try: length = int(headers.get(b'content-length', b'0'))
        except ValueError: length = storage.BODY_LIMIT + 1
        if length < 0 or length > storage.BODY_LIMIT:
            return await JSONResponse({'detail': {'code': 'media_too_large', 'message': 'Upload request exceeds 101 MiB'}}, status_code=413)(scope, receive, send)
        size = 0
        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get('body', b''))
            if size > storage.BODY_LIMIT: raise MultiPartException('media_body_limit')
            return message
        await self.app(scope, bounded_receive, send)


@router.post('', status_code=201)
async def upload(request: Request, principal: OwnerPrincipal = Depends(require_owner_session), db: Session = Depends(get_db)):
    async with upload_slots:
        try:
            async with request.form(max_files=1, max_fields=0) as form:
                file = form.get('file')
                if len(form) != 1 or not isinstance(file, UploadFile):
                    raise HTTPException(422, 'Choose exactly one file using the file form field')
                return await run_in_threadpool(service.ingest, db, file, principal)
        except CatalogError as error:
            raise HTTPException(error.status, error.detail) from None
        except StarletteHTTPException as error:
            if error.detail == 'media_body_limit': raise HTTPException(413, 'Upload exceeds 101 MiB') from None
            raise


@router.get('')
def library(db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    statement = select(MediaAsset).where(MediaAsset.state == 'ready')
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.scalars(statement.order_by(MediaAsset.created_at.desc(), MediaAsset.id).offset((page-1)*page_size).limit(page_size))
    return {'assets': [service.owner_asset(a, db) for a in rows], 'total': total, 'page': page, 'page_size': page_size}


@router.post('/products/{product_id}')
def product_media(product_id: str, payload: ProductMediaCommand, db: Session = Depends(get_db)):
    return persist(db, lambda: service.replace_product_media(db, product_id, payload), product_response)


@router.post('/collections/{collection_id}')
def collection_media(collection_id: str, payload: CollectionMediaCommand, db: Session = Depends(get_db)):
    return persist(db, lambda: service.set_collection_media(db, collection_id, payload), collection_response)


@router.post('/{asset_id}/poster')
def poster(asset_id: str, payload: PosterCommand, db: Session = Depends(get_db)):
    return persist(db, lambda: service.set_poster(db, asset_id, payload), service.owner_asset)


@router.post('/{asset_id}/delete')
def remove(asset_id: str, payload: StrictCommand, db: Session = Depends(get_db)):
    return persist(db, lambda: service.delete_asset(db, asset_id, payload), lambda result: result)


@router.get('/{asset_id}')
def detail(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(MediaAsset, asset_id)
    if asset is None or asset.state != 'ready': raise HTTPException(404, 'Media not found')
    return service.owner_asset(asset, db)


@public_router.api_route('/media/{asset_id}/content', methods=['GET', 'HEAD'])
def content(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(MediaAsset, asset_id)
    if asset is None or asset.state != 'ready': raise HTTPException(404, 'Media not found')
    try: path = storage.object_path(asset.storage_key)
    except CatalogError: raise HTTPException(404, 'Media not found') from None
    if not path.is_file(): raise HTTPException(404, 'Media file not found')
    return FileResponse(path, media_type=asset.content_type, headers={
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'public, max-age=31536000, immutable',
        'Content-Disposition': 'inline', 'ETag': '"' + asset.checksum + '"',
    })
