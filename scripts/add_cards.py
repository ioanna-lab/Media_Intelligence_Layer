"""
Add missing Trello cards for the enhanced Media Intelligence Agent project.
Run from the project root:
    python3 scripts/add_cards.py
"""
import os, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("TRELLO_API_KEY", "4be320746ac47e22b738c883d20dec0c")
TOKEN    = os.getenv("TRELLO_TOKEN")
BOARD_ID = "ZJJ0XusF"
BASE     = "https://api.trello.com/1"

def auth():
    return {"key": API_KEY, "token": TOKEN}

def get(path, params={}):
    r = requests.get(f"{BASE}/{path}", params={**auth(), **params}, timeout=10)
    r.raise_for_status()
    return r.json()

def post(path, data={}):
    r = requests.post(f"{BASE}/{path}", params=auth(), json=data, timeout=10)
    r.raise_for_status()
    return r.json()

def put(path, data={}):
    r = requests.put(f"{BASE}/{path}", params={**auth(), **data}, timeout=10)
    r.raise_for_status()
    return r.json()

# Get list IDs
lists      = get(f"boards/{BOARD_ID}/lists")
list_ids   = {l["name"]: l["id"] for l in lists}
backlog_id = next(l["id"] for l in lists if "Backlog" in l["name"])
done_id    = next(l["id"] for l in lists if l["name"] == "Done")

# Get existing card names
all_cards    = get(f"boards/{BOARD_ID}/cards")
existing     = {c["name"]: c["id"] for c in all_cards}

# Cards to create in Backlog
new_backlog_cards = [
    {
        "name": "P2.4 | Build MediaStack tool (MCP)",
        "desc": (
            "MCP tool wrapper for MediaStack News API.\n\n"
            "Solves the NewsAPI free tier date restriction — MediaStack allows\n"
            "up to 1 year of historical data on the free tier.\n\n"
            "Function: get_mediastack_articles(outlet_name, days_back, max_results)\n"
            "Function: get_articles_all_windows(outlet_name) — 30/90/180 day windows\n\n"
            "File: src/tools/mediastack_tool.py\n\n"
            "Done when: all 3 time windows return articles for Reuters."
        )
    },
    {
        "name": "P2.5 | Build Wikipedia tool (MCP)",
        "desc": (
            "MCP tool wrapper for Wikipedia REST API.\n"
            "No API key required — completely free and open.\n\n"
            "Functions:\n"
            "- get_wikipedia_summary(outlet_name) → structured summary\n"
            "- get_wikipedia_sections(outlet_name, sections) → specific sections\n"
            "- get_outlet_profile(outlet_name) → summary + key sections\n\n"
            "Uses MediaWiki parse API (mobile-sections was decommissioned).\n\n"
            "File: src/tools/wikipedia_tool.py\n\n"
            "Done when: profile for 'Der Spiegel' returns summary + History section."
        )
    },
    {
        "name": "P2.6 | Build RSS feed tool (MCP)",
        "desc": (
            "MCP tool wrapper for reading outlet RSS feeds directly.\n"
            "No API key required — RSS is a public standard.\n\n"
            "Functions:\n"
            "- get_rss_articles(outlet_name, max_results) → recent articles\n"
            "- get_topic_clusters_from_rss(outlet_name) → articles + topic signals\n"
            "- add_rss_feed(outlet_name, url) → add new outlet dynamically\n\n"
            "Includes SSL fallback handler for macOS certificate issues.\n"
            "Uses HTTP feeds where available to avoid SSL entirely.\n\n"
            "File: src/tools/rss_tool.py\n\n"
            "Done when: BBC, Guardian, Der Spiegel feeds return articles."
        )
    },
    {
        "name": "P2.7 | Build competitor identification node",
        "desc": (
            "Agent automatically identifies 2 closest competitors for the target outlet.\n\n"
            "Logic:\n"
            "- Fetch Wikipedia profile of target outlet\n"
            "- LLM analyses profile + RAG context to identify 2 competitors\n"
            "- Returns: [competitor_1, competitor_2] as structured output\n"
            "- Used as input to research_node for parallel research\n\n"
            "File: src/agent/competitor_identifier.py\n\n"
            "Done when: given 'Der Spiegel', returns 2 sensible German/European competitors."
        )
    },
    {
        "name": "P2.8 | Build retriever.py (Pinecone query function)",
        "desc": (
            "File: src/rag/retriever.py\n\n"
            "Functions:\n"
            "- retrieve(query, top_k, min_score) → top-k relevant chunks\n"
            "- retrieve_for_outlet(outlet_name) → 4 targeted queries, deduplicated\n"
            "- format_context(chunks, max_chars) → formatted string for LLM prompt\n\n"
            "Uses text-embedding-3-small for query embedding.\n"
            "Filters results below min_score=0.3 threshold.\n\n"
            "Done when: query 'BBC editorial independence' returns relevant corpus chunks."
        )
    },
    {
        "name": "P3.2 | Build drift_analysis_node",
        "desc": (
            "Temporal drift analysis across 3 time windows per outlet.\n\n"
            "Input state: raw_research (articles per window per outlet)\n\n"
            "Steps:\n"
            "1. Extract topic clusters per window using LLM\n"
            "2. Compare clusters across windows:\n"
            "   - Emerging: in window A (last 30d), not in B or C\n"
            "   - Fading: strong in C (6mo), declining in A\n"
            "   - Stable core: consistent across all 3\n"
            "   - Volume shift: article count change %\n"
            "3. Store drift results in state\n\n"
            "Done when: drift analysis for 'Reuters' shows meaningful topic movement."
        )
    },
    {
        "name": "P3.3 | Build consensus_scoring_node (Krippendorff's Alpha)",
        "desc": (
            "Consensus scoring with inter-rater reliability.\n\n"
            "For each of 6 dimensions per outlet:\n"
            "  1. Run 3 independent LLM evaluations (different prompts/temps)\n"
            "  2. Each returns score 1-5\n"
            "  3. Calculate Krippendorff's Alpha across 3 scores\n"
            "  4. Classify: HIGH (a>0.6), MODERATE (0.4-0.6), LOW (<0.4)\n"
            "  5. If LOW: flag as 'contested — human review recommended'\n\n"
            "6 Dimensions:\n"
            "  - Editorial independence\n"
            "  - Coverage breadth and depth\n"
            "  - Audience trust signals\n"
            "  - Investigative capacity\n"
            "  - Digital and audio positioning\n"
            "  - Competitive differentiation\n\n"
            "Library: pip install krippendorff\n\n"
            "Done when: scoring node produces consensus scores + alpha values for all 3 outlets."
        )
    },
    {
        "name": "P4.6 | [STRETCH] Signal detection node",
        "desc": (
            "Detect cross-outlet and outlet-specific signals.\n\n"
            "- Topics in only 1 outlet = outlet-specific signal\n"
            "- Topics in all 3 = industry-wide trend\n"
            "- Unusual volume spikes vs baseline\n"
            "- Competitor gaps: topics outlet A covers that B and C don't\n\n"
            "Output: 'Signals to Watch' section in report.\n\n"
            "Done when: signal node identifies at least 2 meaningful signals per run."
        )
    },
    {
        "name": "P4.7 | [STRETCH] Event-triggered N8N monitoring + Slack",
        "desc": (
            "Weekly N8N schedule monitoring for trigger events:\n"
            "- Ownership change mentions in recent articles\n"
            "- Editorial leadership changes\n"
            "- Major coverage spikes (>50% volume increase)\n"
            "- Story retractions\n\n"
            "When trigger fires:\n"
            "1. Agent generates a brief report\n"
            "2. N8N posts Slack summary via existing Slack API key\n\n"
            "Done when: simulated trigger event produces Slack notification with summary."
        )
    },
]

# Cards already done — move to Done list
already_done = [
    "P2.7 | Build retriever.py (Pinecone query function)",
]

created  = 0
skipped  = 0
moved    = 0

for card in new_backlog_cards:
    if card["name"] in existing:
        print(f"  Skipped (exists): {card['name']}")
        skipped += 1
    else:
        post("cards", {"name": card["name"], "desc": card["desc"], "idList": backlog_id})
        print(f"  Created: {card['name']}")
        created += 1

# Move P2.8 (retriever) to Done since it's complete
for card_name in already_done:
    # Find matching card by partial name
    match = next((c for c in all_cards if card_name[:20] in c["name"]), None)
    if match:
        put(f"cards/{match['id']}", {"idList": done_id})
        print(f"  Moved to Done: {match['name']}")
        moved += 1

print(f"\nDone: {created} created, {skipped} skipped, {moved} moved to Done.")
print(f"View: https://trello.com/b/{BOARD_ID}")
