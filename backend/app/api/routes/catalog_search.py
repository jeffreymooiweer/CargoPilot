from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.catalog_search import search_catalog

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/search")
def catalog_search(
    q: str = Query("", min_length=0, max_length=200),
    limit: int = Query(25, ge=1, le=50),
    # De suggestie die de gebruiker aanklikt wordt de omschrijving op zijn
    # document; die hoort in de taal te staan waarin hij werkt.
    language: str = Query("nl", max_length=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"results": search_catalog(db, q, limit=limit, language=language)}
