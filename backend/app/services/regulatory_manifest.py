"""Welke editie van welke regelgeving er in deze installatie zit.

CargoPilot rekent met vijf regelsets die elk hun eigen ritme van herzien
hebben: ADR om de twee jaar, de IMDG-code om de twee jaar met een
overgangsjaar, de IATA DGR élk jaar. Tot nu toe stond die herkomst verspreid
over de seeds, de compliance-configuratie en de documentatie, en was er van
buitenaf niet te zien wat een draaiende installatie werkelijk gebruikt.

Dat is niet alleen boekhouding. De IATA DGR 67e editie geldt tot en met
31 december 2026; op 1 januari 2027 rekent deze app met een verlopen editie
en is er niets dat dat zegt. Het manifest draagt daarom per regelset een
geldigheidsperiode, en `expired_rule_sets()` maakt er een uitspraak van.

De controlesom is er voor het omgekeerde geval: een seed die stilletjes is
veranderd. Twee installaties die hetzelfde manifest-id melden, rekenen met
dezelfde gegevens.
"""
from __future__ import annotations

import hashlib
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.version import get_version

SEED = Path(__file__).resolve().parents[2] / "seed" / "dg"
CONFIG = Path(__file__).resolve().parents[1] / "config"

# Per regelset: wat er geldt, waar het vandaan komt en welke bestanden het
# dragen. Alleen wat aan een bron te staven is — waar iets niet is bijgehouden
# staat dat er als zodanig, want "onbekend" is een bruikbaarder antwoord dan
# een editienummer dat niemand heeft nagekeken.
RULE_SETS: list[dict[str, Any]] = [
    {
        "key": "adr",
        "name": "ADR — vervoer over de weg",
        "edition": "2025",
        "source": "UNECE ADR 2025, Tabel A via rkstgr/adr-substances",
        "source_url": "https://unece.org/transport/dangerous-goods/adr-2025-files",
        "valid_from": "2025-01-01",
        # ADR wordt om de twee jaar herzien; ADR 2027 vervangt deze editie, met
        # een overgangstermijn tot 30 juni van dat jaar.
        "valid_until": "2027-06-30",
        "errata": [],
        "covers": [
            "classificatie per UN-nummer (klasse, verpakkingsgroep, etiketten, LQ/EQ)",
            "1.1.3.6 puntentelling",
            "7.5.2 samenlading en 7.5.4/CV28",
        ],
        "files": ["un_numbers.json", "packagings.json"],
    },
    {
        "key": "imdg",
        "name": "IMDG-code — vervoer over zee",
        "edition": "Amendment 42-24 (2024 Edition)",
        "source": "IMO-resolutie MSC.556(108), aangenomen 23 mei 2024",
        "source_url": "https://www.cepa.be/wp-content/uploads/IMDG_Code-amdt_42_24.pdf",
        "valid_from": "2026-01-01",
        # 44-26 volgt de gebruikelijke tweejaarlijkse cyclus.
        "valid_until": "2028-12-31",
        "errata": [],
        "covers": [
            "Dangerous Goods List (hoofdstuk 3.2), inclusief kolom 16a en 16b",
            "stuwage-, behandelings- en scheidingscodes (7.1.5, 7.1.6, 7.2.8)",
            "de verschillenlaag 42-24 over de UN-kaarten van 41-22",
        ],
        "files": ["imdg_dgl.json", "imdg_codes.json", "imdg_42_24.json"],
    },
    {
        "key": "imdg_class_tables",
        "name": "IMDG-code — scheidingstabellen hoofdstuk 7.2 en 3.1.4.4",
        "edition": "Amendment 40-20, geverifieerd ongewijzigd in 42-24",
        "source": (
            "IMDG-code hoofdstuk 7.2 en 3.1.4.4. De secties 7.2.4, 7.2.6.3, "
            "7.2.7.1.4 en 3.1.4.4 zijn tegen 42-24 nagelopen en ongewijzigd; "
            "de enige wijziging in 7.2 is een herformulering van 7.2.6.1."
        ),
        "valid_from": "2026-01-01",
        "valid_until": "2028-12-31",
        "errata": [],
        "covers": [
            "7.2.4 klassescheidingstabel",
            "7.2.6.3 vrijstellingstabellen",
            "7.2.7.1.4 compatibiliteitsmatrix klasse 1",
            "3.1.4.4 scheidingsgroepen",
        ],
        "files": ["segregation_groups.json"],
    },
    {
        "key": "ems",
        "name": "EmS Guide — noodprocedures aan boord",
        "edition": "MSC.1/Circ.1588/Rev.3",
        "source": "IMO MSC.1/Circ.1588/Rev.3, EmS Guide — index per UN-nummer",
        "valid_from": "2022-05-01",
        # Een circulaire heeft geen einddatum; zij geldt tot een Rev.4 verschijnt.
        "valid_until": None,
        "errata": [
            "De UN-nummers die 42-24 toevoegt staan nog niet in deze index; "
            "hun schema's komen uit imdg_42_24.json."
        ],
        "covers": ["brand- en lekkageschema's per UN-nummer"],
        "files": ["ems.json"],
    },
    {
        "key": "iata",
        "name": "IATA DGR — luchtvracht",
        "edition": "67e editie (2026)",
        "source": "IATA Dangerous Goods Regulations, 67e editie",
        "valid_from": "2026-01-01",
        # De DGR wordt jaarlijks vervangen; editie 68 geldt vanaf 1-1-2027.
        "valid_until": "2026-12-31",
        "errata": [
            "Addenda en operator/state variations worden niet bijgehouden; "
            "raadpleeg die apart.",
        ],
        "covers": [
            "9.3.2 Table 9.3.A segregatie",
            "5.0.2.11 Q-waarde voor 'all packed in one'",
            "lithium- en natrium-ionbatterijen (Guidance 2026)",
        ],
        "files": [],
    },
    {
        "key": "imdg_un_cards",
        "name": "IMDG UN-kaarten — aanvullende stofgegevens",
        "edition": "41-22 (2023)",
        "source": "Cantell IMDG UN cards, 2023 edition",
        "valid_from": "2024-01-01",
        "valid_until": "2025-12-31",
        "errata": [
            "Achterhaald voor kolom 16a en 16b: die komen sinds v1.23.0 uit de "
            "Dangerous Goods List van 42-24.",
            "De klasse is onbruikbaar voor UN 2984-2992, 3548 en 3550: daar "
            "staan volgnummers in plaats van klassen.",
        ],
        "covers": ["marine pollutant (kolom 4)", "bulkvervoer"],
        "files": ["card_data.json"],
    },
]


def _checksum(path: Path) -> dict[str, Any] | None:
    """Inhoudshash van een gegevensbestand.

    De hash gaat over de inhoud en niet over de tijdstempel: die laatste
    verschilt per build zonder dat de gegevens veranderen, en zou twee gelijke
    installaties verschillend laten lijken.
    """
    try:
        data = path.read_bytes()
    except OSError:  # pragma: no cover - bestand ontbreekt
        return None
    return {
        "file": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _parse(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def rule_set_status(rule_set: dict[str, Any], today: date) -> str:
    """"current", "not_yet_in_force" of "expired"."""
    starts = _parse(rule_set.get("valid_from"))
    ends = _parse(rule_set.get("valid_until"))
    if starts and today < starts:
        return "not_yet_in_force"
    if ends and today > ends:
        return "expired"
    return "current"


def build_manifest(today: date | None = None) -> dict[str, Any]:
    """Het volledige manifest, met controlesommen en geldigheid."""
    today = today or date.today()
    rule_sets = []
    digest = hashlib.sha256()

    for entry in RULE_SETS:
        datasets = [c for name in entry["files"] if (c := _checksum(SEED / name))]
        for dataset in datasets:
            digest.update(dataset["sha256"].encode())
        rule_sets.append({
            **{k: v for k, v in entry.items() if k != "files"},
            "status": rule_set_status(entry, today),
            "datasets": datasets,
        })

    # Eén id over alle gegevensbestanden samen: twee installaties die hetzelfde
    # id melden, rekenen met dezelfde gegevens.
    return {
        "manifest_version": 1,
        "application_version": get_version(),
        "generated_for": today.isoformat(),
        "manifest_id": digest.hexdigest()[:16],
        "rule_sets": rule_sets,
        "disclaimer": (
            "Feitencompilatie als invulhulp. De gepubliceerde uitgave van ADR, "
            "RID, ADN, de IMDG-code en de IATA DGR blijft leidend; zie DISCLAIMER.md."
        ),
    }


def expired_rule_sets(today: date | None = None) -> list[str]:
    """De regelsets die niet meer geldig zijn op deze datum.

    Hiermee kan de app zeggen dat zij met een verlopen editie rekent, in
    plaats van dat stil te blijven doen.
    """
    today = today or date.today()
    return [r["key"] for r in RULE_SETS if rule_set_status(r, today) == "expired"]


@lru_cache
def _cached_summary() -> dict[str, str]:
    return {r["key"]: r["edition"] for r in RULE_SETS}


def summary(today: date | None = None) -> dict[str, Any]:
    """Compacte vorm, klein genoeg om aan /api/health te hangen."""
    manifest = build_manifest(today)
    return {
        "manifest_id": manifest["manifest_id"],
        "editions": _cached_summary(),
        "expired": expired_rule_sets(today),
    }
