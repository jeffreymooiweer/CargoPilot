"""Twee explosieven in één zending gaven een serverfout in plaats van een antwoord.

Gemeld gedrag: een zending met twee colli van klasse 1 — bijvoorbeeld slagpijpjes
(compatibiliteitsgroep B) naast een springstof (groep D), wat een alledaagse
combinatie is — leverde geen nalevingsuitkomst op maar een fout. Zowel het paneel
in de wizard als de export loopt over `check_compliance`, dus er kwam ook geen
document uit.

De oorzaak zat op de naad, zoals hier vaker. In v1.38.0 werd `class1_products`
van een lijst etiketten een lijst tupels `(etiket, UN-nummer)`, omdat de
voetnoten van 7.5.2.1 het UN-nummer nodig hebben. De melding van 7.5.2.2 een
paar regels verderop bleef `", ".join(class1_products)` doen en kreeg vanaf dat
moment tupels aangeboden: `TypeError`. Geen enkele test merkte het, en daar zit
het tweede defect.

Want waarom merkte niemand het? Omdat de groep werd afgelezen uit het
*klasseveld* met een strak anker (`^1\\.\\d([A-S])$`), en ADR Tabel A zet in de
klassekolom bij explosieven alleen "1" — de divisie met haar
compatibiliteitsgroep staat in de classificatiecode. Voor elke rij die
rechtstreeks uit de seed komt, vond die controle dus nooit een groep, ging
7.5.2.2 nooit af, en bleef de kapotte regel onbereikbaar. Een controle die niet
liep zag eruit als een controle die niets te melden had.

Twee defecten die elkaar dekten: de stille versie maskeerde de luide. Daarom
staan ze in één bestand, en daarom staat er onderaan een veegtest die niet naar
een specifieke regel kijkt maar alleen eist dat geen enkele zending de controle
kan laten struikelen.

Gemeten op de echte gegevens vóór herstel: 344 van 4.000 willekeurige zendingen
van twee tot vijf UN-nummers eindigden in een uitzondering (8,6%).
"""

import json
import random
from pathlib import Path

import pytest

from app.services.dg.autofill import derive_product
from app.services.dg.compliance import check_adr_mixed_loading, check_compliance

# UN 0027 zwart buskruit is 1.1D, UN 0029 slagpijpjes zijn 1.1B. Samen laden mag
# alleen voor zover tabel 7.5.2.2 het toestaat — de vraag die de applicatie moet
# stellen in plaats van erop stuk te lopen.
BLACK_POWDER = {
    "un_number": "0027",
    "proper_shipping_name": "BLACK POWDER",
    "class": "1.1D",
    "classification_code": "1.1D",
}
DETONATORS = {
    "un_number": "0029",
    "proper_shipping_name": "DETONATORS, NON-ELECTRIC",
    "class": "1.1B",
    "classification_code": "1.1B",
}
# Zoals Tabel A het werkelijk levert: klasse "1", groep in de classificatiecode.
DETONATORS_TABLE_A = dict(DETONATORS, **{"class": "1"})


def load(*products, language="nl"):
    return check_adr_mixed_loading([{"line_id": "L1", "products": list(products)}], language)


def compat_warnings(warnings):
    return [w for w in warnings if w["rule"].startswith("ADR 7.5.2.2")]


def test_twee_compatibiliteitsgroepen_geven_een_antwoord_en_geen_fout():
    """De crash zelf: dit riep tot v1.40.1 `TypeError` op in plaats van te melden.

    Sinds v1.41.0 wordt de tabel ook echt gelezen, dus wat er uit komt is het
    vakje B × D — voetnoot (a) — en niet meer de vraag teruggegeven.
    """
    found = compat_warnings(load(BLACK_POWDER, DETONATORS))

    assert len(found) == 1
    assert found[0]["rule"] == "ADR 7.5.2.2 (B × D) (a)"
    assert found[0]["severity"] == "warning"


def test_de_melding_noemt_de_betrokken_colli():
    """`products` droeg tupels; wat de gebruiker zoekt is welke colli het betreft."""
    found = compat_warnings(load(BLACK_POWDER, DETONATORS))[0]

    assert found["products"] == "UN 0029 DETONATORS, NON-ELECTRIC, UN 0027 BLACK POWDER"


def test_de_groep_komt_uit_de_classificatiecode_niet_uit_de_klassekolom():
    """Tabel A zegt in de klassekolom "1"; de groep staat in de classificatiecode.

    Dit is het stille defect. Zolang de groep alleen uit het klasseveld werd
    gelezen, ging 7.5.2.2 op echte seedgegevens nooit af — en werd de crash
    erboven nooit bereikt.
    """
    found = compat_warnings(load(BLACK_POWDER, DETONATORS_TABLE_A))

    assert len(found) == 1
    assert found[0]["rule"] == "ADR 7.5.2.2 (B × D) (a)"


def test_een_enkele_groep_geeft_geen_melding():
    """7.5.2.2 gaat over verschíllende groepen; twee keer D is niets aan de hand."""
    assert compat_warnings(load(BLACK_POWDER, dict(BLACK_POWDER, un_number="0028"))) == []


def test_klasse_1_naast_klasse_1_met_nevengevaar_laat_de_zeecontrole_staan():
    """IMDG 7.2.4: een "*" verwijst door naar 7.2.7 en mag geen cijfer verdringen.

    De tabel geeft voor klasse 1 tegen klasse 1 een "*". Stond die er als eerste,
    dan vergeleek de volgende cel `int(value) > int("*")` en viel de controle om.
    UN 0018 draagt nevengevaren 6.1 en 8, dus een tweede klasse 1-collo levert
    precies die volgorde op: eerst de "*", daarna een cijfer.
    """
    entries = [{"line_id": "L1", "products": [
        {"un_number": "0018", "class": "1.2G", "classification_code": "1.2G",
         "subsidiary_risks": "6.1+8", "proper_shipping_name": "AMMUNITION, TOXIC"},
        {"un_number": "0183", "class": "1.1D", "classification_code": "1.1D",
         "proper_shipping_name": "ROCKETS, INERT HEAD"},
    ]}]

    findings = check_compliance(entries, ["IMDG"], "nl")["imdg_segregation"]

    table = [f for f in findings if f["rule"].startswith("IMDG 7.2.4")]
    assert table, "de klassescheidingstabel hoort een uitspraak te doen"
    # Het cijfer wint van de "*": 4 is "separated longitudinally by an
    # intervening complete compartment or hold from".
    assert table[0]["code"] == "4"


def _seed_un_numbers() -> list[str]:
    seed = Path(__file__).resolve().parents[1] / "seed" / "dg" / "un_numbers.json"
    return sorted({str(row["un"]) for row in json.loads(seed.read_text(encoding="utf-8"))})


@pytest.mark.parametrize("profile", ["ADR", "RID", "ADN", "IMDG", "IATA_DGR"])
def test_geen_enkele_zending_laat_de_nalevingscontrole_struikelen(profile):
    """Een veegtest over de echte gegevens, langs de weg die de wizard ook loopt.

    Beide defecten hierboven zijn zo gevonden en niet door te lezen. Ze zijn ook
    alleen langs deze weg te vinden: op de kale seedrij staat "1" in de
    klassekolom en gebeurt er niets, pas ná `derive_product` — wat de interface
    invult zodra iemand een UN-nummer kiest — draagt het product de divisie.

    Vast ingezaaid, zodat een fout van vandaag ook morgen dezelfde fout is.
    """
    uns = _seed_un_numbers()
    rng = random.Random(20260808)
    cache: dict[str, dict] = {}

    def product(un: str) -> dict:
        if un not in cache:
            base = {
                "un_number": un,
                "net_mass_liters_per_package": "5 kg",
                "quantity_packages": "3",
                "gross_mass": "40 kg",
            }
            base.update(derive_product(base, "nl", [profile]).get("patch", {}))
            cache[un] = base
        return dict(cache[un])

    for _ in range(300):
        picks = rng.sample(uns, rng.choice([2, 3, 4, 5]))
        entries = [{"line_id": "L1", "products": [product(un) for un in picks]}]
        try:
            check_compliance(entries, [profile], "nl")
        except Exception as exc:  # pragma: no cover - de melding ís de test
            pytest.fail(f"{profile} viel om op {picks}: {type(exc).__name__}: {exc}")
