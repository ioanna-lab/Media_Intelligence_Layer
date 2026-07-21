"""
RSS Feed Tool — Media Intelligence Agent
MCP-style tool wrapper for reading RSS/Atom news feeds directly.

What this does:
    Fetches and parses the RSS feed of a media outlet directly.
    No API key required — RSS is a public standard.

Why RSS:
    RSS feeds give us real-time article data directly from the outlet
    itself, bypassing third-party aggregators. They are fast, free,
    and always up to date.

    Limitations:
    - RSS feeds typically only contain the last 20-50 articles
    - No historical data beyond what is currently in the feed
    - Some outlets have restricted or paywalled RSS feeds
    - SSL certificate issues on some networks/systems

Requires: pip install feedparser
"""
import ssl
import feedparser
import urllib.request
from datetime import datetime

# ── SSL fix for macOS / corporate networks ────────────────
# Some systems (especially macOS with older Python) fail SSL verification
# for certain news sites. We create an unverified SSL context as fallback.
# This is acceptable for reading public RSS feeds (we are not sending
# sensitive data, only reading public content).
try:
    _SSL_CONTEXT = ssl.create_default_context()
    _SSL_CONTEXT.check_hostname = False
    _SSL_CONTEXT.verify_mode = ssl.CERT_NONE
except Exception:
    _SSL_CONTEXT = None

# RSS feed URLs for major outlets
OUTLET_RSS_FEEDS = {
    "bbc":             "http://feeds.bbci.co.uk/news/rss.xml",      # HTTP (avoids SSL)
    "bbc news":        "http://feeds.bbci.co.uk/news/rss.xml",
    "reuters":         "http://feeds.reuters.com/reuters/topNews",   # HTTP fallback
    "guardian":        "https://www.theguardian.com/world/rss",
    "the guardian":    "https://www.theguardian.com/world/rss",
    "der spiegel":     "https://www.spiegel.de/international/index.rss",
    "spiegel":         "https://www.spiegel.de/international/index.rss",
    "new york times":  "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "nyt":             "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "al jazeera":      "https://www.aljazeera.com/xml/rss/all.xml",
    "le monde":        "https://www.lemonde.fr/rss/une.xml",
    "financial times": "https://www.ft.com/rss/home",
    "ft":              "https://www.ft.com/rss/home",
    "cnn":             "http://rss.cnn.com/rss/edition.rss",
    "washington post": "https://feeds.washingtonpost.com/rss/world",
    "the independent": "https://www.independent.co.uk/news/rss",
    "independent":     "https://www.independent.co.uk/news/rss",
    # The Times: hard paywall, no public RSS feed available
    # "the times": removed — paywall
    "associated press":"https://feeds.apnews.com/rss/apf-topnews",
    "ap":              "https://feeds.apnews.com/rss/apf-topnews",
    "bloomberg":       "https://feeds.bloomberg.com/markets/news.rss",
    "die zeit":        "https://newsfeed.zeit.de/index",
    "focus":           "https://rss.focus.de/fol/XML/rss_folnews.xml",
}


def _resolve_feed_url(outlet_name: str) -> str | None:
    key = outlet_name.lower().strip()
    return OUTLET_RSS_FEEDS.get(key)


def _parse_feed(feed_url: str) -> feedparser.FeedParserDict:
    """
    Parse a feed URL with SSL fallback handling.
    Tries standard parse first, then falls back to unverified SSL.
    """
    # First attempt: standard parse
    feed = feedparser.parse(feed_url)

    # If failed due to SSL, retry with unverified context
    if feed.bozo and "SSL" in str(feed.bozo_exception):
        print(f"[rss_tool] SSL issue detected, retrying with relaxed SSL...")
        try:
            if _SSL_CONTEXT:
                handler = urllib.request.HTTPSHandler(context=_SSL_CONTEXT)
                opener  = urllib.request.build_opener(handler)
                response = opener.open(feed_url, timeout=10)
                feed = feedparser.parse(response.read())
        except Exception as e:
            print(f"[rss_tool] SSL fallback also failed: {e}")

    return feed


def get_rss_articles(outlet_name: str, max_results: int = 30) -> list[dict]:
    """
    Fetch and parse articles from a media outlet's RSS feed.

    Args:
        outlet_name: Name of the media outlet (e.g. "BBC News", "Reuters")
        max_results: Maximum number of articles to return

    Returns:
        List of dicts with keys: title, summary, published_at, url, tags.
        Returns empty list if feed not found or on failure.
    """
    feed_url = _resolve_feed_url(outlet_name)

    if not feed_url:
        print(f"[rss_tool] No RSS feed configured for: {outlet_name}")
        return []

    try:
        feed = _parse_feed(feed_url)

        if feed.bozo and not feed.entries:
            print(f"[rss_tool] Could not parse feed for {outlet_name}: {feed.bozo_exception}")
            return []

        articles = []
        for entry in feed.entries[:max_results]:

            published_at = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    dt = datetime(*entry.published_parsed[:6])
                    published_at = dt.strftime("%Y-%m-%d")
                except Exception:
                    published_at = entry.get("published", "")[:10]

            tags = []
            if hasattr(entry, "tags"):
                tags = [t.get("term", "") for t in entry.tags if t.get("term")][:5]

            articles.append({
                "title":        entry.get("title", "No title"),
                "summary":      (entry.get("summary") or "")[:300],
                "published_at": published_at,
                "url":          entry.get("link", ""),
                "tags":         tags,
            })

        print(f"[rss_tool] '{outlet_name}' RSS → {len(articles)} articles")
        return articles

    except Exception as e:
        print(f"[rss_tool] Error fetching feed for {outlet_name}: {e}")
        return []


def get_topic_clusters_from_rss(outlet_name: str) -> dict:
    """
    Get articles from RSS and extract topic signals for drift analysis.
    """
    articles = get_rss_articles(outlet_name)

    topic_signals = {}
    for article in articles:
        for tag in article.get("tags", []):
            tag_clean = tag.strip().lower()
            if tag_clean:
                topic_signals[tag_clean] = topic_signals.get(tag_clean, 0) + 1

    stopwords = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and",
                 "or", "but", "is", "are", "was", "were", "has", "have", "be",
                 "it", "its", "as", "by", "from", "with", "that", "this", ""}
    title_words = {}
    for article in articles:
        words = article["title"].lower().split()
        for word in words:
            clean = word.strip(".,!?;:'\"()[]")
            if clean not in stopwords and len(clean) > 3:
                title_words[clean] = title_words.get(clean, 0) + 1

    top_keywords = dict(sorted(title_words.items(), key=lambda x: x[1], reverse=True)[:20])

    return {
        "articles":      articles,
        "topic_signals": topic_signals,
        "top_keywords":  top_keywords,
    }


def add_rss_feed(outlet_name: str, feed_url: str):
    """Dynamically add a new RSS feed URL."""
    OUTLET_RSS_FEEDS[outlet_name.lower()] = feed_url
    print(f"[rss_tool] Added feed for '{outlet_name}': {feed_url}")


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing RSS tool...\n")

    articles = get_rss_articles("BBC News")
    if articles:
        print(f"Found {len(articles)} articles. First 3:\n")
        for a in articles[:3]:
            print(f"  Title: {a['title']}")
            print(f"  Date:  {a['published_at']}")
            print(f"  Tags:  {', '.join(a['tags']) if a['tags'] else 'none'}")
            print()
    else:
        print("No articles from BBC RSS.")

    print("\nTesting topic clusters for Guardian...")
    clusters = get_topic_clusters_from_rss("The Guardian")
    print(f"  Articles: {len(clusters['articles'])}")
    print(f"  Top keywords: {list(clusters['top_keywords'].items())[:5]}")

    print("\nTesting Der Spiegel RSS...")
    articles = get_rss_articles("Der Spiegel")
    print(f"  Articles found: {len(articles)}")
    if articles:
        print(f"  Sample: {articles[0]['title']}")
