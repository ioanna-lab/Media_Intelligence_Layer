"""
MediaStack API Tool — Media Intelligence Agent
MCP-style tool wrapper for the MediaStack News API.

What this does:
    Fetches news articles from a named media outlet across extended date
    ranges. MediaStack free tier allows up to 1 year of historical data,
    which solves the NewsAPI free tier limitation (30 days only).

Why MediaStack complements NewsAPI:
    NewsAPI free tier: last 30 days only.
    MediaStack free tier: up to 1 year back, 500 requests/month.
    Together they give us reliable coverage for all 3 time windows
    needed for temporal drift analysis.

Free tier limits:
    - 500 requests/month
    - 100 results per request
    - 1 year historical data
    - HTTP only (HTTPS requires paid tier) — we handle this below
"""
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

MEDIASTACK_API_KEY = os.getenv("MEDIASTACK_API_KEY")
MEDIASTACK_URL     = "http://api.mediastack.com/v1/news"  # HTTP (free tier)
MAX_RETRIES        = 1   # reduced -- if rate limited, fail fast and use other sources
RETRY_DELAY        = 2
_rate_limited      = False  # module-level flag: once rate limited, skip further calls

# MediaStack uses language codes and source identifiers
# For outlet-specific searches we use keywords rather than source IDs
LANGUAGE = "en"


def get_mediastack_articles(
    outlet_name: str,
    days_back: int = 30,
    max_results: int = 25
) -> list[dict]:
    """
    Fetch news articles mentioning a media outlet from MediaStack.

    Args:
        outlet_name: Name of the media outlet to research
        days_back:   How many days back to search (up to 365 on free tier)
        max_results: Maximum number of results (max 100 per request)

    Returns:
        List of dicts with keys: title, description, published_at, url, source.
        Returns empty list on failure.
    """
    if not MEDIASTACK_API_KEY:
        print("[mediastack_tool] ERROR: MEDIASTACK_API_KEY not set in .env")
        return []

    # Calculate date range
    date_to   = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "access_key": MEDIASTACK_API_KEY,
        "keywords":   outlet_name,
        "languages":  LANGUAGE,
        "date":       f"{date_from},{date_to}",
        "limit":      min(max_results, 100),
        "sort":       "published_desc",
    }

    global _rate_limited

    # If we've been consistently rate limited this session, skip
    if _rate_limited:
        print(f"[mediastack_tool] Skipping '{outlet_name}' — quota exhausted this session")
        return []

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(MEDIASTACK_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                print(f"[mediastack_tool] API error: {data['error'].get('message', 'Unknown')}")
                return []

            articles = []
            for item in data.get("data", []):
                articles.append({
                    "title":        item.get("title", "No title"),
                    "description":  (item.get("description") or "")[:300],
                    "published_at": (item.get("published_at") or "")[:10],
                    "url":          item.get("url", ""),
                    "source":       item.get("source", outlet_name),
                })

            print(f"[mediastack_tool] '{outlet_name}' (last {days_back}d) → {len(articles)} articles")
            return articles

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    print(f"[mediastack_tool] Quota exhausted — skipping MediaStack for this session")
                    _rate_limited = True
                    return []
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"[mediastack_tool] Rate limited. Waiting {wait}s (attempt {attempt+1})...")
                time.sleep(wait)
            else:
                print(f"[mediastack_tool] HTTP error: {e}")
                return []

        except requests.exceptions.Timeout:
            print(f"[mediastack_tool] Timeout on attempt {attempt+1}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[mediastack_tool] Unexpected error: {e}")
            return []

    return []


def get_articles_all_windows(outlet_name: str) -> dict:
    """
    Fetch articles across all 3 time windows for drift analysis.
    Makes ONE API call (180 days) then filters locally to avoid rate limits.

    Returns:
        Dict with keys: window_a (30d), window_b (90d), window_c (180d)
    """
    from datetime import datetime, timedelta

    print(f"\n[mediastack_tool] Fetching 180d window for: {outlet_name} (filtering locally)")

    # One call for 180 days
    all_articles = get_mediastack_articles(outlet_name, days_back=180, max_results=100)

    if not all_articles:
        return {"window_a": [], "window_b": [], "window_c": all_articles}

    # Filter locally by date
    now     = datetime.now()
    cut_30  = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    cut_90  = (now - timedelta(days=90)).strftime("%Y-%m-%d")

    window_a = [a for a in all_articles if a.get("published_at", "") >= cut_30]
    window_b = [a for a in all_articles if a.get("published_at", "") >= cut_90]
    window_c = all_articles  # all 180 days

    print(f"[mediastack_tool] Filtered: {len(window_a)} (30d), {len(window_b)} (90d), {len(window_c)} (180d)")
    return {
        "window_a": window_a,
        "window_b": window_b,
        "window_c": window_c,
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing MediaStack tool...\n")

    articles = get_mediastack_articles("BBC News", days_back=30)
    if articles:
        print(f"Found {len(articles)} articles. First 3:\n")
        for a in articles[:3]:
            print(f"  Title:  {a['title']}")
            print(f"  Date:   {a['published_at']}")
            print(f"  Source: {a['source']}")
            print()
    else:
        print("No articles returned.")

    print("\nTesting all time windows for Reuters...")
    windows = get_articles_all_windows("Reuters")
    for window, arts in windows.items():
        print(f"  {window}: {len(arts)} articles")
