import sys
import os
import json

# Make sure Python can find our other files
sys.path.insert(0, os.path.dirname(__file__))

from processor import process_document
from retriever import build_index, retrieve
from generator import generate_draft
from editor import load_learned_patterns


def run_pipeline(filepath, doc_id=None):
    """
    Run the full pipeline on one document.
    """
    if doc_id is None:
        doc_id = os.path.basename(filepath).replace(".", "_")

    print(f"\n{'='*50}")
    print(f"RUNNING PIPELINE ON: {filepath}")
    print(f"{'='*50}")

    # STAGE 1: Process document
    print("\n[Stage 1] Document Processing...")
    processed = process_document(filepath)
    if "error" in processed:
        print(f"ERROR: {processed['error']}")
        return None

    # STAGE 2: Build retrieval index
    print("\n[Stage 2] Building Retrieval Index...")
    index_data = build_index(processed)

    # STAGE 3: Retrieve evidence + generate draft
    print("\n[Stage 3] Retrieving Evidence & Generating Draft...")

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

    # Remove duplicate chunks
    seen = set()
    unique_chunks = []
    for c in all_chunks:
        if c["chunk_id"] not in seen:
            seen.add(c["chunk_id"])
            unique_chunks.append(c)

    # Load any learned patterns from past edits
    learned_patterns = load_learned_patterns()
    if learned_patterns:
        print(f"  Applying {len(learned_patterns)} learned patterns from past edits")

    draft_result = generate_draft(unique_chunks, learned_patterns)

    # SAVE OUTPUT
    output_path = f"sample_outputs/{doc_id}_draft.txt"
    os.makedirs("sample_outputs", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(draft_result["draft"])

    print(f"\n[Done] Draft saved to: {output_path}")
    print(f"  Tokens used: {draft_result['input_tokens']} in, {draft_result['output_tokens']} out")
    print(f"\n{'='*50}")
    print("GENERATED DRAFT:")
    print('='*50)
    print(draft_result["draft"])

    return draft_result


if __name__ == "__main__":
    # Run on all sample inputs
    sample_dir = "sample_inputs"
    files = [f for f in os.listdir(sample_dir) if f.endswith((".pdf", ".txt"))]

    if not files:
        print("No files found in sample_inputs/")
    else:
        for filename in files:
            filepath = os.path.join(sample_dir, filename)
            doc_id = filename.split(".")[0]
            run_pipeline(filepath, doc_id)