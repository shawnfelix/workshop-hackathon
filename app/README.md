# PCB Parts GraphRAG App

Minimal Text2Cypher GraphRAG app over the seeded Neo4j parts graph.

## Setup

```bash
pip install -r app/requirements.txt
```

Uses `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `OPENAI_API_KEY`,
`OPENAI_BASE_URL` from the repo root `.env`. Defaults to `gpt-4o-mini` (override with
`OPENAI_MODEL`).

## Run

```bash
streamlit run app/streamlit_app.py
```

## Files

- `rag.py` — `ask(question)`: Text2CypherRetriever + GraphRAG, returns answer + generated
  Cypher + raw rows. No embeddings/vector index required — reads the graph structurally.
- `streamlit_app.py` — chat UI with expandable "Generated Cypher" / "Raw rows" per answer.
