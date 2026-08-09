"""Which language the proper shipping name belongs in on the document.

The ADR table in `seed/dg/un_numbers.json` carries two official names per UN
number: `name_en` and `name_de`. Until now the app always took the English one,
even for a German user with a German waybill — while the official German name
was sitting right next to it.

Putting that right is not simply "translate along with the screen", because the
regulations say something different about it per mode:

* **ADR 5.4.1.4.1** (road), and along the same lines RID and ADN: the transport
  document is drawn up in an official language of the forwarding country, and if
  that is not German, English or French, additionally in one of those three. A
  German name on a CMR or CIM is therefore exactly what a German consignor
  needs.
* **IMDG 5.4.1.4.1** (sea) requires English, French or Spanish — not German.
* **IATA DGR 8.1.2.1** (air) requires English.

"SALZSÄURE" on a Shipper's Declaration is therefore not a translation choice but
a refused consignment. Hence: German only when no sea or air profile is in play.

For a multimodal consignment English satisfies all three regimes and German only
one, so the name in the field is then English — including on the CMR, where
German would have been allowed. That is deliberate. A consignment with a road
and a sea leg then carries the same goods description on every piece of paper,
and that is exactly what a forwarder and customs want to see match; two
languages for the same substance on two documents of the same consignment is a
question you do not want to be asked.

What remains is the case you cannot rule out: first drawing up a German road
document, then adding a sea leg. The name is already in the field by then and is
not derived again. That is what :func:`resolve_for_profile` is for, which
resolves the name per document at the moment it goes on paper.
"""

from __future__ import annotations

from typing import Any

from app.core.languages import normalise

#: Profiles for which the name has to stay English.
ENGLISH_ONLY_PROFILES = {"IMDG", "IATA_DGR"}


def requires_english_name(profiles: list[str] | set[str] | None) -> bool:
    """Does one of the chosen profiles force an English name?"""
    chosen = {str(profile).strip().upper() for profile in (profiles or [])}
    return bool(chosen & ENGLISH_ONLY_PROFILES)


def proper_shipping_name(
    entry: dict[str, Any],
    language: str = "nl",
    profiles: list[str] | set[str] | None = None,
) -> str:
    """The proper shipping name from an ADR entry, in capitals.

    German when the user reads German and no chosen profile forces English;
    otherwise English. There is no Dutch column in the ADR table, so Dutch gets
    — as before — the English name.
    """
    if normalise(language) == "de" and not requires_english_name(profiles):
        german = str(entry.get("name_de") or "").strip()
        if german:
            return german.upper()
    return str(entry.get("name_en") or entry.get("name_de") or "").strip().upper()


def is_german_name(entry: dict[str, Any], name: Any) -> bool:
    """Does this text carry the German name of this entry?

    Used by the export check: whoever first draws up a road document in German
    and then adds a sea leg keeps the German name already filled in — and it may
    not stand there.
    """
    german = str(entry.get("name_de") or "").strip()
    english = str(entry.get("name_en") or "").strip()
    given = str(name or "").strip()
    if not german or not given:
        return False
    if german.casefold() == english.casefold():
        # Some entries read the same in both languages; then there is nothing to
        # report.
        return False
    return given.casefold() == german.casefold()


def resolve_for_profile(product: dict[str, Any], profile: str) -> tuple[str, str]:
    """The shipping name belonging on *this* document, and the name replaced.

    The language of the name belongs to the document, not to the consignment.
    One consignment produces a CMR with "BENZIN ODER OTTOKRAFTSTOFF" and an IMO
    DGF with "GASOLINE", from the same data. So there is no point in refusing
    the export and making the user retype the English: CargoPilot knows what has
    to be there and puts it there itself.

    Only what CargoPilot derived itself is adjusted. If there is wording of the
    user's own — a technical name with an n.o.s. entry, an addition by the
    consignor — it stays; we cannot assess that and certainly must not overwrite
    it silently.

    Returns ``(name_for_this_document, replaced_name)``. When nothing was
    adjusted, the second field is empty.
    """
    current = str(product.get("proper_shipping_name") or "").strip()
    if not current or not requires_english_name([profile]):
        return current, ""

    # Enclosed import: database reads naming, so the other way round only here.
    from app.services.dg.database import get_un_entries

    for entry in get_un_entries(str(product.get("un_number") or "")):
        if is_german_name(entry, current):
            english = proper_shipping_name(entry, "en")
            if english:
                return english, current
        break
    return current, ""
