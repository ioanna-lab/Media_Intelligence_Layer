"""
Tavily Web Search Tool — Media Intelligence Agent
MCP-style tool wrapper for the Tavily Search API.

What this does:
    Accepts a search query string and returns a clean list of web search
    results that the ReAct agent can reason about.

Why we need this:
    The agent cannot call raw APIs directly. It needs a clean, typed
    function with a predictable interface. This wrapper handles the HTTP
    call, error handling, retries, and normalises the response into a
    consistent format.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_URL     = "https://api.tavily.com/search"
MAX_RETRIES    = 2
RETRY_DELAY    = 2  # seconds


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Tavily and return clean, structured results.

    Args:
        query:       The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        List of dicts, each with keys: title, url, snippet.
        Returns empty list on failure.

    Example:
        results = web_search("Reuters editorial focus 2024")
        # [{"title": "...", "url": "...", "snippet": "..."}, ...]
    """
    if not TAVILY_API_KEY:
        print("[tavily_tool] ERROR: TAVILY_API_KEY not set in .env")
        return []

    payload = {
        "api_key":     TAVILY_API_KEY,
        "query":       query,
        "max_results": max_results,
        "search_depth": "basic",       # "basic" or "advanced" (advanced costs more credits)
        "include_answer": False,       # we want raw results, not a pre-summarised answer
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(TAVILY_URL, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Normalise: extract only what the agent needs
            results = []
            for item in data.get("results", []):
                results.append({
                    "title":   item.get("title", "No title"),
                    "url":     item.get("url", ""),
                    "snippet": item.get("content", "")[:500],  # cap at 500 chars
                })

            print(f"[tavily_tool] Query: '{query}' → {len(results)} results")
            return results

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                # Rate limited — wait and retry
                print(f"[tavily_tool] Rate limited. Waiting {RETRY_DELAY}s... (attempt {attempt+1})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[tavily_tool] HTTP error: {e}")
                return []

        except requests.exceptions.Timeout:
            print(f"[tavily_tool] Timeout on attempt {attempt+1}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[tavily_tool] Unexpected error: {e}")
            return []

    print(f"[tavily_tool] All retries exhausted for query: '{query}'")
    return []


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Tavily tool...\n")
    results = web_search("BBC News editorial focus and coverage strategy")

    if results:
        for i, r in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Title:   {r['title']}")
            print(f"  URL:     {r['url']}")
            print(f"  Snippet: {r['snippet'][:100]}...")
            print()
    else:
        print("No results returned.")
