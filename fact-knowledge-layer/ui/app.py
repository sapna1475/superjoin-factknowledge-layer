import os

import requests
import streamlit as st

API = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Fact Knowledge Layer", layout="wide")
st.title("Fact Knowledge Layer")

uploaded = st.file_uploader("Upload a PDF", type="pdf")
if uploaded and st.button("Process document"):
    with st.spinner("Extracting facts..."):
        resp = requests.post(f"{API}/documents", files={"file": (uploaded.name, uploaded.getvalue())})
    if resp.ok:
        st.success(f"Extracted {resp.json()['facts_extracted']} facts.")
    else:
        st.error("Upload failed.")

st.divider()

documents = requests.get(f"{API}/documents").json()
doc_options = {"All documents": None}
doc_options.update({d["filename"]: d["id"] for d in documents})
selected = st.selectbox("Document", list(doc_options.keys()))

tab_facts, tab_relations = st.tabs(["Facts", "Relations"])

with tab_facts:
    params = {"document_id": doc_options[selected]} if doc_options[selected] else {}
    for fact in requests.get(f"{API}/facts", params=params).json():
        d = fact["data"]
        title = f"{d.get('subject', '')} — {d.get('predicate', '')}: {d.get('value', '')} {d.get('unit') or ''}"
        with st.expander(title.strip()):
            st.write(f"Source: {fact['filename']}, page {fact['page']}")
            st.write(f'Quote: "{fact["quote"]}"')
            if not fact["grounded"]:
                st.warning("Quote not found verbatim in source page")

with tab_relations:
    relation_type = st.selectbox("Type", ["All", "corroborates", "contradicts", "reconciled"])
    params = {} if relation_type == "All" else {"relation_type": relation_type}
    for rel in requests.get(f"{API}/relations", params=params).json():
        a, b = rel["fact_a"], rel["fact_b"]
        st.markdown(f"**{rel['relation_type']}**  ·  confidence {rel['confidence']:.2f}")
        st.write(f"A: \"{a['quote']}\" — {a['filename']}, page {a['page']}")
        st.write(f"B: \"{b['quote']}\" — {b['filename']}, page {b['page']}")
        st.caption(rel["explanation"])
        st.divider()
