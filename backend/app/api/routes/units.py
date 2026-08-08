"""De eenhedencatalogus, en het omrekenen van één regel.

De interface moet twee dingen weten die alleen de backend heeft: welke eenheden
er bestaan, en welke daarvan bij een bepaald goed voor de hand liggen. Beide
staan hier, zodat de lijst op één plek wordt onderhouden en de frontend hem niet
nog eens overschrijft.
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
    # Welk deel van een kuub materiaal is. Zichtbaar zodat een gebruiker kan
    # zien waarom "los gestort" lichter uitpakt dan "gestapeld".
    fill_factor: float


class UnitCatalogue(BaseModel):
    units: list[UnitOut]
    forms: list[FormOut]
    # Per categorie de vormen die van toepassing zijn, standaard vooraan. Leeg
    # betekent dat de vorm niet speelt: bij grind en graan is het opgeslagen
    # getal al een stortdichtheid en zou een tweede factor de lucht dubbel tellen.
    forms_by_category: dict[str, list[str]]
    # Per categorie de eenheden die voor de hand liggen, standaard vooraan. Een
    # voorstel: de volledige lijst blijft kiesbaar, want een database van 400
    # goederen in 16 categorieen heeft altijd uitzonderingen en vastlopen op een
    # uitzondering is erger dan een ongebruikelijke eenheid.
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
    # Waarmee er daadwerkelijk is gerekend, en in welke vorm.
    density_used_kg_m3: float | None
    fill_factor: float
    form: str | None
    # Gevuld wanneer een van beide niet kon worden bepaald. Geen fout maar een
    # uitkomst: 40 pallets zonder gewicht per pallet wegen een onbekend aantal
    # kilo, en daar een 0 van maken levert een totaal op dat klopt noch opvalt.
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
