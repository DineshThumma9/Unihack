_SYSTEM_PROMPT = """\
You are an expert industrial product data specialist.
Given a raw product description, manufacturer name, brand name, and web research evidence, enrich the product record by filling the requested fields.

Structured Attributes Rules:
- Extract all specifications into the `attributes` list as key-value objects: {"label": ..., "value": ..., "unit": ..., "evidence": ...}.
- `label`: Standard canonical attribute name in Title Case (e.g. 'Voltage Rating', 'Amperage Rating', 'Width', 'Length', 'Height', 'Weight', 'Material', 'Color', 'Grit', 'Mounting Type', 'Series', 'Sound Level', 'Number of Wash Cycles', 'Pack Quantity', 'Fitting Type').
- `value`: Clean attribute value string (e.g. '120', '1/2', 'Stainless Steel', '5', 'Leg'). Do NOT put the unit inside `value`.
- `unit`: Standard UOM abbreviation if applicable ('in', 'ft', 'V', 'A', 'W', 'lb', 'kg', 'dBA', 'psi', 'rpm'), or null for non-numeric/categorical attributes.
- `evidence`: EXACT quote or snippet from the product description or research evidence supporting this attribute.
- Every extracted attribute MUST have non-empty supporting evidence. Do NOT invent attributes without evidence.

Description & Taxonomy Rules:
- INVOICE_DESC: ALL CAPS, ≤ 40 characters, use abbreviations to fit
- MOBILE_DESC: 60–80 characters, Title Case, Brand + Type + Series + MPN
- SHORT_DESC: ~100–150 characters, Title Case, Brand® Series MPN Type, Key Attr
- LONG_DESC: 150–400 characters, full sentence, comma-separated specs
- RETAIL_DESC: 80–200 characters, natural conversational tone.
- MARKETING_DESCRIPTION: 100–300 characters, authentic benefit-driven copy.
- Classpath: use format "Category > Subcategory > Leaf Node" with Title Case
- TRADE_NAME: Leave null unless explicitly confirmed in Part_Desc or official manufacturer source. Do NOT invent product lines or generic terms (e.g. 'Detail File').
- UOM abbreviations: in, ft, V, A, W, lb, kg, dBA — no trailing period
- Country of origin: infer from brand if confident (Makita→Japan, Festool→Germany)
- If you cannot determine a value confidently, leave it as null
"""


# Every value that means "we don't know"
_PLACEHOLDERS: set[str] = {
    "--",
    "-",
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "-- no brand --",
    "",
}

# Known manufacturer-name → canonical brand name mapping
# (extracted from DIB_Brand / E1_Brand cross-analysis + domain knowledge)
_MANUF_TO_BRAND: dict[str, str] = {
    "freud inc": "Diablo",
    "black & decker/dewlt": "DEWALT",
    "black & decker": "DEWALT",
    "milwaukee accessory": "Milwaukee",
    "phillips lighting": "Philips",
    "satco prod inc": "Satco",
    "makita usa inc": "Makita",
    "festool usa": "Festool",
    "leviton mfg co": "Leviton",
    "southwire/g turner": "Southwire",
    "kichler lighting": "Kichler",
    "boise cascade building materials": "Boise Cascade",
    "parksite": "Parksite",
    "u s lumber": "US Lumber",
    "appliance dealers cooperative": None,  # distributor, not a brand
    "jam industrial supply llc": None,  # distributor, not a brand
    "v & v appliance parts inc": None,  # distributor, not a brand
    "tech gear 5.7 inc": "Tech Gear",
}

# Common abbreviation → full word (used for Part_Desc cleaning / display)
_ABBREV_MAP: dict[str, str] = {
    r"\bSS\b": "Stainless Steel",
    r"\bBRS\b": "Brass",
    r"\bAL\b": "Aluminum",
    r"\bCS\b": "Carbon Steel",
    r"\bGALV\b": "Galvanized",
    r"\bPVC\b": "PVC",
    r"\bSTL\b": "Steel",
    r"\bCPLG\b": "Coupling",
    r"\bRED\b": "Reducer",
    r"\bELL\b": "Elbow",
    r"\bNIPP?\b": "Nipple",
    r"\bHEX\b": "Hex",
    r"\bSCR\b": "Screw",
    r"\bSKT\b": "Socket",
    r"\bFLG\b": "Flange",
    r"\bCAP\b": "Cap",
    r"\bTEE\b": "Tee",
    r"\bUNION\b": "Union",
    r"\bPLUG\b": "Plug",
    r"\bBUSH\b": "Bushing",
    r"\bEXT\b": "Extension",
    r"\bINT\b": "Internal",
    r"\bFEM\b": "Female",
    r"\bMALE\b": "Male",
    r"\bNPT\b": "NPT",
    r"\bMNPT\b": "MNPT",
    r"\bFNPT\b": "FNPT",
    r"\b(\d+)PC\b": r"\1-Piece",
    r"\b(\d+)PCS\b": r"\1-Piece",
    r"\bPK\b": "Pack",
    r"\b#(\d+)\b": r"No. \1",  # 150# → No. 150
}

# Well-known brand prefixes that appear at the start of Part_Desc
_KNOWN_BRAND_PREFIXES: list[str] = [
    "3M",
    "DEWALT",
    "Milwaukee",
    "Makita",
    "Bosch",
    "Festool",
    "Philips",
    "Leviton",
    "Southwire",
    "Kichler",
    "Satco",
    "Diablo",
    "Freud",
    "Eaton",
    "Square D",
    "Hubbell",
    "Legrand",
    "GE",
    "Siemens",
    "Klein",
    "Fluke",
    "Ideal",
    "Greenlee",
    "Panduit",
    "Erico",
    "Simpson",
    "USG",
    "Georgia-Pacific",
    "LP",
    "James Hardie",
    "Trex",
    "TimberTech",
    "AZEK",
]


cols = {
    "manufacturer_name": "Manufacturer Name (parsed + inferred)",
    "manufacturer_code": "Manufacturer Code",
    "brand_name": "Brand Name (resolved)",
    "clean_desc": "Clean Description (MPN stripped)",
    "expanded_desc": "Expanded Description",
    "E1_Brand": "E1_Brand (original)",
    "DIB_Brand": "DIB_Brand (original)",
}
_AD_TRACKER_HOSTS = {
    "bing.com",
    "www.bing.com",
    "google.com",
    "www.google.com",
    "doubleclick.net",
    "adservice.google.com",
    "duckduckgo.com",
    "syndicatedsearch.goog",
    "adnxs.com",
    "advertising.com",
}


_MANUFACTURER_DOMAINS = {
    "3m.com",
    "diablotools.com",
    "mirka.com",
    "freud.com",
    "makitatools.com",
    "dewalt.com",
    "milwaukeetool.com",
}


# Marketplace domains excluded from manufacturer sourcing
_MARKETPLACE_DOMAINS = {
    "amazon.com",
    "ebay.com",
    "walmart.com",
    "homedepot.com",
    "lowes.com",
    "wayfair.com",
    "acehardware.com",
    "grainger.com",
    "zoro.com",
    "alibaba.com",
    "aliexpress.com",
}
