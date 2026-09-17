"""Run a .cypher file against Aura, one statement per transaction (statements separated by lone ';' lines)."""
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from neo4j import GraphDatabase  # noqa: E402


def split_statements(text: str) -> list[str]:
    stmts, buf = [], []
    for line in text.splitlines():
        if line.strip() == ";":
            stmt = "\n".join(buf).strip()
            if stmt:
                stmts.append(stmt)
            buf = []
        else:
            buf.append(line)
    tail = "\n".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def main():
    path = Path(sys.argv[1])
    stmts = split_statements(path.read_text())
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    ok = 0
    with driver.session(database=database) as session:
        for i, stmt in enumerate(stmts, 1):
            try:
                session.run(stmt).consume()
                ok += 1
            except Exception as e:
                print(f"[{i}/{len(stmts)}] FAILED: {e}\n  stmt: {stmt[:120]}")
    driver.close()
    print(f"Executed {ok}/{len(stmts)} statements OK")


if __name__ == "__main__":
    main()
