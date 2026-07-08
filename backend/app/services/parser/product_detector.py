import re

PRODUCT_PATTERNS = {
    "angle_profile": [
        r"hoekprofiel", r"hoeklijn", r"hoekstaal", r"hoekijzer", r"hoekstrip",
        r"angle\s*profile", r"angle\s*iron", r"angle\s*bar", r"angle\s*steel",
        r"l[\s-]?profiel", r"l\s*profile", r"corner\s*profile",
    ],
    "square_tube": [
        r"kokerprofiel", r"\bkoker\b", r"square\s*tube", r"rectangular\s*tube",
        r"hollow\s*section", r"\bshs\b", r"\brhs\b", r"vierkant\s*koker",
        r"rechthoekig(?:e)?\s*koker", r"box\s*section",
    ],
    "round_tube": [
        r"\bbuis\b", r"\bpipe\b", r"\btube\b", r"ronde\s*buis", r"ronde\s*pijp",
        r"stalen\s*buis", r"steel\s*pipe", r"steel\s*tube", r"\bchs\b",
    ],
    "round_bar": [
        r"ronde\s*staf", r"rond\s*staal", r"rondijzer", r"round\s*bar",
        r"round\s*steel", r"round\s*rod", r"\brond\b", r"\bstaf\b",
    ],
    "plate": [
        r"\bplaat\b", r"\bplate\b", r"\bstrip\b", r"plaatstaal", r"vlakstaal",
        r"flat\s*bar", r"stalen\s*plaat", r"steel\s*plate", r"stripstaal",
    ],
    "beam": [r"\bbalk\b", r"\bbeam\b", r"\bplank\b", r"\bboard\b", r"i[\s-]?balk", r"dwarsbalk"],
    "standard_profile": [
        r"\bunp\b", r"\bupn\b", r"\bupe\b", r"\bipe\b", r"\bhea\b", r"\bheb\b", r"\bhem\b",
        r"\bipn\b", r"\binp\b", r"u[\s-]?profiel", r"i[\s-]?profiel",
    ],
    "concrete_slab": [
        r"stelconplaat", r"\bstelcon\b", r"betonplaat", r"concrete\s*slab",
        r"gewapend\s*beton", r"beton\s*plaat", r"betonblok",
    ],
    "plywood": [
        r"multiplex", r"plywood", r"\bosb\b", r"\bmdf\b", r"betonplex",
        r"triplex", r"timmerplaat", r"plaatmateriaal",
    ],
    "pvc_pipe": [r"pvc\s*buis", r"pvc\s*pipe", r"kunststof\s*buis", r"plastic\s*buis"],
    "plastic_sheet": [
        r"kunststof\s*plaat", r"plastic\s*sheet", r"plastic\s*plaat",
        r"plexiglas\s*plaat", r"plexiglas", r"\bpmma\b",
    ],
}


def detect_product_type(text: str) -> str | None:
    lower = text.lower()
    for product_type, patterns in PRODUCT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return product_type
    return None
