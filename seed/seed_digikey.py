"""Seed the graph with real Digikey parts, 20-30 per category.

Usage:
  python seed/seed_digikey.py                 # pull + write
  python seed/seed_digikey.py --dry-run       # pull only, print counts
  python seed/seed_digikey.py --kind Switch --kind Diode
  python seed/seed_digikey.py --from-cache    # reuse seed/cache/*.json, no API calls

Raw API responses are cached under seed/cache/ so reruns don't burn quota.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import CATALOG  # noqa: E402
from digikey_client import DigikeyClient, RateLimited  # noqa: E402
from mapper import map_product, upsert_cypher  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(__file__).resolve().parent / "cache"
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("seed")


def fetch_category(client: DigikeyClient | None, entry: dict, from_cache: bool) -> list[dict]:
    """Return de-duplicated Digikey Product dicts for one catalog entry."""
    kind, limit = entry["kind"], entry["limit"]
    cache_file = CACHE / f"{kind}.json"
    if from_cache or (client is None):
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        log.warning("no cache for %s", kind)
        return []

    per_query = max(5, -(-limit // len(entry["queries"])))  # ceil
    seen: dict[str, dict] = {}
    for q in entry["queries"]:
        if len(seen) >= limit:
            break
        try:
            resp = client.keyword_search(q, limit=min(per_query + 5, 50))
        except RateLimited as e:
            log.error("%s: %s", kind, e)
            break
        products = resp.get("Products") or []
        log.info("  %-16s %-45r -> %d results (%d total)", kind, q, len(products), resp.get("ProductsCount", 0))
        for prod in products:
            mpn = prod.get("ManufacturerProductNumber")
            if not mpn or mpn in seen:
                continue
            if prod.get("Discontinued") or prod.get("EndOfLife"):
                continue
            seen[mpn] = prod
            if len(seen) >= limit:
                break

    products = list(seen.values())
    CACHE.mkdir(exist_ok=True)
    cache_file.write_text(json.dumps(products, indent=1))
    return products


def write_rows(driver, kind: str, rows: list[dict], database: str) -> int:
    if not rows:
        return 0
    with driver.session(database=database) as session:
        rec = session.execute_write(lambda tx: tx.run(upsert_cypher(kind), rows=rows).single())
    return rec["parts"] if rec else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--kind", action="append", help="only these kind labels")
    args = ap.parse_args()

    entries = [e for e in CATALOG if not args.kind or e["kind"] in args.kind]
    client = None if args.from_cache else DigikeyClient(sandbox=args.sandbox)

    driver = None
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    if not args.dry_run:
        driver = GraphDatabase.driver(
            os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
        )
        driver.verify_connectivity()

    total = 0
    try:
        for entry in entries:
            kind = entry["kind"]
            products = fetch_category(client, entry, args.from_cache)
            rows = [map_product(p, kind_label=kind, source="seed") for p in products]
            if args.dry_run:
                log.info("%-16s %3d parts (dry run)", kind, len(rows))
                for r in rows[:3]:
                    log.info("    e.g. %s | %s | %s | pkg=%s offers=%d", r["manufacturer"]["name"], r["part"]["mpn"],
                             r["part"]["name"][:50], r["package"], len(r["offers"]))
            else:
                n = write_rows(driver, kind, rows, database)
                log.info("%-16s wrote %3d parts", kind, n)
                total += n
    finally:
        if driver:
            driver.close()
    if client:
        log.info("Digikey API calls used: %d", client.calls)
    if not args.dry_run:
        log.info("Total parts upserted: %d", total)


if __name__ == "__main__":
    main()
