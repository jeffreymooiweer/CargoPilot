from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas import CatalogSyncStatus
from app.services.catalog_sync import get_sync_status, sync_catalogs

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/sync-status", response_model=CatalogSyncStatus)
def catalog_sync_status(user: User = Depends(get_current_user)):
    return CatalogSyncStatus(**get_sync_status())


@router.post("/sync", response_model=CatalogSyncStatus)
def catalog_sync_now(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    status = sync_catalogs(db)
    return CatalogSyncStatus(**status)
