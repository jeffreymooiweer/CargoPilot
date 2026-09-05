"""The address book's routes: read, add, change, remove — for everybody.

Mounted with the history (see ``main.py``). Every signed-in user may do all
four: an address book that only an administrator can add to is a book
nobody keeps up to date, and the entries are operational data of the same
kind the equipment library holds, not accounts. What is kept, and that it
is kept, is in ``docs/privacy.md``.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.address import Address
from app.models.user import User

router = APIRouter(prefix="/addresses", tags=["addresses"])

MAX_ENTRIES = 5000


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=2000)
    contact: str = Field(default="", max_length=255)

    @field_validator("name", "address", "contact")
    @classmethod
    def _trimmed(cls, value: str) -> str:
        return (value or "").strip()


class AddressOut(BaseModel):
    id: int
    name: str
    address: str
    contact: str


def _out(entry: Address) -> AddressOut:
    return AddressOut(id=entry.id, name=entry.name, address=entry.address or "",
                      contact=entry.contact or "")


def _entry(address_id: int, db: Session) -> Address:
    entry = db.get(Address, address_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No such address")
    return entry


@router.get("", response_model=list[AddressOut])
def list_addresses(q: str = Query(default="", max_length=120),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Address)
    needle = q.strip()
    if needle:
        like = f"%{needle}%"
        query = query.filter(or_(Address.name.ilike(like), Address.address.ilike(like),
                                 Address.contact.ilike(like)))
    return [_out(e) for e in query.order_by(Address.name).limit(500).all()]


@router.post("", response_model=AddressOut)
def create_address(payload: AddressIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if payload.name == "":
        raise HTTPException(status_code=422, detail="An address needs a name.")
    if db.query(Address).count() >= MAX_ENTRIES:
        raise HTTPException(status_code=409, detail="The address book is full.")
    # The same party saved twice from two shipments is one entry, brought up
    # to date — not a list that grows by one every time somebody presses save.
    existing = db.query(Address).filter(Address.name.ilike(payload.name)).first()
    if existing is not None:
        existing.address = payload.address
        existing.contact = payload.contact
        db.commit()
        db.refresh(existing)
        return _out(existing)
    entry = Address(name=payload.name, address=payload.address, contact=payload.contact,
                    created_by_id=user.id if user.id else None)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _out(entry)


@router.put("/{address_id}", response_model=AddressOut)
def update_address(address_id: int, payload: AddressIn,
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.name == "":
        raise HTTPException(status_code=422, detail="An address needs a name.")
    entry = _entry(address_id, db)
    entry.name, entry.address, entry.contact = payload.name, payload.address, payload.contact
    db.commit()
    db.refresh(entry)
    return _out(entry)


@router.delete("/{address_id}")
def delete_address(address_id: int, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    db.delete(_entry(address_id, db))
    db.commit()
    return {"ok": True}
