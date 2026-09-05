"""The articles library's routes.

Mounted only beside the history, like the address book: master data the
office reuses belongs to an installation that keeps things. Everybody signed
in may read and change it — the list is maintained by whoever ships, not by
an administrator — and a spreadsheet goes in and out in the same columns.
"""
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.messages import error as api_error
from app.models.article import Article
from app.models.user import User
from app.services import articles
from app.services.spreadsheet_io import (
    MAX_IMPORT_CELL_CHARS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_ROWS,
    ImportLimitError,
    build_xlsx,
    build_xlsx_template,
    read_limited_upload,
    read_tabular_file,
)

router = APIRouter(prefix="/articles", tags=["articles"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ArticleIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=255)
    un_number: str = Field(default="", max_length=16)
    proper_shipping_name: str = Field(default="", max_length=255)
    technical_name: str = Field(default="", max_length=255)
    hazard_class: str = Field(default="", max_length=16, alias="class")
    packing_group: str = Field(default="", max_length=8)
    type_of_package: str = Field(default="", max_length=64)
    net_per_package: str = Field(default="", max_length=64)
    notes: str = Field(default="", max_length=4000)
    active: bool = True

    model_config = {"populate_by_name": True}


def _article(article_id: int, db: Session) -> Article:
    found = db.get(Article, article_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No such article")
    return found


@router.get("")
def list_articles(q: str = Query(default="", max_length=120),
                  active_only: bool = False,
                  user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return [articles.to_dict(a) for a in articles.search(db, q, active_only=active_only)]


@router.post("")
def save_article(payload: ArticleIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)) -> dict[str, Any]:
    """Keep an article; a code that exists is brought up to date."""
    try:
        article, _created = articles.upsert(db, user, payload.model_dump(by_alias=False))
    except articles.ArticleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return articles.to_dict(article)


@router.put("/{article_id}")
def update_article(article_id: int, payload: ArticleIn,
                   user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict[str, Any]:
    existing = _article(article_id, db)
    try:
        article, _created = articles.upsert(db, user, payload.model_dump(by_alias=False), existing=existing)
    except articles.ArticleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return articles.to_dict(article)


@router.delete("/{article_id}")
def delete_article(article_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict[str, bool]:
    articles.remove(db, _article(article_id, db))
    return {"ok": True}


@router.get("/import-template")
def download_template(user: User = Depends(get_current_user)):
    content = build_xlsx_template(articles.ARTICLE_HEADERS, articles.ARTICLE_EXAMPLE, sheet_name="Articles")
    return Response(content=content, media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="articles_import_template.xlsx"'})


@router.get("/export")
def export_library(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The library in the import's own columns, so what comes out goes back in."""
    content = build_xlsx(articles.ARTICLE_HEADERS, articles.articles_to_rows(articles.search(db, limit=articles.MAX_ARTICLES)),
                         sheet_name="Articles")
    return Response(content=content, media_type=XLSX,
                    headers={"Content-Disposition": 'attachment; filename="articles_export.xlsx"'})


@router.post("/import")
async def import_file(file: UploadFile = File(...), user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict[str, Any]:
    if not file.filename:
        raise api_error(400, "import.filename_missing")
    try:
        content = await read_limited_upload(file)
    except ImportLimitError as exc:
        raise api_error(413, exc.code, **exc.params) from exc
    if not content:
        raise api_error(400, "import.empty_file")
    try:
        rows = read_tabular_file(content, file.filename, max_rows=MAX_IMPORT_ROWS,
                                 max_columns=MAX_IMPORT_COLUMNS, max_cell_chars=MAX_IMPORT_CELL_CHARS)
    except ImportLimitError as exc:
        raise api_error(422, exc.code, **exc.params) from exc
    result = articles.import_rows(db, user, rows)
    if result.created == 0 and result.updated == 0 and not result.errors:
        raise api_error(400, "import.no_usable_lines")
    return {"created": result.created, "updated": result.updated, "skipped": result.skipped,
            "errors": result.errors}
