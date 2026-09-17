"""Map Digikey ProductSearch v4 `Product` JSON -> rows for the graph.

Shared by the seeder and the runtime gap-filling agent so both write identical shapes.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

ALLOWED_KIND_LABELS = {
    "Switch", "Diode", "Microcontroller", "Connector", "HotswapSocket", "Stabilizer",
    "Resistor", "Capacitor", "Led", "Crystal", "VoltageRegulator", "Fastener", "Standoff",
    "Plate", "Case", "Keycap", "FlashMemory", "Encoder", "Display", "Battery", "Charger",
    "EsdProtection", "TactileSwitch",
}

# Digikey parameter names that describe the physical package
PACKAGE_PARAMS = ("Package / Case", "Supplier Device Package", "Mounting Type")
# packages where the package name doubles as the PCB footprint
PASSIVE_PACKAGE_RE = re.compile(r"^(0402|0603|0805|1206|1210|SOD-123|SOD-323|SOT-23|SOT-23-5|SOT-223|SOT-89)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _category_path(cat: dict | None) -> list[dict]:
    """Walk the nested CategoryNode chain into [{name, path}] from root to leaf."""
    out: list[dict] = []
    node = cat
    parts: list[str] = []
    while node and node.get("Name"):
        parts.append(node["Name"].strip())
        out.append({"name": parts[-1], "path": "/".join(parts), "digikeyId": node.get("CategoryId")})
        children = node.get("ChildCategories") or []
        node = children[0] if children else None
    return out


def _params(product: dict) -> dict[str, str]:
    return {
        p["ParameterText"].strip(): (p.get("ValueText") or "").strip()
        for p in product.get("Parameters") or []
        if p.get("ParameterText")
    }


def _package_name(params: dict[str, str]) -> str | None:
    for key in PACKAGE_PARAMS[:2]:
        v = params.get(key)
        if v and v != "-":
            return v.split(",")[0].split("(")[0].strip()
    return None


def _price(variation: dict, product: dict) -> float:
    breaks = variation.get("StandardPricing") or []
    if breaks:
        return float(breaks[0].get("UnitPrice") or 0.0)
    return float(product.get("UnitPrice") or 0.0)


def map_product(product: dict, *, kind_label: str, source: str = "seed", extra_props: dict | None = None) -> dict:
    """Return a flat row with part, manufacturer, category chain, package, and offers."""
    if kind_label not in ALLOWED_KIND_LABELS:
        raise ValueError(f"unknown kind label {kind_label!r}")

    mpn = (product.get("ManufacturerProductNumber") or "").strip()
    mfr = (product.get("Manufacturer") or {}).get("Name", "Unknown").strip()
    desc = product.get("Description") or {}
    params = _params(product)
    status = (product.get("ProductStatus") or {}).get("Status") or "Unknown"
    variations = product.get("ProductVariations") or []
    now = _now()

    package = _package_name(params)
    footprint = None
    if package and PASSIVE_PACKAGE_RE.match(package):
        footprint = PASSIVE_PACKAGE_RE.match(package).group(1)

    offers = []
    for v in variations:
        sku = v.get("DigiKeyProductNumber")
        if not sku:
            continue
        offers.append(
            {
                "offerId": f"digikey:{sku}",
                "sku": sku,
                "url": product.get("ProductUrl"),
                "unitPrice": _price(v, product),
                "currency": "USD",
                "moq": int(v.get("MinimumOrderQuantity") or 1),
                "stock": int(v.get("QuantityAvailableforPackageType") or 0),
                "packaging": (v.get("PackageType") or {}).get("Name"),
                "standardPackage": int(v.get("StandardPackage") or 0),
                "priceBreaks": [
                    f"{b.get('BreakQuantity')}@{b.get('UnitPrice')}" for b in v.get("StandardPricing") or []
                ],
                "marketplace": bool(v.get("MarketPlace")),
                "lastCheckedAt": now,
            }
        )

    part = {
        "partId": f"{mfr}|{mpn}",
        "mpn": mpn,
        "name": (desc.get("ProductDescription") or mpn).strip(),
        "description": (desc.get("DetailedDescription") or "").strip(),
        "datasheetUrl": product.get("DatasheetUrl"),
        "photoUrl": product.get("PhotoUrl"),
        "productUrl": product.get("ProductUrl"),
        "lifecycle": status,
        "series": (product.get("Series") or {}).get("Name"),
        "rohs": (product.get("Classifications") or {}).get("RohsStatus"),
        "specs": [f"{k}={v}" for k, v in params.items() if v and v != "-"],
        "source": source,
        "digikeyPn": offers[0]["sku"] if offers else None,
        "digikeyQtyAvailable": int(product.get("QuantityAvailable") or 0),
        "ingestedAt": now,
        "verified": source == "seed",
    }
    if extra_props:
        part.update(extra_props)

    return {
        "kind": kind_label,
        "part": part,
        "manufacturer": {"name": mfr, "digikeyId": (product.get("Manufacturer") or {}).get("Id")},
        "categories": _category_path(product.get("Category")),
        "package": package,
        "footprint": footprint,
        "offers": offers,
    }


# One statement per kind label; label is interpolated after whitelist check above.
UPSERT_ROWS_CYPHER = """
UNWIND $rows AS row
MERGE (p:Part {partId: row.part.partId})
SET p += row.part, p:%(label)s
WITH p, row
MERGE (m:Manufacturer {name: row.manufacturer.name})
  ON CREATE SET m.digikeyId = row.manufacturer.digikeyId
MERGE (p)-[:MADE_BY]->(m)
WITH p, row
CALL (p, row) {
  WITH p, row
  WHERE row.package IS NOT NULL
  MERGE (pk:Package {name: row.package})
  MERGE (p)-[:HAS_PACKAGE]->(pk)
}
CALL (p, row) {
  WITH p, row
  WHERE row.footprint IS NOT NULL
  MERGE (fp:Footprint {name: row.footprint})
  MERGE (p)-[:HAS_FOOTPRINT]->(fp)
}
CALL (p, row) {
  WITH p, row
  WHERE size(row.categories) > 0
  UNWIND range(0, size(row.categories) - 1) AS i
  WITH p, row, i, row.categories[i] AS c
  MERGE (cat:Category {path: c.path})
    ON CREATE SET cat.name = c.name, cat.digikeyId = c.digikeyId
  WITH p, row, i, cat
  CALL (row, i, cat) {
    WITH row, i, cat
    WHERE i > 0
    MERGE (parent:Category {path: row.categories[i-1].path})
    MERGE (cat)-[:SUBCATEGORY_OF]->(parent)
  }
  WITH p, i, cat, size(row.categories) AS n
  WHERE i = n - 1
  MERGE (p)-[:IN_CATEGORY]->(cat)
}
CALL (p, row) {
  WITH p, row
  MERGE (s:Supplier {name: 'Digikey'})
    ON CREATE SET s.website = 'https://www.digikey.com'
  WITH p, row, s
  UNWIND row.offers AS o
  MERGE (of:Offer {offerId: o.offerId})
  SET of += o
  MERGE (p)-[:OFFERED_AS]->(of)
  MERGE (of)-[:SOLD_BY]->(s)
}
RETURN count(DISTINCT p) AS parts
"""


def upsert_cypher(kind_label: str) -> str:
    if kind_label not in ALLOWED_KIND_LABELS:
        raise ValueError(kind_label)
    return UPSERT_ROWS_CYPHER % {"label": kind_label}
