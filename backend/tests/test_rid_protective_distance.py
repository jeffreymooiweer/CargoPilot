"""RID 7.5.3: de bepaling waar het ADR niet voor kon invallen.

Voor bijna alles wat het spoor van de weg onderscheidt geldt dat CargoPilot de
ADR-tabel gebruikte en dat er een grondslagmelding onder stond: bruikbaar als
indicatie, toets het aan de tekst. Voor 7.5.3 kon dat niet, en het is de moeite
waard waarom: **het ADR heeft er geen tegenhanger van.** 7.5.3 gaat over hoe een
trein wordt samengesteld, en een vervoerseenheid over de weg rijdt alleen. Het
ADR-hoofdstuk leverde hier dus niet een minder precies antwoord — het leverde er
geen.

De tekst, woordelijk opgehaald uit RID 2025 (Aanhangsel C bij het COTIF, Bijlage),
bladzijde 1103, met `scripts/read_land_regulations.py --doc rid --page 1101-1103`:

    "Every wagon, large container, portable tank or road vehicle containing
     substances or articles of Class 1 and bearing a placard conforming to models
     Nos. 1, 1.5 or 1.6, shall be separated on the same train from wagons, large
     containers, portable tanks, tank-containers, MEGCs or road vehicles bearing a
     placard conforming to models Nos. 2.1, 3, 4.1, 4.2, 4.3, 5.1 or 5.2 [...] by a
     protective distance.
     The requirement for this protective distance is met if the space [...] is:
     (a) at least 18 m, or
     (b) occupied by two 2-axle wagons or a wagon with 4 or more axles."

Twee dingen die de tekst precies zegt en waar je makkelijk overheen leest:

**De aanleiding is het plakkaat, niet de divisie.** Genoemd worden de modellen 1,
1.5 en 1.6. Model 1.4 wordt níét genoemd, en dat is geen omissie — 1.4 heeft zijn
eigen plakkaatmodel. Een wagen met uitsluitend goederen van divisie 1.4 valt dus
buiten deze bepaling.

**De tegenhanger is een korte lijst.** 2.1, 3, 4.1, 4.2, 4.3, 5.1 en 5.2 — de
brandbare en oxiderende kanten. Klasse 8, 6.1 en 9 staan er niet bij, hoe
gevaarlijk ze verder ook zijn.

En wat CargoPilot hier niet kan weten, zegt het: de rest van de trein staat niet
in de applicatie. Een zending met één wagen klasse 1 en verder niets krijgt
daarom geen "niets aan de hand" maar de bepaling zelf, om door te geven aan de
vervoerder.
"""

import pytest

from app.services.dg.compliance import check_compliance, check_rid_protective_distance

BLACK_POWDER = {"un_number": "0027", "class": "1.1D", "classification_code": "1.1D",
                "proper_shipping_name": "BLACK POWDER"}
FIREWORKS_14 = {"un_number": "0336", "class": "1.4G", "classification_code": "1.4G",
                "proper_shipping_name": "FIREWORKS"}
GASOLINE = {"un_number": "1203", "class": "3", "proper_shipping_name": "GASOLINE"}
ACID = {"un_number": "1789", "class": "8", "proper_shipping_name": "HYDROCHLORIC ACID"}
PROPANE = {"un_number": "1978", "class": "2.1", "proper_shipping_name": "PROPANE"}


def wagons(*positions):
    return [{"vehicle": name, "products": list(products)} for name, products in positions]


def findings(entries, language="nl"):
    return check_rid_protective_distance(entries, language)


def test_klasse_1_en_een_brandbare_wagen_vragen_om_de_afstand():
    found = findings(wagons(("Wagen 1", [BLACK_POWDER]), ("Wagen 2", [GASOLINE])))

    assert len(found) == 1
    assert found[0]["rule"] == "RID 7.5.3"
    assert found[0]["products"] == "Wagen 1 ↔ Wagen 2"
    assert "18 m" in found[0]["message"]


def test_de_tegenhangerlijst_is_geen_lijst_van_gevaarlijke_stoffen():
    """Klasse 8 staat niet in 7.5.3, hoe bijtend het ook is.

    Er blijft wel een melding staan, maar dan de algemene: de trein bevat meer
    dan deze zending. Wat er níét mag gebeuren is dat de wagen met zoutzuur als
    tegenhanger wordt aangewezen — dat zou een afstand voorschrijven die de
    tekst niet vraagt.
    """
    found = findings(wagons(("Wagen 1", [BLACK_POWDER]), ("Wagen 2", [ACID])))

    assert len(found) == 1
    assert "Wagen 2" not in found[0]["products"]


def test_divisie_14_zet_de_bepaling_niet_in_werking():
    """Model 1.4 wordt in 7.5.3 niet genoemd; alleen 1, 1.5 en 1.6."""
    assert findings(wagons(("Wagen 1", [FIREWORKS_14]), ("Wagen 2", [GASOLINE]))) == []


@pytest.mark.parametrize("counterpart", [GASOLINE, PROPANE])
def test_elke_genoemde_tegenhanger_telt(counterpart):
    found = findings(wagons(("W1", [BLACK_POWDER]), ("W2", [counterpart])))

    assert found and "↔" in found[0]["products"]


def test_een_zending_zonder_tegenhanger_krijgt_de_bepaling_toch_te_horen():
    """CargoPilot ziet de trein niet, en dat mag er niet uitzien als vrij baan."""
    found = findings(wagons(("Wagen 1", [BLACK_POWDER])))

    assert len(found) == 1
    assert found[0]["products"] == "Wagen 1"
    assert "vervoerder" in found[0]["message"]


def test_zonder_klasse_1_gebeurt_er_niets():
    assert findings(wagons(("W1", [GASOLINE]), ("W2", [PROPANE]))) == []


def test_binnen_een_wagen_gaat_het_niet_over_afstand_maar_over_samenlading():
    """7.5.3 scheidt eenheden in de trein; binnen één wagen geldt 7.5.2."""
    found = findings([{"vehicle": "Wagen 1", "products": [BLACK_POWDER, GASOLINE]}])

    assert len(found) == 1
    assert "↔" not in found[0]["products"]


def test_de_bepaling_hoort_bij_het_spoor_en_niet_bij_de_weg():
    entries = wagons(("Wagen 1", [BLACK_POWDER]), ("Wagen 2", [GASOLINE]))

    rail = check_compliance(entries, ["RID"], "nl")["adr_mixed_loading"]
    road = check_compliance(entries, ["ADR"], "nl")["adr_mixed_loading"]

    assert any(w["rule"] == "RID 7.5.3" for w in rail)
    assert not any("7.5.3" in w["rule"] for w in road)


def test_het_spoor_haalt_de_levensmiddelenbepaling_onder_zijn_eigen_naam_aan():
    """RID 7.5.4 verwijst naar CW 28 in kolom (18), het ADR naar CV28.

    De tekst van 7.5.4 is in beide regimes woordelijk gelijk, dus inhoudelijk
    verandert er niets. Maar een CIM-vrachtbrief die "CV28" aanhaalt noemt een
    code die in het RID niet bestaat, en dat is onjuiste informatie die de
    applicatie zelf toevoegt — dezelfde fout als de tunnelcode op een CIM.
    """
    toxic = {"un_number": "1230", "class": "3", "subsidiary_risks": "6.1",
             "proper_shipping_name": "METHANOL"}
    entries = [{"vehicle": "Wagen 1", "products": [toxic]}]

    rail = check_compliance(entries, ["RID"], "nl")["adr_mixed_loading"]
    road = check_compliance(entries, ["ADR"], "nl")["adr_mixed_loading"]

    assert any(w["rule"] == "RID CW28 / 7.5.4" for w in rail)
    assert any(w["rule"] == "ADR CV28 / 7.5.4" for w in road)


def test_de_bevinding_komt_in_de_lijst_die_ook_de_export_leest():
    """Een spoorbepaling die alleen op het scherm staat, staat niet op het document.

    De export leest `adr_mixed_loading`; daarom staat 7.5.3 daarin en niet onder
    een eigen sleutel die alleen het paneel kent.
    """
    entries = wagons(("Wagen 1", [BLACK_POWDER]), ("Wagen 2", [GASOLINE]))

    outcome = check_compliance(entries, ["RID"], "nl")

    assert any(w["rule"] == "RID 7.5.3" for w in outcome["adr_mixed_loading"])
