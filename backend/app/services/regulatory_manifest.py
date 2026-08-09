"""Which edition of which regulations sits in this installation.

CargoPilot computes with five rule sets, each with its own revision rhythm: ADR
every two years, the IMDG Code every two years with a transitional year, the
IATA DGR *every* year. Until now that provenance was spread over the seeds, the
compliance configuration and the documentation, and there was no way to see from
the outside what a running installation actually uses.

That is not merely bookkeeping. The IATA DGR 67th edition applies up to and
including 31 December 2026; on 1 January 2027 this app computes with an expired
edition and there is nothing that says so. The manifest therefore carries a
validity period per rule set, and `expired_rule_sets()` turns that into a
statement.

The checksum is there for the opposite case: a seed that changed quietly. Two
installations reporting the same manifest id compute with the same data.
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

# Per rule set: what applies, where it comes from and which files carry it.
# Only what can be substantiated against a source — where something has not been
# kept up, it says so, because "unknown" is a more usable answer than an edition
# number nobody has checked.
RULE_SETS: list[dict[str, Any]] = [
    {
        "key": "adr",
        "profiles": ["ADR", "RID", "ADN"],
        "name": "ADR — vervoer over de weg",
        "edition": "2025",
        "source": "UNECE ADR 2025, Tabel A via rkstgr/adr-substances",
        "source_url": "https://unece.org/transport/dangerous-goods/adr-2025-files",
        "valid_from": "2025-01-01",
        # ADR is revised every two years; ADR 2027 replaces this edition, with a
        # transitional period to 30 June of that year.
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
        "profiles": ["IMDG"],
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
        "profiles": ["IMDG"],
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
        "profiles": ["IMDG"],
        "name": "EmS Guide — noodprocedures aan boord",
        "edition": "MSC.1/Circ.1588/Rev.3",
        "source": "IMO MSC.1/Circ.1588/Rev.3, EmS Guide — index per UN-nummer",
        "valid_from": "2022-05-01",
        # A circular has no end date; it applies until a Rev.4 appears.
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
        "profiles": ["IATA"],
        "name": "IATA DGR — luchtvracht",
        "edition": "67e editie (2026)",
        "source": "IATA Dangerous Goods Regulations, 67e editie",
        "valid_from": "2026-01-01",
        # The DGR is replaced annually; edition 68 applies from 1-1-2027.
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
        "profiles": ["IMDG"],
        # Expired, and we know it: columns 16a and 16b have come from the 42-24
        # Dangerous Goods List since v1.23.0. What the cards still supply —
        # marine pollutant and bulk — did not change with the edition. Warning
        # about this on every check would make the warning itself worthless.
        "superseded_by": "imdg",
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
    """Content hash of a data file.

    The hash is over the content and not over the timestamp: the latter differs
    per build without the data changing, and would make two identical
    installations look different.
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
    """The full manifest, with checksums and validity."""
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

    # One id over all data files together: two installations reporting the same
    # id compute with the same data.
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


def stale_rule_sets(profiles: list[str] | None = None,
                    today: date | None = None) -> list[dict[str, Any]]:
    """Rule sets that have expired without anything taking their place.

    This is not the same as `expired_rule_sets()`. The 41-22 UN cards have
    expired *and* been deliberately replaced: columns 16a and 16b come from the
    42-24 list and what the cards still supply did not change with the edition.
    Warning about that on every check would make the warning itself worthless —
    whoever dismisses a message every time will dismiss the one that matters too.

    What remains is the case this is meant for: an edition that has run out and
    that nobody has done anything about. Today that yields nothing; on 1 January
    2027 it yields the IATA DGR.
    """
    today = today or date.today()
    wanted = {str(p).strip().upper() for p in (profiles or [])}
    out = []
    for entry in RULE_SETS:
        if rule_set_status(entry, today) != "expired" or entry.get("superseded_by"):
            continue
        covered = {p.upper() for p in entry.get("profiles", [])}
        if wanted and not (covered & wanted):
            continue
        out.append({
            "key": entry["key"],
            "name": entry["name"],
            "edition": entry["edition"],
            "expired_on": entry["valid_until"],
            "profiles": entry.get("profiles", []),
        })
    return out


def expired_rule_sets(today: date | None = None) -> list[str]:
    """The rule sets that are no longer valid on this date.

    With this the app can say that it is computing with an expired edition,
    instead of quietly going on doing so.
    """
    today = today or date.today()
    return [r["key"] for r in RULE_SETS if rule_set_status(r, today) == "expired"]


@lru_cache
def _cached_summary() -> dict[str, str]:
    return {r["key"]: r["edition"] for r in RULE_SETS}


def summary(today: date | None = None) -> dict[str, Any]:
    """Compact form, small enough to hang off /api/health."""
    manifest = build_manifest(today)
    return {
        "manifest_id": manifest["manifest_id"],
        "editions": _cached_summary(),
        "expired": expired_rule_sets(today),
    }
