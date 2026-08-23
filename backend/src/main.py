from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from time import perf_counter
from typing import TypedDict
from urllib.parse import urlparse

import httpx
import pandas as pd
from constants import _AD_TRACKER_HOSTS, _MARKETPLACE_DOMAINS, _SYSTEM_PROMPT
from dotenv import load_dotenv
from extractor import extract_attributes, extract_commerce
from langchain_mistralai import ChatMistralAI
from langgraph.graph import END, START, StateGraph
from models import (
    Attribute,
    CompleteProduct,
    ProductAttributes,
    ProductCommerce,
    ProductDescription,
    ProductDimensions,
    ProductEnrichment,
    ProductFeatures,
    ProductIdentity,
    ProductIDs,
    ProductMeta,
    ProductSources,
)
from preprocess import preprocess

load_dotenv()


class State(TypedDict, total=False):
    row: dict
    context: str
    deterministic: dict
    search_context: str
    search_sources: list[str]
    llm_result: ProductEnrichment
    product: CompleteProduct
    validation: dict[str, bool]
    retry_count: int
    delivery_row: dict
    source_map: dict[str, str]


# Rate limiting throttles
REQUEST_DELAY = 1.0
MAX_REPAIR_ATTEMPTS = 2

FEATURE_SLOTS = 20

# Search settings
SEARCH_RESULTS_PER_QUERY = 4
SEARCH_MAX_SNIPPET_CHARS = 300

# Number of Serper requests allowed to be in-flight at once.
# Start with 3; lower to 2 if Serper rate-limits your account.
SEARCH_CONCURRENCY = 3
_semaphores: dict = {}
_locks: dict = {}


def get_search_semaphore() -> asyncio.Semaphore:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop not in _semaphores:
        _semaphores[loop] = asyncio.Semaphore(SEARCH_CONCURRENCY)
    return _semaphores[loop]


def get_request_lock() -> asyncio.Lock:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop not in _locks:
        _locks[loop] = asyncio.Lock()
    return _locks[loop]


last_request_time = 0.0


def log(message: str, level: int = 0) -> None:
    indent = "    " * level
    print(f"{indent}{message}", flush=True)


def elapsed(start: float) -> str:
    return f"{perf_counter() - start:.2f}s"


def make_llm() -> ChatMistralAI:
    return ChatMistralAI(
        model="ministral-14b-2512",
        temperature=0,
    )


async def call_llm(name: str, chain, prompt):
    global last_request_time
    start = perf_counter()
    async with get_request_lock():
        now = perf_counter()
        wait = REQUEST_DELAY - (now - last_request_time)
        if wait > 0:
            log(f"[THROTTLE] {name}: waiting {wait:.2f}s", 2)
            await asyncio.sleep(wait)
        log(f"├─ [LLM:{name}] request started", 2)
        last_request_time = perf_counter()
        try:
            result = await chain.ainvoke(prompt)
            log(f"├─ [LLM:{name}] ✓ completed in {elapsed(start)}", 2)
            return result
        except Exception as exc:
            log(
                f"├─ [LLM:{name}] ❌ {type(exc).__name__}: {exc} after {elapsed(start)}",
                2,
            )
            raise


def deterministic_node(state: State) -> dict:
    start = perf_counter()
    log("├─ [DETERMINISTIC] extracting", 1)
    row = defaultdict(str, state["row"])
    part_desc = row["Part_Desc"]
    mpn = row["Mfg_Part_Num"]
    clean_desc = row["clean_desc"] or part_desc

    log(f"MPN          : {mpn}", 2)
    log(f"Brand        : {row['brand_name'] or 'UNKNOWN'}", 2)
    log(f"Manufacturer : {row['manufacturer_name'] or 'UNKNOWN'}", 2)

    # --- Classpath ---
    classpath = (
        f"{row['Dept']} > {row['Class']} > {row['Fine']}"
        if all(row.get(col) for col in ["Dept", "Class", "Fine"])
        else None
    )
    log(f"Classpath    : {classpath or 'Not Specified'}", 2)

    ids = ProductIDs(
        mfg_part_num=mpn,
        part_desc=part_desc,
        e1_brand=row["E1_Brand"],
        dib_brand=row["DIB_Brand"],
        part_manuf=row["Part_Manuf"],
    )

    identity = ProductIdentity(
        manufacturer_name=row.get("manufacturer_name"),
        brand_name=row.get("brand_name"),
        manufacturer_part_number=mpn,
        classpath=classpath,  # NEW
    )

    extracted_attributes = extract_attributes(clean_desc)
    log(f"Regex attributes ({len(extracted_attributes)}):", 2)
    for attr in extracted_attributes:
        log(f"  - {attr.label}: {attr.value} {attr.uom or ''}", 3)

    attributes = ProductAttributes(attributes=extracted_attributes)

    selling_qty, selling_uom = extract_commerce(clean_desc)
    log(f"Commerce     : qty={selling_qty}, uom={selling_uom}", 2)
    commerce = ProductCommerce(
        selling_qty=selling_qty,
        selling_uom=selling_uom,
    )

    meta = ProductMeta(
        discontinued=False,
        actual_image="No",
    )
    log(f"└─ [DETERMINISTIC] ✓ {elapsed(start)}", 1)
    return {
        "deterministic": {
            "ids": ids,
            "identity": identity,
            "attributes": attributes,
            "commerce": commerce,
            "meta": meta,
        }
    }


def _build_search_queries(row: dict) -> list[str]:
    """Build MPN-first research queries.

    The MPN is the primary product key.  We must be able to research a
    product even when both brand and manufacturer are unknown.
    """
    mpn = (row.get("Mfg_Part_Num") or "").strip()

    if not mpn:
        return []

    queries: list[str] = [
        f'"{mpn}"',
        f'"{mpn}" specifications',
        f'"{mpn}" datasheet',
        f'"{mpn}" filetype:pdf',
    ]

    return queries


def _is_ad_tracker_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return True
    url_lower = url.lower()
    if any(p in url_lower for p in ["/aclick", "/pagead/", "y.js", "/ad/", "click?"]):
        return True
    try:
        parsed = urlparse(url_lower)
        hostname = parsed.netloc.split(":")[0] if parsed.netloc else ""
        if any(ad_host in hostname for ad_host in _AD_TRACKER_HOSTS):
            return True
    except Exception:
        return True
    return False


def _is_valid_source_url(url: str) -> bool:
    if _is_ad_tracker_url(url):
        return False
    try:
        parsed = urlparse(url.lower())
        hostname = parsed.netloc.split(":")[0] if parsed.netloc else ""
        if any(mkt in hostname for mkt in _MARKETPLACE_DOMAINS):
            return False
        return True
    except Exception:
        return False


async def _throttled_search(query: str) -> list[dict]:
    """Run one Serper query under the global concurrency limit."""
    api_key = os.getenv("SERPER_API_KEY")

    if not api_key:
        log("[SEARCH] ⚠️ SERPER_API_KEY missing", 2)
        return []

    # This limits the number of simultaneous Serper requests.
    # Unlike the old search_lock, it does NOT serialize all requests.
    async with get_search_semaphore():
        start = perf_counter()

        try:
            log(f"├─ [SEARCH] request started: {query!r}", 3)

            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "q": query,
                "num": SEARCH_RESULTS_PER_QUERY,
            }

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

            if resp.status_code != 200:
                log(
                    f"├─ [SEARCH] ❌ Serper HTTP {resp.status_code} " f"for {query!r}",
                    3,
                )
                return []

            data = resp.json()
            organic = data.get("organic", [])

            results = []
            for item in organic:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "body": item.get("snippet", ""),
                        "href": item.get("link", ""),
                    }
                )

            log(
                f"├─ [SEARCH] ✓ {query!r} "
                f"({len(results)} results, {elapsed(start)})",
                3,
            )
            return results

        except Exception as exc:
            log(
                f"├─ [SEARCH] ❌ query failed {query!r}: "
                f"{type(exc).__name__}: {exc}",
                3,
            )
            return []


async def search_node(state: State) -> dict:
    """Research the product using MPN-first web retrieval.

    Search results are kept structured so the LLM can distinguish source,
    query and evidence instead of receiving one opaque text blob.
    """
    start = perf_counter()
    log("├─ [SEARCH] researching product", 1)

    row = defaultdict(str, state["row"])

    # Use deterministic identity when available, but do not require it.

    queries = _build_search_queries(row)
    if not queries:
        log("├─ [SEARCH] no MPN available — skipping", 2)
        return {
            "search_context": "No MPN available for web research.",
            "search_sources": [],
        }

    log(f"├─ [SEARCH] {len(queries)} MPN-first queries", 2)

    # Fire all queries concurrently, while _throttled_search()
    # limits the number of requests that are actually in-flight.
    #
    # This preserves every query/result while reducing the total search
    # latency from roughly sum(query latencies) to roughly the slowest
    # batch of queries.
    log(
        f"├─ [SEARCH] launching {len(queries)} queries "
        f"(max {SEARCH_CONCURRENCY} concurrent)",
        2,
    )

    search_tasks = [asyncio.create_task(_throttled_search(q)) for q in queries]

    query_results = await asyncio.gather(
        *search_tasks,
        return_exceptions=True,
    )

    all_results: list[dict] = []
    found_domain = None
    manuf = (row.get("manufacturer_name") or "").strip().lower()
    if manuf:
        manuf_first_word = (
            manuf.split()[0].replace(",", "").replace(".", "").replace("-", "")
        )

    for q, results in zip(queries, query_results):
        if isinstance(results, Exception):
            log(
                f"├─ [SEARCH] ❌ {q!r}: " f"{type(results).__name__}: {results}",
                2,
            )
            continue

        for result in results:
            result = dict(result)
            result["query"] = q
            all_results.append(result)

            # Domain discovery logic
            if not found_domain and manuf:
                url = (result.get("href") or "").lower()
                try:
                    hostname = urlparse(url).netloc
                    if len(manuf_first_word) > 2 and manuf_first_word in hostname:
                        # For simple implementation, use the hostname as domain.
                        # (A more complex approach would strip subdomains like www.)
                        found_domain = hostname.replace("www.", "")
                except Exception:
                    pass

    if found_domain:
        log(f"├─ [SEARCH] Found candidate manufacturer domain: {found_domain}", 2)
        mpn = (row.get("Mfg_Part_Num") or "").strip()
        phase2_queries = [
            f'site:{found_domain} "{mpn}"',
            f'site:{found_domain} "{mpn}" specifications',
            f'site:{found_domain} "{mpn}" filetype:pdf',
        ]
        log(
            f"├─ [SEARCH] launching {len(phase2_queries)} Phase 2 queries for {found_domain}",
            2,
        )

        phase2_tasks = [
            asyncio.create_task(_throttled_search(q)) for q in phase2_queries
        ]
        phase2_results = await asyncio.gather(
            *phase2_tasks,
            return_exceptions=True,
        )
        for q, results in zip(phase2_queries, phase2_results):
            if isinstance(results, Exception):
                log(
                    f"├─ [SEARCH] ❌ Phase 2 query failed {q!r}: {type(results).__name__}",
                    2,
                )
                continue
            for result in results:
                result = dict(result)
                result["query"] = q
                all_results.append(result)

    # Deduplicate by URL.  Search engines frequently return the same page
    # for several queries.
    unique: dict[str, dict] = {}
    for result in all_results:
        url = (result.get("href") or "").strip()
        if not url or not _is_valid_source_url(url):
            continue
        unique.setdefault(url, result)

    # Prefer likely authoritative sources.  We cannot always know the exact
    # manufacturer domain before identity resolution, so classify conservatively.
    def source_type(result: dict) -> str:
        url = (result.get("href") or "").lower()
        title = (result.get("title") or "").lower()
        hostname = urlparse(url).netloc.lower()

        if any(token in hostname for token in [".gov", ".edu"]):
            return "authoritative"
        if (
            ".pdf" in url
            or url.endswith(".pdf")
            or "specification" in title
            or "datasheet" in title
        ):
            return "technical_document"
        if any(
            token in title for token in ["official", "manufacturer", "product support"]
        ):
            return "manufacturer_candidate"
        return "web"

    evidence: list[dict] = []
    for result in unique.values():
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()
        url = (result.get("href") or "").strip()
        if not body:
            continue

        evidence.append(
            {
                "query": result.get("query", ""),
                "source_type": source_type(result),
                "title": title,
                "url": url,
                "evidence": body[:SEARCH_MAX_SNIPPET_CHARS],
            }
        )

    # Keep the context bounded.  Exact-MPN research is more valuable than
    # simply dumping every result returned by the search engine.
    priority = {
        "authoritative": 0,
        "manufacturer_candidate": 1,
        "technical_document": 2,
        "web": 3,
    }
    evidence.sort(key=lambda item: priority.get(item["source_type"], 9))
    evidence = evidence[:12]

    if evidence:
        blocks = []
        for index, item in enumerate(evidence, start=1):
            blocks.append(
                "\n".join(
                    [
                        f"EVIDENCE {index}",
                        f"Source type: {item['source_type']}",
                        f"Query: {item['query']}",
                        f"Title: {item['title']}",
                        f"URL: {item['url']}",
                        f"Evidence: {item['evidence']}",
                    ]
                )
            )
        search_context = "\n\n".join(blocks)
    else:
        search_context = "No usable web evidence found."

    sources = [item["url"] for item in evidence if item["url"]]

    log(f"├─ [SEARCH] {len(evidence)} evidence items", 2)
    for item in evidence[:5]:
        log(f"  - [{item['source_type']}] {item['title']}", 3)
    log(f"└─ [SEARCH] ✓ {elapsed(start)}", 1)

    return {
        "search_context": search_context,
        "search_sources": sources,
    }


def context_node(
    state: State,
) -> dict:
    start = perf_counter()
    log("├─ [CONTEXT] preparing LLM context", 1)
    row = defaultdict(str, state["row"])
    deterministic = state["deterministic"]
    attributes = deterministic["attributes"]

    attribute_text = "\n".join(
        f"- {attribute.label}: {attribute.value}" for attribute in attributes.attributes
    )
    if not attribute_text:
        attribute_text = "None extracted."

    search_context = state.get("search_context") or "No web search results available."

    context = f"""
PRODUCT INPUT

Part Description:
{row["clean_desc"] or row["Part_Desc"]}

Original Part Description:
{row["Part_Desc"]}

Manufacturer:
{row["manufacturer_name"] or "Unknown"}

Brand:
{row["brand_name"] or "Unknown"}

Manufacturer Part Number:
{row["Mfg_Part_Num"]}

Deterministically Extracted Attributes:
{attribute_text}

WEB RESEARCH EVIDENCE
Use this evidence to resolve the product identity and enrich the record. Search evidence may establish facts that are UNKNOWN in the raw input. Prefer exact-MPN evidence over generic category knowledge.
{search_context}

EVIDENCE RULES
1. Prefer an exact-match official manufacturer page or manufacturer technical PDF.
2. Next prefer an exact-match authoritative catalog/distributor source.
3. Use other exact-MPN sources only as corroboration.
4. The raw input is authoritative for the MPN itself and for facts explicitly present in it.
5. UNKNOWN input fields may be populated from strong web evidence.
6. Never treat a distributor/seller as the manufacturer merely because it appears in Part_Manuf.
7. Never invent SKU, PART_NUMBER, UPC, EAN, GTIN, warranty, origin, dimensions, or specifications.
8. If sources conflict, prefer the strongest exact-MPN source and do not silently combine incompatible products.
9. If evidence is insufficient, return null rather than guessing.
""".strip()

    log(f"Context length: {len(context)} chars", 2)
    log(f"└─ [CONTEXT] ✓ {elapsed(start)}", 1)
    return {"context": context}


async def llm_node(
    state: State,
) -> dict:
    start = perf_counter()
    log("├─ [LLM] starting enrichment", 1)
    llm = make_llm()
    enrichment_chain = llm.with_structured_output(ProductEnrichment)
    prompt = [
        (
            "system",
            _SYSTEM_PROMPT,
        ),
        (
            "human",
            state["context"],
        ),
    ]
    result = await call_llm("enrichment", enrichment_chain, prompt)
    log(f"└─ [LLM] ✓ {elapsed(start)}", 1)
    return {"llm_result": result}


def _fix_feature_length(
    features: ProductFeatures,
) -> ProductFeatures:
    padded = (features.item_features + [None] * FEATURE_SLOTS)[:FEATURE_SLOTS]
    return features.model_copy(update={"item_features": padded})


def _build_sources(urls: list[str]) -> ProductSources:
    urls = [u for u in urls if u][:6]
    mfr_url = urls[0] if urls else None
    rest = urls[1:6]
    rest = rest + [None] * (5 - len(rest))
    return ProductSources(mfr_url=mfr_url, ref_urls=rest)


def merge_node(
    state: State,
) -> dict:
    start = perf_counter()
    log("├─ [MERGE] combining deterministic + LLM", 1)
    deterministic = state["deterministic"]
    enrichment = state["llm_result"]

    # Merge identity with evidence-aware precedence.
    #
    # High-confidence curated input (E1/DIB brand) and an explicitly supplied
    # manufacturer should be preserved.  A manufacturer inferred from the raw
    # description is deliberately lower confidence: exact-MPN web evidence
    # is allowed to replace it.  This prevents an early heuristic from
    # permanently blocking product research.
    det_identity = deterministic["identity"]
    llm_identity = enrichment.identity
    identity_data = llm_identity.model_dump()
    row = defaultdict(str, state["row"])

    e1_brand = (row.get("E1_Brand") or "").strip()
    dib_brand = (row.get("DIB_Brand") or "").strip()
    manufacturer_inferred = bool(row.get("manufacturer_inferred"))

    if det_identity.manufacturer_name and not manufacturer_inferred:
        identity_data["manufacturer_name"] = det_identity.manufacturer_name

    if e1_brand or dib_brand:
        if det_identity.brand_name:
            identity_data["brand_name"] = det_identity.brand_name

    # MPN from the raw record is authoritative and must never be changed.
    if det_identity.manufacturer_part_number:
        identity_data["manufacturer_part_number"] = (
            det_identity.manufacturer_part_number
        )

    # The deterministic classpath is retained when explicitly supplied by
    # the source dataset; otherwise the LLM may resolve it from evidence.
    if det_identity.classpath:
        identity_data["classpath"] = det_identity.classpath

    identity = ProductIdentity(**identity_data)

    # Populate taxonomy levels (Dept, Class, Fine) from Classpath
    classpath = identity.classpath or ""
    parts = [p.strip() for p in classpath.split(">") if p.strip()]
    dept = parts[0] if len(parts) > 0 else None
    class_ = parts[1] if len(parts) > 1 else None
    fine = parts[2] if len(parts) > 2 else (parts[-1] if parts else None)

    # PART_NUMBER and SKU are catalog identifiers, not values that can be
    # safely invented from an MPN.  Keep them unknown unless an upstream
    # source explicitly supplies them.
    ids = ProductIDs(
        part_number=None,
        dept=dept,
        class_=class_,
        fine=fine,
        sku=None,
        mfg_part_num=deterministic["ids"].mfg_part_num,
        part_desc=deterministic["ids"].part_desc,
        e1_brand=deterministic["ids"].e1_brand,
        dib_brand=deterministic["ids"].dib_brand,
        part_manuf=deterministic["ids"].part_manuf,
    )

    # 1. Merge Attributes
    # Process deterministic attributes first (highest priority), then LLM attributes (filtering out unsupported attributes missing evidence).
    from extractor import normalize_attribute

    merged_attrs: list[Attribute] = []
    seen_labels: set[str] = set()

    for raw_attr in deterministic["attributes"].attributes:
        norm = normalize_attribute(raw_attr)
        if norm and norm.label.lower() not in seen_labels:
            merged_attrs.append(norm)
            seen_labels.add(norm.label.lower())

    for raw_attr in enrichment.attributes:
        norm = normalize_attribute(raw_attr)
        if norm and norm.evidence and norm.label.lower() not in seen_labels:
            merged_attrs.append(norm)
            seen_labels.add(norm.label.lower())

    # Pad to exactly 50 slots
    padded_attrs = (merged_attrs + [Attribute() for _ in range(50)])[:50]
    attributes = ProductAttributes(attributes=padded_attrs)

    # 2. Merge Commerce
    det_comm = deterministic["commerce"]
    llm_comm = enrichment.commerce
    commerce = ProductCommerce(
        upc=det_comm.upc or llm_comm.upc,
        ean=det_comm.ean or llm_comm.ean,
        gtin=det_comm.gtin or llm_comm.gtin,
        unspsc=det_comm.unspsc or llm_comm.unspsc,
        warranty=det_comm.warranty or llm_comm.warranty,
        list_price=det_comm.list_price or llm_comm.list_price,
        selling_qty=det_comm.selling_qty or llm_comm.selling_qty,
        selling_uom=det_comm.selling_uom or llm_comm.selling_uom,
        standard_packaging_info=det_comm.standard_packaging_info
        or llm_comm.standard_packaging_info,
    )

    # 3. Dimensions (with decimal fraction conversion!)
    from extractor import decimal_to_fraction

    dm = enrichment.dimensions
    length_val = (
        decimal_to_fraction(dm.length)
        if dm.length and dm.length_uom == "in"
        else dm.length
    )
    width_val = (
        decimal_to_fraction(dm.width) if dm.width and dm.width_uom == "in" else dm.width
    )
    height_val = (
        decimal_to_fraction(dm.height)
        if dm.height and dm.height_uom == "in"
        else dm.height
    )

    dimensions = ProductDimensions(
        length=length_val,
        length_uom=dm.length_uom,
        width=width_val,
        width_uom=dm.width_uom,
        height=height_val,
        height_uom=dm.height_uom,
        weight=dm.weight,
        weight_uom=dm.weight_uom,
        volume=dm.volume,
        volume_uom=dm.volume_uom,
    )

    # 4. Deterministic Descriptions (Formulaic Assembly)
    brand = identity.brand_name or identity.manufacturer_name or "Unbranded"
    series = identity.trade_name or ""
    mpn = identity.manufacturer_part_number or ""
    
    item_type = (row.get("Part_Desc") or "Product").split(",")[0][:30].strip()
    if identity.classpath:
        parts = [p.strip() for p in identity.classpath.split(">") if p.strip()]
        if parts:
            item_type = parts[-1]
            
    active_attrs = [a for a in attributes.attributes if a.label and a.value]
    key_attrs = []
    priority = ["Material", "Voltage Rating", "Amperage Rating", "Size", "Diameter", "Wattage"]
    
    for label in priority:
        for attr in active_attrs:
            if attr.label == label:
                val = f"{attr.value} {attr.uom}" if attr.uom else str(attr.value)
                if val not in key_attrs:
                    key_attrs.append(val)
                if len(key_attrs) >= 2:
                    break
        if len(key_attrs) >= 2:
            break
            
    if len(key_attrs) < 2:
        for attr in active_attrs:
            if attr.label not in priority:
                val = f"{attr.value} {attr.uom}" if attr.uom else str(attr.value)
                if val not in key_attrs:
                    key_attrs.append(val)
                if len(key_attrs) >= 2:
                    break
                    
    # Invoice Desc (<= 40 chars, upper)
    invoice_parts = [item_type.upper()] + [k.upper() for k in key_attrs]
    invoice_desc = " ".join(invoice_parts)[:40].strip()
    
    # Mobile Desc (<= 80 chars)
    mobile_parts = [brand, item_type]
    if series:
        mobile_parts.append(series)
    if mpn:
        mobile_parts.append(mpn)
    mobile_desc = ", ".join(mobile_parts)
    
    # Pad with key attributes if it's too short
    if len(mobile_desc) < 60 and key_attrs:
        mobile_desc += f", {', '.join(key_attrs)}"
        
    if len(mobile_desc) > 80:
        mobile_desc = mobile_desc[:77].strip() + "..."
        
    # Short Desc (~100-150 chars)
    short_parts = [brand]
    if series:
        short_parts.append(series)
    if mpn:
        short_parts.append(mpn)
    short_parts.append(item_type)
    short_desc_base = " ".join(short_parts)
    short_desc = f"{short_desc_base} With {', '.join(key_attrs)}" if key_attrs else short_desc_base
    if len(short_desc) > 150:
        short_desc = short_desc[:147].strip() + "..."
        
    final_desc = enrichment.description.model_copy(update={
        "invoice_desc": invoice_desc,
        "mobile_desc": mobile_desc,
        "short_desc": short_desc
    })

    product = CompleteProduct(
        ids=ids,
        identity=identity,
        description=final_desc,
        features=_fix_feature_length(enrichment.features),
        attributes=attributes,
        commerce=commerce,
        dimensions=dimensions,
        assets=enrichment.assets,
        sources=_build_sources(state.get("search_sources") or []),
        meta=enrichment.meta,
    )
    log(f"└─ [MERGE] ✓ {elapsed(start)}", 1)
    return {"product": product}


def validate_node(
    state: State,
) -> dict:
    start = perf_counter()
    log("├─ [VALIDATE] checking product", 1)

    product = state["product"]
    description = product.description
    identity = product.identity

    invoice_desc = description.invoice_desc or ""
    mobile_desc = description.mobile_desc or ""
    classpath = identity.classpath or ""
    active_attrs = [a for a in product.attributes.attributes if a.label and a.value]

    checks = {
        "invoice_desc_caps": bool(invoice_desc)
        and invoice_desc == invoice_desc.upper(),
        "invoice_desc_length": 0 < len(invoice_desc) <= 40,
        "mobile_desc_length": 0 < len(mobile_desc) <= 80,
        "classpath_valid": bool(classpath)
        and " > " in classpath
        and len(classpath.split(" > ")) >= 3,
        "has_manufacturer": bool(identity.manufacturer_name),
        "has_brand": bool(identity.brand_name),
        "has_attributes": len(active_attrs) >= 1,
        "attributes_supported": all(bool(a.evidence) for a in active_attrs),
    }

    passed = [rule for rule, value in checks.items() if value]
    failed = [rule for rule, value in checks.items() if not value]

    log(f"Passed: {len(passed)}/{len(checks)}", 2)
    if failed:
        log(f"Failed: {failed}", 2)
        for rule in failed:
            if rule == "classpath_valid":
                log(f"  - Classpath: '{classpath}' (must be 'Cat > Subcat > Leaf')", 3)
            elif rule == "invoice_desc_length":
                log(
                    f"  - INVOICE_DESC length: {len(invoice_desc)} (must be 1-40 chars)",
                    3,
                )
            elif rule == "mobile_desc_length":
                log(
                    f"  - MOBILE_DESC length: {len(mobile_desc)} (must be 1-80 chars)",
                    3,
                )

    log(f"└─ [VALIDATE] {'✓' if not failed else '⚠'} {elapsed(start)}", 1)
    return {"validation": checks}


def validation_router(
    state: State,
) -> str:
    failed = [rule for rule, passed in state["validation"].items() if not passed]
    retry_count = state["retry_count"]
    if not failed or retry_count >= MAX_REPAIR_ATTEMPTS:
        return "output"
    return "repair"


async def repair_node(
    state: State,
) -> dict:
    start = perf_counter()
    retry = state["retry_count"] + 1
    product = state["product"]
    failed = [rule for rule, passed in state["validation"].items() if not passed]

    log(f"├─ [REPAIR] attempt {retry}/{MAX_REPAIR_ATTEMPTS}", 1)
    log(f"Failed rules: {failed}", 2)

    llm = make_llm()
    repair_chain = llm.with_structured_output(ProductDescription)

    prompt = f"""
The generated product record failed these validation rules: {failed}

CURRENT PRODUCT DESCRIPTION:
{product.description.model_dump_json(indent=2)}

PRODUCT INFORMATION:
Manufacturer: {product.identity.manufacturer_name}
Brand: {product.identity.brand_name}
MPN: {product.identity.manufacturer_part_number}
Classpath: {product.identity.classpath}
Attributes: {product.attributes.model_dump_json(indent=2)}

TASK:
Fix ONLY the fields necessary to satisfy the failed validation rules.
1. Preserve every existing valid field.
2. Do NOT set unrelated fields to null.
3. Do NOT invent product facts.
4. If a field does not need modification, preserve its current value.
5. Return a complete ProductDescription object.
6. The mobile description must satisfy the required length if mobile_desc_length failed.
"""

    result = await call_llm(
        "repair",
        repair_chain,
        [
            (
                "system",
                _SYSTEM_PROMPT,
            ),
            (
                "human",
                prompt,
            ),
        ],
    )

    # Defensive merge: update only modified non-None fields to preserve existing valid data
    original_data = product.description.model_dump()
    repaired_data = result.model_dump()
    changed_fields = []

    for field, new_value in repaired_data.items():
        if new_value is None:
            continue
        old_value = original_data.get(field)
        if old_value != new_value:
            changed_fields.append(field)
        original_data[field] = new_value

    repaired_description = ProductDescription(**original_data)
    repaired_product = product.model_copy(update={"description": repaired_description})

    log(f"Changed fields: {changed_fields}", 2)
    log(f"└─ [REPAIR] ✓ {elapsed(start)}", 1)
    return {
        "product": repaired_product,
        "retry_count": retry,
    }


def output_node(
    state: State,
) -> dict:
    start = perf_counter()
    log("├─ [OUTPUT] converting product", 1)

    delivery_row, source_map = state["product"].to_delivery_row()

    # Hackathon Polish: Flag dimensions as Regex if they match the deterministic extractions exactly
    dims = ["LENGTH", "HEIGHT", "WIDTH", "WEIGHT"]
    if "deterministic" in state:
        det_attrs = state["deterministic"].get("attributes", [])
        for d in dims:
            row_val = str(delivery_row.get(d, "")).strip()
            if not row_val or row_val == "None":
                continue
            # Search deterministic attributes for a match
            for attr in det_attrs:
                # If Regex found an exact string match for this value, mark it Verified
                if str(attr.value).strip() == row_val:
                    source_map[d] = "Regex"
                    break
            
            if d not in source_map:
                source_map[d] = "LLM" # Default to Inferred if it didn't come from Regex

    # Do not fabricate catalog identifiers or product facts.  If UPC/EAN/GTIN,
    # warranty, origin, UNSPSC, etc. were not established by input or research,
    # leave them empty so downstream consumers can distinguish unknown from real data.

    log(f"└─ [OUTPUT] ✓ {elapsed(start)}", 1)
    return {"delivery_row": delivery_row, "source_map": source_map}


def build_graph():
    log("[GRAPH] Building LangGraph...", 0)
    graph = StateGraph(State)

    graph.add_node("deterministic", deterministic_node)
    graph.add_node("search", search_node)
    graph.add_node("context", context_node)
    graph.add_node("llm", llm_node)
    graph.add_node("merge", merge_node)
    graph.add_node("validate", validate_node)
    graph.add_node("repair", repair_node)
    graph.add_node("output", output_node)

    graph.add_edge(START, "deterministic")
    graph.add_edge(START, "search")

    # Fan-in: context runs only after BOTH independent branches finish.
    graph.add_edge("deterministic", "context")
    graph.add_edge("search", "context")

    graph.add_edge("context", "llm")
    graph.add_edge("llm", "merge")
    graph.add_edge("merge", "validate")

    graph.add_conditional_edges(
        "validate",
        validation_router,
        {
            "repair": "repair",
            "output": "output",
        },
    )

    graph.add_edge("repair", "validate")
    graph.add_edge("output", END)

    compiled = graph.compile()
    log("[GRAPH] ✓ Graph compiled", 0)
    return compiled


async def run_pipeline(
    csv_path: str,
    output_path: str = "output_enriched.csv",
    limit: int | None = None,
) -> None:
    total_start = perf_counter()

    print("\n" + "=" * 70, flush=True)
    print("PRODUCT INTELLIGENCE PIPELINE", flush=True)
    print("=" * 70, flush=True)

    log("[PIPELINE] Loading + preprocessing...", 0)
    df = preprocess(csv_path)
    if limit is not None:
        df = df.head(limit)
    total_products = len(df)

    print(f"\n[PIPELINE] Processing {total_products} products", flush=True)
    print(f"[PIPELINE] Mistral request delay: {REQUEST_DELAY:.1f}s", flush=True)
    print(
        f"[PIPELINE] Serper concurrency: {SEARCH_CONCURRENCY} "
        f"(max in-flight requests)",
        flush=True,
    )

    graph = build_graph()
    results = []
    successful = 0
    validation_failures = 0
    hard_failures = 0

    for position, (_, row) in enumerate(df.iterrows(), start=1):
        mpn = row["Mfg_Part_Num"]
        print("\n" + "═" * 70, flush=True)
        print(f"[{position}/{total_products}] PRODUCT: {mpn}", flush=True)
        print("═" * 70, flush=True)
        product_start = perf_counter()

        try:
            state: State = {
                "row": row.to_dict(),
                "retry_count": 0,
            }
            result = await graph.ainvoke(state)
            results.append(result["delivery_row"])

            failed = [
                rule for rule, passed in result["validation"].items() if not passed
            ]
            product_time = perf_counter() - product_start

            if failed:
                validation_failures += 1
                print("\n ⚠ PRODUCT COMPLETE WITH VALIDATION FAILURES", flush=True)
                print(f" Failed: {failed}", flush=True)
            else:
                successful += 1
                print("\n ✓ PRODUCT COMPLETE", flush=True)

            print(f" Time: {product_time:.2f}s", flush=True)
            completed = position
            total_elapsed = perf_counter() - total_start
            average_time = total_elapsed / completed
            remaining = total_products - completed
            eta_seconds = remaining * average_time

            print(
                f"  Progress: {completed}/{total_products} ({completed / total_products * 100:.1f}%)",
                flush=True,
            )
            print(f" Average/product: {average_time:.2f}s", flush=True)
            print(f" Estimated remaining: {eta_seconds / 60:.1f} min", flush=True)

        except Exception as exc:
            hard_failures += 1
            product_time = perf_counter() - product_start
            print("\n ❌ PRODUCT FAILED", flush=True)
            print(f" Error: {type(exc).__name__}: {exc}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("[PIPELINE] Writing output...", flush=True)
    output_df = pd.DataFrame(results)
    output_df.to_csv(output_path, index=False)
    total_time = perf_counter() - total_start

    print("\n" + "=" * 70, flush=True)
    print("PIPELINE COMPLETE", flush=True)
    print("=" * 70, flush=True)
    print(f"Processed: {len(results)}/{total_products}", flush=True)
    print(f"Successful: {successful}", flush=True)
    print(f"Validation failures: {validation_failures}", flush=True)
    print(f"Hard failures: {hard_failures}", flush=True)
    print(f"Output: {output_path}", flush=True)
    print(f"Total time: {total_time / 60:.2f} minutes", flush=True)
    if total_products:
        print(f"Average/product: {total_time / total_products:.2f}s", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(
        run_pipeline(
            csv_path="Unihack_ Sample Dataset - Input.csv",
            output_path="output_enriched.csv",
            limit=100,
        )
    )
