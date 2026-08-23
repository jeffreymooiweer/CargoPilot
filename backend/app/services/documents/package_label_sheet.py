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

**The marks, each in the way its own provision defines it.** The
environmentally hazardous substance mark and the marine pollutant mark are one
figure, cut whole from the edition, and print at the same size as a label. The
battery mark is not cut whole, and the reason is worth stating: its printed
figure is wrapped in dimension annotations that abut its hatched edging, and it
carries an asterisk where a package needs the actual UN number. Everything
about that mark except the symbol is given in the provision *in words* — a
rectangle, 100 mm by 100 mm, red hatched edging at least 5 mm wide, the symbol
above the UN number or numbers — so the frame is built from those values and
the symbol, which is the only part words cannot carry, is the edition's own.
The orientation arrows are cut whole, and are the one figure the regulation
gives no size for: 5.2.1.10.1 asks only that they be "clearly visible
commensurate with the size of the package", so the sheet prints them at a size
it names as its own choice rather than as a requirement.

What it still refuses to print, and why: **anything at all for air.** The IATA
marking rules have not been read.

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
from reportlab.lib.utils import ImageReader
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

#: The battery mark of 5.2.1.9.2, in the numbers the provision states: a
#: rectangle 100 mm by 100 mm, with hatched edging at least 5 mm wide, the
#: hatching red and the symbol black. Only the symbol comes from the edition;
#: the rest of this figure is words, and words are what these are.
BATTERY_SIZE_MM = 100.0
BATTERY_HATCH_MM = 5.0
BATTERY_HATCH_PITCH_MM = 3.5
BATTERY_RED = colors.HexColor("#d0021b")

#: The orientation arrows have no prescribed size at all — 5.2.1.10.1 asks for
#: "a size that is clearly visible commensurate with the size of the package",
#: which is a judgement about the package and not a number. This is the sheet's
#: own choice, and the caption says so, because presenting a chosen size as a
#: prescribed one would be the same lie as printing a label at the wrong size.
ARROWS_HEIGHT_MM = 100.0

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
    "mark": {"nl": "Merk", "en": "Mark", "de": "Kennzeichen", "fr": "Marque"},
    "battery_mark": {
        "nl": "Batterijmerk", "en": "Battery mark",
        "de": "Batteriekennzeichen", "fr": "Marque pour piles et batteries",
    },
    "battery_built": {
        "nl": "Het symbool komt uit de officiële uitgave (figuur 5.2.1.9.2). De rechthoek "
              "eromheen is opgebouwd uit wat 5.2.1.9.2 met zoveel woorden voorschrijft: "
              "100 bij 100 mm, met een rode arcering van ten minste 5 mm. Het UN-nummer "
              "staat eronder, zoals het voorschrift het vraagt; de gedrukte figuur zet daar "
              "een sterretje, en een sterretje op een collo is geen UN-nummer.",
        "en": "The symbol is from the official edition (Figure 5.2.1.9.2). The rectangle "
              "around it is built from what 5.2.1.9.2 prescribes in as many words: 100 mm "
              "by 100 mm, with red hatching at least 5 mm wide. The UN number goes below "
              "it, as the provision asks; the printed figure puts an asterisk there, and an "
              "asterisk on a package is not a UN number.",
        "de": "Das Symbol stammt aus der amtlichen Ausgabe (Abbildung 5.2.1.9.2). Das "
              "Rechteck darum ist aus dem aufgebaut, was 5.2.1.9.2 wörtlich vorschreibt: "
              "100 mal 100 mm, mit roter Schraffur von mindestens 5 mm. Die UN-Nummer steht "
              "darunter, wie die Vorschrift es verlangt; die gedruckte Abbildung setzt dort "
              "einen Stern, und ein Stern auf einem Versandstück ist keine UN-Nummer.",
        "fr": "Le symbole provient de l'édition officielle (figure 5.2.1.9.2). Le rectangle "
              "qui l'entoure est construit à partir de ce que le 5.2.1.9.2 prescrit en "
              "toutes lettres : 100 mm sur 100 mm, avec des hachures rouges d'au moins "
              "5 mm. Le numéro ONU figure en dessous, comme la disposition l'exige ; la "
              "figure imprimée y met un astérisque, et un astérisque sur un colis n'est pas "
              "un numéro ONU.",
    },
    "battery_reduction": {
        "nl": "Als de afmetingen van het collo dat vragen, mag het merk kleiner: niet minder "
              "dan 100 mm breed bij 70 mm hoog.",
        "en": "If the size of the package so requires, the mark may be reduced — to not less "
              "than 100 mm wide by 70 mm high.",
        "de": "Wenn die Größe des Versandstücks es erfordert, darf das Kennzeichen kleiner "
              "sein — nicht weniger als 100 mm breit und 70 mm hoch.",
        "fr": "Si la taille du colis l'exige, la marque peut être réduite — à pas moins de "
              "100 mm de large sur 70 mm de haut.",
    },
    "arrows_mark": {
        "nl": "Oriëntatiepijlen", "en": "Orientation arrows",
        "de": "Ausrichtungspfeile", "fr": "Flèches d'orientation",
    },
    "arrows_size": {
        "nl": "Voor deze pijlen schrijft 5.2.1.10.1 geen maat voor: ze moeten \"duidelijk "
              "zichtbaar zijn in verhouding tot de grootte van het collo\". De maat hierna "
              "is dus een keuze van dit blad en geen eis. De rechthoek eromheen is volgens "
              "hetzelfde voorschrift facultatief. Ze horen op twee tegenover elkaar liggende "
              "verticale zijden, met de punt omhoog.",
        "en": "5.2.1.10.1 prescribes no size for these arrows: they must be \"of a size that "
              "is clearly visible commensurate with the size of the package\". The size "
              "below is therefore this sheet's choice and not a requirement. The rectangular "
              "border around them is optional under the same provision. They belong on two "
              "opposite vertical sides, pointing upright.",
        "de": "Für diese Pfeile schreibt 5.2.1.10.1 keine Größe vor: sie müssen \"in einer "
              "Größe, die im Verhältnis zur Größe des Versandstücks deutlich sichtbar ist\" "
              "sein. Die folgende Größe ist daher die Wahl dieses Blattes und keine "
              "Vorgabe. Der Rahmen darum ist nach derselben Vorschrift freigestellt. Sie "
              "gehören auf zwei gegenüberliegende senkrechte Seiten, Spitze nach oben.",
        "fr": "Le 5.2.1.10.1 ne prescrit aucune dimension pour ces flèches : elles doivent "
              "être \"d'une taille clairement visible en rapport avec la taille du colis\". "
              "La taille ci-après est donc un choix de cette feuille et non une exigence. Le "
              "cadre rectangulaire qui les entoure est facultatif selon la même disposition. "
              "Elles vont sur deux côtés verticaux opposés, pointe vers le haut.",
    },
    "arrows_only_if": {
        "nl": "Alleen afdrukken als het collo onder 5.2.1.10.1 valt en niet onder een van de "
              "uitzonderingen van 5.2.1.10.2. Deze applicatie kent de verpakkingssoort niet "
              "en kan dat dus niet beoordelen. 5.2.1.10.3 verbiedt pijlen voor een ander doel "
              "op een collo dat volgens deze onderafdeling gemerkt is.",
        "en": "Use this only if the package falls under 5.2.1.10.1 and under none of the "
              "exceptions of 5.2.1.10.2. This application does not know the kind of packaging "
              "and cannot judge that. 5.2.1.10.3 forbids arrows for any other purpose on a "
              "package marked under this sub-section.",
        "de": "Nur verwenden, wenn das Versandstück unter 5.2.1.10.1 fällt und unter keine "
              "der Ausnahmen des 5.2.1.10.2. Diese Anwendung kennt die Verpackungsart nicht "
              "und kann das nicht beurteilen. 5.2.1.10.3 verbietet Pfeile zu anderen Zwecken "
              "auf einem nach diesem Unterabschnitt gekennzeichneten Versandstück.",
        "fr": "N'utilisez ceci que si le colis relève du 5.2.1.10.1 et d'aucune des "
              "exceptions du 5.2.1.10.2. Cette application ignore le type d'emballage et ne "
              "peut en juger. Le 5.2.1.10.3 interdit les flèches à toute autre fin sur un "
              "colis marqué au titre de cette sous-section.",
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

#: The mark kinds this sheet prints, and the artwork each one is drawn from.
#: The environmentally hazardous substance mark and the marine pollutant mark
#: are the same figure under two names — 5.2.1.8.3 on land, 5.2.1.6 at sea —
#: and the file is the one the UN cards already use. The battery mark has no
#: single file because only its symbol is cut; it is assembled instead.
DIAMOND_MARKS = {"environmentally_hazardous": "MP", "marine_pollutant": "MP"}
BUILT_MARKS = {"battery"}


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


class _BatteryMark(Flowable):
    """The mark of 5.2.1.9.2: the edition's symbol inside a frame of words.

    Everything here except the symbol image comes from the provision's own
    numbers — 100 mm by 100 mm, hatched edging at least 5 mm wide, the hatching
    red, the symbol above the UN number or numbers. The hatching is drawn as
    diagonal strokes clipped to the border band, which is what "hatched edging"
    describes and what the figure shows.

    The UN number is printed, not left as the asterisk the figure carries. The
    figure's asterisk is a footnote to a book; on a package it would be a mark
    that says nothing, and the whole point of this mark is to say which cells
    are inside.
    """

    def __init__(self, symbol: Path | None, un_numbers: list[str],
                 side_mm: float = BATTERY_SIZE_MM):
        super().__init__()
        self.symbol = symbol
        self.un_numbers = un_numbers
        self.size = side_mm * mm
        self.width = self.size
        self.height = self.size

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self) -> None:
        canvas = self.canv
        band = BATTERY_HATCH_MM * mm
        canvas.saveState()

        # The hatching first, over the whole square, then the inside painted
        # back to white. Clipping strokes to a frame is fiddly and this is the
        # same picture with one fewer thing to get wrong.
        canvas.setStrokeColor(BATTERY_RED)
        canvas.setLineWidth(0.9)
        pitch = BATTERY_HATCH_PITCH_MM * mm
        steps = int(2 * self.size / pitch) + 1
        canvas.saveState()
        path = canvas.beginPath()
        path.rect(0, 0, self.size, self.size)
        canvas.clipPath(path, stroke=0)
        for step in range(steps):
            offset = step * pitch - self.size
            canvas.line(offset, 0, offset + self.size, self.size)
        canvas.restoreState()
        canvas.setFillColor(colors.white)
        canvas.rect(band, band, self.size - 2 * band, self.size - 2 * band,
                    stroke=0, fill=1)

        # The two outlines the figure draws: the edge of the mark and the edge
        # of the hatched band.
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.7)
        canvas.rect(0, 0, self.size, self.size, stroke=1, fill=0)
        canvas.rect(band, band, self.size - 2 * band, self.size - 2 * band,
                    stroke=1, fill=0)

        inner = self.size - 2 * band
        text_height = 9 * mm if self.un_numbers else 0.0
        if self.symbol is not None:
            canvas.drawImage(
                str(self.symbol), band, band + text_height,
                width=inner, height=inner - text_height,
                preserveAspectRatio=True, anchor="c", mask="auto")
        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", 16)
        if self.un_numbers:
            canvas.drawCentredString(self.size / 2, band + 2 * mm,
                                     "  ".join(self.un_numbers))
        canvas.restoreState()


class _Figure(Flowable):
    """One cut figure at a chosen height, keeping the proportions it was cut at.

    Used for the orientation arrows, which is the one figure in this chapter
    with no prescribed size. "In approximate proportion to those shown" is what
    5.2.1.10.1 does prescribe, so the width follows the image rather than the
    page.
    """

    def __init__(self, image: Path, height_mm: float):
        super().__init__()
        self.image = image
        self.height = height_mm * mm
        reader = ImageReader(str(image))
        pixel_width, pixel_height = reader.getSize()
        self.width = self.height * pixel_width / pixel_height

    def wrap(self, available_width, available_height):
        return self.width, self.height

    def draw(self) -> None:
        self.canv.drawImage(str(self.image), 0, 0,
                            width=self.width, height=self.height,
                            preserveAspectRatio=True, anchor="c", mask="auto")


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


def _mark_pages(result: dict[str, Any], styles: dict[str, Any],
                lang: str) -> list[Any]:
    """The marks, after the labels, one to a page.

    Ordered by kind rather than by goods line, because a mark is a mark whoever
    carries it: the environmentally hazardous substance mark is the same figure
    for every line that needs it, and printing it once per line would produce a
    stack of identical pages. The battery mark is the exception — it carries the
    UN number of the cells inside — so it is printed once per set of numbers.
    """
    story: list[Any] = []

    diamonds: dict[str, str] = {}
    batteries: dict[str, list[str]] = {}
    for block in result.get("regimes", []):
        for item in block.get("items", []):
            for mark in item.get("marks", []):
                kind = mark.get("kind")
                if kind in DIAMOND_MARKS:
                    diamonds.setdefault(DIAMOND_MARKS[kind], mark.get("provision", ""))
                elif kind in BUILT_MARKS:
                    number = str(mark.get("text") or "").replace("UN ", "").strip()
                    if number:
                        batteries.setdefault(item["product"], []).append(number)

    for artwork, provision in sorted(diamonds.items()):
        image = LABELS / f"{artwork}.png"
        if not image.exists():
            continue
        story.append(PageBreak())
        story.append(_p(f"{_t('mark', lang)} — {_t('provision', lang)} {provision}",
                        styles["meta"]))
        story.append(Spacer(1, 6))
        story.append(_FullSizeLabel(image))

    # No symbol, no page. A frame with the UN number in it and an empty middle
    # is not a lesser version of this mark; it is a different one, and the whole
    # reason it is recognised on a pallet is the picture in the middle.
    symbol = LABELS / "BATTERY_SYMBOL.png"
    for product, numbers in (batteries.items() if symbol.exists() else ()):
        story.append(PageBreak())
        story.append(_p(f"{_t('battery_mark', lang)} — {product} "
                        f"({_t('provision', lang)} 5.2.1.9.2)", styles["meta"]))
        story.append(Spacer(1, 4))
        story.append(_p(_t("battery_built", lang), styles["fixed"]))
        story.append(_p(_t("battery_reduction", lang), styles["fixed"]))
        story.append(Spacer(1, 6))
        story.append(_BatteryMark(symbol if symbol.exists() else None,
                                  sorted(dict.fromkeys(numbers))))

    # The arrows are printed whenever the check could not settle them, which is
    # every consignment: the four cases of 5.2.1.10.1 turn on the kind of
    # packaging and the application does not know it. Printing them behind that
    # caveat beats withholding them — a packer who does need them would
    # otherwise have nothing, and the caption says in the provision's own terms
    # when they apply and when they are forbidden.
    arrows = LABELS / "ORIENTATION.png"
    if "orientation_arrows" in result.get("not_assessed", []) and arrows.exists():
        story.append(PageBreak())
        story.append(_p(f"{_t('arrows_mark', lang)} "
                        f"({_t('provision', lang)} 5.2.1.10.1)", styles["meta"]))
        story.append(Spacer(1, 4))
        story.append(_p(_t("arrows_only_if", lang), styles["fixed"]))
        story.append(_p(_t("arrows_size", lang), styles["fixed"]))
        story.append(Spacer(1, 6))
        story.append(_Figure(arrows, ARROWS_HEIGHT_MM))
    return story


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

    story.extend(_mark_pages(result, styles, lang))
    doc.build(story)
    return out_path
