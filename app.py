import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from processor import process_document
from retriever import build_index, retrieve
from generator import generate_draft
from editor import process_operator_edit, load_learned_patterns

# Page config
st.set_page_config(
    page_title="Legal Document Pipeline",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Legal Document Intelligence Pipeline")
st.markdown("Upload a legal document → get a grounded Case Fact Summary → improve it over time.")

# Sidebar info
with st.sidebar:
    st.header("How it works")
    st.markdown("""
    **Stage 1 — Process**  
    Extracts text from PDF or TXT files. Falls back to OCR for scanned pages.
    
    **Stage 2 — Retrieve**  
    Finds the most relevant evidence chunks using vector search.
    
    **Stage 3 — Generate**  
    Builds a grounded draft using only what's in your document.
    
    **Stage 4 — Learn**  
    Edit the draft → the system learns your preferences for next time.
    """)

    st.divider()

    # Show learned patterns
    patterns = load_learned_patterns()
    st.header(f"Learned Patterns ({len(patterns)})")
    if patterns:
        for p in patterns:
            st.markdown(f"- {p}")
    else:
        st.caption("No patterns learned yet. Edit a draft to start learning.")

# Main tabs
tab1, tab2 = st.tabs(["Generate Draft", "Improve from Edits"])

# ─── TAB 1: GENERATE ───────────────────────────────────────────
with tab1:
    st.header("Step 1 — Upload a Document")

    uploaded_file = st.file_uploader(
        "Upload a legal document",
        type=["pdf", "txt"],
        help="Supports PDF (including scanned) and plain text files"
    )

    if uploaded_file is not None:
        # Save uploaded file temporarily
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Uploaded: {uploaded_file.name}")

        # Show processing button
        if st.button("Generate Case Fact Summary", type="primary"):

            with st.spinner("Stage 1: Extracting text..."):
                processed = process_document(temp_path)

            if "error" in processed:
                st.error(f"Processing failed: {processed['error']}")
            else:
                # Show extraction info
                col1, col2, col3 = st.columns(3)
                col1.metric("Pages", processed["total_pages"])
                col2.metric("Confidence", f"{processed['confidence'] * 100:.0f}%")
                col3.metric("Dates Found", len(processed["structured"]["dates"]))

                with st.expander("View extracted structured fields"):
                    st.json(processed["structured"])

                with st.spinner("Stage 2: Building retrieval index..."):
                    index_data = build_index(processed)

                with st.spinner("Stage 3: Retrieving evidence and generating draft..."):
                    queries = [
                        "What are the main claims and allegations?",
                        "Who are the parties and what are the key dates?",
                        "What relief is being sought?",
                        "What contract clauses are referenced?",
                    ]
                    all_chunks = []
                    for query in queries:
                        chunks = retrieve(query, index_data, top_k=2)
                        all_chunks.extend(chunks)

                    seen = set()
                    unique_chunks = []
                    for c in all_chunks:
                        if c["chunk_id"] not in seen:
                            seen.add(c["chunk_id"])
                            unique_chunks.append(c)

                    learned_patterns = load_learned_patterns()
                    draft_result = generate_draft(unique_chunks, learned_patterns)

                st.success("Draft generated!")

                # Show retrieved evidence
                with st.expander("View retrieved evidence chunks"):
                    for chunk in unique_chunks:
                        st.markdown(f"**Chunk {chunk['chunk_id']} — relevance: {chunk['relevance_score']}**")
                        st.text(chunk["text"][:400])
                        st.divider()

                # Show the draft
                st.header("Generated Case Fact Summary")
                st.text_area(
                    "Draft output",
                    value=draft_result["draft"],
                    height=500,
                    key="generated_draft"
                )

                # Save to session state so Tab 2 can use it
                st.session_state["last_draft"] = draft_result["draft"]
                st.session_state["last_doc_id"] = uploaded_file.name.split(".")[0]

                # Download button
                st.download_button(
                    label="Download Draft",
                    data=draft_result["draft"],
                    file_name=f"{uploaded_file.name.split('.')[0]}_draft.txt",
                    mime="text/plain"
                )

                if learned_patterns:
                    st.info(f"This draft applied {len(learned_patterns)} learned patterns from previous operator edits.")

        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ─── TAB 2: IMPROVE FROM EDITS ─────────────────────────────────
with tab2:
    st.header("Step 2 — Review and Edit the Draft")
    st.markdown("Edit the draft below. When you submit, the system learns from your changes and applies them to future drafts.")

    # Pre-fill with last generated draft if available
    default_draft = st.session_state.get("last_draft", "")
    doc_id = st.session_state.get("last_doc_id", "unknown_doc")

    if not default_draft:
        st.info("Generate a draft in the first tab, then come here to edit it.")

    original_draft = st.text_area(
        "Original draft (do not edit this box)",
        value=default_draft,
        height=300,
        disabled=True
    )

    edited_draft = st.text_area(
        "Your edited version (make your corrections here)",
        value=default_draft,
        height=300,
        key="edited_draft"
    )

    if st.button("Submit Edit — Learn from My Changes", type="primary"):
        if not edited_draft.strip():
            st.warning("Please write your edited version first.")
        elif edited_draft == original_draft:
            st.warning("No changes detected. Edit the draft before submitting.")
        else:
            with st.spinner("Extracting patterns from your edits..."):
                new_patterns = process_operator_edit(doc_id, original_draft, edited_draft)

            st.success("Learned from your edits!")
            st.markdown("**Patterns now active for future drafts:**")
            for p in new_patterns:
                st.markdown(f"- {p}")
            st.info("Run a new document through Tab 1 to see the improvement.")