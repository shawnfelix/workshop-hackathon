"""Simple user 'projects' (a named list of parts) backed by the same Neo4j graph.

(:Project {projectId, name, createdAt})-[:CONTAINS]->(:Part)

Kept intentionally minimal: no auth/multi-tenant scoping, projects are global
to the graph. Good enough for a single-user demo/workshop app.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from rag import _driver  # reuse the same cached driver/credentials


def _db() -> str | None:
    return os.getenv("NEO4J_DATABASE")


def list_projects() -> list[dict]:
    query = """
    MATCH (pr:Project)
    OPTIONAL MATCH (pr)-[:CONTAINS]->(p:Part)
    RETURN pr.projectId AS projectId, pr.name AS name, pr.createdAt AS createdAt,
           count(p) AS partCount
    ORDER BY pr.createdAt DESC
    """
    with _driver().session(database=_db()) as session:
        return [r.data() for r in session.run(query)]


def create_project(name: str) -> dict:
    project_id = str(uuid.uuid4())
    query = """
    CREATE (pr:Project {projectId: $projectId, name: $name, createdAt: $createdAt})
    RETURN pr.projectId AS projectId, pr.name AS name, pr.createdAt AS createdAt
    """
    with _driver().session(database=_db()) as session:
        rec = session.run(
            query, projectId=project_id, name=name, createdAt=datetime.now(timezone.utc).isoformat()
        ).single()
    return rec.data()


def add_part_to_project(project_id: str, mpn: str) -> bool:
    query = """
    MATCH (pr:Project {projectId: $projectId})
    MATCH (p:Part {mpn: $mpn})
    MERGE (pr)-[:CONTAINS]->(p)
    RETURN count(p) AS n
    """
    with _driver().session(database=_db()) as session:
        rec = session.run(query, projectId=project_id, mpn=mpn).single()
    return bool(rec and rec["n"])


def remove_part_from_project(project_id: str, mpn: str) -> None:
    query = """
    MATCH (pr:Project {projectId: $projectId})-[r:CONTAINS]->(p:Part {mpn: $mpn})
    DELETE r
    """
    with _driver().session(database=_db()) as session:
        session.run(query, projectId=project_id, mpn=mpn).consume()


def delete_project(project_id: str) -> None:
    query = "MATCH (pr:Project {projectId: $projectId}) DETACH DELETE pr"
    with _driver().session(database=_db()) as session:
        session.run(query, projectId=project_id).consume()


def get_project_parts(project_id: str) -> list[dict]:
    query = """
    MATCH (pr:Project {projectId: $projectId})-[:CONTAINS]->(p:Part)
    OPTIONAL MATCH (p)-[:OFFERED_AS]->(o:Offer)
    WITH p, min(o.unitPrice) AS price
    RETURN p.mpn AS mpn, p.name AS name, p.photoUrl AS photoUrl, price,
           [l IN labels(p) WHERE l <> 'Part'][0] AS kind
    ORDER BY p.mpn
    """
    with _driver().session(database=_db()) as session:
        return [r.data() for r in session.run(query, projectId=project_id)]


def get_project_graph(project_id: str) -> dict:
    """Return nodes/edges among the project's parts plus their direct
    graph relationships (REQUIRES, COMPATIBLE_WITH, MADE_BY, HAS_FOOTPRINT, etc.)
    so the UI can render an interactive node-link diagram.
    """
    query = """
    MATCH (pr:Project {projectId: $projectId})-[:CONTAINS]->(p:Part)
    WITH collect(p) AS parts
    UNWIND parts AS p
    OPTIONAL MATCH (p)-[r]-(n)
      WHERE n IN parts OR n:Manufacturer OR n:Footprint OR n:Interface
         OR n:Package OR n:Firmware OR n:Feature OR n:Thread
    WITH parts, collect(DISTINCT p) + collect(DISTINCT n) AS all_nodes,
         collect(DISTINCT {rel: r, a: p, b: n}) AS rels
    UNWIND all_nodes AS node
    WITH parts, rels, collect(DISTINCT node) AS nodes
    RETURN
      [n IN nodes WHERE n IS NOT NULL | {
        id: [l IN labels(n) WHERE l <> 'Part'][0] + ':' + coalesce(n.partId, n.name, n.mpn, toString(id(n))),
        label: coalesce(n.mpn, n.name),
        kind: [l IN labels(n) WHERE l <> 'Part'][0],
        photoUrl: n.photoUrl
      }] AS nodes,
      [x IN rels WHERE x.rel IS NOT NULL | {
        source: [l IN labels(x.a) WHERE l <> 'Part'][0] + ':' + coalesce(x.a.partId, x.a.name, x.a.mpn, toString(id(x.a))),
        target: [l IN labels(x.b) WHERE l <> 'Part'][0] + ':' + coalesce(x.b.partId, x.b.name, x.b.mpn, toString(id(x.b))),
        type: type(x.rel)
      }] AS rels
    """
    with _driver().session(database=_db()) as session:
        rec = session.run(query, projectId=project_id).single()
    if not rec:
        return {"nodes": [], "rels": []}
    return {"nodes": rec["nodes"], "rels": rec["rels"]}
