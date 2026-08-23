"""The package label sheet: chapter 5.2, printed at the size it prescribes.

The placarding sheet tells someone what to hang on the outside of a vehicle,
and deliberately does not draw it — a placard printed on a laser printer is not
a placard. The labels of chapter 5.2 are a different case, and the difference
is not a matter of taste. Package labels are routinely printed on adhesive
stock in practice; the regulation prescribes the artwork, the size and the
colours; and the artwork itself was cut from the official edition rather than
redrawn. What is left to get wrong is the size, and that is now measured.

So this sheet prints two things.

**A working page**, per goods line and per regime, listing which labels and
which marks that package carries and under which provision. This is the half
that survives being photocopied and is the half a packer actually reads.

**The labels themselves, at full size.** One per A4 page. A full-size label is
141.4 mm across: two side by side need 283 mm of a 210 mm width, which is
impossible, and two stacked need 283 mm of a 297 mm height, which leaves 14 mm
for margins, caption and cut marks together and so is not workable either. Each
page carries corner cut marks and a caption naming the model, the provision and
the goods line it belongs to, so a stack of printed pages cannot be mixed up.

What it refuses to print, and why:

* **the battery mark and the orientation arrows.** Their artwork was never cut
  from the official edition the way the class labels were, and drawing them
  from memory is precisely the failure this application exists to prevent. The
  working page names them, with their provision, and says they are not printed
  here;
* **anything at all for air.** The IATA marking rules have not been read.

And one thing it says out loud on every copy: paper is not the material the
regulation asks for. ADR 5.2.1.2 wants a mark that withstands open weather
exposure, and the IMDG Code wants marks (5.2.1.2) and labels (5.2.2.2.1.7) alike
still identifiable after three months in the sea. An office printer and plain
adhesive stock meet neither — and the sheet names **BS 5609**, the standard the
labelling trade uses to show a material does, because telling someone their
paper will not do without saying what will is half an answer. The sheet gives
the right content at the right size; the material stays the responsibility of
the person applying it.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
)

from app.core.languages import normalise
from app.services.dg.package_marking import check_package_marking, rules
from app.services.documents.pdf_render import (
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _styles,
)

#: Where the official label artwork lives. These were cut from the ADR itself
#: by ``scripts/extract_adr_label_models.py``, against measured crop boxes
#: pinned beside the sha256 of the document they came from. Each image is the
#: diamond's bounding box: its points touch the canvas edges, so drawing it
#: into a square of side ``FULL_SIZE_MM`` gives a label whose own side is the
#: 100 mm the provision asks for.
LABELS = Path(__file__).resolve().parents[4] / "scripts" / "un_cards" / "assets" / "labels"

#: A label is "at least 100 mm on each side" (ADR 5.2.2.2.1.1.2, and 49 CFR
#: 172.407(c)(1) in as many words). A square set at 45 degrees with a side of
#: 100 mm measures 100 * sqrt(2) across, so this is the size of the box the
#: artwork goes into — not the side.
FULL_SIZE_MM = 141.42

#: How far outside the label the corner cut marks sit, and how long they are.
CUT_MARK_OFFSET_MM = 3.0
CUT_MARK_LENGTH_MM = 6.0

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "nl": "Etiketten- en merkenblad voor colli (5.2)",
        "en": "Package label and marking sheet (5.2)",
        "de": "Zettel- und Kennzeichnungsblatt für Versandstücke (5.2)",
        "fr": "Feuille d'étiquetage et de marquage des colis (5.2)",
    },
    "generated": {
        "nl": "Opgesteld op", "en": "Drawn up on",
        "de": "Erstellt am", "fr": "Établie le",
    },
    "consignment": {
        "nl": "Zending", "en": "Consignment",
        "de": "Sendung", "fr": "Envoi",
    },
    "goods": {
        "nl": "Per goederenregel", "en": "Per goods line",
        "de": "Je Gutposition", "fr": "Par ligne de marchandises",
    },
    "labels": {"nl": "Etiketten", "en": "Labels", "de": "Zettel", "fr": "Étiquettes"},
    "marks": {"nl": "Merken", "en": "Marks", "de": "Kennzeichen", "fr": "Marques"},
    "provision": {
        "nl": "Voorziening", "en": "Provision",
        "de": "Vorschrift", "fr": "Disposition",
    },
    "regime": {"nl": "Regelgeving", "en": "Regulation",
               "de": "Vorschrift", "fr": "Réglementation"},
    "size_note": {
        "nl": "De etiketten hierna zijn op ware grootte afgedrukt: 100 mm per zijde, "
              "141 mm van punt tot punt, met de binnenlijn op 5 mm van de rand "
              "(5.2.2.2.1.1.2). Één etiket per bladzijde: twee naast elkaar vragen "
              "283 mm op een blad van 210 mm breed, en twee onder elkaar laten van "
              "de 297 mm nog 14 mm over voor marges, bijschrift en snijlijnen samen.",
        "en": "The labels that follow are printed at full size: 100 mm on each side, "
              "141 mm from point to point, with the inner line 5 mm from the edge "
              "(5.2.2.2.1.1.2). One label per page: two side by side need 283 mm across "
              "a 210 mm sheet, and two stacked leave 14 mm of the 297 mm for margins, "
              "caption and cut marks together.",
        "de": "Die folgenden Zettel sind in Originalgröße gedruckt: 100 mm je Seite, "
              "141 mm von Spitze zu Spitze, mit der Innenlinie 5 mm vom Rand "
              "(5.2.2.2.1.1.2). Ein Zettel je Seite: zwei nebeneinander brauchen 283 mm "
              "auf 210 mm Breite, und zwei übereinander lassen von den 297 mm noch "
              "14 mm für Ränder, Bildunterschrift und Schnittmarken zusammen.",
        "fr": "Les étiquettes qui suivent sont imprimées en taille réelle : 100 mm par "
              "côté, 141 mm de pointe à pointe, la ligne intérieure à 5 mm du bord "
              "(5.2.2.2.1.1.2). Une étiquette par page : deux côte à côte demandent 283 mm "
              "sur une feuille de 210 mm, et deux superposées ne laissent que 14 mm "
              "des 297 mm pour les marges, la légende et les traits de coupe.",
    },
    "material_note": {
        "nl": "Papier is niet het materiaal dat de regelgeving vraagt. 5.2.1.2 eist een "
              "merk dat tegen weersinvloeden bestand is; de IMDG Code eist bovendien dat "
              "merken (5.2.1.2) én etiketten (5.2.2.2.1.7) leesbaar blijven op een collo "
              "dat ten minste drie maanden in zee heeft gelegen. De norm waarmee de "
              "branche aantoont dat een materiaal daaraan voldoet is BS 5609. Dit blad "
              "levert de juiste inhoud op de juiste maat; het materiaal blijft de "
              "verantwoordelijkheid van degene die het aanbrengt.",
        "en": "Paper is not the material the regulation asks for. 5.2.1.2 requires a mark "
              "that withstands open weather exposure; the IMDG Code additionally requires "
              "both marks (5.2.1.2) and labels (5.2.2.2.1.7) to stay identifiable on a "
              "package surviving at least three months' immersion in the sea. BS 5609 is "
              "the standard the labelling trade uses to show a material meets that. This "
              "sheet gives the right content at the right size; the material remains the "
              "responsibility of whoever applies it.",
        "de": "Papier ist nicht das Material, das die Vorschrift verlangt. 5.2.1.2 fordert "
              "ein Kennzeichen, das der Witterung standhält; der IMDG-Code fordert "
              "zusätzlich, dass Kennzeichen (5.2.1.2) und Zettel (5.2.2.2.1.7) auf einem "
              "Versandstück nach mindestens drei Monaten im Meer noch erkennbar sind. Die "
              "Norm, mit der die Etikettenbranche das nachweist, ist BS 5609. Dieses Blatt "
              "liefert den richtigen Inhalt in der richtigen Größe; das Material bleibt "
              "Sache dessen, der es anbringt.",
        "fr": "Le papier n'est pas le matériau exigé par la réglementation. Le 5.2.1.2 "
              "exige une marque résistant aux intempéries ; le code IMDG exige en outre "
              "que marques (5.2.1.2) et étiquettes (5.2.2.2.1.7) restent identifiables sur "
              "un colis ayant séjourné au moins trois mois dans la mer. La norme employée "
              "par la profession pour le démontrer est BS 5609. Cette feuille fournit le "
              "bon contenu à la bonne taille ; le matériau reste la responsabilité de "
              "celui qui l'appose.",
    },
    "not_printed": {
        "nl": "Niet op dit blad afgedrukt",
        "en": "Not printed on this sheet",
        "de": "Auf diesem Blatt nicht gedruckt",
        "fr": "Non imprimé sur cette feuille",
    },
    "not_printed_why": {
        "nl": "Van deze merken is de officiële afbeelding niet uit de uitgave gesneden "
              "zoals bij de klasse-etiketten. Ze worden hier niet nagetekend.",
        "en": "The official artwork for these marks was not cut from the edition the way "
              "the class labels were. They are not redrawn here.",
        "de": "Die amtliche Abbildung dieser Kennzeichen wurde nicht wie bei den "
              "Gefahrzetteln aus der Ausgabe entnommen. Sie werden hier nicht nachgezeichnet.",
        "fr": "L'image officielle de ces marques n'a pas été extraite de l'édition comme "
              "pour les étiquettes de classe. Elles ne sont pas redessinées ici.",
    },
    "not_assessed": {
        "nl": "Niet beoordeeld", "en": "Not assessed",
        "de": "Nicht beurteilt", "fr": "Non évalué",
    },
    "orientation_arrows": {
        "nl": "Oriëntatiepijlen (5.2.1.10): of ze gelden hangt af van de verpakkingssoort "
              "— samengestelde verpakking met vloeibare binnenverpakkingen, enkelvoudige "
              "verpakking met ontluchting, cryogene houder, of machine met vloeibare "
              "gevaarlijke goederen. Die soort kent deze applicatie niet.",
        "en": "Orientation arrows (5.2.1.10): whether they apply turns on the kind of "
              "packaging — a combination packaging with liquid inners, a single packaging "
              "fitted with vents, a cryogenic receptacle, or machinery containing liquid "
              "dangerous goods. This application does not know that kind.",
        "de": "Ausrichtungspfeile (5.2.1.10): ob sie gelten, hängt von der Verpackungsart "
              "ab — zusammengesetzte Verpackung mit flüssigen Innenverpackungen, "
              "Einzelverpackung mit Entlüftung, Kryo-Behälter oder Maschine mit flüssigen "
              "gefährlichen Gütern. Diese Art kennt die Anwendung nicht.",
        "fr": "Flèches d'orientation (5.2.1.10) : leur application dépend du type "
              "d'emballage — emballage combiné à emballages intérieurs liquides, "
              "emballage simple muni d'évents, récipient cryogénique, ou machine "
              "contenant des marchandises dangereuses liquides. L'application ignore ce type.",
    },
    "model": {"nl": "Model", "en": "Model", "de": "Muster", "fr": "Modèle"},
    "line": {"nl": "Goederenregel", "en": "Goods line",
             "de": "Gutposition", "fr": "Ligne de marchandises"},
    "no_goods": {
        "nl": "Deze zending bevat geen gevaarlijke goederen; hoofdstuk 5.2 vraagt dan "
              "geen etiketten of merken op het collo.",
        "en": "This consignment contains no dangerous goods, so chapter 5.2 asks for no "
              "labels or marks on the package.",
        "de": "Diese Sendung enthält keine gefährlichen Güter; Kapitel 5.2 verlangt dann "
              "keine Zettel oder Kennzeichen am Versandstück.",
        "fr": "Cet envoi ne contient pas de marchandises dangereuses ; le chapitre 5.2 "
              "n'exige alors ni étiquette ni marque sur le colis.",
    },
}

#: Which mark kinds this sheet can print at full size, and which it can only
#: name. The split is not about importance — it is about whether the official
#: artwork was cut from the edition.
PRINTABLE_MARKS = {"environmentally_hazardous", "marine_pollutant"}
NAMED_ONLY_MARKS = {"battery"}


def _t(key: str, language: str) -> str:
    block = TEXT[key]
    return block.get(language) or block["en"]


def artwork_for(model: str) -> Path | None:
    """The official artwork file for a label model, or nothing.

    The models are named the way the regulation names them and the files the
    way a filesystem tolerates: "6.1" is ``6_1.png``, "9A" is ``9A.png``. Two
    cases need a decision rather than a substitution:

    * **divisions of class 1.** Table A gives 1.1D, 1.2B and so on, and the
      regulation prints one model for divisions 1.1, 1.2 and 1.3 with a place
      on it for the division and the compatibility group. So those map to
      model 1, and the caption carries the division and group the label has to
      be completed with. Divisions 1.4, 1.5 and 1.6 have models of their own;
    * **a model with no file.** Nothing is substituted. A missing file means
      the label is named on the working page and not printed, which is the
      honest failure — printing a neighbouring model would not be.
    """
    token = (model or "").strip().upper()
    if not token:
        return None
    if token.startswith(("1.1", "1.2", "1.3")):
        token = "1"
    elif token.startswith("1.4"):
        token = "1.4"
    elif token.startswith("1.5"):
        token = "1.5"
    elif token.startswith("1.6"):
        token = "1.6"
    candidate = LABELS / f"{token.replace('.', '_')}.png"
    return candidate if candidate.exists() else None


class _FullSizeLabel(Flowable):
    """One label at 100 mm on each side, with corner cut marks.

    Drawn as a flowable rather than through a page callback so that the cut
    marks cannot drift away from the artwork: both are placed in the same
    coordinate system, in one place, at the moment the label is laid down.
    """

    def __init__(self, image: Path, side_mm: float = FULL_SIZE_MM):
        super().__init__()
        self.image = image
        self.size = side_mm * mm
        self.width = self.size
        self.height = self.size

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        canvas.drawImage(str(self.image), 0, 0, width=self.size, height=self.size,
                         preserveAspectRatio=True, anchor="c", mask="auto")
        offset = CUT_MARK_OFFSET_MM * mm
        length = CUT_MARK_LENGTH_MM * mm
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#9ca3af"))
        canvas.setLineWidth(0.4)
        for x in (0, self.size):
            for y in (0, self.size):
                horizontal = -offset - length if x == 0 else offset + length
                vertical = -offset - length if y == 0 else offset + length
                canvas.line(x + (horizontal if x == 0 else offset),
                            y, x + (-offset if x == 0 else horizontal), y)
                canvas.line(x, y + (vertical if y == 0 else offset),
                            x, y + (-offset if y == 0 else vertical))
        canvas.restoreState()


def _label_header(lang: str) -> list[str]:
    return [_t("regime", lang), _t("line", lang), _t("labels", lang), _t("marks", lang)]


def _label_rows(result: dict[str, Any], lang: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for block in result.get("regimes", []):
        for item in block.get("items", []):
            labels = ", ".join(
                f"{entry['model']}" for entry in item.get("labels", []))
            marks = ", ".join(
                f"{mark['kind'].replace('_', ' ')} ({mark['provision']})"
                for mark in item.get("marks", []))
            rows.append([block["profile"], item["product"], labels or "—", marks or "—"])
    return rows


def render_package_label_sheet(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    profiles: list[str] | None = None,
) -> Path:
    """The sheet, from the answer ``check_package_marking`` already computes.

    Nothing here decides anything about the regulation: every label and every
    mark comes from that check, which read chapter 5.2 out of the official
    editions. What this file adds is paper, at the size the chapter prescribes.
    """
    lang = normalise(language)
    entries = list(dangerous_goods or [])
    wanted = list(profiles or ["ADR"])
    result = check_package_marking(entries, wanted, lang)

    styles = _styles()
    out_path = _output_path()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=_t("title", lang),
    )
    width = doc.width
    story: list[Any] = [
        _p(_t("title", lang), styles["title"]),
        _p(f"{_t('generated', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           styles["meta"]),
        Spacer(1, 6),
    ]

    if result.get("status") != "ok":
        story.append(_p(_t("no_goods", lang), styles["fixed"]))
        doc.build(story)
        return out_path

    reference = values.get("reference") or values.get("order_reference") or ""
    if reference:
        story.append(_p(f"{_t('consignment', lang)}: {reference}", styles["meta"]))
        story.append(Spacer(1, 4))

    story.append(KeepTogether([
        _section_header(_t("goods", lang), styles, width),
        _grid_table(_label_header(lang), _label_rows(result, lang), styles, width),
    ]))
    story.append(Spacer(1, 8))

    # What the check could not settle, in the provision's own terms. The
    # placarding sheet set this pattern: an answer that hides its own gaps is
    # worse than one that names them.
    if "orientation_arrows" in result.get("not_assessed", []):
        story.append(_p(f"<b>{_t('not_assessed', lang)}.</b> "
                        f"{_t('orientation_arrows', lang)}", styles["fixed"]))
        story.append(Spacer(1, 6))

    named_only = sorted({
        mark["kind"]
        for block in result["regimes"] for item in block["items"]
        for mark in item["marks"] if mark["kind"] in NAMED_ONLY_MARKS
    })
    if named_only:
        story.append(_p(f"<b>{_t('not_printed', lang)}.</b> "
                        f"{', '.join(named_only)}. {_t('not_printed_why', lang)}",
                        styles["fixed"]))
        story.append(Spacer(1, 6))

    story.append(_p(_t("size_note", lang), styles["fixed"]))
    story.append(Spacer(1, 4))
    story.append(_p(_t("material_note", lang), styles["fixed"]))

    # One page per label, and never the same model twice for the same line.
    printed: set[tuple[str, str]] = set()
    source = rules()["labels"]["shape"]["provision"]
    for block in result["regimes"]:
        provision = source.get(block["profile"].lower()) or source["adr"]
        for item in block["items"]:
            for entry in item.get("labels", []):
                key = (item["product"], entry["model"])
                if key in printed:
                    continue
                image = artwork_for(entry["model"])
                if image is None:
                    continue
                printed.add(key)
                story.append(PageBreak())
                story.append(_p(
                    f"{_t('model', lang)} {entry['model']} — {item['product']} "
                    f"({_t('provision', lang)} {provision})", styles["meta"]))
                story.append(Spacer(1, 6))
                story.append(_FullSizeLabel(image))

    doc.build(story)
    return out_path
