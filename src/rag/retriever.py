"""
Pinecone Retriever — Media Intelligence Agent
Retrieves relevant context from the pre-loaded RAG corpus.

What this does:
    Takes a query string, embeds it using OpenAI text-embedding-3-small,
    and searches the Pinecone index for the most semantically similar
    corpus chunks. Returns the top-k results as context for the agent.

Why this matters:
    The RAG retriever is what grounds the agent's analysis in verified
    industry knowledge. Instead of relying purely on web search results
    (which can be noisy or biased), the agent can retrieve facts from
    our curated corpus — RSF press freedom data, Reuters Institute
    research, outlet profiles, media regulation, etc.

How it connects to the rest of the system:
    retrieve_node in the LangGraph workflow calls this retriever with
    a query derived from the raw research findings. The returned chunks
    become the rag_context in the state, which the synthesise_node
    uses alongside the raw research to produce a grounded analysis.
"""
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

load_dotenv()

PINECONE_API_KEY   = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX     = os.getenv("PINECONE_INDEX_NAME", "media-intelligence")
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL    = "text-embedding-3-small"

# Initialise clients
_pc     = Pinecone(api_key=PINECONE_API_KEY)
_index  = _pc.Index(PINECONE_INDEX)
_openai = OpenAI(api_key=OPENAI_API_KEY)


def _embed(text: str) -> list[float]:
    """
    Embed a single text string using OpenAI text-embedding-3-small.
    Returns a list of 1536 floats.
    """
    response = _openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding


def retrieve(query: str, top_k: int = 5, min_score: float = 0.3) -> list[dict]:
    """
    Retrieve the most relevant corpus chunks for a given query.

    Args:
        query:     The search query (e.g. "BBC editorial independence funding")
        top_k:     Number of results to return (default 5)
        min_score: Minimum similarity score threshold (0-1, default 0.3)
                   Results below this score are filtered out.

    Returns:
        List of dicts with keys: text, source, score.
        Sorted by score descending (most relevant first).
        Returns empty list on failure.

    Example:
        chunks = retrieve("Guardian ownership structure editorial independence")
        # [{"text": "The Scott Trust...", "source": "media_outlets_profiles.txt", "score": 0.72}, ...]
    """
    if not query or not query.strip():
        print("[retriever] Empty query — returning nothing")
        return []

    try:
        # Embed the query
        query_vector = _embed(query)

        # Search Pinecone
        results = _index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )

        # Normalise and filter by minimum score
        chunks = []
        for match in results.matches:
            if match.score >= min_score:
                chunks.append({
                    "text":   match.metadata.get("text", ""),
                    "source": match.metadata.get("source", "unknown"),
                    "score":  round(match.score, 3),
                })

        print(f"[retriever] Query: '{query[:60]}...' → {len(chunks)} chunks (min_score={min_score})")
        return chunks

    except Exception as e:
        print(f"[retriever] Error: {e}")
        return []


def retrieve_for_outlet(outlet_name: str) -> list[dict]:
    """
    Retrieve RAG context specifically relevant to a named media outlet.
    Runs multiple targeted queries and deduplicates results.

    Args:
        outlet_name: The outlet to retrieve context for

    Returns:
        Combined list of unique relevant chunks.
    """
    queries = [
        f"{outlet_name} editorial positioning and coverage strategy",
        f"{outlet_name} ownership funding model",
        f"{outlet_name} audience reach competitive landscape",
        "media industry trends press freedom digital journalism",
    ]

    seen_texts = set()
    all_chunks = []

    for query in queries:
        chunks = retrieve(query, top_k=3)
        for chunk in chunks:
            # Deduplicate by first 100 chars of text
            key = chunk["text"][:100]
            if key not in seen_texts:
                seen_texts.add(key)
                all_chunks.append(chunk)

    # Sort by score descending
    all_chunks.sort(key=lambda x: x["score"], reverse=True)

    print(f"[retriever] Retrieved {len(all_chunks)} unique chunks for '{outlet_name}'")
    return all_chunks


def format_context(chunks: list[dict], max_chars: int = 3000) -> str:
    """
    Format retrieved chunks into a single context string for the LLM.
    Respects a character limit to avoid exceeding context windows.

    Args:
        chunks:    List of chunk dicts from retrieve()
        max_chars: Maximum total characters (default 3000)

    Returns:
        Formatted string ready to inject into a prompt.
    """
    if not chunks:
        return "No relevant industry context found in knowledge base."

    context_parts = []
    total_chars   = 0

    for chunk in chunks:
        source = chunk["source"].replace(".txt", "").replace("_", " ").title()
        entry  = f"[Source: {source}]\n{chunk['text']}\n"

        if total_chars + len(entry) > max_chars:
            break

        context_parts.append(entry)
        total_chars += len(entry)

    return "\n---\n".join(context_parts)


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Pinecone retriever...\n")

    # Test basic retrieval
    print("Query: 'BBC editorial independence funding model'")
    chunks = retrieve("BBC editorial independence funding model", top_k=3)

    if chunks:
        for i, chunk in enumerate(chunks, 1):
            print(f"\nResult {i}:")
            print(f"  Score:  {chunk['score']}")
            print(f"  Source: {chunk['source']}")
            print(f"  Text:   {chunk['text'][:150]}...")
    else:
        print("No results returned.")

    print("\n\nTesting outlet-specific retrieval for 'Reuters'...")
    chunks = retrieve_for_outlet("Reuters")
    print(f"Total unique chunks: {len(chunks)}")

    print("\n\nFormatted context preview:")
    context = format_context(chunks, max_chars=500)
    print(context[:500])
