"""
GDELT Historical Trends Tool — Media Intelligence Agent
Fetches historical news coverage data from the GDELT Project.

What GDELT is:
    The Global Database of Events, Language, and Tone (GDELT) monitors
    the world's news media in 100+ languages across 65 years of news.
    It is completely free, requires no API key, and has no quota limits.

What this tool does:
    Queries GDELT's DOC 2.0 API to retrieve:
    - Article volume trends for a named outlet over time
    - Topic/theme coverage patterns across time windows
    - Tone and sentiment signals

GDELT DOC 2.0 API:
    https://api.gdeltproject.org/api/v2/doc/doc

Free, no key, no registration required.
"""
import time
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

GDELT_API  = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT requires browser-like User-Agent, otherwise returns 429
HEADERS    = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
MAX_RETRIES = 2
RETRY_DELAY = 3


# GDELT enforces 1 request per 5 seconds -- sleep between every call
GDELT_SLEEP = 6  # 6 seconds to be safe

# Domain map: outlet name → their actual web domain
# Used for domain: queries to get articles FROM the outlet (not about it)
OUTLET_DOMAINS = {
    "bbc":             "bbc.co.uk",
    "bbc news":        "bbc.co.uk",
    "reuters":         "reuters.com",
    "guardian":        "theguardian.com",
    "the guardian":    "theguardian.com",
    "der spiegel":     "spiegel.de",
    "spiegel":         "spiegel.de",
    "new york times":  "nytimes.com",
    "nyt":             "nytimes.com",
    "financial times": "ft.com",
    "ft":              "ft.com",
    "al jazeera":      "aljazeera.com",
    "itv news":        "itv.com",
    "sky news":        "news.sky.com",
    "cnn":             "cnn.com",
    "washington post": "washingtonpost.com",
    "le monde":        "lemonde.fr",
    "die zeit":        "zeit.de",
    "focus":           "focus.de",
}

def _build_query(outlet_name: str, mode: str = "domain") -> str:
    """
    Build a GDELT query for an outlet.
    
    mode="domain": query articles FROM the outlet (domain:outlet.com)
    mode="keyword": query articles ABOUT the outlet ("outlet name")
    """
    if mode == "domain":
        domain = OUTLET_DOMAINS.get(outlet_name.lower().strip())
        if domain:
            return f"domain:{domain} sourcelang:english"
    # Fallback to keyword search
    return f'"{outlet_name}" sourcelang:english'



def _gdelt_request(params: dict) -> dict:
    """Make a request to the GDELT DOC 2.0 API with rate limit compliance."""
    time.sleep(GDELT_SLEEP)  # mandatory sleep before every request

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                GDELT_API,
                params=params,
                headers=HEADERS,
                timeout=20,
            )

            if response.status_code == 429:
                # Check Retry-After header
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"[gdelt_tool] Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            print(f"[gdelt_tool] HTTP error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * 2)
        except requests.exceptions.Timeout:
            print(f"[gdelt_tool] Timeout on attempt {attempt+1}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            print(f"[gdelt_tool] Error: {e}")
            return {}
    return {}


def get_gdelt_articles(
    outlet_name: str,
    days_back: int = 30,
    max_results: int = 25,
) -> list[dict]:
    """
    Fetch articles mentioning a media outlet from GDELT.

    Args:
        outlet_name: Name of the outlet to search for
        days_back:   How many days back to search
        max_results: Maximum articles to return

    Returns:
        List of dicts with keys: title, url, published_at, source, language
    """
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # GDELT date format: YYYYMMDDHHMMSS
    start_str = start_date.strftime("%Y%m%d%H%M%S")
    end_str   = end_date.strftime("%Y%m%d%H%M%S")

    params = {
        "query":      _build_query(outlet_name, mode="domain"),
        "mode":       "artlist",
        "maxrecords": min(max_results, 250),
        "startdatetime": start_str,
        "enddatetime":   end_str,
        "sort":       "datedesc",
        "format":     "json",
    }

    data     = _gdelt_request(params)
    articles = data.get("articles", [])

    result = []
    for a in articles:
        result.append({
            "title":        a.get("title", "No title"),
            "url":          a.get("url", ""),
            "published_at": a.get("seendate", "")[:8],  # YYYYMMDD → date only
            "source":       a.get("domain", ""),
            "language":     a.get("language", "English"),
        })

    print(f"[gdelt_tool] '{outlet_name}' (last {days_back}d) → {len(result)} articles")
    return result


def get_gdelt_timeline(outlet_name: str, days_back: int = 180) -> list[dict]:
    """
    Get article volume timeline for an outlet (articles per week).
    Useful for detecting coverage intensity trends over time.

    Returns:
        List of dicts: {date, volume} showing weekly article counts
    """
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "query":         _build_query(outlet_name, mode="domain"),
        "mode":          "timelinevol",
        "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
        "enddatetime":   end_date.strftime("%Y%m%d%H%M%S"),
        "format":        "json",
    }

    data     = _gdelt_request(params)
    timeline = data.get("timeline", [{}])[0].get("data", [])

    result = []
    for entry in timeline:
        result.append({
            "date":   entry.get("date", ""),
            "volume": entry.get("value", 0),
        })

    print(f"[gdelt_tool] '{outlet_name}' timeline: {len(result)} data points")
    return result


def get_gdelt_themes(outlet_name: str, days_back: int = 30) -> list[dict]:
    """
    Get the top themes/topics covered in articles mentioning an outlet.
    GDELT uses a taxonomy of ~3000 themes (e.g. ECON_INFLATION, ENV_CLIMATECHANGE).

    Returns:
        List of dicts: {theme, count, human_label}
    """
    end_date   = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "query":         _build_query(outlet_name, mode="domain"),
        "mode":          "themelist",
        "startdatetime": start_date.strftime("%Y%m%d%H%M%S"),
        "enddatetime":   end_date.strftime("%Y%m%d%H%M%S"),
        "format":        "json",
    }

    data   = _gdelt_request(params)
    themes = data.get("themes", [])

    # Convert GDELT theme codes to readable labels
    result = []
    for t in themes[:20]:  # top 20 themes
        theme_code = t.get("theme", "")
        count      = t.get("count", 0)
        # Convert GDELT code to readable: ENV_CLIMATECHANGE → Climate Change
        human_label = theme_code.replace("_", " ").replace("ENV ", "").replace("ECON ", "").title()
        result.append({
            "theme":       theme_code,
            "count":       count,
            "human_label": human_label,
        })

    print(f"[gdelt_tool] '{outlet_name}' themes ({days_back}d): {len(result)} themes")
    return result


def get_gdelt_all_windows(outlet_name: str) -> dict:
    """
    Fetch GDELT data across all 3 time windows for drift analysis.
    One function call — 3 separate API queries.

    Returns:
        Dict with window_a (30d), window_b (90d), window_c (180d),
        timeline (volume over 180d), and themes per window.
    """
    print(f"\n[gdelt_tool] Fetching all windows for: {outlet_name}")

    return {
        # Note: GDELT DOC 2.0 API covers last 3 months only
        "window_a":   get_gdelt_articles(outlet_name, days_back=30),
        "window_b":   get_gdelt_articles(outlet_name, days_back=60),
        "window_c":   get_gdelt_articles(outlet_name, days_back=90),
        "timeline":   get_gdelt_timeline(outlet_name, days_back=90),
        "themes_30d": get_gdelt_themes(outlet_name,   days_back=30),
        "themes_90d": get_gdelt_themes(outlet_name,   days_back=60),
        "themes_180d":get_gdelt_themes(outlet_name,   days_back=90),
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing GDELT tool...\n")

    articles = get_gdelt_articles("BBC News", days_back=30)
    if articles:
        print(f"\nFound {len(articles)} articles. First 3:")
        for a in articles[:3]:
            print(f"  Title:  {a['title']}")
            print(f"  Source: {a['source']}")
            print(f"  Date:   {a['published_at']}")
            print(f"  URL:    {a['url']}")
            print()
    else:
        print("No articles returned.")

    print("\nTesting themes for Der Spiegel (30 days)...")
    themes = get_gdelt_themes("Der Spiegel", days_back=30)
    for t in themes[:5]:
        print(f"  {t['human_label']}: {t['count']} articles")

    print("\nTesting timeline for Reuters (180 days)...")
    timeline = get_gdelt_timeline("Reuters", days_back=90)
    print(f"  {len(timeline)} weekly data points")
    if timeline:
        print(f"  Sample: {timeline[0]}")
