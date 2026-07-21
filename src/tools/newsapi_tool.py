"""
NewsAPI Tool — Media Intelligence Agent
MCP-style tool wrapper for the NewsAPI.

What this does:
    Accepts a media outlet name and a time window (number of days back)
    and returns a list of recent articles from that outlet.

Why we need 3 time windows:
    This tool is called THREE times per outlet — for 30, 90, and 180 days.
    By comparing the results across windows, the drift_analysis_node can
    detect which topics are emerging, fading, or stable over time.

NewsAPI source IDs:
    NewsAPI identifies outlets by a source ID string, not the outlet name.
    e.g. "BBC News" → "bbc-news", "Reuters" → "reuters"
    The OUTLET_MAP below handles this translation.
"""
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
NEWSAPI_URL = "https://newsapi.org/v2/everything"
MAX_RETRIES = 2
RETRY_DELAY = 2

# Translation map: outlet name → NewsAPI source ID
# Add more outlets here as needed
OUTLET_MAP = {
    "bbc":            "bbc-news",
    "bbc news":       "bbc-news",
    "reuters":        "reuters",
    "guardian":       "the-guardian-uk",
    "the guardian":   "the-guardian-uk",
    "der spiegel":    "der-spiegel",
    "spiegel":        "der-spiegel",
    "new york times": "the-new-york-times",
    "nyt":            "the-new-york-times",
    "washington post":"the-washington-post",
    "cnn":            "cnn",
    "al jazeera":     "al-jazeera-english",
    "le monde":       "le-monde",
    "Zeit":           "zeit-online",
}


def _resolve_source_id(outlet_name: str) -> str:
    """
    Convert a human-readable outlet name to a NewsAPI source ID.
    Falls back to a slugified version of the name if not in the map.
    """
    key = outlet_name.lower().strip()
    if key in OUTLET_MAP:
        return OUTLET_MAP[key]
    # Fallback: slugify the name (e.g. "Le Monde" → "le-monde")
    return key.replace(" ", "-")


def get_news_articles(outlet_name: str, days_back: int = 30, max_results: int = 20) -> list[dict]:
    """
    Fetch recent articles from a named media outlet via NewsAPI.

    Args:
        outlet_name: Human-readable outlet name (e.g. "BBC News", "Reuters")
        days_back:   How many days back to search (30, 90, or 180 for drift analysis)
        max_results: Maximum number of articles to return

    Returns:
        List of dicts with keys: title, description, published_at, url, source.
        Returns empty list on failure.

    Example:
        articles = get_news_articles("Reuters", days_back=30)
        # [{"title": "...", "description": "...", "published_at": "...", ...}, ...]
    """
    if not NEWSAPI_KEY:
        print("[newsapi_tool] ERROR: NEWSAPI_KEY not set in .env")
        return []

    source_id = _resolve_source_id(outlet_name)
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date   = datetime.now().strftime("%Y-%m-%d")

    params = {
        "apiKey":   NEWSAPI_KEY,
        "sources":  source_id,
        "from":     from_date,
        "to":       to_date,
        "pageSize": min(max_results, 100),  # NewsAPI max is 100 per request
        "sortBy":   "publishedAt",
        "language": "en",
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(NEWSAPI_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "ok":
                print(f"[newsapi_tool] API error: {data.get('message', 'Unknown error')}")
                return []

            articles = []
            for item in data.get("articles", []):
                articles.append({
                    "title":        item.get("title", "No title"),
                    "description":  item.get("description", "")[:300] if item.get("description") else "",
                    "published_at": item.get("publishedAt", ""),
                    "url":          item.get("url", ""),
                    "source":       item.get("source", {}).get("name", outlet_name),
                })

            print(f"[newsapi_tool] '{outlet_name}' (last {days_back}d) → {len(articles)} articles")
            return articles

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print(f"[newsapi_tool] Rate limited. Waiting {RETRY_DELAY}s... (attempt {attempt+1})")
                time.sleep(RETRY_DELAY)
            elif response.status_code == 426:
                print("[newsapi_tool] Free tier limitation — date range may exceed free tier window")
                return []
            else:
                print(f"[newsapi_tool] HTTP error: {e}")
                return []

        except requests.exceptions.Timeout:
            print(f"[newsapi_tool] Timeout on attempt {attempt+1}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[newsapi_tool] Unexpected error: {e}")
            return []

    print(f"[newsapi_tool] All retries exhausted for outlet: '{outlet_name}'")
    return []


def get_articles_all_windows(outlet_name: str) -> dict:
    """
    Fetch articles across all 3 time windows for drift analysis.

    Returns:
        Dict with keys: window_a (30d), window_b (90d), window_c (180d)
        Each value is a list of article dicts.

    This is the main function called by the research_node when building
    the data needed for temporal drift analysis.
    """
    print(f"\n[newsapi_tool] Fetching all time windows for: {outlet_name}")
    return {
        "window_a": get_news_articles(outlet_name, days_back=30),   # NOW
        "window_b": get_news_articles(outlet_name, days_back=90),   # LAST QUARTER
        "window_c": get_news_articles(outlet_name, days_back=180),  # 6 MONTHS AGO
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing NewsAPI tool...\n")

    # Test single window
    articles = get_news_articles("BBC News", days_back=30)
    if articles:
        print(f"Found {len(articles)} articles. First 3:\n")
        for a in articles[:3]:
            print(f"  Title: {a['title']}")
            print(f"  Date:  {a['published_at']}")
            print(f"  URL:   {a['url']}")
            print()
    else:
        print("No articles returned.")

    # Test all windows
    print("\nTesting all time windows for Reuters...")
    windows = get_articles_all_windows("Reuters")
    for window, arts in windows.items():
        print(f"  {window}: {len(arts)} articles")
