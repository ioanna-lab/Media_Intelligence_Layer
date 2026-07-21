"""
Wayback Machine Tool — Media Intelligence Agent
Retrieves historical snapshots of media outlet pages from the Internet Archive.

What the Wayback Machine is:
    The Internet Archive's Wayback Machine has archived over 860 billion
    web pages since 1996. It provides a free API (CDX API) to query what
    pages were archived and when. No key required, no quota.

What this tool does:
    For a named outlet, fetches:
    - Historical homepage snapshots (what the outlet led with at a given time)
    - Snapshot metadata (how frequently pages were archived = proxy for importance)
    - URL patterns showing which sections were most active over time

    This gives us genuine historical evidence of editorial focus that
    no other source provides.

CDX API documentation:
    https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

Free, no key, no registration required.
"""
import time
import requests
from datetime import datetime, timedelta

CDX_API     = "https://web.archive.org/cdx/search/cdx"
ARCHIVE_URL = "https://web.archive.org/web"
HEADERS     = {"User-Agent": "MediaIntelligenceAgent/1.0 (educational project)"}
MAX_RETRIES = 2
RETRY_DELAY = 2

# Known outlet homepage URLs
OUTLET_URLS = {
    "bbc":             "www.bbc.co.uk/news",
    "bbc news":        "www.bbc.co.uk/news",
    "reuters":         "www.reuters.com",
    "guardian":        "www.theguardian.com",
    "the guardian":    "www.theguardian.com",
    "der spiegel":     "www.spiegel.de",
    "spiegel":         "www.spiegel.de",
    "new york times":  "www.nytimes.com",
    "nyt":             "www.nytimes.com",
    "financial times": "www.ft.com",
    "ft":              "www.ft.com",
    "al jazeera":      "www.aljazeera.com",
    "itv news":        "www.itv.com/news",
    "sky news":        "news.sky.com",
    "cnn":             "www.cnn.com",
    "washington post": "www.washingtonpost.com",
    "the independent": "www.independent.co.uk",
    "independent":     "www.independent.co.uk",
    "the times":       "www.thetimes.co.uk",
    "times":           "www.thetimes.co.uk",
    "die zeit":        "www.zeit.de",
    "focus":           "www.focus.de",
    "associated press":"apnews.com",
    "ap":              "apnews.com",
    "bloomberg":       "www.bloomberg.com",
    "le monde":        "www.lemonde.fr",
    "die zeit":        "www.zeit.de",
    "focus":           "www.focus.de",
}


def _resolve_url(outlet_name: str) -> str | None:
    """Resolve outlet name to its homepage URL."""
    key = outlet_name.lower().strip()
    return OUTLET_URLS.get(key)


def get_snapshot_frequency(
    outlet_name: str,
    days_back: int = 180,
) -> dict:
    """
    Get how frequently the Wayback Machine archived an outlet's homepage.
    Snapshot frequency is a proxy for the outlet's web presence and importance.

    Args:
        outlet_name: Outlet name
        days_back:   How many days back to check

    Returns:
        Dict with total_snapshots, snapshots_per_month, first_seen, last_seen
    """
    url = _resolve_url(outlet_name)
    if not url:
        print(f"[wayback_tool] No URL configured for: {outlet_name}")
        return {}

    end_date   = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    params = {
        "url":       url,
        "output":    "json",
        "fl":        "timestamp,statuscode",
        "from":      start_date.strftime("%Y%m%d"),
        "to":        end_date.strftime("%Y%m%d"),
        "limit":     500,
        "collapse":  "timestamp:6",  # collapse to monthly
    }

    try:
        response = requests.get(CDX_API, params=params, headers=HEADERS, timeout=25)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) < 2:
            return {"total_snapshots": 0}

        # First row is headers
        rows       = data[1:]
        total      = len(rows)
        months     = days_back / 30
        per_month  = round(total / months, 1) if months > 0 else 0
        first_seen = rows[0][0][:8] if rows else ""
        last_seen  = rows[-1][0][:8] if rows else ""

        result = {
            "total_snapshots":    total,
            "snapshots_per_month": per_month,
            "first_seen":         first_seen,
            "last_seen":          last_seen,
            "url_checked":        url,
        }

        print(f"[wayback_tool] '{outlet_name}': {total} snapshots in {days_back}d "
              f"({per_month}/month)")
        return result

    except Exception as e:
        print(f"[wayback_tool] Error for {outlet_name}: {e}")
        return {}


def get_historical_headlines(
    outlet_name: str,
    months_back: list[int] = [1, 3, 6],
) -> list[dict]:
    """
    Retrieve actual archived homepage content from specific points in time.
    Shows what the outlet was leading with at different historical moments.

    Args:
        outlet_name: Outlet name
        months_back: List of months to look back (e.g. [1, 3, 6])

    Returns:
        List of dicts: {date, archive_url, note}
    """
    url = _resolve_url(outlet_name)
    if not url:
        return []

    snapshots = []
    now       = datetime.now()

    for months in months_back:
        target_date = now - timedelta(days=months * 30)
        date_str    = target_date.strftime("%Y%m%d")

        # Find closest snapshot to target date
        params = {
            "url":    url,
            "output": "json",
            "fl":     "timestamp,original,statuscode",
            "from":   date_str,
            "limit":  1,
            "filter": "statuscode:200",
        }

        try:
            response = requests.get(CDX_API, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 1:
                row       = data[1]
                timestamp = row[0]
                archive   = f"{ARCHIVE_URL}/{timestamp}/{url}"

                snapshots.append({
                    "months_ago":   months,
                    "date":         timestamp[:8],
                    "archive_url":  archive,
                    "note":         f"Archived homepage from ~{months} month(s) ago",
                })

        except Exception as e:
            print(f"[wayback_tool] Snapshot error for {outlet_name} ({months}mo): {e}")

        time.sleep(0.5)  # be polite to the archive

    print(f"[wayback_tool] '{outlet_name}': {len(snapshots)} historical snapshots retrieved")
    return snapshots


def get_wayback_profile(outlet_name: str) -> dict:
    """
    Get a complete Wayback Machine profile for an outlet.
    Combines snapshot frequency + historical archive links.

    Returns:
        Dict with frequency stats and historical snapshot URLs.
    """
    print(f"\n[wayback_tool] Getting Wayback profile for: {outlet_name}")

    frequency = get_snapshot_frequency(outlet_name, days_back=180)
    snapshots = get_historical_headlines(outlet_name, months_back=[1, 3, 6])

    return {
        "outlet_name": outlet_name,
        "frequency":   frequency,
        "snapshots":   snapshots,
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Wayback Machine tool...\n")

    profile = get_wayback_profile("BBC News")
    print(f"\nBBC News Wayback Profile:")
    print(f"  Snapshots in 180d: {profile['frequency'].get('total_snapshots', 0)}")
    print(f"  Per month: {profile['frequency'].get('snapshots_per_month', 0)}")
    print(f"  Historical snapshots:")
    for s in profile["snapshots"]:
        print(f"    {s['months_ago']}mo ago ({s['date']}): {s['archive_url']}")

    print("\nTesting Der Spiegel...")
    profile = get_wayback_profile("Der Spiegel")
    print(f"  Snapshots in 180d: {profile['frequency'].get('total_snapshots', 0)}")
