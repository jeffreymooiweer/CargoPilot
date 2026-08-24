"""Chapter 5.2: what goes on the package itself.

Chapter 5.3 — what goes on the *outside of the vehicle, wagon, vessel or
container* — has been derived per mode since v1.53.0, and printed as a sheet
since the placarding sheet existed. Chapter 5.2 is the other half and had
nothing: the application knew which labels a substance carries, because column
(5) of Table A is read for eight other purposes, but nobody ever asked it what
the person packing the drum has to stick on it.

This module answers that, per goods line and per regime, out of the values read
from the official editions into ``seed/dg/package_marking.json``. It draws
nothing; it decides. The sheet that prints the result is a separate file, for
the same reason the placarding sheet is separate from ``check_adr_placarding``.

Three things it deliberately does not do.

**It does not guess the package.** The character height of the UN number under
5.2.1.1 steps down at 30 litres and again at 5 litres, and the orientation
arrows of 5.2.1.10 turn on whether the packaging is a combination packaging
with liquid inners, a single packaging with vents, a cryogenic receptacle or
machinery under special provision 301. The application knows none of that: it
has the quantity carried, not the shape of the box it travels in. So the marks
that depend on it are reported as **not assessed**, with the provision's own
cases named, rather than answered from an assumption. The one exception is the
UN number itself, which is offered at the full 12 mm — larger than required is
never a breach, and it is the only tier that is right whatever the package is.

**It does not treat the sea as the land renumbered.** The IMDG Code requires
the proper shipping name on every package where ADR asks for it only on Class 1
and Class 7; it calls the environmentally hazardous substance mark the marine
pollutant mark and puts it at 5.2.1.6 rather than 5.2.1.8; and it takes the
primary label from column 3 of the Dangerous Goods List and each subsidiary
from column 4, where Table A has one column for both. Each regime is therefore
built from its own provisions, and a sea consignment never inherits a road
answer.

**It reads column 6, and applies only what column 6 decides.** IMDG 5.2.2.1.2
lets a special provision add a subsidiary label where column 4 shows none and
remove one where it does, and 5.2.2.1.2.1 can drop the labelling altogether for a
substance of a low degree of danger. All 262 numbers the column cites were found
in chapter 3.3 and the forty-two that mention a label, a mark or an exemption
were judged one by one. Most of them condition rather than decide — on a
competent authority's permission, on how much phlegmatizer a mixture holds, on
which packing instruction was used — and those are named against the entry that
cites them instead of being applied. One decides: special provision **384** says
the label is model No. 9A and that only the placard on the unit is model No. 9,
which is where the battery label now comes from.

The marine pollutant mark shows how far that restraint goes and where it stops.
IMDG 2.10.2.7 relieves the mark at 5 l or 5 kg per inner or single packaging —
the same figures the land regulations use — but only for substances that *also*
fall in a hazard class from 1 to 9 other than 7, and expressly **not** for
UN 3077 and UN 3082. Those two are the generic environmentally hazardous
entries, which is to say exactly the ones a reader would expect the relief to
cover, so for them the answer is certain: the mark applies whatever the packing
holds. For everything else the threshold turns on the quantity per inner
packaging, which is a property of the packing rather than of the goods, so it is
named and not applied. Erring towards a mark the packer removes is the safe
direction; erring towards a missing one is not.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.languages import normalise
from app.services.dg import dangerous_goods_list, database

_SEED = Path(__file__).resolve().parents[3] / "seed" / "dg" / "package_marking.json"

#: The land regimes share chapter 5.2 word for word — RID 5.2.2.2.1.1 and ADN
#: 5.2.2.2.1.1 were quoted beside the ADR in one run and are identical down to
#: the figure and the colour rule for the inner line. They are listed
#: separately anyway, so that a future edition that diverges has a place to say
#: so rather than being silently folded into the road answer.
LAND_PROFILES = ("ADR", "RID", "ADN")

#: The UN numbers that carry the battery mark, from ADR 5.2.1.9.2. The mark is
#: required for cells and batteries "prepared in accordance with special
#: provision 188 or 400", and the provision then names the six numbers. Both
#: tests are applied: the number has to be one of these *and* the entry has to
#: carry 188 or 400 in column (6), because an entry that is not prepared under
#: those provisions is not marked under this one.
BATTERY_UN_NUMBERS = {"3090", "3480", "3551", "3091", "3481", "3552"}
BATTERY_PROVISIONS = {"188", "400"}

#: The two entries IMDG 2.10.2.7 refuses its own relief to. Its threshold — the
#: same 5 l and 5 kg the land regulations use — reaches only substances that
#: also fall in a hazard class from 1 to 9 other than 7, and it says in as many
#: words that it does not apply to these two. They are the generic
#: environmentally hazardous entries, which is to say exactly the ones a reader
#: would expect it to cover, so the answer states it rather than leaving it to
#: be inferred.
ALWAYS_MARKED_POLLUTANTS = {"3077", "3082"}


@lru_cache
def rules() -> dict[str, Any]:
    return json.loads(_SEED.read_text(encoding="utf-8"))


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().upper() in {"P", "Y", "YES", "JA", "TRUE", "1"}


def _adr_special_provisions(un: str) -> set[str]:
    """Column (6) of ADR Table A — the land's own.

    Named for the book it comes from, because there is a second column 6 in
    this module and the two are different sets of numbers. Reading one to
    answer the other's question is a mistake that leaves no trace: the numbers
    look plausible either way. It happened once here, between writing
    ``_apply_column_6`` and testing it.
    """
    rows = database.get_un_entries(un)
    raw = str((rows[0] if rows else {}).get("special_provisions") or "")
    return {token for token in re.split(r"[,;\s]+", raw) if token}


def _label_models(product: dict[str, Any]) -> list[dict[str, str]]:
    """The label models of the land regimes: column (5) of Table A.

    Column (5) already lists the primary and the subsidiary labels together and
    in that order, which is why 5.2.2.1.1 can point at one column. The model
    letter is kept here, unlike in ``_label_numbers`` where 8.1.5.1 wants the
    bare number: a package of lithium batteries carries model 9A, and 9A is a
    different piece of artwork from 9.
    """
    raw = str(product.get("labels") or "").strip()
    models: list[dict[str, str]] = []
    seen: set[str] = set()
    for token in re.split(r"[,;+/\s]+", raw):
        model = token.strip().upper()
        if not model or model in seen:
            continue
        if not re.match(r"^\d(?:\.\d)?[A-Z]?$", model):
            continue
        seen.add(model)
        models.append({
            # The first model that survives the filter is the primary one, not
            # the first *token*: a column (5) value that starts with a space
            # splits to an empty leading element, and counting tokens would
            # then label the primary hazard as a subsidiary one.
            "model": model,
            "role": "primary" if not models else "subsidiary",
            "source": "Table A, column (5)",
        })
    return models


def _imdg_label_models(product: dict[str, Any]) -> list[dict[str, str]]:
    """The sea regime's labels: column 3 for the primary, column 4 for the rest.

    IMDG 5.2.2.1.2 splits what Table A keeps in one column, and the split is not
    cosmetic: column 3 is the *class*, so the primary label follows the class
    and not a label column that may carry a model letter. Column 4 then lists
    every subsidiary hazard, and 5.2.2.1.1 says the "EXPLOSIVE" subsidiary label
    is model No. 1.

    The columns are read from the Dangerous Goods List and not from the product
    as the wizard filled it in, because the wizard's class comes from Table A
    and the two books do not always say the same thing. UN 0004 is "1" in Table
    A and "1.1D" in the List; a sea label built from the product would have
    printed the class where the Code asks for the division and the compatibility
    group. Where the List has no row — an entry the land regimes carry and the
    sea one does not — the product's own class is used and the row is marked as
    coming from Table A, so the reader can see which book answered.
    """
    models: list[dict[str, str]] = []
    seen: set[str] = set()

    un = str(product.get("un_number") or "").strip()
    row = dangerous_goods_list.entry_for(
        un, str(product.get("packing_group") or "")) if un else {}

    primary = str(row.get("class") or "").strip().upper()
    origin = "Dangerous Goods List, column 3"
    if not primary:
        primary = str(product.get("class") or "").strip().upper()
        origin = "Table A, column (3) — no Dangerous Goods List row for this entry"
    if primary:
        seen.add(primary)
        models.append({
            "model": primary,
            "role": "primary",
            "source": origin,
        })

    # Class 9 needs one more step. Column 3 gives the class, not the label
    # model, so it says plain "9" for the lithium and sodium battery entries and
    # cannot choose between models 9 and 9A. Three provisions settle it: 5.2.2.2.1.3
    # gives 9A a layout of its own, special provision 188 names it beside the
    # lithium battery mark, and 5.3.1.1.2 forbids 9A *for placarding purposes* —
    # a prohibition that only means something if 9A is a package label. Table A
    # column (5) already names 9A per entry for the same substances, so where it
    # does, the package takes 9A and the unit keeps 9.
    if primary == "9":
        land = str(product.get("labels") or "").upper()
        if "9A" in re.split(r"[,;+/\s]+", land):
            models[0]["model"] = "9A"
            models[0]["source"] = (
                "Dangerous Goods List, column 3 (class 9), refined to model 9A "
                "by Table A column (5); 5.3.1.1.2 keeps 9A off the unit")
            seen.add("9A")

    subsidiary = str(row.get("subsidiary_hazards") or "").strip()
    if not subsidiary or subsidiary in {"-", "–"}:
        subsidiary = str(product.get("subsidiary_risks") or "").strip()
    for token in re.split(r"[,;+/\s]+", subsidiary):
        model = token.strip().upper()
        if not model or model in seen or not re.match(r"^\d(?:\.\d)?$", model):
            continue
        seen.add(model)
        models.append({
            "model": model,
            "role": "subsidiary",
            "source": "Dangerous Goods List, column 4",
        })
    return models


def _imdg_special_provisions(un: str, packing_group: str) -> list[str]:
    """Column 6 of the Dangerous Goods List — the sea's own, not Table A's.

    Both books have a column of special provisions and both number them, and
    the numbers are not the same set: the Code carries a 900 series the ADR has
    no counterpart for, and where a number exists in both it need not say the
    same thing. Reading Table A here to answer a sea question would be the exact
    mistake this module was built to avoid, and it would be invisible — the
    numbers would look plausible either way.
    """
    row = dangerous_goods_list.entry_for(un, packing_group) if un else {}
    return dangerous_goods_list.special_provisions(row) if row else []


def _apply_column_6(un: str, packing_group: str,
                    labels: list[dict[str, str]]) -> tuple[list[dict[str, str]],
                                                           list[dict[str, Any]]]:
    """What column 6 does to this entry's labels, and what it might do.

    IMDG 5.2.2.1.2 gives a special provision the power to add a subsidiary
    label where column 4 shows none and to take one away where it does, and
    5.2.2.1.2.1 lets one drop the labelling altogether. Until now the answer
    said only that the column had not been read. It has been read: all 262
    numbers it cites were found in chapter 3.3 and the forty-two that mention a
    label, a mark or an exemption were judged one by one.

    Judging them does not make them all applicable. Most turn on something no
    consignment record holds — whether the competent authority of the country of
    origin dispensed with a label, how much phlegmatizer the mixture contains,
    whether the article is water-activated, which packing instruction was used.
    Those are **named**, against the entry that cites them, with what they would
    do and what it depends on. A packer who can see the drum can finish the
    sentence; the application cannot, and saying so beats guessing either way.

    One is applied, because it decides rather than conditions: **384** says in
    as many words that the label is model No. 9A and that only the placard on
    the cargo transport unit is model No. 9. That is the provision v1.161.1 had
    to reach by inference from three others, and it is now read from the column
    that assigns it, per substance.
    """
    rules_for = rules().get("column_6", {}).get("effects", {})
    cited = [number for number in _imdg_special_provisions(un, packing_group)
             if number in rules_for]
    if not cited:
        return labels, []

    found: list[dict[str, Any]] = []
    for number in sorted(cited, key=int):
        effect = dict(rules_for[number])
        effect["provision"] = number
        effect["source"] = "Dangerous Goods List, column 6"
        found.append(effect)
        # Applied, not merely named: the model this provision fixes replaces the
        # one the class column implies. Everything else in the block is
        # conditional on the packing, and a conditional applied blindly is a
        # wrong label rather than a missing one.
        if effect.get("effect") == "model" and effect.get("certain"):
            model = (effect.get("models") or [None])[0]
            if model and labels:
                labels = [dict(entry) for entry in labels]
                labels[0]["model"] = model
                labels[0]["source"] = (
                    f"Dangerous Goods List, column 6, special provision {number}")
    return labels, found


def _un_mark(un: str) -> dict[str, Any]:
    """The UN number mark, offered at the tier that is always enough.

    5.2.1.1 gives three heights, and which one applies depends on the capacity
    of the package — 12 mm normally, 6 mm at 30 litres or 30 kilograms and for
    cylinders of 60 litres water capacity, "an appropriate size" at 5 litres or
    5 kilograms. The application does not know the package, so it offers the
    12 mm the provision asks for by default. Printing a mark larger than the
    minimum is not a breach of a minimum; printing one smaller than it is.
    """
    return {
        "kind": "un_number",
        "text": f"UN {un}",
        "provision": "5.2.1.1",
        "height_mm": 12,
        "height_note": "smaller_packages_may_use_6mm",
        "certain": True,
    }


def _marks_for_land(product: dict[str, Any], un: str) -> tuple[list[dict[str, Any]], list[str]]:
    marks: list[dict[str, Any]] = [_un_mark(un)]
    open_points: list[str] = []
    data = rules()

    label_numbers = {
        model["model"][0] for model in _label_models(product) if model["model"]
    }
    is_class1 = str(product.get("class") or "").strip().startswith("1")
    is_class7 = "7" in label_numbers or str(product.get("class") or "").strip().startswith("7")

    # 5.2.1.5 — Class 1 carries the proper shipping name on the package too,
    # in French, German or English at the least. 5.2.1.7.2 asks the same of
    # radioactive material. No other class does, which is exactly where the
    # sea regime parts company.
    name = str(product.get("proper_shipping_name") or "").strip()
    if is_class1 or is_class7:
        marks.append({
            "kind": "proper_shipping_name",
            "text": name,
            "provision": "5.2.1.5" if is_class1 else "5.2.1.7.2",
            "certain": bool(name),
            "language_rule": is_class1,
        })

    if _truthy(product.get("salvage_packaging")):
        marks.append({
            "kind": "salvage",
            "text": "SALVAGE",
            "provision": "5.2.1.3",
            "height_mm": 12,
            "certain": True,
        })

    # 5.2.1.8 — and its own exemption, which is the reason this cannot be
    # decided from the substance alone: the mark falls away at 5 litres or
    # 5 kilograms *per inner or single packaging*, which is a property of the
    # packing and not of the goods.
    if _truthy(product.get("environmentally_hazardous")):
        mark = dict(data["marks"]["environmentally_hazardous"]["size"])
        marks.append({
            "kind": "environmentally_hazardous",
            "provision": "5.2.1.8",
            "size": mark,
            "certain": False,
            "exempt_unless": "inner_or_single_packaging_over_5l_or_5kg",
        })
        open_points.append("environmentally_hazardous_threshold")

    if un in BATTERY_UN_NUMBERS and (_adr_special_provisions(un) & BATTERY_PROVISIONS):
        marks.append({
            "kind": "battery",
            "text": f"UN {un}",
            "provision": "5.2.1.9",
            "size": {"min_width_mm": 100, "min_height_mm": 100},
            "reduction": {"floor_width_mm": 100, "floor_height_mm": 70},
            "certain": True,
        })

    lq = _limited_quantities_mark(product)
    if lq is not None:
        marks.append(lq)

    return marks, open_points


def _limited_quantities_mark(product: dict[str, Any]) -> dict[str, Any] | None:
    """The diamond of 3.4.7, when the line actually travels under chapter 3.4.

    Whether it does is not decided here. ``check_lq_eq`` already tests the line
    against column 7a and the 30 kg limit of 3.4.2, and a second reading of the
    same question is how two answers begin to disagree — which for this mark
    would mean a package that carries it on one screen and not on the other.
    So the same function answers both, and this one only asks.
    """
    from app.services.dg.compliance import _assess_lq, _parse_measures

    raw = str(product.get("limited_quantity") or "").strip()
    if not raw:
        return None
    if product.get("transport_forbidden"):
        return None

    inner = _parse_measures(product.get("net_per_inner_packaging"))
    gross = _parse_measures(product.get("gross_mass_per_package"))
    gross_kg = gross[0][0] / 1000.0 if gross and gross[0][1] == "mass" else None
    verdict = _assess_lq(raw, inner, gross_kg, "en")
    if verdict.get("status") != "within_limits":
        return None

    mark = rules()["marks"]["limited_quantities"]
    return {
        "kind": "limited_quantities",
        "provision": mark["provision"],
        "size": dict(mark["size"]),
        "reduction": dict(mark["reduction"]),
        "certain": True,
        # 3.4.8 is offered, never required: the Code says a package packed to
        # the ICAO instructions "may bear" the Y. Air is locked here besides.
        "air_variant": {
            "provision": mark["air_variant"]["provision"],
            "symbol": mark["air_variant"]["symbol"],
            "optional": True,
        },
    }


def _marks_for_sea(product: dict[str, Any], un: str) -> tuple[list[dict[str, Any]], list[str]]:
    marks: list[dict[str, Any]] = [_un_mark(un)]
    open_points: list[str] = []

    # IMDG 5.2.1.1 — the difference that reaches every package: the proper
    # shipping name is marked on all of them, not only on Class 1 and Class 7.
    name = str(product.get("proper_shipping_name") or "").strip()
    marks.append({
        "kind": "proper_shipping_name",
        "text": name,
        "provision": "5.2.1.1",
        "certain": bool(name),
        "language_rule": False,
    })

    hazard = str(product.get("class") or "").strip().upper()
    if hazard.startswith("1.4") and hazard.endswith("S"):
        marks.append({
            "kind": "division_and_compatibility_group",
            "text": "1.4S",
            "provision": "5.2.1.1",
            "certain": True,
            "unless": "label_1_4s_displayed",
        })

    if _truthy(product.get("salvage_packaging")):
        marks.append({
            "kind": "salvage",
            "text": "SALVAGE",
            "provision": "5.2.1.3",
            "height_mm": 12,
            "certain": True,
        })

    # IMDG 5.2.1.6 — the marine pollutant mark, and 2.10.2.7's exemption from
    # it. The threshold is the same 5 l and 5 kg the land regulations use, but
    # it is fenced twice: it reaches only substances that *also* fall in a
    # hazard class from 1 to 9 other than 7, and it is expressly withheld from
    # UN 3077 and UN 3082 — the two generic environmentally hazardous entries,
    # which are exactly the ones a reader would expect it to cover. Those two
    # therefore always carry the mark, and for them the answer is certain
    # rather than conditional.
    if _truthy(product.get("marine_pollutant")) or _truthy(product.get("environmentally_hazardous")):
        never_exempt = un in ALWAYS_MARKED_POLLUTANTS
        mark: dict[str, Any] = {
            "kind": "marine_pollutant",
            "provision": "5.2.1.6",
            "size": {"min_width_mm": 100, "min_height_mm": 100, "min_line_mm": 2},
            "certain": never_exempt,
        }
        if never_exempt:
            mark["no_exemption"] = "2.10.2.7 withholds its relief from UN 3077 and UN 3082"
        else:
            # The exemption turns on the quantity per inner or single packaging,
            # which is a property of the packing rather than of the goods, so it
            # is named and not applied — the same restraint the land answer uses
            # for 5.2.1.8.
            mark["exempt_unless"] = "inner_or_single_packaging_over_5l_or_5kg"
            mark["exemption_provision"] = "2.10.2.7"
            open_points.append("marine_pollutant_threshold")
        marks.append(mark)

    # The limited quantities mark is deliberately absent here. The land answer
    # carries it from ADR 3.4.7, and the Code has a chapter 3.4 of its own with
    # its own numbering — which is exactly the shape of mistake this module has
    # already made once, in column 6, where the sea was answered out of the
    # land's book because the numbers looked plausible either way. The Code's
    # chapter has not been read, so nothing is claimed from it.
    if str(product.get("limited_quantity") or "").strip():
        open_points.append("imdg_chapter_3_4_not_read")

    return marks, open_points


def _product_key(entry: dict[str, Any], index: int, un: str) -> str:
    line = str(entry.get("line_id") or entry.get("vehicle") or "").strip()
    label = f"UN {un}" if un else f"#{index + 1}"
    return f"{line} · {label}" if line else label


def check_package_marking(
    entries: list[dict[str, Any]],
    profiles: list[str] | None = None,
    language: str = "nl",
) -> dict[str, Any]:
    """What each package in the consignment carries, per regime.

    Returns one block per regime asked for, because the regimes genuinely
    differ, and a shared list of what could not be settled. A caller that finds
    ``status`` set to ``not_checked`` has asked about a consignment with no
    dangerous goods in it, which is not a gap but an answer.
    """
    lang = normalise(language)
    wanted = {str(profile).strip().upper() for profile in (profiles or [])}
    data = rules()

    regimes: list[dict[str, Any]] = []
    not_assessed: set[str] = set()
    open_points: set[str] = set()
    seen_any = False

    for profile in (*LAND_PROFILES, "IMDG"):
        if profile not in wanted:
            continue
        items: list[dict[str, Any]] = []
        for entry in entries:
            for index, product in enumerate(entry.get("products") or []):
                un = str(product.get("un_number") or "").strip()
                if not un or product.get("transport_forbidden"):
                    continue
                seen_any = True
                provisions: list[dict[str, Any]] = []
                if profile == "IMDG":
                    marks, opened = _marks_for_sea(product, un)
                    labels = _imdg_label_models(product)
                    labels, provisions = _apply_column_6(
                        un, str(product.get("packing_group") or ""), labels)
                else:
                    marks, opened = _marks_for_land(product, un)
                    labels = _label_models(product)
                open_points.update(opened)
                items.append({
                    "product": _product_key(entry, index, un),
                    "un_number": un,
                    "labels": labels,
                    "marks": marks,
                    "column_6": provisions,
                })
        if not items:
            continue
        # The two marks that depend on the shape of the packaging rather than
        # on the goods. Named per regime because their provision numbers differ
        # between land and sea, and a reader checking the answer against the
        # book needs the number that is actually in their book.
        not_assessed.add("orientation_arrows")
        regimes.append({
            "profile": profile,
            "source": data["source"]["imdg" if profile == "IMDG" else profile.lower()],
            "label_shape": data["labels"]["shape"],
            "items": items,
        })

    if not seen_any or not regimes:
        return {"status": "not_checked", "regimes": [], "not_assessed": [], "open": []}

    return {
        "status": "ok",
        "regimes": regimes,
        "not_assessed": sorted(not_assessed),
        "open": sorted(open_points),
        "durability": {
            "land": "withstand open weather exposure without a substantial reduction in effectiveness (5.2.1.2)",
            "sea": "still identifiable after at least three months' immersion in the sea (IMDG 5.2.1.2)",
        },
        "language": lang,
    }
