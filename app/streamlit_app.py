"""Chat UI for the PCB parts GraphRAG assistant, plus simple "projects"
(named part lists) with a graph view.

Run with: streamlit run app/streamlit_app.py
"""
import streamlit as st
from streamlit_agraph import agraph, Config, Edge, Node

import projects as pj
from rag import ask

st.set_page_config(page_title="PCB Parts GraphRAG", page_icon="🔩", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None

with st.sidebar:
    st.header("Projects")
    all_projects = pj.list_projects()
    options = {p["projectId"]: f"{p['name']} ({p['partCount']} parts)" for p in all_projects}

    new_name = st.text_input("New project name", key="new_project_name")
    if st.button("Create project", disabled=not new_name.strip()):
        created = pj.create_project(new_name.strip())
        st.session_state.active_project_id = created["projectId"]
        st.rerun()

    if options:
        current = st.session_state.active_project_id if st.session_state.active_project_id in options else None
        selected = st.selectbox(
            "Active project",
            options=list(options.keys()),
            format_func=lambda pid: options[pid],
            index=list(options.keys()).index(current) if current else 0,
        )
        st.session_state.active_project_id = selected
        if st.button("Delete this project"):
            pj.delete_project(selected)
            st.session_state.active_project_id = None
            st.rerun()
    else:
        st.caption("No projects yet — create one above.")

    st.divider()

def render_image_gallery(images: list[dict], key_prefix: str) -> None:
    """Thumbnail cards whose <img> src points straight at Digikey's CDN --
    the browser fetches them client-side, the app never proxies the bytes."""
    if not images:
        return
    cols = st.columns(min(len(images), 4))
    for i, img in enumerate(images):
        with cols[i % len(cols)]:
            st.image(img["photoUrl"], caption=img["mpn"])
            price = img.get("price")
            st.caption(f"{img['name'][:40]}" + (f" — ${price:.2f}" if price is not None else ""))
            if img.get("productUrl"):
                st.markdown(f"[View on Digikey]({img['productUrl']})")
            project_id = st.session_state.active_project_id
            if st.button("➕ Add to project", key=f"{key_prefix}-{i}-{img['mpn']}", disabled=not project_id):
                pj.add_part_to_project(project_id, img["mpn"])
                st.toast(f"Added {img['mpn']} to project")


def render_project_graph(project_id: str) -> None:
    graph = pj.get_project_graph(project_id)
    if not graph["nodes"]:
        st.info("This project has no parts yet. Add some from the chat tab.")
        return

    kind_colors = {
        "Manufacturer": "#F4A261", "Footprint": "#2A9D8F", "Interface": "#E9C46A",
        "Package": "#264653", "Firmware": "#8AB17D", "Feature": "#E76F51", "Thread": "#6D6875",
    }
    nodes = [
        Node(
            id=n["id"],
            label=n["label"],
            shape="circularImage" if n.get("photoUrl") else "dot",
            image=n.get("photoUrl"),
            color=kind_colors.get(n["kind"], "#457B9D"),
            size=30 if n.get("photoUrl") else 15,
            title=f"{n['kind']}: {n['label']}",
        )
        for n in graph["nodes"]
    ]
    edges = [Edge(source=r["source"], target=r["target"], label=r["type"]) for r in graph["rels"]]
    config = Config(height=500, width=900, directed=True, physics=True, hierarchical=False)
    agraph(nodes=nodes, edges=edges, config=config)


st.title("🔩 PCB Parts GraphRAG")
st.caption("Ask questions about the seeded Neo4j parts graph (switches, MCUs, BOM requirements, designs, ...).")

tab_chat, tab_project = st.tabs(["💬 Chat", "📦 Project"])

with tab_project:
    project_id = st.session_state.active_project_id
    if not project_id:
        st.info("Create or select a project in the sidebar to view it here.")
    else:
        parts = pj.get_project_parts(project_id)
        st.subheader(f"Parts ({len(parts)})")
        if parts:
            part_cols = st.columns(min(len(parts), 5))
            for i, p in enumerate(parts):
                with part_cols[i % len(part_cols)]:
                    if p.get("photoUrl"):
                        st.image(p["photoUrl"], caption=p["mpn"])
                    else:
                        st.caption(p["mpn"])
                    st.caption(f"{p['kind']} — {p['name'][:30]}")
                    if st.button("Remove", key=f"remove-{p['mpn']}"):
                        pj.remove_part_from_project(project_id, p["mpn"])
                        st.rerun()

        st.subheader("Graph view")
        render_project_graph(project_id)

with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("cypher"):
                with st.expander("Generated Cypher"):
                    st.code(msg["cypher"], language="cypher")
            render_image_gallery(msg.get("images") or [], key_prefix=f"hist-{id(msg)}")

    if question := st.chat_input("e.g. What parts does the RP2040 require?"):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Querying the graph..."):
                result = ask(question)

            if result["error"]:
                st.error(result["error"])
                content = f"Error: {result['error']}"
                cypher = None
                images = []
            else:
                content = result["answer"]
                cypher = result["cypher"]
                images = result["images"]
                st.markdown(content)
                if cypher:
                    with st.expander("Generated Cypher"):
                        st.code(cypher, language="cypher")
                render_image_gallery(images, key_prefix="live")
                if result["rows"]:
                    with st.expander(f"Raw rows ({len(result['rows'])})"):
                        st.write(result["rows"])

        st.session_state.messages.append(
            {"role": "assistant", "content": content, "cypher": cypher, "images": images}
        )

with st.sidebar:
    st.header("Example questions")
    for ex in [
        "What parts does the RP2040 require?",
        "Which switches are cheapest?",
        "What features does the demo design want?",
        "List microcontrollers that support QMK firmware.",
        "Which fasteners are compatible with which standoffs?",
    ]:
        st.markdown(f"- {ex}")
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
