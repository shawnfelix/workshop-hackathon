"""Text2Cypher GraphRAG over the PCB parts graph.

Loads Neo4j + OpenAI credentials from the repo root .env and exposes a single
`ask(question)` function that returns a natural-language answer plus the
generated Cypher and raw rows for transparency.
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv
from neo4j import GraphDatabase, Record
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.retrievers.text2cypher import Text2CypherRetrievalError
from neo4j_graphrag.types import RetrieverResultItem

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# Schema hint keeps the LLM focused on this graph's real labels/relationships
# instead of paying for (and drifting from) a full auto-fetched schema dump.
NEO4J_SCHEMA = """
Node labels: Part (+ secondary kind label: Switch, Diode, Microcontroller, Connector,
  HotswapSocket, Stabilizer, Resistor, Capacitor, Led, Crystal, VoltageRegulator,
  Fastener, Standoff, FlashMemory, Encoder, Display, Battery, EsdProtection, TactileSwitch),
  Manufacturer, Supplier, Offer, Category, Footprint, Package, Interface, Thread,
  Firmware, Design, Feature.

Part properties: partId, mpn, name, description, datasheetUrl, lifecycle, source,
  digikeyPn, verified, specs (list of "key=value" strings).
Offer properties: offerId, sku, url, unitPrice (float), currency, moq, stock (int).
Category properties: name, path.
Design properties: designId, name, layout, revision.
Feature properties: name, description, keywords.

Relationships:
  (Part)-[:MADE_BY]->(Manufacturer)
  (Part)-[:IN_CATEGORY]->(Category), (Category)-[:SUBCATEGORY_OF]->(Category)
  (Part)-[:HAS_FOOTPRINT]->(Footprint)
  (Part)-[:HAS_PACKAGE]->(Package)
  (Part)-[:IMPLEMENTS]->(Interface)
  (Part)-[:HAS_THREAD]->(Thread)
  (Part)-[:SUPPORTED_BY]->(Firmware)
  (Part)-[:OFFERED_AS]->(Offer)-[:SOLD_BY]->(Supplier)
  (Part)-[:REQUIRES {qty, note}]->(Part)
  (Part)-[:COMPATIBLE_WITH {reason, source}]->(Part)
  (Part)-[:PROVIDES]->(Feature)
  (Design)-[:USES {qty, refDes}]->(Part)
  (Design)-[:WANTS]->(Feature)
"""

EXAMPLES = [
    "Q: What parts does the RP2040 require? "
    "A: MATCH (mcu:Part:Microcontroller)-[:MADE_BY]->(m:Manufacturer) "
    "WHERE toLower(m.name) CONTAINS 'raspberry pi' OR mcu.description CONTAINS '56QFN' "
    "MATCH (mcu)-[r:REQUIRES]->(dep) RETURN mcu.mpn, dep.mpn, dep.name, r.qty, r.note",
    "Q: Which switches are cheapest? "
    "A: MATCH (p:Part:Switch)-[:OFFERED_AS]->(o:Offer) RETURN p.mpn, p.name, o.unitPrice ORDER BY o.unitPrice ASC LIMIT 10",
    "Q: What features does a design want that no part provides? "
    "A: MATCH (d:Design)-[:WANTS]->(f:Feature) WHERE NOT (:Part)-[:PROVIDES]->(f) RETURN d.name, f.name",
    "Q: What features does the demo design want? "
    "A: MATCH (d:Design)-[:WANTS]->(f:Feature) RETURN d.name, d.designId, f.name, f.description",
]

# Part names/descriptions rarely contain the colloquial chip name (e.g. "RP2040"),
# only the Digikey MPN/description/specs do -- steer the LLM to search broadly.
SEARCH_HINT = (
    "When the question names a specific chip, connector, or component by a common name "
    "(e.g. RP2040, WS2812B, USB-C), match against mpn, name, description AND specs "
    "with CONTAINS/toLower, not just an exact mpn equality. Data is sourced from Digikey, "
    "so common chip codenames (like 'RP2040') may only appear via the Manufacturer name "
    "(e.g. Manufacturer 'Raspberry Pi') or package details, not the Part's own text fields -- "
    "if a direct text match returns nothing, also try MADE_BY manufacturer name."
)


@lru_cache(maxsize=1)
def _driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )


def _row_formatter(record: Record) -> RetrieverResultItem:
    # content stays a string (GraphRAG joins it into the LLM prompt as-is);
    # the structured dict goes in metadata so the UI can pull mpn/photoUrl
    # for the client-side image gallery without re-parsing str(record).
    data = record.data()
    return RetrieverResultItem(content=str(record), metadata=data)


@lru_cache(maxsize=1)
def _rag() -> tuple[GraphRAG, Text2CypherRetriever]:
    llm = OpenAILLM(
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        model_params={"temperature": 0},
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    retriever = Text2CypherRetriever(
        driver=_driver(),
        llm=llm,
        neo4j_schema=NEO4J_SCHEMA + "\n" + SEARCH_HINT,
        examples=EXAMPLES,
        neo4j_database=os.getenv("NEO4J_DATABASE"),
        result_formatter=_row_formatter,
    )
    return GraphRAG(retriever=retriever, llm=llm), retriever


def fetch_part_images(mpns: list[str]) -> list[dict]:
    """Look up photoUrl/name/price for a set of MPNs so the UI can render
    thumbnail cards whose images are fetched client-side straight from Digikey."""
    if not mpns:
        return []
    query = """
    MATCH (p:Part) WHERE p.mpn IN $mpns AND p.photoUrl IS NOT NULL
    OPTIONAL MATCH (p)-[:OFFERED_AS]->(o:Offer)
    WITH p, min(o.unitPrice) AS price
    RETURN p.mpn AS mpn, p.name AS name, p.photoUrl AS photoUrl,
           p.productUrl AS productUrl, price
    """
    with _driver().session(database=os.getenv("NEO4J_DATABASE")) as session:
        return [r.data() for r in session.run(query, mpns=mpns)]


def ask(question: str) -> dict:
    """Run a natural-language question through Text2Cypher GraphRAG.

    Returns {"answer": str, "cypher": str | None, "rows": list, "error": str | None}.
    """
    rag, retriever = _rag()
    try:
        response = rag.search(
            query_text=question,
            return_context=True,
            response_fallback="I couldn't find anything in the graph matching that question. "
            "Try rephrasing with a part name, MPN, category, or feature.",
        )
    except Text2CypherRetrievalError as e:
        return {"answer": None, "cypher": None, "rows": [], "images": [], "error": str(e)}

    result = response.retriever_result
    cypher = getattr(result, "metadata", {}).get("cypher") if result else None
    items = result.items if result else []
    rows = [item.metadata for item in items]

    # rows are dicts like {"p.mpn": "...", ...} -- pull any *.mpn-ish values
    # to fetch their Digikey photo for the gallery.
    mpns = sorted({v for row in rows for k, v in row.items() if k.endswith("mpn") and isinstance(v, str)})
    images = fetch_part_images(mpns)

    return {"answer": response.answer, "cypher": cypher, "rows": rows, "images": images, "error": None}


def close() -> None:
    if _driver.cache_info().currsize:
        _driver().close()
