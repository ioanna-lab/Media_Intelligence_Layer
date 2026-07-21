"""
GDELT Cache — Media Intelligence Agent
Caches GDELT API results to disk to avoid repeated rate-limited calls.

What this does:
    Wraps the GDELT tool functions with a simple JSON file cache.
    Results are stored in /cache/gdelt/ and reused if less than
    CACHE_TTL_HOURS old. Only calls the real GDELT API when the
    cache is stale or missing.

Why this matters:
    GDELT enforces 1 request per 5 seconds and blocks for 15+ minutes
    if exceeded. During development, the same outlets are tested many
    times. Without caching, every test run hits the API. With caching,
    only the first run hits the API -- all subsequent runs use the
    cached result instantly.

Cache location: /cache/gdelt/{outlet_name}_{window}.json
Cache TTL: 24 hours (GDELT updates every 15 minutes but we don't need
           that freshness for development and testing)
"""
import os
import json
import time
import hashlib
from datetime import datetime, timedelta

# Cache settings
CACHE_DIR     = "cache/gdelt"
CACHE_TTL_HOURS = 24


def _cache_key(outlet_name: str, query_type: str, days_back: int) -> str:
    """Generate a safe cache filename."""
    raw = f"{outlet_name}_{query_type}_{days_back}"
    slug = raw.lower().replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"{slug}.json")


def _is_fresh(filepath: str) -> bool:
    """Check if a cache file exists and is within TTL."""
    if not os.path.exists(filepath):
        return False
    modified = datetime.fromtimestamp(os.path.getmtime(filepath))
    return datetime.now() - modified < timedelta(hours=CACHE_TTL_HOURS)


def _read_cache(filepath: str) -> dict | None:
    """Read cached data from disk."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None


def _write_cache(filepath: str, data: dict):
    """Write data to cache file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[gdelt_cache] Cache write error: {e}")


def get_gdelt_articles_cached(outlet_name: str, days_back: int = 30, max_results: int = 25) -> list[dict]:
    """
    Cached version of get_gdelt_articles.
    Returns cached results if fresh, otherwise calls the API.
    """
    cache_file = _cache_key(outlet_name, "articles", days_back)

    if _is_fresh(cache_file):
        data = _read_cache(cache_file)
        if data is not None:
            print(f"[gdelt_cache] Cache HIT: '{outlet_name}' articles {days_back}d")
            return data

    print(f"[gdelt_cache] Cache MISS: '{outlet_name}' articles {days_back}d -- calling API")
    from src.tools.gdelt_tool import get_gdelt_articles
    result = get_gdelt_articles(outlet_name, days_back, max_results)
    _write_cache(cache_file, result)
    return result


def get_gdelt_timeline_cached(outlet_name: str, days_back: int = 90) -> list[dict]:
    """Cached version of get_gdelt_timeline."""
    cache_file = _cache_key(outlet_name, "timeline", days_back)

    if _is_fresh(cache_file):
        data = _read_cache(cache_file)
        if data is not None:
            print(f"[gdelt_cache] Cache HIT: '{outlet_name}' timeline {days_back}d")
            return data

    print(f"[gdelt_cache] Cache MISS: '{outlet_name}' timeline {days_back}d -- calling API")
    from src.tools.gdelt_tool import get_gdelt_timeline
    result = get_gdelt_timeline(outlet_name, days_back)
    _write_cache(cache_file, result)
    return result


def get_gdelt_themes_cached(outlet_name: str, days_back: int = 30) -> list[dict]:
    """Cached version of get_gdelt_themes."""
    cache_file = _cache_key(outlet_name, "themes", days_back)

    if _is_fresh(cache_file):
        data = _read_cache(cache_file)
        if data is not None:
            print(f"[gdelt_cache] Cache HIT: '{outlet_name}' themes {days_back}d")
            return data

    print(f"[gdelt_cache] Cache MISS: '{outlet_name}' themes {days_back}d -- calling API")
    from src.tools.gdelt_tool import get_gdelt_themes
    result = get_gdelt_themes(outlet_name, days_back)
    _write_cache(cache_file, result)
    return result


def get_gdelt_all_windows_cached(outlet_name: str) -> dict:
    """
    Cached version of get_gdelt_all_windows.
    Makes 7 API calls total (with 6s sleep each = ~42s).
    With cache, returns instantly on repeat calls within 24h.
    """
    cache_file = _cache_key(outlet_name, "all_windows", 90)

    if _is_fresh(cache_file):
        data = _read_cache(cache_file)
        if data is not None:
            print(f"[gdelt_cache] Cache HIT: '{outlet_name}' all windows")
            return data

    print(f"[gdelt_cache] Cache MISS: '{outlet_name}' all windows -- calling API (takes ~42s)")

    result = {
        "window_a":    get_gdelt_articles_cached(outlet_name, days_back=30),
        "window_b":    get_gdelt_articles_cached(outlet_name, days_back=60),
        "window_c":    get_gdelt_articles_cached(outlet_name, days_back=90),
        "timeline":    get_gdelt_timeline_cached(outlet_name, days_back=90),
        "themes_30d":  get_gdelt_themes_cached(outlet_name,   days_back=30),
        "themes_90d":  get_gdelt_themes_cached(outlet_name,   days_back=60),
        "themes_180d": get_gdelt_themes_cached(outlet_name,   days_back=90),
    }

    _write_cache(cache_file, result)
    return result


def clear_cache(outlet_name: str = None):
    """
    Clear the GDELT cache.
    If outlet_name provided, clears only that outlet's cache.
    If None, clears all cached data.
    """
    if not os.path.exists(CACHE_DIR):
        print("[gdelt_cache] No cache directory found.")
        return

    if outlet_name:
        slug    = outlet_name.lower().replace(" ", "_").replace("/", "_")
        cleared = 0
        for f in os.listdir(CACHE_DIR):
            if f.startswith(slug):
                os.remove(os.path.join(CACHE_DIR, f))
                cleared += 1
        print(f"[gdelt_cache] Cleared {cleared} cache files for '{outlet_name}'")
    else:
        import shutil
        shutil.rmtree(CACHE_DIR)
        print("[gdelt_cache] Full cache cleared.")


def cache_status() -> dict:
    """Return status of all cached data."""
    if not os.path.exists(CACHE_DIR):
        return {"total": 0, "files": []}

    files = []
    for f in sorted(os.listdir(CACHE_DIR)):
        filepath = os.path.join(CACHE_DIR, f)
        modified = datetime.fromtimestamp(os.path.getmtime(filepath))
        age_hours = (datetime.now() - modified).total_seconds() / 3600
        files.append({
            "file":      f,
            "age_hours": round(age_hours, 1),
            "fresh":     age_hours < CACHE_TTL_HOURS,
            "size_kb":   round(os.path.getsize(filepath) / 1024, 1),
        })

    return {"total": len(files), "files": files}


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing GDELT cache...\n")
    print("Cache status:", cache_status())
    print("\nNote: First run calls API (slow). Second run uses cache (instant).")
    print("Run this script twice to see the difference.")
