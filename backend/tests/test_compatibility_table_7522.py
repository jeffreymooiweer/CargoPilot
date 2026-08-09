"""Tabel 7.5.2.2 gelezen in plaats van doorverwezen — en het RID leest anders.

Tot v1.41.0 telde CargoPilot bij twee compatibiliteitsgroepen alleen hoeveel er
waren en gaf het de vraag terug: "controleer de compatibiliteitsgroepen". Dat is
op zichzelf eerlijk, maar het is ook precies de vraag die de gebruiker niet kan
beantwoorden — hij heeft de boekwerken niet. De tabel staat nu in de
configuratie en wordt gelezen.

De teksten zijn woordelijk opgehaald met `scripts/read_land_regulations.py`:

- **ADR 2025 Volume II (ECE/TRANS/352 Vol. II), 7.5.2.2, gedrukte bladzijde 593**
  (`--doc adr2 --page 602-603`)
- **RID 2025 (Aanhangsel C bij het COTIF, Bijlage), 7.5.2.2, bladzijde 1102**
  (`--doc rid --page 1101-1103`)

En daar zit een verschil dat het waard is om vast te leggen: **de RID-tabel is de
ADR-tabel zonder compatibiliteitsgroep A.** Het ADR loopt van A tot en met S, het
RID van B tot en met S. Geen van beide kent groep K. Dat is een verschil in wat
de tabel beantwoordt en niet in het antwoord — dus krijgt een spoortraject de
spoortabel, en krijgt een collo van groep A op het spoor te horen dat de tabel er
niets over zegt. Een verbod lenen is voorzichtig, een toestemming lenen niet, en
een tabelrij lenen die er in het andere regime niet ís, is geen van beide.

De vier voetnoten staan in beide teksten in dezelfde bewoordingen (het RID zegt
"wagen" waar het ADR "voertuig" zegt):

    (a) Colli van groep B en colli van groep D mogen samen worden geladen mits
        doeltreffend gescheiden, zodat detonatie niet van B naar D kan overslaan.
        Scheiding met gescheiden compartimenten of een bijzonder omhullingssysteem,
        en de bevoegde autoriteit moet de methode goedkeuren.
    (b) Verschillende soorten voorwerpen van 1.6N alleen samen als door beproeving
        of analogie is aangetoond dat er geen sympathische detonatie optreedt.
    (c) Voorwerpen van groep N samen met C, D of E: N wordt behandeld als D.
    (d) Colli van groep L alleen samen met colli met hetzelfde soort stof of
        voorwerp van die groep.

Eén ding dat hier fout in had gekund en het niet is: **1.4S hoort er wél bij.**
Voetnoot (a) bij 7.5.2.1 haalt 1.4S weg uit de vergelijking met ándere klassen,
en de oude code liet 1.4S daarom overal buiten. Maar 7.5.2.2 gaat over
explosieven onderling en heeft een rij S — die niet overal op X staat. S naast
groep L is leeg, dus verboden. Een uitzondering uit de ene bepaling naar de
andere doortrekken had die combinatie stilzwijgend goedgekeurd.
"""

import pytest

from app.services.dg.compliance import check_adr_mixed_loading, get_compliance_rules


def product(un, code, name="ARTICLES"):
    return {"un_number": un, "class": code, "classification_code": code,
            "proper_shipping_name": name}


def load(*products, profiles=("ADR",), language="nl"):
    entries = [{"line_id": "L1", "products": list(products)}]
    return [
        w for w in check_adr_mixed_loading(entries, language, list(profiles))
        if "7.5.2.2" in w["rule"]
    ]


def table(which):
    return get_compliance_rules()["adr_mixed_loading"]["compatibility"][which]


@pytest.mark.parametrize("which,size", [("road", 12), ("rail", 11)])
def test_de_tabel_is_symmetrisch(which, size):
    """De controle waarmee het aflezen van het raster is geverifieerd.

    Een tabel van kruisjes komt als een kolom losse tekens uit een PDF; één
    kolom verkeerd tellen levert een tabel op die er plausibel uitziet. Maar
    samenladen is wederkerig: als B naast D mag, mag D naast B. Een verschoven
    kolom breekt die symmetrie vrijwel zeker ergens. Dat is hier de enige
    onafhankelijke toets op het aflezen, en daarom staat hij vast.
    """
    data = table(which)
    order, matrix = data["group_order"], data["matrix"]

    assert len(order) == size
    assert sorted(matrix) == sorted(order)
    for group in order:
        assert len(matrix[group]) == size, f"rij {group} heeft niet {size} vakjes"
    for a in order:
        for b in order:
            assert matrix[a][order.index(b)] == matrix[b][order.index(a)], f"{a} × {b}"


def test_de_spoortabel_is_de_wegtabel_zonder_groep_a():
    """Het enige verschil tussen de twee teksten, hier vastgelegd.

    Zou het RID ergens anders van het ADR afwijken, dan hoort deze test te
    breken en niet stilletjes mee te gaan.
    """
    road, rail = table("road"), table("rail")

    assert set(road["group_order"]) - set(rail["group_order"]) == {"A"}
    for group in rail["group_order"]:
        expected = [road["matrix"][group][road["group_order"].index(other)]
                    for other in rail["group_order"]]
        assert rail["matrix"][group] == expected, f"rij {group} wijkt af"
    assert "K" not in road["group_order"] and "K" not in rail["group_order"]


def test_toegestane_combinatie_levert_geen_melding():
    """C naast D is een X in de tabel; dan hoort de gebruiker niets te horen."""
    assert load(product("0160", "1.1C", "POWDER"), product("0027", "1.1D")) == []


def test_verboden_combinatie_is_een_fout_en_geen_waarschuwing():
    """Groep A naast D is een leeg vakje: dat is een verbod, niet een aandachtspunt."""
    found = load(product("0473", "1.1A"), product("0027", "1.1D"))

    assert len(found) == 1
    assert found[0]["severity"] == "error"
    assert found[0]["rule"] == "ADR 7.5.2.2 (A × D)"


def test_voetnoot_a_maakt_van_een_verbod_een_voorwaarde():
    """B naast D mag, maar alleen met goedgekeurde scheiding — en dat staat erbij."""
    found = load(product("0029", "1.1B", "DETONATORS"), product("0027", "1.1D"))

    assert len(found) == 1
    assert found[0]["severity"] == "warning"
    assert "bevoegde autoriteit" in found[0]["message"]


def test_een_vakje_met_twee_voetnoten_geeft_ze_allebei():
    """Bij D × N staat "(b), (c)"; beide voorwaarden gelden, dus beide worden genoemd."""
    found = load(product("0027", "1.1D"), product("0486", "1.6N"))

    assert {w["rule"] for w in found} == {
        "ADR 7.5.2.2 (D × N) (b)",
        "ADR 7.5.2.2 (D × N) (c)",
    }


def test_veertien_s_telt_mee_voor_de_compatibiliteitstabel():
    """1.4S valt buiten 7.5.2.1, maar niet buiten 7.5.2.2 — en S × L is leeg.

    De oude code sloot 1.4S overal uit met de uitzondering die bij 7.5.2.1
    hoort. Deze combinatie kwam daardoor niet eens aan de tabel toe.
    """
    found = load(product("0349", "1.4S"), product("0190", "1.1L", "SAMPLES"))

    assert len(found) == 1
    assert found[0]["severity"] == "error"
    assert found[0]["rule"] == "ADR 7.5.2.2 (L × S)"


def test_twee_colli_van_groep_l_krijgen_voetnoot_d():
    """Op de diagonaal gaat het over twee colli van dezelfde groep."""
    found = load(product("0190", "1.1L", "SAMPLES A"), product("0224", "1.1L", "SAMPLES B"))

    assert [w["rule"] for w in found] == ["ADR 7.5.2.2 (L × L) (d)"]


def test_een_enkel_collo_van_groep_l_valt_niets_samen_te_laden():
    """Met één collo is er geen combinatie; voetnoot (d) gaat dan nergens over."""
    assert load(product("0190", "1.1L", "SAMPLES")) == []


def test_het_spoor_zegt_dat_groep_a_niet_in_zijn_tabel_staat():
    """Geen ADR-rij op leen: het RID kent groep A niet en zegt dat."""
    found = load(product("0473", "1.1A"), product("0027", "1.1D"), profiles=("RID",))

    assert len(found) == 1
    assert found[0]["rule"] == "RID 7.5.2.2"
    assert found[0]["severity"] == "warning"
    assert "A" in found[0]["message"] and "RID" in found[0]["message"]


def test_zonder_groep_wordt_er_niet_gegokt():
    """Een klasse 1-collo zonder classificatiecode is niet te toetsen; dat staat er."""
    found = load({"un_number": "0027", "class": "1", "proper_shipping_name": "BLACK POWDER"},
                 product("0029", "1.1B", "DETONATORS"))

    assert len(found) == 1
    assert "niet bekend" in found[0]["message"]


def test_de_bron_staat_bij_de_tabel():
    """Regelgevingswaarden dragen hier hun vindplaats; anders is er niets na te lezen."""
    compatibility = get_compliance_rules()["adr_mixed_loading"]["compatibility"]

    assert "7.5.2.2" in compatibility["_source"]
    assert "page 593" in compatibility["_source"]
    assert "1102" in compatibility["_source"]
