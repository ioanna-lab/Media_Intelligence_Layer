"""
Trello Sync — Media Intelligence Agent
Updates the board to reflect actual project state.

Run from project root:
    python3 scripts/sync_trello.py
"""
import os, requests, time
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

def delete(path):
    r = requests.delete(f"{BASE}/{path}", params=auth(), timeout=10)
    r.raise_for_status()
    return r.json()

# ── Get board state ───────────────────────────────────────
lists    = get(f"boards/{BOARD_ID}/lists")
list_ids = {l["name"]: l["id"] for l in lists}

backlog_id  = next(l["id"] for l in lists if "Backlog"     in l["name"])
progress_id = next(l["id"] for l in lists if "In Progress" in l["name"])
done_id     = next(l["id"] for l in lists if l["name"] == "Done")

all_cards   = get(f"boards/{BOARD_ID}/cards")
cards_by_name = {}
for c in all_cards:
    name = c["name"]
    if name not in cards_by_name:
        cards_by_name[name] = []
    cards_by_name[name].append(c)

print(f"Board has {len(all_cards)} cards across {len(lists)} lists\n")

# ── Step 1: Remove duplicates (keep the one in Done, delete the other) ─────
print("Step 1: Removing duplicate cards...")
duplicates = [name for name, cards in cards_by_name.items() if len(cards) > 1]
for name in duplicates:
    cards = cards_by_name[name]
    # Find which is in Done
    done_card = next((c for c in cards if c["idList"] == done_id), None)
    if done_card:
        # Delete the non-Done ones
        for c in cards:
            if c["id"] != done_card["id"]:
                delete(f"cards/{c['id']}")
                print(f"  Deleted duplicate: {name}")
    else:
        # No done card -- delete all but one (keep first)
        for c in cards[1:]:
            delete(f"cards/{c['id']}")
            print(f"  Deleted duplicate: {name}")

# ── Step 2: Move completed cards to Done ─────────────────
print("\nStep 2: Moving completed cards to Done...")

# Cards that are actually done but in wrong list
move_to_done = [
    "P4.1 | Wrap agent as standalone Python script",
    "P4.4 | README + architecture diagram",
]

for card_name in move_to_done:
    # Find by partial match
    match = next((c for c in all_cards
                  if card_name[:25] in c["name"] and c["idList"] != done_id), None)
    if match:
        put(f"cards/{match['id']}", {"idList": done_id})
        print(f"  Moved to Done: {match['name']}")
    else:
        print(f"  Not found or already done: {card_name[:30]}")

# ── Step 3: Add missing cards ─────────────────────────────
print("\nStep 3: Adding missing cards...")

existing_names = {c["name"] for c in get(f"boards/{BOARD_ID}/cards")}

new_done_cards = [
    {
        "name": "P2.4b | Build GDELT historical trends tool",
        "desc": (
            "Replaced MediaStack. GDELT = Global Database of Events, Language & Tone.\n"
            "Free, no key, no quota. Covers last 3 months of global news.\n\n"
            "Functions:\n"
            "- get_gdelt_articles(outlet, days_back) -- articles FROM outlet (domain query)\n"
            "- get_gdelt_timeline(outlet, days_back) -- weekly volume trend data\n"
            "- get_gdelt_themes(outlet, days_back)   -- structured topic taxonomy\n"
            "- get_gdelt_all_windows(outlet)         -- all 3 windows in one call\n\n"
            "Key lesson: use domain:bbc.co.uk not 'BBC News' as query.\n"
            "Rate limit: 1 req/5s. 6s sleep between calls. Browser User-Agent required.\n\n"
            "File: src/tools/gdelt_tool.py\n"
            "Cache: src/tools/gdelt_cache.py (24h TTL, JSON files)"
        ),
    },
    {
        "name": "P2.4c | Build Wayback Machine historical tool",
        "desc": (
            "Internet Archive CDX API. Free, no key, no quota.\n\n"
            "Functions:\n"
            "- get_snapshot_frequency(outlet, days_back) -- how often homepage was archived\n"
            "  (proxy for outlet web prominence)\n"
            "- get_historical_headlines(outlet, months_back) -- archive URLs for 1/3/6mo ago\n"
            "- get_wayback_profile(outlet) -- combined frequency + snapshot links\n\n"
            "Output in report: clickable links to actual historical homepage snapshots.\n"
            "Gives readers direct access to what the outlet was covering at past dates.\n\n"
            "File: src/tools/wayback_tool.py"
        ),
    },
    {
        "name": "P2.9 | Extend Guardian API for historical windows",
        "desc": (
            "Extended existing guardian_tool.py with 2 new functions:\n\n"
            "- get_guardian_historical_windows(outlet) -- 30d/90d/180d windows\n"
            "  (Guardian has no date limit -- covers the 180d window GDELT cannot)\n"
            "- get_guardian_competitive_coverage(outlets, days_back)\n"
            "  -- all 3 outlets simultaneously for competitive comparison\n\n"
            "File: src/tools/guardian_tool.py (appended)"
        ),
    },
    {
        "name": "P3.4 | Build evidence layer on scoring (Problem 1)",
        "desc": (
            "Every dimension score now includes 2-6 evidence bullets with URLs.\n\n"
            "How it works:\n"
            "- Scoring prompt asks for structured JSON including evidence array\n"
            "- Each evidence item: {fact, url}\n"
            "- Evidence collected from all 3 evaluations and deduplicated\n"
            "- Rendered in report as clickable links\n\n"
            "Example output:\n"
            "Editorial Independence: 4.2/5\n"
            "- BBC funded by licence fee not advertising [source: bbc.co.uk/aboutthebbc]\n"
            "- Royal Charter mandates impartiality [source: wikipedia.org/wiki/BBC]\n\n"
            "Files: src/scoring/consensus.py, src/report/generator.py"
        ),
    },
    {
        "name": "P3.5 | Build competitive position section (Problem 4)",
        "desc": (
            "Replaced single-bullet competitive position with 5-question framework.\n\n"
            "Function: generate_competitive_position() in src/report/generator.py\n\n"
            "5 sections (all comparative, all evidenced):\n"
            "1. Market Position: LEADING/CHALLENGING/FOLLOWING + confidence\n"
            "2. Editorial Differentiation: unique topics + coverage gaps\n"
            "3. Reputation Signals: peer journalism perception vs competitors\n"
            "4. Trajectory: IMPROVING/STABLE/DECLINING + confidence + volume data\n"
            "5. Strategic Assessment: vulnerabilities + opportunities vs competitors\n\n"
            "Cross-outlet LLM call with all 3 outlets data simultaneously.\n"
            "Structured JSON output ensures consistent formatting.\n\n"
            "File: src/report/generator.py"
        ),
    },
    {
        "name": "P3.6 | Clean architecture refactor",
        "desc": (
            "Separated concerns into dedicated modules:\n\n"
            "Before: all logic in nodes.py (500+ lines)\n"
            "After:\n"
            "- src/scoring/dimensions.py -- 6 dimension definitions\n"
            "- src/scoring/consensus.py  -- Krippendorff scoring logic\n"
            "- src/report/template.py    -- report section structure\n"
            "- src/report/generator.py   -- Markdown assembly\n"
            "- src/agent/nodes.py        -- thin orchestration only\n\n"
            "nodes.py now ~20 lines per node. Logic lives in the right module."
        ),
    },
    {
        "name": "P3.7 | Build FastAPI REST service",
        "desc": (
            "Standalone web service exposing the pipeline as a REST API.\n\n"
            "Endpoints:\n"
            "POST /research        -- run full pipeline, returns report JSON\n"
            "GET  /health          -- service health check\n"
            "GET  /report/{outlet} -- fetch saved report as Markdown\n"
            "GET  /reports         -- list all generated reports\n"
            "GET  /docs            -- auto-generated interactive documentation\n\n"
            "Start: python3 src/app.py\n"
            "URL:   http://localhost:8000\n"
            "Docs:  http://localhost:8000/docs\n\n"
            "Satisfies instructor requirement for 'runs independently'.\n"
            "Not Gradio (demo tool) -- proper REST API any caller can use.\n\n"
            "File: src/app.py"
        ),
    },
]

new_backlog_cards = [
    {
        "name": "P3.8 | Add outlet categorisation by sector",
        "desc": (
            "Classify each outlet into 1-3 primary categories:\n"
            "General news, Financial/business, Culture/arts, Technology,\n"
            "Science/health, Sport, Political/policy, Regional/local,\n"
            "Investigative, Trade/industry\n\n"
            "Add to competitor identification step -- find competitors\n"
            "within the same category, not just generically.\n\n"
            "Output in report: sector tags shown in header per outlet.\n\n"
            "File: src/agent/competitor_identifier.py (extend)"
        ),
    },
    {
        "name": "P3.9 | Add topic examples with URLs to drift analysis (Problem 2)",
        "desc": (
            "Every drift topic now shows article examples with URLs.\n\n"
            "Example:\n"
            "↑ Emerging: Climate Change\n"
            "  - [BBC warns of record temperatures](https://bbc.co.uk/...) — 2026-07-15\n"
            "  - [Net zero target under pressure](https://bbc.co.uk/...) — 2026-07-12\n\n"
            "Implementation:\n"
            "- find_articles_for_topic() in nodes.py matches topic keywords to articles\n"
            "- drift_results state now includes emerging_with_examples, fading_with_examples\n"
            "- generator.py renders examples under each topic label\n\n"
            "Status: logic built in nodes.py and generator.py, needs testing."
        ),
    },
    {
        "name": "P4.2 | Build N8N workflow",
        "desc": (
            "Nodes:\n"
            "1. Webhook (POST /research -- body: {outlet: string})\n"
            "2. Execute Command: python3 src/run_agent.py --outlet={{$json.outlet}}\n"
            "3. IF node: check exit code = 0\n"
            "4. Respond to Webhook: return report JSON on success\n"
            "5. Error handler: log failure\n\n"
            "Note: run_agent.py already built (P4.1 done).\n"
            "Export workflow JSON to n8n/workflow.json after build.\n\n"
            "Done when: POST to webhook with {outlet: 'BBC News'} returns full report."
        ),
    },
    {
        "name": "P4.3 | Error handling audit",
        "desc": (
            "Review all tools and nodes:\n"
            "- GDELT: rate limit + session flag + cache\n"
            "- Wayback: timeout handling\n"
            "- Guardian: graceful on empty results\n"
            "- NewsAPI: 400 on date range (documented, expected)\n"
            "- RSS: SSL fallback in place\n"
            "- Scoring: fallback score on JSON parse error\n"
            "- Report: graceful on competitive position LLM failure\n\n"
            "Done when: 3 consecutive full pipeline runs complete without crash."
        ),
    },
    {
        "name": "P4.5 | Demo video (5-7 min)",
        "desc": (
            "Record screen capture showing:\n"
            "1. FastAPI /docs page\n"
            "2. POST /research triggered from browser\n"
            "3. Pipeline running in terminal (node logs visible)\n"
            "4. Final report output with scorecard + competitive position\n"
            "5. Brief walkthrough: LangGraph graph, RAG retrieval, consensus scoring\n"
            "6. Mention planned extension: daily briefing service\n\n"
            "Tool: Loom (free) or QuickTime.\n"
            "Done when: video uploaded and link added to README."
        ),
    },
    {
        "name": "P4.6 | [STRETCH] Signal detection node",
        "desc": (
            "Cross-outlet signal detection:\n"
            "- Topic in only 1 outlet = outlet-specific signal\n"
            "- Topic in all 3 = industry-wide trend\n"
            "- Volume spike >50% vs baseline\n"
            "- Competitor gap: topic A covers, B and C don't\n\n"
            "Output: 'Signals to Watch' section in report.\n\n"
            "File: src/agent/nodes.py (new signal_detection_node)"
        ),
    },
    {
        "name": "P4.7 | [STRETCH] Daily personalised briefing service",
        "desc": (
            "New N8N workflow (separate from competitive brief):\n\n"
            "User configures:\n"
            "- Topics of interest (climate, AI, finance, culture, geopolitics)\n"
            "- Preferred outlet categories\n\n"
            "Daily at 7am:\n"
            "- Agent queries GDELT + Guardian + RSS per topic\n"
            "- Ranks stories by relevance + source quality + recency\n"
            "- Deduplicates across sources\n"
            "- Weights by outlet trust score from competitive brief\n"
            "- Formats email with top 5 per topic, summaries, links\n"
            "- N8N sends via email node\n\n"
            "Quality curation handled autonomously by agent.\n"
            "Uses outlet categorisation from P3.8 as topic taxonomy."
        ),
    },
    {
        "name": "P4.8 | [STRETCH] Event-triggered N8N monitoring + Slack",
        "desc": (
            "Weekly N8N schedule monitoring for trigger events:\n"
            "- Ownership change mentions\n"
            "- Editorial leadership changes\n"
            "- Coverage spikes >50%\n"
            "- Major retractions\n\n"
            "When trigger fires:\n"
            "1. Agent generates brief update report\n"
            "2. N8N posts Slack summary via existing Slack key\n\n"
            "Done when: simulated trigger produces Slack notification."
        ),
    },
]

# Create done cards
for card in new_done_cards:
    if card["name"] not in existing_names:
        post("cards", {"name": card["name"], "desc": card["desc"], "idList": done_id})
        print(f"  Created (Done): {card['name'][:60]}")
        existing_names.add(card["name"])
        time.sleep(0.3)
    else:
        print(f"  Exists: {card['name'][:60]}")

# Create backlog cards
for card in new_backlog_cards:
    if card["name"] not in existing_names:
        post("cards", {"name": card["name"], "desc": card["desc"], "idList": backlog_id})
        print(f"  Created (Backlog): {card['name'][:60]}")
        existing_names.add(card["name"])
        time.sleep(0.3)
    else:
        print(f"  Exists: {card['name'][:60]}")

# ── Step 4: Mark MediaStack as obsolete ──────────────────
print("\nStep 4: Updating MediaStack card...")
ms_card = next((c for c in get(f"boards/{BOARD_ID}/cards")
                if "MediaStack" in c["name"]), None)
if ms_card:
    put(f"cards/{ms_card['id']}", {
        "name": "P2.4 | [REMOVED] Build MediaStack tool → replaced by GDELT + Wayback"
    })
    print(f"  Updated: {ms_card['name']}")

print("\n✓ Trello sync complete!")
print(f"View: https://trello.com/b/{BOARD_ID}")
