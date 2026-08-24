"""The way back: empty uncleaned packagings returned to the filler.

A drum goes out full and comes back empty and uncleaned, and the return is
almost the outward consignment read backwards — the same drums, the same
substance, the two parties the other way round. Almost, and the differences
are the whole of this module.

**What swaps.** Consignor and consignee, with their addresses and contacts.
The filler receives what they sent.

**What is set.** Every goods line becomes ``empty_uncleaned``, which the
document line already understands: 5.4.1.1.6.1 puts the words after the
description, and 5.4.1.1.1 (f) then composes no total quantity, because these
are residues nobody has weighed. That has been built since v1.90.0.

**What is dropped, and why it must be.** Every quantity the outward
consignment carried. Not because they are stale but because they are *false*
on the way back: an empty drum does not contain 200 litres, and a form that
carries the number over invites somebody to sign for it. This is the half a
one-click return gets wrong when it is written as a copy — copying is the
easy part, and knowing what may not be copied is the work.

**What stays.** The number of packages, because the same drums come back, and
the substance itself, because 5.4.1.1.6.1 describes the residue by the goods
that were in it.

**What this does not decide.** Whether the return is dangerous goods carriage
at all. An empty uncleaned packaging normally is, and stays under ADR — that
is why 1.1.3.6.1 has a rule for counting it — but the reliefs of 4.1.1.11 and
of special provisions can take a particular one out, and neither is a
judgement this transformation can make from what it is handed. It produces
the shipment; the checks then answer it exactly as they answer any other.
"""
from __future__ import annotations

import copy
from typing import Any

#: Consignor and consignee change places. Nothing else about a party does: a
#: contact is a contact and an address is an address, whichever end they sit
#: at.
_SWAPPED_PARTY_FIELDS = ("name", "address", "contact")

#: Every quantity the outward consignment stated. They are dropped rather than
#: kept, because on the way back each of them is a number that is not true.
#: ``quantity_packages`` is deliberately absent: the same drums come back.
QUANTITY_FIELDS = (
    "adr_total_quantity",
    "net_mass_liters_per_package",
    "net_per_inner_packaging",
    "gross_mass_per_package",
    "net_explosive_mass",
    "q_net_quantity",
    "q_max_net_quantity",
)

#: Values that describe this journey rather than the goods, and would be a
#: quiet lie on the next one.
JOURNEY_FIELDS = (
    "shipment_reference",
    "loading_date",
    "requested_departure_date",
    "document_date",
    "declaration_date",
    "vgm_reference",
    "cargo_mass_kg",
    "packaging_mass_kg",
    "pallets_mass_kg",
    "securing_mass_kg",
)


def _swap_parties(values: dict[str, Any]) -> dict[str, Any]:
    out = dict(values)
    for field in _SWAPPED_PARTY_FIELDS:
        consignor, consignee = f"consignor_{field}", f"consignee_{field}"
        out[consignor] = values.get(consignee, "")
        out[consignee] = values.get(consignor, "")
    return out


def return_shipment(
    values: dict[str, Any],
    lines: list[dict[str, Any]] | None,
    dangerous_goods: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """The outward consignment turned round, as data for the wizard.

    Pure: it is handed the shipment and hands one back, storing nothing and
    deciding nothing about the regulation. Every check that runs on the result
    runs on it exactly as it would on a shipment somebody typed.
    """
    turned = _swap_parties(values or {})
    for field in JOURNEY_FIELDS:
        # Emptied rather than deleted, so a field the wizard is showing does
        # not vanish from under the person looking at it.
        if field in turned:
            turned[field] = ""

    # The consignor's declaration belonged to the outward consignment and was
    # signed for those goods. It is not carried over onto a different one.
    turned.pop("consignor_declarations", None)
    turned["signature_image"] = ""

    entries = copy.deepcopy(dangerous_goods or [])
    for entry in entries:
        for product in entry.get("products") or []:
            product["empty_uncleaned"] = True
            for field in QUANTITY_FIELDS:
                if field in product:
                    product[field] = ""

    return {
        "values": turned,
        "lines": copy.deepcopy(lines or []),
        "dangerous_goods": entries,
    }
