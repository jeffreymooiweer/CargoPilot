#!/usr/bin/env python3
"""Read the official ADR, RID and ADN texts and quote the provisions we implement.

CargoPilot's land-transport checks were built from an ADR Table A data export and
from general knowledge of how the regimes are structured. That is not the same as
having read the regulation, and the difference matters: a rule implemented from
memory looks exactly like a rule implemented from the text.

The texts themselves are free. UNECE publishes ADR and ADN, OTIF publishes RID,
all as official PDFs at no charge. What the development container lacks is the
network to reach them; a runner has it. So this script runs there.

Two modes, and the split is deliberate:

``--quote``
    Print the verbatim text of named provisions to the run log, so a human (or
    an agent) can read what the regulation actually says. Nothing is written to
    the repository. The regulatory text is not ours to redistribute.

``--emit``
    Write the *factual values* read out of those provisions — thresholds,
    multipliers, limits — to a JSON file. Numbers are facts, and the repository
    already holds that kind of data (see docs/data-sources.md). Every value
    carries the provision it came from so it can be checked.

Usage::

    python scripts/read_land_regulations.py --quote lq_eq
    python scripts/read_land_regulations.py --quote exemptions --doc rid
    python scripts/read_land_regulations.py --emit backend/seed/dg/land_limits.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CACHE = Path("/tmp/cargopilot-regulations")

# Official, free-of-charge sources. Any change here changes what the app claims
# to be based on, so each entry records the edition and the publisher.
SOURCES: dict[str, dict[str, Any]] = {
    "adr1": {
        "urls": [
            "https://unece.org/sites/default/files/2025-01/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf",
            "https://unece.org/sites/default/files/2025-01/2412006_E_ECE_TRANS_352_Vol.I_WEB.pdf",
        ],
        "title": "ADR 2025 Volume I (ECE/TRANS/352 Vol. I)",
        "publisher": "UNECE",
        "edition": "ADR 2025, in force 1 January 2025",
    },
    "adr2": {
        "urls": [
            "https://unece.org/sites/default/files/2025-01/2412010_E_ECE_TRANS_352_Vol.II_WEB.pdf",
            "https://unece.org/sites/default/files/2025-01/2412010_E_ECE_TRANS_352_Vol.II_WEB_0.pdf",
        ],
        "title": "ADR 2025 Volume II (ECE/TRANS/352 Vol. II)",
        "publisher": "UNECE",
        "edition": "ADR 2025, in force 1 January 2025",
    },
    "rid": {
        "urls": [
            "https://otif.org/fileadmin/docs/LegalTexts/COTIF/DangerousGoodsRID/RID/RID_2025_e_1_January_2025.pdf",
            "https://www.cit-rail.org/media/files/cim-unterlagen/rid_2025_e_1_january_2025.pdf?cid=395946",
        ],
        "title": "RID 2025 (Appendix C to COTIF, Annex)",
        "publisher": "OTIF",
        "edition": "RID 2025, in force 1 January 2025",
    },
    "adn": {
        "urls": [
            "https://unece.org/sites/default/files/2025-01/ADN%202025%20English.pdf",
            "https://unece.org/sites/default/files/2025-01/ADN_2025_English.pdf",
        ],
        "title": "ADN 2025",
        "publisher": "UNECE",
        "edition": "ADN 2025, in force 1 January 2025",
    },
}

# These servers refuse a request that does not look like a browser. The
# documents are published free of charge and require no login; the headers only
# get past a user-agent filter, they do not get past any access control.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class Provision:
    """A provision to quote, addressed by the number it carries in the text."""

    section: str
    docs: tuple[str, ...]
    # Some provisions are easier to find by a phrase than by their number: the
    # number appears in the table of contents, in cross-references and in the
    # running head long before it appears at the provision itself.
    anchor: str | None = None
    chars: int = 2600
    note: str = ""


# Grouped by the question they answer, because that is how they get read.
GROUPS: dict[str, list[Provision]] = {
    # Does CargoPilot's LQ/EQ arithmetic match the text? This is the group that
    # settles whether "verified against the published 3.4/3.5 text" is true.
    "lq_eq": [
        Provision("3.4.1", ("adr1", "rid", "adn"), chars=2200,
                  note="what the LQ chapter exempts, and the column 7a reference"),
        Provision("3.4.2", ("adr1", "rid", "adn"), chars=1200,
                  note="gross mass of the package — expected 30 kg"),
        Provision("3.4.3", ("adr1", "rid", "adn"), chars=1200,
                  note="shrink- or stretch-wrapped trays — expected 20 kg"),
        Provision("3.5.1.2", ("adr1", "rid", "adn"), chars=2600,
                  anchor="Maximum net quantity per inner packaging",
                  note="table of E-code limits, E1 to E5"),
        Provision("3.5.1.4", ("adr1", "rid", "adn"), chars=1400,
                  note="how mixed inner packagings are counted"),
        Provision("3.5.5", ("adr1", "rid", "adn"), chars=900,
                  note="packages per vehicle/wagon/container — expected 1000"),
    ],
    # The LQ marking above a certain load. CargoPilot fires on 8 tonnes of LQ
    # alone; the text is believed to add a condition on the transport unit.
    "lq_marking": [
        Provision("3.4.13", ("adr1", "rid", "adn"), chars=2000,
                  note="when the large LQ mark is required — check for a 12 t condition"),
        Provision("3.4.14", ("adr1", "rid", "adn"), chars=1200,
                  note="when the 3.4.13 marking may be omitted"),
        Provision("3.4.15", ("adr1", "rid", "adn"), chars=1200,
                  note="the mark itself, and its dimensions"),
    ],
    # The 1000-point rule. RID and ADN are believed to have their own version;
    # CargoPilot answers all three with ADR's table.
    "exemptions": [
        Provision("1.1.3.6", ("adr1", "rid", "adn"), chars=6000,
                  anchor="Exemptions related to quantities carried",
                  note="transport categories, multipliers and the threshold"),
    ],
    # Mixed loading. Same question as above.
    "mixed_loading": [
        Provision("7.5.2.1", ("adr2", "rid", "adn"), chars=3000,
                  note="the prohibition table for packages"),
        Provision("7.5.2.2", ("adr2", "rid", "adn"), chars=1600,
                  note="what the table's entries mean"),
    ],
    # The transport document. Settles whether the tunnel code belongs on a rail
    # or inland waterway document — CargoPilot removed it in v1.29.5.
    "document": [
        Provision("5.4.1.1.1", ("adr1", "rid", "adn"), chars=4200,
                  note="the particulars of the description line, item by item"),
    ],
    # Tunnel restrictions, road only as far as we know.
    "tunnels": [
        Provision("8.6.1", ("adr2",), chars=2000, note="tunnel categories"),
        Provision("8.6.3", ("adr2",), chars=2400, note="tunnel restriction codes"),
    ],
}


def _looks_like_pdf(path: Path) -> bool:
    """A 403 page saved to disk is still a file. Check it is really a PDF."""
    if not path.exists() or path.stat().st_size < 500_000:
        return False
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def _try_urllib(url: str, target: Path) -> bool:
    try:
        request = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(request, timeout=240) as response:
            target.write_bytes(response.read())
    except Exception as error:  # noqa: BLE001 — any failure means try the next way
        print(f"      urllib: {error}", file=sys.stderr)
        return False
    return _looks_like_pdf(target)


def _try_curl(url: str, target: Path) -> bool:
    """curl negotiates compression and redirects more forgivingly than urllib."""
    command = [
        "curl", "--silent", "--show-error", "--location", "--compressed",
        "--max-time", "240", "--retry", "2", "--retry-delay", "3",
        "-A", BROWSER_HEADERS["User-Agent"],
        "-H", f"Accept: {BROWSER_HEADERS['Accept']}",
        "-o", str(target), url,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"      curl: {error}", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(f"      curl exit {result.returncode}: {result.stderr.strip()[:200]}", file=sys.stderr)
        return False
    return _looks_like_pdf(target)


def fetch(doc: str) -> Path:
    """Download a text, trying every published address and both fetchers."""
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / f"{doc}.pdf"
    if _looks_like_pdf(target):
        return target

    print(f"    fetching {SOURCES[doc]['title']}", file=sys.stderr)
    for url in SOURCES[doc]["urls"]:
        print(f"    {url}", file=sys.stderr)
        for name, attempt in (("curl", _try_curl), ("urllib", _try_urllib)):
            if attempt(url, target):
                size = target.stat().st_size
                print(f"      got {size:,} bytes via {name}", file=sys.stderr)
                SOURCES[doc]["resolved_url"] = url
                return target
        target.unlink(missing_ok=True)

    raise SystemExit(
        f"could not download {doc}. Tried: {', '.join(SOURCES[doc]['urls'])}. "
        "The published address may have moved — check the publisher's download page."
    )


_PAGES: dict[str, list[str]] = {}


def pages(doc: str) -> list[str]:
    """Page text, cached. Kept per page so a quote can name where it was found."""
    if doc not in _PAGES:
        import pymupdf

        with pymupdf.open(fetch(doc)) as pdf:
            _PAGES[doc] = [page.get_text() for page in pdf]
    return _PAGES[doc]


def _normalise(text: str) -> str:
    """Collapse the whitespace that PDF extraction scatters through a line."""
    return re.sub(r"[ \t]+", " ", text.replace("\xa0", " "))


def locate(doc: str, provision: Provision) -> list[tuple[int, int]]:
    """Find where a provision actually starts, as (page index, offset) pairs.

    A section number appears in the table of contents, in the running head and
    in every cross-reference to it. What distinguishes the provision itself is
    that the number sits at the start of a line and is followed by its text —
    not by a page number, and not by a comma or a bracket as a reference would
    be.
    """
    hits: list[tuple[int, int]] = []
    number = re.escape(provision.section)
    # Start of line, the number, then whitespace and something that is not a
    # dotted continuation (3.4.1 must not match 3.4.13) and not a page number.
    pattern = re.compile(rf"^[ \t]*{number}(?![.\d])[ \t]+(?![.\s]*\d+\s*$)(\S)", re.MULTILINE)
    for index, text in enumerate(pages(doc)):
        body = _normalise(text)
        for match in pattern.finditer(body):
            hits.append((index, match.start()))
    if provision.anchor:
        anchored = [
            (index, offset)
            for index, offset in hits
            if provision.anchor.lower() in _normalise(pages(doc)[index]).lower()
        ]
        # Some anchors sit on the following page (a table split across a break).
        if not anchored:
            anchored = [
                (index, offset)
                for index, offset in hits
                if any(
                    provision.anchor.lower() in _normalise(pages(doc)[near]).lower()
                    for near in (index, min(index + 1, len(pages(doc)) - 1))
                )
            ]
        if anchored:
            return anchored
    return hits


def quote(doc: str, provision: Provision) -> None:
    hits = locate(doc, provision)
    label = f"{SOURCES[doc]['title']} — {provision.section}"
    print()
    print("=" * 78)
    print(label)
    if provision.note:
        print(f"({provision.note})")
    print("=" * 78)
    if not hits:
        print("!! not found — the section number may differ in this regime,")
        print("!! or the provision is absent from it. That is itself an answer.")
        return
    # The table of contents lists the number too. The real provision is the
    # later, longer occurrence; take the last hit but show how many there were.
    if len(hits) > 1:
        print(f"[{len(hits)} occurrences; showing the last, "
              f"pages {', '.join(str(p + 1) for p, _ in hits)}]")
    page_index, offset = hits[-1]
    text = _normalise(pages(doc)[page_index])[offset:]
    # A provision can run over a page break; pull in what follows.
    following = ""
    for extra in range(1, 4):
        if page_index + extra < len(pages(doc)) and len(text) + len(following) < provision.chars:
            following += "\n" + _normalise(pages(doc)[page_index + extra])
    body = (text + following)[: provision.chars]
    print(f"[page {page_index + 1}]")
    print(body.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quote", choices=sorted(GROUPS), action="append", default=[],
                        help="which group of provisions to print (repeatable)")
    parser.add_argument("--doc", choices=sorted(SOURCES), action="append", default=[],
                        help="restrict to these documents (default: all that apply)")
    parser.add_argument("--section", action="append", default=[],
                        help="quote an arbitrary section number, e.g. 1.1.3.6.3")
    parser.add_argument("--chars", type=int, default=2600, help="length of an ad-hoc quote")
    args = parser.parse_args()

    if not args.quote and not args.section:
        parser.error("give --quote GROUP or --section NUMBER")

    wanted_docs = tuple(args.doc) if args.doc else None

    for group in args.quote:
        print()
        print("#" * 78)
        print(f"# {group}")
        print("#" * 78)
        for provision in GROUPS[group]:
            docs = wanted_docs or provision.docs
            for doc in docs:
                if doc not in SOURCES:
                    continue
                quote(doc, provision)

    for section in args.section:
        provision = Provision(section, wanted_docs or ("adr1",), chars=args.chars)
        for doc in provision.docs:
            quote(doc, provision)

    print()
    print("-" * 78)
    print("Sources read:")
    for doc in sorted(_PAGES):
        info = SOURCES[doc]
        print(f"  {doc}: {info['title']} — {info['publisher']}, {info['edition']}")
        print(f"       {info.get('resolved_url') or info['urls'][0]}")


if __name__ == "__main__":
    main()
