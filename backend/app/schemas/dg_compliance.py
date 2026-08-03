"""Wat de compliance-endpoint binnen mag krijgen.

De controle stond tot nu toe op `list[dict]`: Pydantic keek er niet naar en de
rekenlaag moest elke waarde zelf defensief omzetten. Dat maakt één soort fout
onzichtbaar en juist die is hier gevaarlijk — een hoeveelheid van -5 L verlaagt
het ADR-puntentotaal en spiegelt een vrijstelling voor die er niet is, en een
profiel dat "IDMG" heet levert stilzwijgend géén zeevaartcontrole op in plaats
van een foutmelding.

Deze modellen zetten die twee dingen vast aan de rand: een onbekend profiel of
een onbruikbare hoeveelheid geeft HTTP 422 vóórdat er gerekend wordt. Wat de
regelgeving zelf betreft blijven de velden bewust ruim — de klasse van een stof
is 1.4S of 4.1 of straks iets wat nu nog niet bestaat, en daar hoort de
regelgevingslaag over te gaan, niet het schema.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegulatoryProfile(str, Enum):
    """De regelgevingsprofielen waarvoor controles bestaan."""

    ADR = "ADR"
    RID = "RID"
    ADN = "ADN"
    IMDG = "IMDG"
    IATA = "IATA"


# ADR 1.1.3.6 kent categorie 0 t/m 4; 0 betekent "geen vrijstelling mogelijk".
TRANSPORT_CATEGORIES = {"0", "1", "2", "3", "4"}
PACKING_GROUPS = {"I", "II", "III"}


class DangerousGoodsProduct(BaseModel):
    """Eén gevaarlijke stof op een positie.

    Alles is optioneel: de wizard stuurt onderweg halve invoer door en de
    controle hoort dan "incomplete" te melden, niet om te vallen. Wat wél wordt
    afgedwongen is dat een ingevulde waarde bruikbaar is.
    """

    model_config = ConfigDict(extra="allow")

    un_number: str | None = None
    proper_shipping_name: str | None = None
    hazard_class: str | None = Field(default=None, alias="class")
    subsidiary_risks: str | None = None
    classification_code: str | None = None
    packing_group: str | None = None
    segregation_group: str | None = None
    transport_category: str | None = None
    cargo_aircraft_only: bool | None = None

    # Hoeveelheden komen als tekst binnen ("5 kg", "12,5 L"); de rekenlaag pelt
    # het getal eruit. Hier wordt alleen geweigerd wat niet door de beugel kan.
    adr_total_quantity: str | float | int | None = None
    q_net_quantity: str | float | int | None = None
    q_max_net_quantity: str | float | int | None = None

    @field_validator("packing_group")
    @classmethod
    def _known_packing_group(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        cleaned = str(value).strip().upper()
        if cleaned not in PACKING_GROUPS:
            raise ValueError(f"onbekende verpakkingsgroep {value!r}; verwacht I, II of III")
        return cleaned

    @field_validator("transport_category")
    @classmethod
    def _known_transport_category(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return value
        cleaned = str(value).strip()
        if cleaned not in TRANSPORT_CATEGORIES:
            raise ValueError(
                f"onbekende vervoerscategorie {value!r}; ADR 1.1.3.6 kent 0 t/m 4"
            )
        return cleaned

    @field_validator("adr_total_quantity", "q_net_quantity", "q_max_net_quantity")
    @classmethod
    def _usable_quantity(cls, value: Any) -> Any:
        """Een ingevulde hoeveelheid moet positief zijn.

        Leeg mag: dan is het veld nog niet ingevuld en meldt de controle dat
        zelf. Nul of negatief mag niet — dat zou het puntentotaal verlagen of
        een Q-component laten verdwijnen zonder dat iemand het merkt.
        """
        if value is None or not str(value).strip():
            return value
        import re

        match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
        if not match:
            raise ValueError(f"hoeveelheid {value!r} bevat geen getal")
        if float(match.group(0).replace(",", ".")) <= 0:
            raise ValueError(f"hoeveelheid {value!r} moet groter dan nul zijn")
        return value


class ShipmentPosition(BaseModel):
    """Een voertuig, container of regel met de stoffen die erop staan."""

    model_config = ConfigDict(extra="allow")

    vehicle: str | None = None
    line_id: str | None = None
    products: list[DangerousGoodsProduct] = Field(default_factory=list)


class ComplianceRequest(BaseModel):
    entries: list[ShipmentPosition] = Field(default_factory=list)
    profiles: list[RegulatoryProfile] = Field(default_factory=list)
    language: str = "nl"

    def as_dicts(self) -> list[dict[str, Any]]:
        """De posities zoals de rekenlaag ze leest.

        `by_alias` houdt "class" op zijn eigen naam — in Python kan dat geen
        veldnaam zijn, maar de hele rekenlaag en de frontend kennen hem zo.
        """
        return [
            entry.model_dump(by_alias=True, exclude_none=True) for entry in self.entries
        ]

    def profile_names(self) -> list[str]:
        return [profile.value for profile in self.profiles]
