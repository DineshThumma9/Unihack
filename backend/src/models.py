from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ══════════════════════════════════════════════════════════════
#  PRIMITIVE BUILDING BLOCKS
# ══════════════════════════════════════════════════════════════


class Attribute(BaseModel):
    """
    A single structured product attribute consisting of a label, its value,
    an optional unit of measure, and supporting evidence.
    """

    label: Optional[str] = Field(
        default=None,
        description=(
            "The attribute name / property label in canonical Title Case. "
            "Examples: 'Voltage Rating', 'Amperage Rating', 'Width', 'Material', 'Color', "
            "'Thread Size', 'Grit', 'Pack Quantity', 'Fitting Type', 'Mounting Type', 'Series'."
        ),
    )
    value: Optional[str] = Field(
        default=None,
        description=(
            "The attribute value as a string. Use numeric strings for quantities "
            "(e.g. '120', '1/2', '6'). Use Title Case for categorical values "
            "(e.g. 'Stainless Steel', 'Black', 'Female'). "
            "Do NOT include the unit here — put that in uom/unit."
        ),
    )
    uom: Optional[str] = Field(
        default=None,
        alias="unit",
        description=(
            "Unit of measure using standard abbreviations. Leave None for "
            "non-numeric or dimensionless values. "
            "Common approved abbreviations: in, ft, mm, cm, m, "
            "V, A, W, Hz, dBA, lb, kg, oz, g, gal, L, fl oz, "
            "rpm, psi, BTU, cu ft, sq ft."
        ),
    )
    evidence: Optional[str] = Field(
        default=None,
        description=(
            "Direct quote, snippet, or source reference from the product input or web evidence "
            "that explicitly supports this attribute."
        ),
    )
    source: str = Field(
        default="LLM",
        exclude=True,
    )

    model_config = ConfigDict(populate_by_name=True)

    @property
    def unit(self) -> Optional[str]:
        return self.uom


# ══════════════════════════════════════════════════════════════
#  INPUT MODEL  (raw catalogue row — 6 columns)
# ══════════════════════════════════════════════════════════════


class Product(BaseModel):
    """
    Raw input row exactly as it comes from the distributor CSV.
    Do NOT modify these fields — they are read-only pass-through values.
    Treat placeholder strings like '-- Unbranded --', '-- No Unilog Brand --',
    '-- No DIB Brand --' as equivalent to None / missing.
    """

    mfg_part_num: Optional[str] = Field(
        default=None,
        description="Manufacturer's own part number. Treat as the primary product identifier.",
    )
    part_desc: Optional[str] = Field(
        default=None,
        description=(
            "Raw, abbreviated product description from the distributor. "
            "Often starts with the MPN. Contains cryptic abbreviations "
            "(SS=Stainless Steel, BRS=Brass, CPLG=Coupling, etc.). "
            "This is your primary source for all enrichment tasks."
        ),
    )
    e1_brand: Optional[str] = Field(
        default=None,
        description="Brand name as recorded in the E1 system. Treat placeholder strings as None.",
    )
    unilog_brand: Optional[str] = Field(
        default=None,
        description="Unilog internal brand field — always a placeholder, ignore it.",
    )
    dib_brand: Optional[str] = Field(
        default=None,
        description="Brand name from the DIB system. Treat placeholder strings as None.",
    )
    part_manuf: Optional[str] = Field(
        default=None,
        description=(
            "Manufacturer or distributor name with internal code in parentheses, "
            "e.g. 'Freud Inc (2435)'. Note: this may be a *distributor*, not the "
            "actual product manufacturer — cross-check with part_desc."
        ),
    )


# ══════════════════════════════════════════════════════════════
#  OUTPUT SUB-MODELS
# ══════════════════════════════════════════════════════════════


class ProductSources(BaseModel):
    """
    URLs pointing to the manufacturer's own website and reference pages.
    Only use manufacturer-official sources (manufacturer.com). Do NOT use
    marketplaces (Amazon, eBay) or distributor sites as sources.
    """

    mfr_url: Optional[str] = Field(
        default=None,
        description=(
            "Primary URL from the manufacturer's official website for this product. "
            "Must be a direct product page, not a home page or search result. "
            "Example: 'https://www.diablotools.com/products/dcb518asts06g'"
        ),
    )
    ref_urls: List[Optional[str]] = Field(
        default_factory=lambda: [None] * 5,
        description=(
            "Up to 5 additional reference URLs from the manufacturer's official site "
            "that were used to enrich this record (spec sheets, category pages, etc.). "
            "Each element is a URL string or None. Never use distributor or marketplace URLs."
        ),
    )


class ProductIDs(BaseModel):
    """
    Internal taxonomy IDs assigned to this product record, plus the original
    raw input fields passed through unchanged.
    """

    part_number: Optional[str] = Field(
        default=None,
        description="Internal system part number assigned to this record.",
    )
    dept: Optional[str] = Field(
        default=None,
        description=(
            "Top-level department / division. Broad product category. "
            "Examples: 'Electrical', 'Plumbing', 'Tools', 'Building Materials', "
            "'Lighting', 'Appliances'."
        ),
    )
    class_: Optional[str] = Field(
        default=None,
        alias="class",
        description=(
            "Mid-level product class within the department. "
            "Examples: 'Abrasives', 'Wire & Cable', 'Pipe Fittings', 'Power Tools'."
        ),
    )
    fine: Optional[str] = Field(
        default=None,
        description=(
            "Fine / leaf-level product category. Most specific classification. "
            "Examples: 'Sanding Belts', 'NM Cable', 'Couplings', 'Angle Grinders'."
        ),
    )
    sku: Optional[str] = Field(
        default=None,
        description="Distributor's own SKU / stock-keeping unit number for this product.",
    )
    # Pass-through raw input fields
    mfg_part_num: Optional[str] = Field(
        default=None, description="Pass-through: raw Mfg_Part_Num from input CSV."
    )
    part_desc: Optional[str] = Field(
        default=None, description="Pass-through: raw Part_Desc from input CSV."
    )
    e1_brand: Optional[str] = Field(
        default=None, description="Pass-through: raw E1_Brand from input CSV."
    )
    unilog_brand: Optional[str] = Field(
        default=None, description="Pass-through: raw Unilog_Brand from input CSV."
    )
    dib_brand: Optional[str] = Field(
        default=None, description="Pass-through: raw DIB_Brand from input CSV."
    )
    part_manuf: Optional[str] = Field(
        default=None, description="Pass-through: raw Part_Manuf from input CSV."
    )

    model_config = {"populate_by_name": True}


class ProductIdentity(BaseModel):
    """
    Canonical product identity fields after normalization.
    These must use official, correctly-cased names — not the raw supplier strings.
    """

    manufacturer_name: Optional[str] = Field(
        default=None,
        description=(
            "Canonical legal name of the product MANUFACTURER (not the distributor). "
            "Use proper casing including legal suffixes: Inc, LLC, Ltd, Co. "
            "Include trademark symbols where applicable: ®, ™. "
            "Example: 'Freud Inc', '3M Company', 'Milwaukee Tool'. "
            "If part_manuf is a distributor, identify the real manufacturer from part_desc."
        ),
    )
    brand_name: Optional[str] = Field(
        default=None,
        description=(
            "The consumer-facing BRAND name sold under (may differ from manufacturer). "
            "Use exact registered casing. "
            "Examples: 'DEWALT', 'Diablo', 'Philips', 'Milwaukee', 'Cubitron II'. "
            "If no distinct brand exists, use the manufacturer name."
        ),
    )
    trade_name: Optional[str] = Field(
        default=None,
        description=(
            "Product line, series, or trademark name within the brand. "
            "Examples: 'Cubitron II', 'CleanBoost', 'Professional Series', "
            "'REDLITHIUM', 'Stikit'. Leave None if no distinct trade name exists."
        ),
    )
    manufacturer_part_number: Optional[str] = Field(
        default=None,
        description=(
            "The exact part number as published by the manufacturer on their website. "
            "Usually identical to Mfg_Part_Num but confirm against manufacturer source. "
            "Preserve exact casing and punctuation."
        ),
    )
    alternate_part_number: Optional[str] = Field(
        default=None,
        description=(
            "Any additional part numbers for this product (superseded MPNs, "
            "OEM equivalents, UPC-based identifiers). Separate multiple values "
            "with a pipe: 'ALT-001 | ALT-002'. Leave None if unknown."
        ),
    )
    classpath: Optional[str] = Field(
        default=None,
        description=(
            "Full product taxonomy path using ' > ' as separator. "
            "Must have at least 2 levels, ideally 3. Use Title Case. "
            "Examples: "
            "'Abrasives > Coated Abrasives > Sanding Belts', "
            "'Electrical > Wiring Devices > Outlets & Receptacles', "
            "'Plumbing > Pipe Fittings > Couplings', "
            "'Lighting > LED Bulbs > A-Series Bulbs'."
        ),
    )


class ProductDescription(BaseModel):
    """
    Human-readable product descriptions written for five different contexts
    and character-length targets. Each variant must describe the SAME product
    but formatted differently for its intended use.
    """

    invoice_desc: Optional[str] = Field(
        default=None,
        description=(
            "INVOICE / TILL RECEIPT description. "
            "Rules: ALL UPPERCASE, maximum 40 characters (including spaces), "
            "use standard abbreviations to fit (e.g. SS=Stainless Steel, "
            "1/2=half inch, PC=piece, W=wide, D=deep, H=high). "
            "Format: ITEM-TYPE KEY-SPEC KEY-SPEC ... "
            "Example: 'SANDING BELT 1/2X18 6PC' (22 chars) "
            "Example: 'DISHWASHER LEG 5 SST 120V 15A 50-1/4IN' (39 chars)"
        ),
    )
    mobile_desc: Optional[str] = Field(
        default=None,
        description=(
            "MOBILE APP / SEARCH RESULTS description. "
            "Rules: 60–80 characters (including spaces), Title Case, "
            "include Brand + key product type + 1-2 key specs + MPN. "
            "Format: 'Brand Manufacturer, Product Type, Series, MPN' "
            "Example: 'Rheem Manufacturing FRIGIDAIRE, Dishwasher, Professional Series, PDSH4816AF' (75 chars)"
        ),
    )
    short_desc: Optional[str] = Field(
        default=None,
        description=(
            "PRODUCT PAGE TITLE / SHORT description. "
            "Rules: ~100-150 characters, Title Case, "
            "format: Brand® Series MPN ItemType With KeyAttribute1, KeyAttribute2. "
            "Include trademark symbols (®, ™) where applicable. "
            "Example: 'FRIGIDAIRE® Professional Series PDSH4816AF Dishwasher "
            "With CleanBoost™, Leg Mounting, 5-Wash Cycle, Stainless Steel'"
        ),
    )

    @field_validator("invoice_desc", mode="before")
    @classmethod
    def truncate_invoice_desc(cls, v: Any) -> Any:
        if isinstance(v, str) and len(v) > 40:
            return v[:40].strip()
        return v

    @field_validator("mobile_desc", mode="before")
    @classmethod
    def truncate_mobile_desc(cls, v: Any) -> Any:
        if isinstance(v, str) and len(v) > 80:
            return v[:77].strip() + "..."
        return v

    long_desc: Optional[str] = Field(
        default=None,
        description=(
            "FULL PRODUCT PAGE description. "
            "Rules: Complete sentence paragraph, 150-400 characters, Title Case, "
            "list key specs separated by commas, include voltage/amperage/dimensions "
            "where applicable. Include brand® at the start. "
            "Use approved UOM abbreviations (in, V, A, dBA, lb). "
            "Example: 'FRIGIDAIRE® Dishwasher With CleanBoost™, Professional Series, "
            "5 Wash Cycles, 120 V, 15 A, Leg Mounting, 24 in W x 24-1/4 in D, "
            "50-1/4 in Depth With Door Open, 47 dBA Sound Level, Stainless Steel'"
        ),
    )
    retail_desc: Optional[str] = Field(
        default=None,
        description=(
            "RETAIL / E-COMMERCE listing description. "
            "Conversational, natural tone, 80-200 characters, highlights top 2-3 "
            "customer benefits. Title Case. Write naturally"
        ),
    )
    marketing_description: Optional[str] = Field(
        default=None,
        description=(
            "MARKETING / PROMOTIONAL description. "
            "Engaging, authentic benefit-focused language, 100-300 characters. "
            "Emphasize technical performance and key specs. Title Case. "
        ),
    )


class ProductFeatures(BaseModel):
    """
    Bullet-point features and compliance/application metadata.
    """

    item_features: List[Optional[str]] = Field(
        default_factory=lambda: [None] * 20,
        description=(
            "Up to 20 bullet-point product features. Each bullet should be a concise, "
            "standalone sentence or phrase (max ~120 chars each) describing a distinct "
            "feature, benefit, or specification. Start each bullet with a capital letter. "
            "Fill from index 0 upward; leave trailing entries as None. "
            "Example bullets: "
            "'Aluminum oxide abrasive for long cutting life', "
            "'Fits standard 1/2 in x 18 in belt sanders', "
            "'6-pack for extended use without frequent replacement'."
        ),
    )
    with_: Optional[str] = Field(
        default=None,
        description=(
            "Proprietary technology, feature name, or included component that "
            "distinguishes this product. Often a brand trademark feature. "
            "Example: 'CleanBoost™ Technology', 'REDLITHIUM Battery System'."
        ),
    )
    standards_approvals: Optional[str] = Field(
        default=None,
        description=(
            "Certifications, standards, and regulatory approvals this product meets. "
            "Examples: 'UL Listed', 'CSA Certified', 'ENERGY STAR', 'ANSI', "
            "'ISO 9001', 'RoHS Compliant', 'CE Marked'. "
            "Separate multiple values with commas."
        ),
    )
    prop_65: Optional[str] = Field(
        default=None,
        description=(
            "California Proposition 65 warning if applicable. "
            "Use 'Yes' if a Prop 65 warning applies, 'No' if confirmed safe, "
            "None if unknown."
        ),
    )
    application: Optional[str] = Field(
        default=None,
        description=(
            "Intended use cases, compatible surfaces, or application environments. "
            "Examples: 'Wood, Metal, Plastic surfaces', "
            "'Residential and light commercial use', 'Indoor/Outdoor'."
        ),
    )
    includes: Optional[str] = Field(
        default=None,
        description=(
            "List of items included in the package/box beyond the main product. "
            "Examples: 'Mounting hardware', 'Installation manual', "
            "'2 AA batteries', 'Carrying case'. "
            "Leave None if product ships alone with no extras."
        ),
    )
    product_name: Optional[str] = Field(
        default=None,
        description=(
            "Short, clean product display name without brand prefix. "
            "Title Case. Usually the item type + key differentiator. "
            "Examples: 'Sanding Belt', 'Built-In Dishwasher', '15A Duplex Receptacle'."
        ),
    )


class ProductAttributes(BaseModel):
    """
    Up to 50 structured attribute triplets. Extract all measurable and
    categorical properties from the product description and manufacturer data.
    Common attributes include: Material, Color, Voltage, Amperage, Width,
    Length, Height, Weight, Grit, Thread Size, Fitting Type, Pack Quantity,
    Mounting Type, Finish, Series, Watts, Lumens, etc.
    Only include attributes you can confidently identify — do not guess.
    """

    attributes: List[Attribute] = Field(
        default_factory=lambda: [Attribute() for _ in range(50)],
        description=(
            "List of up to 50 Attribute objects (label/value/uom). "
            "Fill from index 0 upward. Leave trailing entries as empty Attribute(). "
            "Each attribute must have at least label and value. "
            "uom is required for any numeric/dimensional value."
        ),
    )


class ProductCommerce(BaseModel):
    """
    Barcodes, classification codes, pricing and packaging information.
    """

    upc: Optional[str] = Field(
        default=None,
        description="12-digit Universal Product Code barcode. Digits only, no dashes.",
    )
    ean: Optional[str] = Field(
        default=None,
        description="13-digit International Article Number barcode. Digits only, no dashes.",
    )
    gtin: Optional[str] = Field(
        default=None,
        description="14-digit Global Trade Item Number. Digits only, no dashes.",
    )
    unspsc: Optional[str] = Field(
        default=None,
        description=(
            "United Nations Standard Products and Services Code. "
            "8-digit numeric code formatted as XX-XX-XX-XX (with dashes) or XXXXXXXX. "
            "Example: '27112700' for Power Hand Tools."
        ),
    )
    warranty: Optional[str] = Field(
        default=None,
        description=(
            "Manufacturer warranty duration and terms. "
            "Examples: '1 Year Limited', '5 Year Manufacturer Warranty', "
            "'Lifetime Guarantee'. Leave None if not stated."
        ),
    )
    list_price: Optional[str] = Field(
        default=None,
        description="Manufacturer suggested retail price as a string. Example: '24.99'. Leave None if unknown.",
    )
    selling_qty: Optional[str] = Field(
        default=None,
        description=(
            "Quantity per sellable unit (how many pieces in the package sold). "
            "Numeric string. Example: '6' for a 6-pack, '1' for a single item, "
            "'50' for a box of 50."
        ),
    )
    selling_uom: Optional[str] = Field(
        default=None,
        description=(
            "Unit in which this product is sold. "
            "Examples: 'EA' (each), 'BX' (box), 'PK' (pack), "
            "'CS' (case), 'PR' (pair), 'BG' (bag), 'RL' (roll)."
        ),
    )
    standard_packaging_info: Optional[str] = Field(
        default=None,
        description=(
            "Distributor/manufacturer standard packaging details. "
            "Example: 'Master Pack: 12 | Inner Pack: 6 | Each: 1'."
        ),
    )


class ProductDimensions(BaseModel):
    """
    Physical shipping/product dimensions and weight.
    All values are numeric strings. All UOMs use standard abbreviations.
    """

    length: Optional[str] = Field(
        default=None,
        description="Product or package length as a numeric string. Example: '18', '24-1/4'.",
    )
    length_uom: Optional[str] = Field(
        default=None,
        description="Unit for length. Use: 'in', 'ft', 'mm', 'cm', 'm'.",
    )
    height: Optional[str] = Field(
        default=None,
        description="Product or package height as a numeric string. Example: '50.25', '12'.",
    )
    height_uom: Optional[str] = Field(
        default=None,
        description="Unit for height. Use: 'in', 'ft', 'mm', 'cm', 'm'.",
    )
    width: Optional[str] = Field(
        default=None,
        description="Product or package width as a numeric string. Example: '24', '0.5'.",
    )
    width_uom: Optional[str] = Field(
        default=None,
        description="Unit for width. Use: 'in', 'ft', 'mm', 'cm', 'm'.",
    )
    weight: Optional[str] = Field(
        default=None,
        description="Product or package weight as a numeric string. Example: '5.2', '0.75'.",
    )
    weight_uom: Optional[str] = Field(
        default=None,
        description="Unit for weight. Use: 'lb', 'oz', 'kg', 'g'.",
    )
    volume: Optional[str] = Field(
        default=None,
        description="Package volume as a numeric string. Example: '1.5'.",
    )
    volume_uom: Optional[str] = Field(
        default=None,
        description="Unit for volume. Use: 'cu ft', 'cu in', 'L', 'ml', 'gal'.",
    )


class ProductAssets(BaseModel):
    """
    URLs to digital assets: product images, compliance documents, and videos.
    All URLs must be direct links from the manufacturer's official website.
    """

    product_image: Optional[str] = Field(
        default=None,
        description="URL of the primary product image from the manufacturer's website. Must end in .jpg, .png, or .webp.",
    )
    alternate_images: List[Optional[str]] = Field(
        default_factory=lambda: [None] * 4,
        description="Up to 4 URLs of alternate product images (angles, lifestyle, detail shots). Each element is a URL or None.",
    )
    sds: Optional[str] = Field(
        default=None,
        description="URL to the Safety Data Sheet (SDS/MSDS) document. Required for chemical or hazardous products.",
    )
    sds_1: Optional[str] = Field(
        default=None,
        description="URL to an additional Safety Data Sheet if multiple SDS documents exist.",
    )
    warranty_information: Optional[str] = Field(
        default=None,
        description="URL to the manufacturer's warranty terms document or warranty information page.",
    )
    catalog: Optional[str] = Field(
        default=None,
        description="URL to the manufacturer's product catalog PDF containing this item.",
    )
    specification_sheet: Optional[str] = Field(
        default=None,
        description="URL to the product specification / data sheet PDF from the manufacturer.",
    )
    installation_manual: Optional[str] = Field(
        default=None,
        description="URL to the installation or instruction manual PDF.",
    )
    service_manual: Optional[str] = Field(
        default=None,
        description="URL to the service/repair manual PDF. Typically for appliances and power tools.",
    )
    owners_manual: Optional[str] = Field(
        default=None,
        description="URL to the owner's / user manual PDF.",
    )
    line_drawing: Optional[str] = Field(
        default=None,
        description="URL to a technical line drawing or dimensional diagram image/PDF.",
    )
    mtr: Optional[str] = Field(
        default=None,
        description="URL to the Material Test Report (MTR) document. Typically for pipe/fitting/metal products.",
    )
    rohs: Optional[str] = Field(
        default=None,
        description="URL to the RoHS (Restriction of Hazardous Substances) compliance certificate.",
    )
    full_engineering_drawing: Optional[str] = Field(
        default=None,
        description="URL to the full engineering / CAD drawing document.",
    )
    energy_star_guide: Optional[str] = Field(
        default=None,
        description="URL to the ENERGY STAR program guide or certificate for this product.",
    )
    technical_bulletin: Optional[str] = Field(
        default=None,
        description="URL to a manufacturer technical bulletin or product advisory document.",
    )
    submittal: Optional[str] = Field(
        default=None,
        description="URL to the product submittal sheet used in commercial/construction projects.",
    )
    compatibility_chart: Optional[str] = Field(
        default=None,
        description="URL to a compatibility chart showing which systems/models this product works with.",
    )
    size_chart: Optional[str] = Field(
        default=None,
        description="URL to a sizing guide or size chart. Relevant for apparel, gloves, or sized accessories.",
    )
    product_label_insert: Optional[str] = Field(
        default=None,
        description="URL to the product packaging label or insert document.",
    )
    video_link: Optional[str] = Field(
        default=None,
        description="URL to a primary product demonstration or installation video (YouTube or manufacturer site).",
    )
    video_link_1: Optional[str] = Field(
        default=None,
        description="URL to an additional product video.",
    )


class ProductMeta(BaseModel):
    """
    Record-level metadata about this product's status and image availability.
    """

    country_of_origin: Optional[str] = Field(
        default=None,
        description=(
            "Country where the product is manufactured. Use full country name. "
            "Examples: 'United States', 'China', 'Japan', 'Germany', 'Mexico'. "
            "Infer from brand if confidently known (e.g. Makita → Japan, "
            "Festool → Germany). Leave None if uncertain."
        ),
    )
    discontinued: Optional[bool] = Field(
        default=None,
        description=(
            "True if this product has been discontinued by the manufacturer. "
            "False if it is currently active. None if status is unknown."
        ),
    )
    actual_image: Optional[Literal["Yes", "No"]] = Field(
        default=None,
        description=(
            "'Yes' if a real product photograph is available in product_image. "
            "'No' if only a placeholder, line drawing, or no image is available."
        ),
    )


class ProductEnrichment(BaseModel):
    description: ProductDescription
    identity: ProductIdentity
    features: ProductFeatures
    meta: ProductMeta
    dimensions: ProductDimensions
    assets: ProductAssets
    commerce: ProductCommerce
    attributes: List[Attribute] = Field(
        default_factory=list,
        description="List of structured attributes (label/value/uom) found in manufacturer sources.",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_nulls_to_dicts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If the LLM returns null or omits these objects entirely, coerce them to empty dicts
            for field in [
                "dimensions",
                "assets",
                "features",
                "meta",
                "commerce",
                "description",
                "identity",
            ]:
                if data.get(field) is None:
                    data[field] = {}
        return data


# ══════════════════════════════════════════════════════════════
#  TOP-LEVEL OUTPUT MODEL  (252-column delivery format)
# ══════════════════════════════════════════════════════════════


class CompleteProduct(BaseModel):
    """
    Full enriched product record matching the 252-column delivery format.
    Composed of 10 logical sub-models. The LLM should populate each sub-model
    based on the raw Product input and any retrieved manufacturer information.

    Sub-models:
      sources      → manufacturer URL + up to 5 reference URLs
      ids          → internal IDs (Dept/Class/Fine/SKU) + raw input pass-through
      identity     → canonical MANUFACTURER_NAME, BRAND_NAME, TRADE_NAME, Classpath
      description  → 6 description variants (invoice/mobile/short/long/retail/marketing)
      features     → up to 20 bullet features + compliance/application fields
      attributes   → up to 50 structured attribute triplets (label/value/uom)
      commerce     → UPC/EAN/GTIN/UNSPSC, pricing, packaging
      dimensions   → physical length/height/width/weight/volume + UOMs
      assets       → image URLs, document URLs, video URLs
      meta         → Country of Origin, Discontinued flag, Actual Image flag
    """

    sources: ProductSources = Field(
        default_factory=ProductSources, description="Manufacturer and reference URLs."
    )
    ids: ProductIDs = Field(
        default_factory=ProductIDs,
        description="Internal taxonomy IDs and raw input pass-through fields.",
    )
    identity: ProductIdentity = Field(
        default_factory=ProductIdentity,
        description="Canonical manufacturer, brand, trade name, MPN, and classpath.",
    )
    description: ProductDescription = Field(
        default_factory=ProductDescription,
        description="All 6 description variants: invoice, mobile, short, long, retail, marketing.",
    )
    features: ProductFeatures = Field(
        default_factory=ProductFeatures,
        description="Up to 20 bullet features plus compliance/application metadata.",
    )
    attributes: ProductAttributes = Field(
        default_factory=ProductAttributes,
        description="Up to 50 structured attribute triplets.",
    )
    commerce: ProductCommerce = Field(
        default_factory=ProductCommerce,
        description="Barcodes, UNSPSC, pricing and packaging details.",
    )
    dimensions: ProductDimensions = Field(
        default_factory=ProductDimensions,
        description="Physical dimensions and weight with UOMs.",
    )
    assets: ProductAssets = Field(
        default_factory=ProductAssets,
        description="Image, document, and video URLs from manufacturer sources only.",
    )
    meta: ProductMeta = Field(
        default_factory=ProductMeta,
        description="Record-level metadata: country of origin, discontinued status, image flag.",
    )

    def to_delivery_row(self) -> tuple[dict, dict]:
        """Return a flat dict whose keys match the exact 252-column delivery CSV, and a source map dict."""
        s, i, id_, d, f, at, c, dm, as_, m = (
            self.sources,
            self.ids,
            self.identity,
            self.description,
            self.features,
            self.attributes,
            self.commerce,
            self.dimensions,
            self.assets,
            self.meta,
        )
        row: dict = {}
        source_map: dict[str, str] = {}
        row["MFR URL"] = s.mfr_url
        for n, url in enumerate(s.ref_urls, 1):
            row[f"Ref URL {n}"] = url
        row["PART_NUMBER"] = i.part_number
        row["Dept"] = i.dept
        row["Class"] = i.class_
        row["Fine"] = i.fine
        row["SKU - MY_PART_NUMBER"] = i.sku
        row["Mfg_Part_Num"] = i.mfg_part_num
        row["Part_Desc"] = i.part_desc
        row["E1_Brand"] = i.e1_brand
        row["Unilog_Brand"] = i.unilog_brand
        row["DIB_Brand"] = i.dib_brand
        row["Part_Manuf"] = i.part_manuf
        row["MANUFACTURER_NAME"] = id_.manufacturer_name
        row["BRAND_NAME"] = id_.brand_name
        row["TRADE_NAME"] = id_.trade_name
        row["MANUFACTURER_PART_NUMBER"] = id_.manufacturer_part_number
        row["ALTERNATE_PART_NUMBER"] = id_.alternate_part_number
        row["Classpath"] = id_.classpath
        row["MOBILE_DESC"] = d.mobile_desc
        row["INVOICE_DESC"] = d.invoice_desc
        row["SHORT_DESC"] = d.short_desc
        row["LONG_DESC1"] = d.long_desc
        row["RETAIL_DESC"] = d.retail_desc
        row["MARKETING_DESCRIPTION"] = d.marketing_description
        for n, feat in enumerate(f.item_features, 1):
            row[f"ITEM_FEATURES_{n}"] = feat
        row["With"] = f.with_
        row["Standard/Approvals"] = f.standards_approvals
        row["Prop 65"] = f.prop_65
        row["Application"] = f.application
        row["Includes"] = f.includes
        row["Product Name"] = f.product_name
        for n in range(1, 51):
            attr = at.attributes[n - 1] if (n - 1) < len(at.attributes) else None
            row[f"ATTRIBUTE_LABEL {n}"] = attr.label if attr else None
            row[f"ATTRIBUTE_VALUE {n}"] = attr.value if attr else None
            row[f"ATTRIBUTE_UOM {n}"] = attr.uom if attr else None
            if attr:
                source_map[f"ATTRIBUTE_VALUE {n}"] = attr.source
        row["UPC"] = c.upc
        row["EAN"] = c.ean
        row["GTIN"] = c.gtin
        row["UNSPSC"] = c.unspsc
        row["Warranty"] = c.warranty
        row["List Price"] = c.list_price
        row["Selling Qty"] = c.selling_qty
        row["Selling UOM"] = c.selling_uom
        row["Standard Packaging Information"] = c.standard_packaging_info
        row["LENGTH"] = dm.length
        row["LENGTH_UOM"] = dm.length_uom
        row["HEIGHT"] = dm.height
        row["HEIGHT_UOM"] = dm.height_uom
        row["WIDTH"] = dm.width
        row["WIDTH_UOM"] = dm.width_uom
        row["WEIGHT"] = dm.weight
        row["WEIGHT_UOM"] = dm.weight_uom
        row["VOLUME"] = dm.volume
        row["VOLUME_UOM"] = dm.volume_uom
        row["Product Image"] = as_.product_image
        for n, img in enumerate(as_.alternate_images, 1):
            row[f"Alternate Image {n}"] = img
        row["SDS"] = as_.sds
        row["SDS_1"] = as_.sds_1
        row["Warranty Information"] = as_.warranty_information
        row["Catalog"] = as_.catalog
        row["Specification Sheet"] = as_.specification_sheet
        row["Instruction/Installation Manual"] = as_.installation_manual
        row["Service Manual"] = as_.service_manual
        row["Owners/User Manual"] = as_.owners_manual
        row["Line Drawing"] = as_.line_drawing
        row["MTR"] = as_.mtr
        row["RoHS"] = as_.rohs
        row["Full Engineering Drawing"] = as_.full_engineering_drawing
        row["Energy Star Guide"] = as_.energy_star_guide
        row["Technical Bulletin"] = as_.technical_bulletin
        row["Submittal"] = as_.submittal
        row["Compatibility Chart"] = as_.compatibility_chart
        row["Size Chart"] = as_.size_chart
        row["Product Label/Insert"] = as_.product_label_insert
        row["Video Link"] = as_.video_link
        row["Video Link 1"] = as_.video_link_1
        row["Country Of Origin"] = m.country_of_origin
        row["Discontinued"] = m.discontinued
        row["Actual Image (Yes/No)"] = m.actual_image
        return row, source_map
