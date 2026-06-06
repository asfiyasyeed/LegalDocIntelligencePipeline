import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import re

# Load the embedding model once (downloads ~80MB first time, then cached)
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")


def chunk_text(text, chunk_size=300, overlap=50):
    """
    Split text into overlapping chunks of ~300 words.
    Overlap means the last 50 words of chunk 1 appear at the start of chunk 2.
    This prevents cutting off important evidence mid-sentence.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)
        start += chunk_size - overlap  # move forward, but keep overlap

    return chunks


def build_index(processed_doc):
    """
    Take the processed document output from processor.py
    and build a searchable FAISS index from its chunks.
    """
    full_text = processed_doc["raw_text"]
    pages = processed_doc["pages"]

    # Create chunks from the full text
    chunks = chunk_text(full_text)
    print(f"  Created {len(chunks)} chunks from document")

    # Embed all chunks (convert text → vectors)
    print("  Embedding chunks...")
    embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")

    # Build FAISS index
    dimension = embeddings.shape[1]  # size of each vector (384 for MiniLM)
    index = faiss.IndexFlatL2(dimension)  # L2 = euclidean distance search
    index.add(embeddings)

    # Store metadata so we can trace back which chunk came from where
    chunk_metadata = []
    for i, chunk in enumerate(chunks):
        # Estimate which page this chunk is from (rough approximation)
        chunk_metadata.append({
            "chunk_id": i,
            "text": chunk,
            "word_count": len(chunk.split()),
        })

    print(f"  Index built with {index.ntotal} vectors")

    return {
        "index": index,
        "chunks": chunks,
        "metadata": chunk_metadata,
        "embeddings": embeddings,
    }


def retrieve(query, index_data, top_k=3):
    """
    Given a question/query, find the top_k most relevant chunks.
    Returns the chunks + their similarity scores.
    """
    # Embed the query
    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    # Search the FAISS index
    distances, indices = index_data["index"].search(query_embedding, top_k)

    results = []
    for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx == -1:  # FAISS returns -1 if not enough results
            continue
        chunk = index_data["metadata"][idx]
        results.append({
            "rank": rank + 1,
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "distance": float(dist),
            "relevance_score": round(1 / (1 + float(dist)), 3),  # convert distance to 0-1 score
        })

    return results


# Test it
if __name__ == "__main__":
    from processor import process_document

    doc = process_document("sample_inputs/case1.pdf")
    index_data = build_index(doc)

    query = "What are the main claims made by the plaintiff?"
    results = retrieve(query, index_data)

    print(f"\n=== TOP {len(results)} CHUNKS FOR QUERY: '{query}' ===")
    for r in results:
        print(f"\nRank {r['rank']} (score: {r['relevance_score']})")
        print(r["text"][:300])
        print("...")