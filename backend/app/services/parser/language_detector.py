NL_KEYWORDS = {"staal", "stalen", "hoekprofiel", "kokerprofiel", "gegalvaniseerd", "verzinkt", "hout", "beton", "aantal", "stuks", "lengte"}
EN_KEYWORDS = {"steel", "angle", "profile", "galvanized", "galvanised", "wood", "concrete", "quantity", "length", "pieces"}


def detect_language(text: str) -> str:
    lower = text.lower()
    nl = sum(1 for k in NL_KEYWORDS if k in lower)
    en = sum(1 for k in EN_KEYWORDS if k in lower)
    return "nl" if nl >= en else "en"
