import re

PRODUCT_PATTERNS = {
    "angle_profile": [
        r"hoekprofiel", r"angle\s*profile", r"l[\s-]?profiel", r"l\s*profile",
    ],
    "square_tube": [
        r"kokerprofiel", r"square\s*tube", r"rectangular\s*tube", r"hollow\s*section", r"\bshs\b", r"\brhs\b",
    ],
    "round_tube": [r"\buis\b", r"\bpipe\b", r"\btube\b", r"ronde\s*buis"],
    "round_bar": [r"rond", r"round\s*bar", r"\bstaf\b"],
    "plate": [r"\bplaat\b", r"\bplate\b", r"\bstrip\b"],
    "beam": [r"\bbalk\b", r"\bbeam\b", r"\bplank\b", r"\bboard\b"],
    "standard_profile": [r"\bunp\b", r"\bupn\b", r"\bupe\b", r"\bipe\b", r"\bhea\b", r"\bheb\b", r"\bhem\b"],
    "concrete_slab": [r"stelconplaat", r"betonplaat", r"concrete\s*slab", r"gewapend\s*beton"],
    "plywood": [r"multiplex", r"plywood", r"\bosb\b", r"\bmdf\b", r"betonplex"],
    "pvc_pipe": [r"pvc\s*buis", r"pvc\s*pipe"],
    "plastic_sheet": [r"kunststof\s*plaat", r"plastic\s*sheet"],
}


def detect_product_type(text: str) -> str | None:
    lower = text.lower()
    for product_type, patterns in PRODUCT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return product_type
    return None
