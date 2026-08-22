"""
extractor.py - Regex attribute extraction from product descriptions.
"""

import re
from typing import Optional
from models import Attribute


def _first(pattern: str, text: str, flags=re.IGNORECASE) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


def _inch_frac_to_decimal(s: str) -> str:
    s = s.strip().lstrip(".")
    if s.startswith("."):
        s = "0" + s
    return s


def decimal_to_fraction(val: Optional[str]) -> Optional[str]:
    """Convert decimal dimension string (e.g. '0.5' or '4.25') to standard fractional inches."""
    if not val:
        return val
    val = val.strip()
    try:
        fval = float(val)
        if fval.is_integer():
            return str(int(fval))
        
        integer_part = int(fval)
        decimal_part = fval - integer_part
        
        # Round to nearest 64th
        closest_n = round(decimal_part * 64)
        if closest_n == 64:
            return str(integer_part + 1)
        if closest_n == 0:
            return str(integer_part) if integer_part > 0 else "0"
            
        import math
        gcd = math.gcd(closest_n, 64)
        num = closest_n // gcd
        den = 64 // gcd
        
        frac_str = f"{num}/{den}"
        return f"{integer_part}-{frac_str}" if integer_part > 0 else frac_str
    except ValueError:
        return val


# --- Pack Quantity & Selling UOM ---
_QTY_PATTERNS = [
    (
        r"(\d+)\s*(?:disc|sheet|roll|pad|blade|piece|pc|pcs)s?\s*/\s*(?:box|bx|bag|pk)",
        lambda m: (m.group(1), "BX"),
    ),
    (r"(\d+)\s*(?:pc|pcs)\b", lambda m: (m.group(1), "PK")),
    (r"(\d+)[\s\-]pack\b", lambda m: (m.group(1), "PK")),
    (r"(\d+)[\s\-]piece", lambda m: (m.group(1), "EA")),
    (r"(\d+)\s*pk\b", lambda m: (m.group(1), "PK")),
]

# --- Dimensions ---
_NUM = r"(?:\d+[-\s]\d+/\d+|\d+/\d+|\d*\.\d+|\d+)"
_IN_MARKER = r"(?:\"|in\.?|\"|\')?\s*"

def extract_quantity(desc: str) -> tuple[Optional[str], Optional[str]]:
    for pattern, handler in _QTY_PATTERNS:
        m = _first(pattern, desc)
        if m:
            qty, uom = handler(m)
            return qty, uom
    return None, None


def _parse_num(s: str) -> str:
    return _inch_frac_to_decimal(s.strip())


def extract_dimensions(desc: str) -> list[Attribute]:
    attrs: list[Attribute] = []

    # Three-part: D x T x Arbor (e.g. 4-1/2"x.045"x7/8")
    m = re.search(
        rf"({_NUM}){_IN_MARKER}[xX×]{_IN_MARKER}({_NUM}){_IN_MARKER}[xX×]{_IN_MARKER}({_NUM})",
        desc,
        re.IGNORECASE,
    )
    if m:
        ev = f"Matched '{m.group(0)}' in raw product description"
        attrs.append(
            Attribute(label="Diameter", value=_parse_num(m.group(1)), uom="in", evidence=ev)
        )
        attrs.append(
            Attribute(label="Thickness", value=_parse_num(m.group(2)), uom="in", evidence=ev)
        )
        attrs.append(
            Attribute(label="Arbor Size", value=_parse_num(m.group(3)), uom="in", evidence=ev)
        )
        return attrs

    # Two-part: W x L (e.g. 1/2"x18", 2.75x30)
    m = re.search(
        rf"({_NUM}){_IN_MARKER}[xX×]{_IN_MARKER}({_NUM})", desc, re.IGNORECASE
    )
    if m:
        ev = f"Matched '{m.group(0)}' in raw product description"
        w, l = _parse_num(m.group(1)), _parse_num(m.group(2))
        attrs.append(Attribute(label="Width", value=w, uom="in", evidence=ev))
        attrs.append(Attribute(label="Length", value=l, uom="in", evidence=ev))
        return attrs

    # Standalone size (e.g. 6-1/2")
    m = re.search(rf"({_NUM})(?:\"|\bin\b)", desc, re.IGNORECASE)
    if m:
        ev = f"Matched '{m.group(0)}' in raw product description"
        attrs.append(Attribute(label="Size", value=_parse_num(m.group(1)), uom="in", evidence=ev))

    return attrs


# --- Electrical Specs ---
def extract_electrical(desc: str) -> list[Attribute]:
    attrs: list[Attribute] = []

    m = re.search(r"(?<!\d)(\d{2,3})\s*[Vv](?!\w)", desc)
    if m:
        v = int(m.group(1))
        if v in {12, 24, 48, 100, 110, 115, 120, 125, 208, 220, 230, 240, 277, 480}:
            ev = f"Matched '{m.group(0)}' in raw product description"
            attrs.append(Attribute(label="Voltage Rating", value=m.group(1), uom="V", evidence=ev))

    m = re.search(r"(?:^|[\s\-])(\d{1,3})\s*[Aa](?:\b|mp)", desc)
    if m:
        a = int(m.group(1))
        if a in {1, 2, 3, 5, 6, 10, 12, 13, 15, 20, 25, 30, 40, 50, 60, 100}:
            ev = f"Matched '{m.group(0)}' in raw product description"
            attrs.append(Attribute(label="Amperage Rating", value=m.group(1), uom="A", evidence=ev))

    m = re.search(r"(?:^|[\s\-])(\d+)\s*[Ww](?:att|atts)?(?:\b|/)", desc)
    if m:
        w = int(m.group(1))
        if 1 <= w <= 10000:
            ev = f"Matched '{m.group(0)}' in raw product description"
            attrs.append(Attribute(label="Wattage", value=m.group(1), uom="W", evidence=ev))

    return attrs


# --- Abrasive Grit ---
def extract_grit(desc: str) -> list[Attribute]:
    attrs: list[Attribute] = []

    # ISO grit: P80, P120, P150
    m = re.search(r"\bP\s*(\d{2,3})\b", desc, re.IGNORECASE)
    if m:
        ev = f"Matched '{m.group(0)}' in raw product description"
        attrs.append(Attribute(label="Grit", value=m.group(1), uom=None, evidence=ev))
        return attrs

    # CAMI grit: 80-Grit, 120 Grit
    m = re.search(r"\b(\d{2,3})[\s\-]grit\b", desc, re.IGNORECASE)
    if m:
        ev = f"Matched '{m.group(0)}' in raw product description"
        attrs.append(Attribute(label="Grit", value=m.group(1), uom=None, evidence=ev))

    return attrs


# --- Canonical Attribute Label Normalization ---
CANONICAL_LABEL_MAP: dict[str, str] = {
    # Electrical
    "voltage": "Voltage Rating",
    "voltage rating": "Voltage Rating",
    "volts": "Voltage Rating",
    "voltage (v)": "Voltage Rating",
    "amperage": "Amperage Rating",
    "amperage rating": "Amperage Rating",
    "amps": "Amperage Rating",
    "current": "Amperage Rating",
    "wattage": "Wattage",
    "watts": "Wattage",
    "power rating": "Wattage",
    "plug type": "Plug Type",

    # Dimensions & Physical
    "width": "Width",
    "item width": "Width",
    "product width": "Width",
    "overall width": "Width",
    "length": "Length",
    "item length": "Length",
    "product length": "Length",
    "overall length": "Length",
    "height": "Height",
    "item height": "Height",
    "product height": "Height",
    "overall height": "Height",
    "depth": "Depth",
    "depth with door open": "Depth With Door Open",
    "minimum height": "Minimum Height",
    "maximum height": "Maximum Height",
    "min height": "Minimum Height",
    "max height": "Maximum Height",
    "size": "Size",
    "diameter": "Diameter",
    "outer diameter": "Diameter",
    "thickness": "Thickness",
    "arbor size": "Arbor Size",
    "arbor": "Arbor Size",
    "weight": "Weight",
    "item weight": "Weight",

    # Abrasives & Tools
    "grit": "Grit",
    "grit size": "Grit",
    "abrasive grit": "Grit",
    "fepa grit": "Grit",
    "cami grit": "Grit",

    # General Product Features
    "series": "Series",
    "product series": "Series",
    "model": "Model",
    "model number": "Model",
    "mounting": "Mounting Type",
    "mounting type": "Mounting Type",
    "mounting style": "Mounting Type",
    "sound level": "Sound Level",
    "noise level": "Sound Level",
    "wash cycles": "Number of Wash Cycles",
    "number of wash cycles": "Number of Wash Cycles",
    "material": "Material",
    "body material": "Material",
    "construction material": "Material",
    "color": "Color",
    "finish": "Finish",
    "color/finish": "Color",
    "pack quantity": "Pack Quantity",
    "package quantity": "Pack Quantity",
    "pack qty": "Pack Quantity",
    "thread size": "Thread Size",
    "fitting type": "Fitting Type",
    "connection type": "Fitting Type",
    "additional information": "Additional Information",
}


def normalize_attribute_label(label: str) -> str:
    if not label:
        return ""
    clean_key = label.strip().lower()
    return CANONICAL_LABEL_MAP.get(clean_key, label.strip().title())


def normalize_attribute(attr: Attribute) -> Optional[Attribute]:
    if not attr or not attr.label or not attr.value:
        return None
    
    label = normalize_attribute_label(attr.label)
    value = str(attr.value).strip()
    uom = attr.uom.strip() if attr.uom else None
    evidence = attr.evidence.strip() if attr.evidence else None
    
    if not label or not value:
        return None

    # Convert decimal inches to fractional inches if UOM is 'in'
    if uom == "in":
        value = decimal_to_fraction(value) or value
        
    return Attribute(
        label=label,
        value=value,
        uom=uom,
        evidence=evidence,
    )


# --- Entry Point ---
def extract_attributes(desc: str) -> list[Attribute]:
    attrs: list[Attribute] = []
    attrs.extend(extract_dimensions(desc))
    attrs.extend(extract_electrical(desc))
    attrs.extend(extract_grit(desc))
    normalized = []
    for a in attrs:
        norm = normalize_attribute(a)
        if norm:
            normalized.append(norm)
    return normalized


def extract_commerce(desc: str) -> tuple[Optional[str], Optional[str]]:
    return extract_quantity(desc)
