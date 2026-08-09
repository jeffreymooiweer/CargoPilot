"""In welke taal een geplakte goederenregel is geschreven.

Dit bepaalt in welke taal de afgeleide omschrijving terugkomt — "Hoekprofiel
staal 80×80×8×6000", "Steel angle profile …" of "Stahl Winkelprofil …". Het is
een gok op trefwoorden en niet meer dan dat; de gebruiker kan de omschrijving
altijd overschrijven.

De herkenning van de materialen zelf loopt langs de synoniemenlijst van de
catalogus, en die kent nog geen Duitse termen. Wat deze detectie oplost is
alleen de taal van wat CargoPilot terugschrijft.
"""

KEYWORDS = {
    "nl": {"staal", "stalen", "hoekprofiel", "kokerprofiel", "gegalvaniseerd",
           "verzinkt", "hout", "beton", "aantal", "stuks", "lengte"},
    "en": {"steel", "angle", "profile", "galvanized", "galvanised", "wood",
           "concrete", "quantity", "length", "pieces"},
    # "verzinkt" en "beton" staan ook in de Nederlandse lijst. Dat is geen
    # fout maar een gelijkspel, en gelijkspel gaat naar het Nederlands.
    "de": {"stahl", "winkelprofil", "quadratrohr", "verzinkt", "holz", "beton",
           "menge", "stück", "länge", "blech", "träger", "rundstab"},
    # "beton" en "profil" komen in meer talen voor; ook hier geldt dat een
    # gelijkspel naar het Nederlands gaat.
    "fr": {"acier", "cornière", "tube", "galvanisé", "bois", "béton",
           "quantité", "longueur", "pièces", "tôle", "poutre", "profilé"},
}

# Bij gelijkspel wint de taal die het eerst staat: die waarin de gegevens het
# volledigst zijn.
_ORDER = ("nl", "en", "de", "fr")


def detect_language(text: str) -> str:
    lower = str(text or "").lower()
    counts = {lang: sum(1 for word in words if word in lower)
              for lang, words in KEYWORDS.items()}
    return max(_ORDER, key=lambda lang: (counts[lang], -_ORDER.index(lang)))
