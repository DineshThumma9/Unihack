"""
preprocess.py - Deterministic cleaning and normalization of raw CSV input.
"""

from __future__ import annotations
import re
import pandas as pd
from constants import (
    _PLACEHOLDERS,
    _KNOWN_BRAND_PREFIXES,
    cols,
    _MANUF_TO_BRAND,
    _ABBREV_MAP,
)

_MANUF_RE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")

STRING_COLUMNS = {
    "Mfg_Part_Num",
    "Part_Desc",
    "E1_Brand",
    "Unilog_Brand",
    "DIB_Brand",
    "Part_Manuf",
    "manufacturer_name",
    "manufacturer_code",
    "brand_name",
    "clean_desc",
    "expanded_desc",
}


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(pd.isna(value))
    except TypeError, ValueError:
        return False


def _clean_string(value) -> str | None:
    if _is_missing(value):
        return None
    val_str = str(value).strip()
    return val_str if val_str else None


def _clean_required_string(value) -> str:
    return _clean_string(value) or ""


def _is_placeholder(value) -> bool:
    if _is_missing(value):
        return True
    return str(value).strip().lower() in _PLACEHOLDERS


def normalize_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    brand_cols = ["E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]
    for column in brand_cols:
        if column in df.columns:
            df[column] = df[column].map(
                lambda val: None if _is_placeholder(val) else _clean_string(val)
            )

    if "Unilog_Brand" in df.columns:
        df = df.drop(columns="Unilog_Brand")
    return df


def parse_manufacturer(value) -> tuple[str | None, str | None]:
    value = _clean_string(value)
    if value is None:
        return None, None
    match = _MANUF_RE.match(value)
    if match:
        return _clean_string(match.group(1)), _clean_string(match.group(2))
    return value, None


def add_manufacturer_columns(df: pd.DataFrame) -> pd.DataFrame:
    parsed = df["Part_Manuf"].map(parse_manufacturer)
    df["manufacturer_name"] = parsed.map(lambda val: val[0])
    df["manufacturer_code"] = parsed.map(lambda val: val[1])
    return df


_KNOWN_BRANDS = sorted(_KNOWN_BRAND_PREFIXES, key=len, reverse=True)


def _infer_manuf_from_desc(part_desc) -> str | None:
    desc = _clean_string(part_desc)
    if desc is None:
        return None
    upper_desc = desc.upper()
    for brand in _KNOWN_BRANDS:
        if upper_desc.startswith(brand.upper()):
            return brand
    return None


def _is_known_distributor(name) -> bool:
    name = _clean_string(name)
    if name is None:
        return False
    key = name.lower()
    return key in _MANUF_TO_BRAND and _MANUF_TO_BRAND[key] is None


def fill_missing_manufacturer(df: pd.DataFrame) -> pd.DataFrame:
    was_missing = df["manufacturer_name"].isna() | df["manufacturer_name"].map(
        _is_known_distributor
    )
    inferred = df.loc[was_missing, "Part_Desc"].map(_infer_manuf_from_desc)
    can_replace = was_missing & inferred.notna()
    df.loc[can_replace, "manufacturer_name"] = inferred[can_replace]
    df["manufacturer_inferred"] = can_replace

    # Ensure unresolved distributor names are cleared to None so LLM/Search can resolve real manufacturer
    still_distributor = df["manufacturer_name"].map(_is_known_distributor)
    df.loc[still_distributor, "manufacturer_name"] = None
    return df


def resolve_brand(row: pd.Series) -> str | None:
    val = _clean_string(row["E1_Brand"])
    if val is not None:
        return val
    val = _clean_string(row["DIB_Brand"])
    if val is not None:
        return val
    manufacturer = _clean_string(row["manufacturer_name"])
    if manufacturer:
        key = manufacturer.lower()
        if key in _MANUF_TO_BRAND:
            return _MANUF_TO_BRAND[key]
        return manufacturer
    return None


def add_brand_column(df: pd.DataFrame) -> pd.DataFrame:
    df["brand_name"] = df.apply(resolve_brand, axis=1)
    return df


def strip_mpn_from_desc(row: pd.Series) -> str:
    desc = _clean_required_string(row["Part_Desc"])
    mpn = _clean_required_string(row["Mfg_Part_Num"])
    if mpn and desc.startswith(mpn):
        return desc[len(mpn) :].lstrip(" -–—").strip()
    return desc


def add_clean_desc(df: pd.DataFrame) -> pd.DataFrame:
    df["clean_desc"] = df.apply(strip_mpn_from_desc, axis=1)
    return df


def expand_abbreviations(text) -> str:
    text = _clean_required_string(text)
    for pattern, replacement in _ABBREV_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def add_expanded_desc(df: pd.DataFrame) -> pd.DataFrame:
    df["expanded_desc"] = df["clean_desc"].map(expand_abbreviations)
    return df


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in STRING_COLUMNS:
        if column in df.columns:
            df[column] = df[column].map(_clean_string)
    if "manufacturer_inferred" in df.columns:
        df["manufacturer_inferred"] = (
            df["manufacturer_inferred"].fillna(False).astype(bool)
        )
    df = df.astype(object)
    df = df.where(pd.notna(df), None)
    return df


def validate_preprocessed_dataframe(df: pd.DataFrame) -> None:
    for column in df.columns:
        for index, value in df[column].items():
            if _is_missing(value):
                continue
            try:
                if pd.isna(value):
                    raise ValueError(
                        f"Unsafe missing value in {column}[{index}]: {value!r}"
                    )
            except TypeError, ValueError:
                pass

    required = {
        "Mfg_Part_Num",
        "Part_Desc",
        "E1_Brand",
        "DIB_Brand",
        "Part_Manuf",
        "manufacturer_name",
        "manufacturer_code",
        "brand_name",
        "clean_desc",
        "expanded_desc",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Preprocessing contract violated. Missing columns: {sorted(missing)}"
        )


def fill_rate_report(df: pd.DataFrame) -> None:
    total = len(df)
    print(f"\n{'Field':<45}{'Filled':>6}  {'%':>5}")
    print("─" * 60)
    for column, label in cols.items():
        if column in df.columns:
            filled = df[column].notna().sum()
            percentage = 100 * filled / total if total else 0
            print(f"{label:<45}{filled:>6}  {percentage:>4.0f}%")
    inferred = df.get("manufacturer_inferred", pd.Series(False, index=df.index))
    print(f"\n  Manufacturer inferred from Part_Desc:  {inferred.sum()} rows")
    unknown = df["manufacturer_name"].isna().sum()
    print(f"  Manufacturer still unknown:            {unknown} rows")


def preprocess(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, keep_default_na=True)
    print(f"Loaded {len(df)} rows")
    df = normalize_placeholders(df)
    df = add_manufacturer_columns(df)
    df = fill_missing_manufacturer(df)
    df = add_brand_column(df)
    df = add_clean_desc(df)
    df = add_expanded_desc(df)
    df = sanitize_dataframe(df)
    validate_preprocessed_dataframe(df)
    fill_rate_report(df)
    return df
