"""The unit catalogue, and converting a single line.

The interface needs to know two things only the backend has: which units exist,
and which of them are the obvious ones for a given commodity. Both live here,
so the list is maintained in one place and the frontend does not overwrite it
with another.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User
from app.services import units as unit_service

router = APIRouter(prefix="/units", tags=["units"])


class UnitOut(BaseModel):
    code: str
    symbol: str
    dimension: str


class FormOut(BaseModel):
    code: str
    # Which part of a cubic metre is material. Visible so a user can see why
    # "loose bulk" comes out lighter than "stacked".
    fill_factor: float


class UnitCatalogue(BaseModel):
    units: list[UnitOut]
    forms: list[FormOut]
    # Per category the forms that apply, the default first. Empty means the
    # form does not come into play: for gravel and grain the stored figure is
    # already a bulk density, and a second factor would count the air twice.
    forms_by_category: dict[str, list[str]]
    # Per category the units that are the obvious ones, the default first. A
    # suggestion: the full list stays selectable, because a database of 400
    # commodities in 16 categories always has exceptions, and getting stuck on
    # an exception is worse than an unusual unit.
    suggested_by_category: dict[str, list[str]]
    default_suggested: list[str]
    density_basis_by_category: dict[str, str]


@router.get("", response_model=UnitCatalogue)
def unit_catalogue(user: User = Depends(get_current_user)) -> UnitCatalogue:
    return UnitCatalogue(
        units=[
            UnitOut(code=unit.code, symbol=unit.symbol, dimension=unit.dimension.value)
            for unit in unit_service.UNITS.values()
        ],
        forms=[
            FormOut(code=form.value, fill_factor=unit_service.FILL_FACTOR[form])
            for form in unit_service.CargoForm
        ],
        forms_by_category={
            category: [form.value for form in unit_service.available_forms(category)]
            for category in unit_service.BASIS_BY_CATEGORY
        },
        suggested_by_category={
            category: list(codes)
            for category, codes in unit_service.SUGGESTED_BY_CATEGORY.items()
        },
        default_suggested=list(unit_service.DEFAULT_SUGGESTED),
        density_basis_by_category={
            category: basis.value
            for category, basis in unit_service.BASIS_BY_CATEGORY.items()
        },
    )


class ConvertRequest(BaseModel):
    quantity: float | None = None
    unit: str | None = None
    density_kg_m3: float | None = None
    category: str | None = None
    mass_per_item_kg: float | None = None
    volume_per_item_m3: float | None = None
    canonical_name: str | None = None
    form: str | None = None


class ConvertResponse(BaseModel):
    mass_kg: float | None
    volume_m3: float | None
    density_basis: str
    # What was actually computed with, and in which form.
    density_used_kg_m3: float | None
    fill_factor: float
    form: str | None
    # Filled when one of the two could not be determined. Not an error but an
    # outcome: 40 pallets without a weight per pallet weigh an unknown number of
    # kilos, and turning that into a 0 produces a total that is neither correct
    # nor conspicuous.
    missing: str | None


@router.post("/convert", response_model=ConvertResponse)
def convert(payload: ConvertRequest, user: User = Depends(get_current_user)) -> ConvertResponse:
    result = unit_service.convert(
        payload.quantity,
        payload.unit,
        payload.density_kg_m3,
        payload.category,
        payload.mass_per_item_kg,
        payload.volume_per_item_m3,
        payload.canonical_name,
        payload.form,
    )
    return ConvertResponse(
        mass_kg=round(result.mass_kg, 3) if result.mass_kg is not None else None,
        volume_m3=round(result.volume_m3, 6) if result.volume_m3 is not None else None,
        density_basis=result.basis.value,
        density_used_kg_m3=(
            round(result.density_used_kg_m3, 2) if result.density_used_kg_m3 else None
        ),
        fill_factor=result.fill_factor,
        form=result.form,
        missing=result.missing,
    )
