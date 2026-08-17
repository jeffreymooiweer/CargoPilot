import re

PRODUCT_PATTERNS = {
    "angle_profile": [
        r"hoekprofiel", r"hoeklijn", r"hoekstaal", r"hoekijzer", r"hoekstrip",
        r"angle\s*profile", r"angle\s*iron", r"angle\s*bar", r"angle\s*steel",
        r"l[\s-]?profiel", r"l\s*profile", r"corner\s*profile",
        r"winkelprofil", r"winkelstahl", r"winkeleisen", r"l[\s-]?profil\b",
    ],
    "square_tube": [
        r"kokerprofiel", r"\bkoker\b", r"square\s*tube", r"rectangular\s*tube",
        r"hollow\s*section", r"\bshs\b", r"\brhs\b", r"vierkant\s*koker",
        r"rechthoekig(?:e)?\s*koker", r"box\s*section",
        r"quadratrohr", r"rechteckrohr", r"vierkantrohr", r"hohlprofil",
    ],
    "round_tube": [
        r"\bbuis\b", r"\bbuizen\b", r"\bpipe\b", r"\bpipes\b", r"\btube\b",
        r"\btubes\b", r"ronde\s*bui(?:s|zen)", r"ronde\s*pijp",
        r"stalen\s*bui(?:s|zen)", r"steel\s*pipes?", r"steel\s*tubes?", r"\bchs\b",
        # Not a bare r"\brohr\b": that would swallow a PVC pipe as well.
        r"rundrohr", r"stahlrohr",
    ],
    "round_bar": [
        r"ronde\s*staf", r"rond\s*staal", r"rondijzer", r"round\s*bar",
        r"round\s*steel", r"round\s*rod", r"\brond\b", r"\bstaf\b",
        r"rundstab", r"rundstahl", r"rundeisen",
    ],
    "plate": [
        # Plural forms carry their own word boundaries: a hundred "platen"
        # never contains the singular "plaat", and went unrecognised for it.
        r"\bplaat\b", r"\bplaten\b", r"\bplate\b", r"\bplates\b",
        r"\bstrip\b", r"plaatstaal", r"vlakstaal",
        r"flat\s*bar", r"stalen\s*pla(?:at|ten)", r"steel\s*plates?", r"stripstaal",
        r"stahlblech", r"\bblech\b", r"\bbleche\b", r"flachstahl", r"flacheisen",
    ],
    "beam": [
        r"\bbalk\b", r"\bbeam\b", r"\bbeams\b", r"\bplank\b", r"\bplanken\b",
        r"\bboard\b", r"\bboards\b", r"i[\s-]?balk", r"dwarsbalk",
        r"\bträger\b", r"\bbalken\b", r"\bbohle\b", r"\bbohlen\b",
        r"\bbrett\b", r"\bbretter\b",
    ],
    "standard_profile": [
        r"\bunp\b", r"\bupn\b", r"\bupe\b", r"\bipe\b", r"\bhea\b", r"\bheb\b", r"\bhem\b",
        r"\bipn\b", r"\binp\b", r"u[\s-]?profiel", r"i[\s-]?profiel",
    ],
    "concrete_slab": [
        r"stelconplaat", r"\bstelcon\b", r"betonplaat", r"concrete\s*slab",
        r"gewapend\s*beton", r"beton\s*plaat", r"betonblok",
        r"betonplatte", r"stahlbeton", r"betonblock",
    ],
    "plywood": [
        r"multiplex", r"plywood", r"\bosb\b", r"\bmdf\b", r"betonplex",
        r"triplex", r"timmerplaat", r"plaatmateriaal",
        r"sperrholz", r"spanplatte", r"tischlerplatte",
    ],
    "pvc_pipe": [
        r"pvc\s*buis", r"pvc\s*pipe", r"kunststof\s*buis", r"plastic\s*buis",
        r"pvc[\s-]*rohr", r"kunststoffrohr",
    ],
    "plastic_sheet": [
        r"kunststof\s*plaat", r"plastic\s*sheet", r"plastic\s*plaat",
        r"plexiglas\s*plaat", r"plexiglas", r"\bpmma\b",
        r"kunststoffplatte", r"acrylglas",
    ],
}


def detect_product_type(text: str) -> str | None:
    lower = text.lower()
    for product_type, patterns in PRODUCT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return product_type
    return None
