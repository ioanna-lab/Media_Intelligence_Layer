"""
Guardian API Tool — Media Intelligence Agent
MCP-style tool wrapper for The Guardian Open Platform API.

What this does:
    Searches The Guardian's archive for articles mentioning a media outlet
    or topic. This gives us cross-reference data — how other quality
    journalism covers and discusses the outlet we are researching.

Why The Guardian specifically:
    The Guardian API is free, well-structured, and returns rich metadata
    including section, tags, and publication date. It is ideal for
    understanding how a media outlet is discussed in the wider press.

Two modes of use:
    1. Cross-reference mode: search for articles ABOUT the target outlet
       e.g. query = "Reuters news agency" → Guardian articles discussing Reuters
    2. Topic mode: search for coverage of a specific topic to compare
       how different outlets approach the same subject
"""
import os
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
GUARDIAN_URL     = "https://content.guardianapis.com/search"
MAX_RETRIES      = 2
RETRY_DELAY      = 2


def get_guardian_coverage(
    query: str,
    days_back: int = 180,
    max_results: int = 20
) -> list[dict]:
    """
    Search The Guardian for articles matching a query.

    Args:
        query:       Search query (e.g. "Reuters news agency", "BBC editorial")
        days_back:   How far back to search (default 180 days)
        max_results: Maximum number of results to return

    Returns:
        List of dicts with keys: headline, section, published_date, url, tags.
        Returns empty list on failure.

    Example:
        results = get_guardian_coverage("Der Spiegel journalism")
        # [{"headline": "...", "section": "...", "published_date": "...", ...}, ...]
    """
    if not GUARDIAN_API_KEY:
        print("[guardian_tool] ERROR: GUARDIAN_API_KEY not set in .env")
        return []

    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "api-key":      GUARDIAN_API_KEY,
        "q":            query,
        "from-date":    from_date,
        "page-size":    min(max_results, 50),   # Guardian API max is 200, we cap at 50
        "order-by":     "relevance",            # most relevant first
        "show-fields":  "headline,trailText",   # extra fields to include
        "show-tags":    "keyword",              # include keyword tags
    }

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(GUARDIAN_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data.get("response", {}).get("status") != "ok":
                print(f"[guardian_tool] API returned non-OK status")
                return []

            results = []
            for item in data.get("response", {}).get("results", []):
                fields = item.get("fields", {})
                tags   = [t.get("webTitle", "") for t in item.get("tags", [])]

                results.append({
                    "headline":       fields.get("headline") or item.get("webTitle", "No headline"),
                    "trail_text":     fields.get("trailText", "")[:300] if fields.get("trailText") else "",
                    "section":        item.get("sectionName", ""),
                    "published_date": item.get("webPublicationDate", "")[:10],  # date only
                    "url":            item.get("webUrl", ""),
                    "tags":           tags[:5],  # cap at 5 tags
                })

            print(f"[guardian_tool] Query: '{query}' (last {days_back}d) → {len(results)} results")
            return results

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                print(f"[guardian_tool] Rate limited. Waiting {RETRY_DELAY}s... (attempt {attempt+1})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[guardian_tool] HTTP error: {e}")
                return []

        except requests.exceptions.Timeout:
            print(f"[guardian_tool] Timeout on attempt {attempt+1}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[guardian_tool] Unexpected error: {e}")
            return []

    print(f"[guardian_tool] All retries exhausted for query: '{query}'")
    return []


def get_outlet_coverage(outlet_name: str) -> dict:
    """
    Get Guardian coverage of a named outlet across two angles:
    1. Direct mentions of the outlet
    2. Media industry coverage (broader context)

    Returns:
        Dict with keys: direct_mentions, industry_context
    """
    print(f"\n[guardian_tool] Getting Guardian coverage for: {outlet_name}")
    return {
        "direct_mentions":  get_guardian_coverage(f'"{outlet_name}"', days_back=180),
        "industry_context": get_guardian_coverage(f"{outlet_name} media journalism", days_back=180),
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Guardian API tool...\n")

    results = get_guardian_coverage("Reuters news agency", days_back=90)

    if results:
        print(f"Found {len(results)} results. First 3:\n")
        for r in results[:3]:
            print(f"  Headline: {r['headline']}")
            print(f"  Section:  {r['section']}")
            print(f"  Date:     {r['published_date']}")
            print(f"  Tags:     {', '.join(r['tags'])}")
            print()
    else:
        print("No results returned.")

    print("\nTesting outlet coverage for 'Der Spiegel'...")
    coverage = get_outlet_coverage("Der Spiegel")
    print(f"  Direct mentions:  {len(coverage['direct_mentions'])} articles")
    print(f"  Industry context: {len(coverage['industry_context'])} articles")


def get_guardian_historical_windows(outlet_name: str) -> dict:
    """
    Fetch Guardian coverage of an outlet across 3 historical windows.
    Uses Guardian's unlimited free API for genuine historical comparison.

    Returns:
        Dict with window_a (30d), window_b (90d), window_c (180d)
        Each window contains articles mentioning the outlet in The Guardian.
    """
    print(f"\n[guardian_tool] Fetching historical windows for: {outlet_name}")

    return {
        "window_a": get_guardian_coverage(f'"{outlet_name}"', days_back=30,  max_results=20),
        "window_b": get_guardian_coverage(f'"{outlet_name}"', days_back=90,  max_results=20),
        "window_c": get_guardian_coverage(f'"{outlet_name}"', days_back=180, max_results=20),
    }


def get_guardian_competitive_coverage(
    outlets: list[str],
    days_back: int = 180,
) -> dict:
    """
    Fetch Guardian coverage of multiple outlets for competitive comparison.
    Shows how the broader journalism community covers each outlet relative
    to its competitors.

    Args:
        outlets:   List of outlet names to compare
        days_back: How far back to search

    Returns:
        Dict mapping outlet_name → list of Guardian articles about it
    """
    print(f"\n[guardian_tool] Competitive coverage analysis for: {outlets}")

    result = {}
    for outlet in outlets:
        result[outlet] = get_guardian_coverage(
            f'"{outlet}" media journalism',
            days_back=days_back,
            max_results=15,
        )
        import time
        time.sleep(0.5)  # polite rate spacing

    return result
