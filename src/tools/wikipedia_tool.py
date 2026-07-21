"""
Wikipedia API Tool — Media Intelligence Agent
MCP-style tool wrapper for the Wikipedia REST API.

What this does:
    Fetches structured factual information about a media outlet from
    Wikipedia. No API key required — Wikipedia's REST API is open.

Why Wikipedia:
    Wikipedia provides reliable, structured factual data about major
    media outlets: founding year, ownership, circulation, editorial
    orientation, notable controversies, and related outlets.

    Particularly valuable for the competitor identification node:
    Wikipedia articles on outlets often name direct competitors,
    sister publications, and comparable outlets.

Endpoints used:
    1. /page/summary/{title}      — short structured summary
    2. MediaWiki parse API        — full article sections (replaces
                                    deprecated mobile-sections endpoint)
"""
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

WIKIPEDIA_API    = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_SEARCH = "https://en.wikipedia.org/w/api.php"
MAX_RETRIES      = 2
RETRY_DELAY      = 1

HEADERS = {
    "User-Agent": "MediaIntelligenceAgent/1.0 (educational project; contact: ioanna@irenta.io)"
}


def _search_wikipedia(outlet_name: str) -> str | None:
    """Find the correct Wikipedia article title for an outlet name."""
    params = {
        "action": "opensearch",
        "search": outlet_name,
        "limit":  3,
        "format": "json",
    }
    try:
        response = requests.get(WIKIPEDIA_SEARCH, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data   = response.json()
        titles = data[1]
        return titles[0] if titles else None
    except Exception as e:
        print(f"[wikipedia_tool] Search error: {e}")
        return None


def get_wikipedia_summary(outlet_name: str) -> dict:
    """
    Fetch a structured summary of a media outlet from Wikipedia.

    Returns:
        Dict with keys: title, summary, url.
        Returns empty dict on failure.
    """
    page_title = _search_wikipedia(outlet_name)
    if not page_title:
        print(f"[wikipedia_tool] No Wikipedia page found for: {outlet_name}")
        return {}

    for attempt in range(MAX_RETRIES + 1):
        try:
            url      = f"{WIKIPEDIA_API}/page/summary/{requests.utils.quote(page_title)}"
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data     = response.json()

            result = {
                "title":   data.get("title", page_title),
                "summary": data.get("extract", "")[:1500],
                "url":     data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }

            print(f"[wikipedia_tool] '{outlet_name}' → '{result['title']}' ({len(result['summary'])} chars)")
            return result

        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"[wikipedia_tool] Page not found: {page_title}")
                return {}
            print(f"[wikipedia_tool] HTTP error: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"[wikipedia_tool] Error: {e}")
            return {}

    return {}


def get_wikipedia_sections(outlet_name: str, sections: list[str] = None) -> dict:
    """
    Fetch specific sections from a Wikipedia article using the parse API.
    Uses MediaWiki action=parse (replaces deprecated mobile-sections endpoint).

    Args:
        outlet_name: Name of the media outlet
        sections:    List of section names to extract (e.g. ["Ownership", "History"])
                     If None, returns all sections found.

    Returns:
        Dict mapping section name → clean text.
    """
    page_title = _search_wikipedia(outlet_name)
    if not page_title:
        return {}

    try:
        # Use MediaWiki parse API to get sections list first
        params = {
            "action":   "parse",
            "page":     page_title,
            "prop":     "sections",
            "format":   "json",
        }
        response = requests.get(WIKIPEDIA_SEARCH, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            print(f"[wikipedia_tool] Parse API error: {data['error'].get('info', 'Unknown')}")
            return {}

        all_section_titles = data.get("parse", {}).get("sections", [])

        # Filter to requested sections
        target_indices = []
        for sec in all_section_titles:
            title = sec.get("line", "")
            if sections is None or any(s.lower() in title.lower() for s in sections):
                target_indices.append((sec.get("index", ""), title))

        if not target_indices:
            print(f"[wikipedia_tool] No matching sections found for '{outlet_name}'")
            # Return just the intro if no sections matched
            return _get_intro_text(page_title)

        # Fetch text for each matching section
        result = {}
        for idx, title in target_indices[:6]:  # cap at 6 sections
            sec_params = {
                "action":  "parse",
                "page":    page_title,
                "prop":    "wikitext",
                "section": idx,
                "format":  "json",
            }
            sec_response = requests.get(WIKIPEDIA_SEARCH, params=sec_params, headers=HEADERS, timeout=10)
            if sec_response.status_code == 200:
                sec_data = sec_response.json()
                wikitext = sec_data.get("parse", {}).get("wikitext", {}).get("*", "")
                # Clean wikitext: remove templates, links, markup
                clean = re.sub(r"\{\{[^}]*\}\}", "", wikitext)   # remove templates
                clean = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", clean)  # [[link|text]] → text
                clean = re.sub(r"'{2,}", "", clean)               # remove bold/italic
                clean = re.sub(r"==+[^=]*==+", "", clean)        # remove headers
                clean = re.sub(r"\s+", " ", clean).strip()        # normalise whitespace
                if clean:
                    result[title] = clean[:500]

        print(f"[wikipedia_tool] '{outlet_name}' sections retrieved: {list(result.keys())}")
        return result

    except Exception as e:
        print(f"[wikipedia_tool] Sections error: {e}")
        return {}


def _get_intro_text(page_title: str) -> dict:
    """Fallback: get just the introduction section."""
    try:
        params = {
            "action":  "parse",
            "page":    page_title,
            "prop":    "wikitext",
            "section": 0,
            "format":  "json",
        }
        response = requests.get(WIKIPEDIA_SEARCH, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data     = response.json()
        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        clean    = re.sub(r"\{\{[^}]*\}\}", "", wikitext)
        clean    = re.sub(r"\[\[([^|\]]*\|)?([^\]]*)\]\]", r"\2", clean)
        clean    = re.sub(r"'{2,}", "", clean)
        clean    = re.sub(r"\s+", " ", clean).strip()
        return {"Introduction": clean[:600]} if clean else {}
    except Exception:
        return {}


def get_outlet_profile(outlet_name: str) -> dict:
    """
    Get a combined Wikipedia profile for a media outlet.
    Returns summary + key sections (ownership, history, editorial stance).
    """
    print(f"\n[wikipedia_tool] Getting profile for: {outlet_name}")

    summary  = get_wikipedia_summary(outlet_name)
    sections = get_wikipedia_sections(
        outlet_name,
        sections=["Ownership", "History", "Editorial", "Controversy", "Circulation", "Format"]
    )

    return {
        "summary":  summary,
        "sections": sections,
    }


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Wikipedia tool...\n")

    # Test summary
    result = get_wikipedia_summary("BBC News")
    if result:
        print(f"Title:   {result['title']}")
        print(f"Summary: {result['summary'][:200]}...")
        print(f"URL:     {result['url']}")
    else:
        print("No summary returned.")

    print("\nTesting outlet profile for 'Der Spiegel'...")
    profile = get_outlet_profile("Der Spiegel")
    print(f"  Summary length: {len(profile['summary'].get('summary', ''))} chars")
    print(f"  Sections found: {list(profile['sections'].keys())}")

    print("\nTesting outlet profile for 'Reuters'...")
    profile = get_outlet_profile("Reuters")
    print(f"  Summary length: {len(profile['summary'].get('summary', ''))} chars")
    print(f"  Sections found: {list(profile['sections'].keys())}")
