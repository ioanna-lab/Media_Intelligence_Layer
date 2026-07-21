"""
RAG Ingestion Pipeline — Media Intelligence Agent
Reads corpus documents, chunks them, embeds with OpenAI, and upserts to Pinecone.

Usage:
    python src/rag/ingest.py
"""
import os
import glob
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

# ── Config ────────────────────────────────────────────────
PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME", "media-intelligence")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL    = "text-embedding-3-small"
CHUNK_SIZE         = 500   # words per chunk
CHUNK_OVERLAP      = 50    # words overlap between chunks
CORPUS_DIR         = "corpus"

# ── Clients ───────────────────────────────────────────────
pc     = Pinecone(api_key=PINECONE_API_KEY)
index  = pc.Index(PINECONE_INDEX)
openai = OpenAI(api_key=OPENAI_API_KEY)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words  = text.split()
    chunks = []
    start  = 0

    while start < len(words):
        end   = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using OpenAI text-embedding-3-small."""
    response = openai.embeddings.create(
        input=texts,
        model=EMBEDDING_MODEL
    )
    return [item.embedding for item in response.data]


def ingest_file(filepath: str) -> int:
    """Read a file, chunk it, embed it, and upsert to Pinecone. Returns chunk count."""
    filename = os.path.basename(filepath)
    doc_id   = filename.replace(".txt", "").replace(" ", "_")

    print(f"\n  Processing: {filename}")

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"  Chunks: {len(chunks)}")

    # Embed in batches of 10
    batch_size = 10
    vectors    = []

    for i in range(0, len(chunks), batch_size):
        batch      = chunks[i:i + batch_size]
        embeddings = embed(batch)

        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            chunk_id = f"{doc_id}_chunk_{i + j}"
            vectors.append({
                "id":     chunk_id,
                "values": embedding,
                "metadata": {
                    "source":   filename,
                    "doc_id":   doc_id,
                    "chunk_id": i + j,
                    "text":     chunk
                }
            })

    # Upsert to Pinecone in batches of 100
    upsert_batch = 100
    for i in range(0, len(vectors), upsert_batch):
        index.upsert(vectors=vectors[i:i + upsert_batch])

    print(f"  Upserted: {len(vectors)} vectors")
    return len(vectors)


def main():
    print("=" * 50)
    print("Media Intelligence Agent — RAG Ingestion")
    print("=" * 50)
    print(f"Index:  {PINECONE_INDEX}")
    print(f"Corpus: {CORPUS_DIR}/")

    # Find all .txt files in corpus/
    files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))

    if not files:
        print(f"\nNo .txt files found in {CORPUS_DIR}/")
        print("Make sure your corpus files are in the corpus/ folder.")
        return

    print(f"\nFound {len(files)} files to ingest:")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    total_vectors = 0
    for filepath in files:
        try:
            count = ingest_file(filepath)
            total_vectors += count
        except Exception as e:
            print(f"  ERROR processing {filepath}: {e}")

    print("\n" + "=" * 50)
    print(f"Ingestion complete!")
    print(f"Total vectors upserted: {total_vectors}")
    print(f"Check your index at: https://app.pinecone.io")
    print("=" * 50)

    # Quick test query
    print("\nRunning test query: 'BBC editorial positioning'...")
    test_embedding = embed(["BBC editorial positioning"])[0]
    results = index.query(
        vector=test_embedding,
        top_k=3,
        include_metadata=True
    )

    print(f"Top 3 results:")
    for match in results.matches:
        print(f"  Score: {match.score:.3f} | Source: {match.metadata['source']}")
        print(f"  Text:  {match.metadata['text'][:100]}...")


if __name__ == "__main__":
    main()
