"""
Trello Board Setup — Media Intelligence Agent
Board: https://trello.com/b/ZJJ0XusF/mediaintelligencelayer

Usage:
    python trello_setup.py setup     # Create all lists and cards
    python trello_setup.py status    # Show current board state
    python trello_setup.py move "card fragment" "List Name"
"""
import os, sys, requests
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
    r = requests.put(f"{BASE}/{path}", params=auth(), json=data, timeout=10)
    r.raise_for_status()
    return r.json()


# ── Board structure ───────────────────────────────────────────────────────────

LISTS = [
    "Backlog",
    "In Progress [WIP: 2]",
    "Done",
    "Blocked",
]

CARDS = {
    "Backlog": [
        # PHASE 1 — RAG Foundation (target: Jul 18)
        {
            "name": "P1.1 | Get NewsAPI, Guardian, Reddit API keys",
            "desc": (
                "Register and obtain free-tier API keys for:\n"
                "- NewsAPI (newsapi.org)\n"
                "- Guardian Open Platform (open-platform.theguardian.com)\n"
                "- Reddit API (apps.reddit.com — script app type)\n\n"
                "Done when: all 3 keys in .env and test call returns 200."
            ),
        },
        {
            "name": "P1.2 | Set up project repo & folder structure",
            "desc": (
                "Create GitHub repo: media-intelligence-agent\n\n"
                "Structure:\n"
                "  src/\n"
                "    tools/          # MCP tool wrappers\n"
                "    agent/          # ReAct agent + LangGraph\n"
                "    rag/            # Pinecone setup + retrieval\n"
                "    report/         # Report generator\n"
                "  n8n/              # Exported workflow JSON\n"
                "  corpus/           # RAG source documents\n"
                "  reports/          # Generated sample reports\n"
                "  tests/\n"
                "  .env.example\n"
                "  requirements.txt\n"
                "  README.md\n\n"
                "Done when: repo pushed, folder structure committed."
            ),
        },
        {
            "name": "P1.3 | Assemble RAG corpus (5-10 docs)",
            "desc": (
                "Collect and prepare source documents for Pinecone:\n"
                "- Reuters Institute Digital News Report (latest available)\n"
                "- RSF Press Freedom Index summary\n"
                "- 2-3 media outlet annual reports or publisher statements\n"
                "- Ofcom / Reuters media consumption data\n\n"
                "Format: plain text or markdown chunks (~500 tokens each).\n"
                "Done when: 5-10 chunked docs in /corpus ready for embedding."
            ),
        },
        {
            "name": "P1.4 | Pinecone index setup + embedding pipeline",
            "desc": (
                "- Create Pinecone index (dimension: 1536 for text-embedding-3-small)\n"
                "- Implement document chunking (RecursiveCharacterTextSplitter)\n"
                "- Embed and upsert all corpus docs\n"
                "- Implement retrieval function: query → top-k chunks\n\n"
                "Test: query 'editorial independence metrics' returns relevant chunks.\n"
                "Done when: retrieval pipeline tested and returning sensible results."
            ),
        },
        # PHASE 2 — Agent & Tools (target: Jul 24)
        {
            "name": "P2.1 | Build Tavily web search tool (MCP)",
            "desc": (
                "Implement MCP-style tool wrapper for Tavily:\n"
                "- Tool name: web_search\n"
                "- Input: query string\n"
                "- Output: list of {title, url, snippet}\n"
                "- Error handling: retry x2, return empty list on failure\n\n"
                "Test standalone: search 'Reuters editorial coverage 2024' returns results.\n"
                "Done when: tool tested independently, returns structured output."
            ),
        },
        {
            "name": "P2.2 | Build NewsAPI tool (MCP)",
            "desc": (
                "Implement MCP-style tool wrapper for NewsAPI:\n"
                "- Tool name: get_news_articles\n"
                "- Input: outlet name, date range (default: last 30 days)\n"
                "- Output: list of {title, description, publishedAt, url}\n"
                "- Normalise outlet name to NewsAPI source ID\n\n"
                "Done when: tool tested independently for 'bbc-news', returns articles."
            ),
        },
        {
            "name": "P2.3 | Build Guardian API tool (MCP)",
            "desc": (
                "Implement MCP-style tool wrapper for Guardian API:\n"
                "- Tool name: get_guardian_coverage\n"
                "- Input: search query (outlet name or topic)\n"
                "- Output: list of {headline, section, date, url}\n"
                "- Use /search endpoint with q parameter\n\n"
                "Done when: cross-reference query 'New York Times' returns Guardian articles mentioning it."
            ),
        },
        {
            "name": "P2.4 | Build Reddit API tool (MCP)",
            "desc": (
                "Implement MCP-style tool wrapper for Reddit:\n"
                "- Tool name: get_reddit_sentiment\n"
                "- Input: outlet name\n"
                "- Output: list of {title, subreddit, score, num_comments, url}\n"
                "- Search r/journalism, r/media, r/news\n"
                "- Use PRAW or direct OAuth requests\n\n"
                "Done when: search 'BBC News' returns posts from media subreddits."
            ),
        },
        {
            "name": "P2.5 | Build ReAct agent with all 4 tools",
            "desc": (
                "Wire all 4 tools into a ReAct agent using LangGraph's create_react_agent:\n"
                "- LLM: gpt-4o-mini (cost-efficient)\n"
                "- Tools: [web_search, get_news_articles, get_guardian_coverage, get_reddit_sentiment]\n"
                "- System prompt: instructs agent to research a named media outlet\n"
                "- Test: run against 'Der Spiegel' — agent should call multiple tools\n\n"
                "Done when: agent reasons across tools and returns raw research findings."
            ),
        },
        # PHASE 3 — LangGraph Workflow + Report (target: Jul 28)
        {
            "name": "P3.1 | Design and implement LangGraph workflow",
            "desc": (
                "Build the full state graph:\n\n"
                "Nodes:\n"
                "  research_node     → runs ReAct agent, gathers raw data\n"
                "  retrieve_node     → queries Pinecone RAG for industry context\n"
                "  synthesise_node   → merges raw data + RAG context\n"
                "  report_node       → generates structured Markdown report\n"
                "  error_node        → handles failures, retries\n\n"
                "State: TypedDict with outlet_name, raw_research, rag_context, synthesis, report\n\n"
                "Done when: graph runs end-to-end on test input and produces a report."
            ),
        },
        {
            "name": "P3.2 | Report template + structured output",
            "desc": (
                "Define the report structure:\n\n"
                "  # Media Intelligence Brief: {outlet}\n"
                "  ## Executive Summary\n"
                "  ## Editorial Focus & Topic Clusters\n"
                "  ## Coverage Volume & Recency\n"
                "  ## Competitive Positioning\n"
                "  ## Audience Sentiment\n"
                "  ## Industry Context (RAG)\n"
                "  ## Key Risks & Opportunities\n"
                "  ## Sources\n\n"
                "Done when: report_node fills all sections from synthesised data."
            ),
        },
        {
            "name": "P3.3 | Generate 3 sample reports",
            "desc": (
                "Run the full pipeline on 3 different outlets:\n"
                "  1. Reuters\n"
                "  2. Der Spiegel\n"
                "  3. The Guardian\n\n"
                "Save outputs to /reports/ as .md files.\n"
                "Review: all sections populated, RAG context appears in Industry Context section.\n\n"
                "Done when: 3 complete reports committed to repo."
            ),
        },
        # PHASE 4 — N8N + Polish (target: Aug 1)
        {
            "name": "P4.1 | Wrap agent as standalone Python script",
            "desc": (
                "Create src/run_agent.py:\n"
                "- Accepts JSON input via stdin or CLI arg: {\"outlet\": \"Reuters\"}\n"
                "- Runs full LangGraph pipeline\n"
                "- Outputs report as JSON to stdout\n"
                "- Saves .md report to /reports/\n\n"
                "Test: python src/run_agent.py --outlet 'Reuters' produces report.\n"
                "Done when: script runs cleanly from command line with no interactive steps."
            ),
        },
        {
            "name": "P4.2 | Build N8N workflow",
            "desc": (
                "Nodes:\n"
                "  1. Webhook (POST /research — body: {outlet: string})\n"
                "  2. Execute Command (python src/run_agent.py --outlet={{body.outlet}})\n"
                "  3. IF node (check exit code = 0)\n"
                "  4. Respond to Webhook (return report JSON on success)\n"
                "  5. Error handler (log failure, respond with error message)\n\n"
                "Done when: POST to webhook with {outlet: 'BBC'} returns a full report."
            ),
        },
        {
            "name": "P4.3 | Error handling audit",
            "desc": (
                "Review every tool and node for:\n"
                "- API rate limit handling (429 → wait + retry)\n"
                "- Empty results (no articles found → graceful fallback message)\n"
                "- LLM timeout (retry x1, then error node)\n"
                "- Pinecone connection failure (fallback: skip RAG, note in report)\n\n"
                "Done when: agent runs 5 consecutive reports without crashing."
            ),
        },
        {
            "name": "P4.4 | README + architecture diagram",
            "desc": (
                "README must include:\n"
                "- Project overview (1 paragraph)\n"
                "- Architecture diagram (Mermaid or image)\n"
                "- Setup instructions (step by step)\n"
                "- .env.example with all required keys listed\n"
                "- How to run (CLI and N8N)\n"
                "- Design decisions (why these APIs, why this graph structure)\n"
                "- Known limitations\n\n"
                "Done when: a new user could set up and run the agent from the README alone."
            ),
        },
        {
            "name": "P4.5 | Demo video (5-7 min)",
            "desc": (
                "Record a screen capture showing:\n"
                "1. N8N webhook trigger with outlet name input\n"
                "2. Execute Command node running Python script\n"
                "3. Agent reasoning steps visible in logs\n"
                "4. Final report output\n"
                "5. Brief walkthrough of LangGraph code and RAG retrieval\n\n"
                "Tool: Loom (free) or QuickTime.\n"
                "Done when: video uploaded and link added to README."
            ),
        },
    ]
}


# ── Commands ──────────────────────────────────────────────────────────────────

def setup():
    print(f"Setting up board {BOARD_ID}...")

    # Get existing lists
    existing = get(f"boards/{BOARD_ID}/lists")
    existing_names = {l["name"]: l["id"] for l in existing}
    list_ids = {}

    # Close any default Trello lists we don't want (To Do, Doing)
    default_to_close = ["To Do", "Doing"]
    for lst in existing:
        if lst["name"] in default_to_close:
            put(f"lists/{lst['id']}/closed", {"value": "true"})
            print(f"  Closed default list: {lst['name']}")

    # Refresh after closing
    existing = get(f"boards/{BOARD_ID}/lists")
    existing_names = {l["name"]: l["id"] for l in existing}

    # Create our lists if they don't exist
    for list_name in LISTS:
        if list_name in existing_names:
            list_ids[list_name] = existing_names[list_name]
            print(f"  List exists: {list_name}")
        else:
            created = post("lists", {"name": list_name, "idBoard": BOARD_ID,
                                     "pos": "bottom"})
            list_ids[list_name] = created["id"]
            print(f"  Created list: {list_name}")

    # Get existing card names to avoid duplicates
    all_cards = get(f"boards/{BOARD_ID}/cards")
    existing_card_names = {c["name"] for c in all_cards}

    # Create cards, skipping any that already exist
    created_count = 0
    skipped_count = 0
    for list_name, cards in CARDS.items():
        lid = list_ids[list_name]
        for card in cards:
            if card["name"] in existing_card_names:
                print(f"  Card exists (skipped): {card['name']}")
                skipped_count += 1
            else:
                post("cards", {"name": card["name"], "desc": card["desc"],
                               "idList": lid})
                print(f"  Card created: {card['name']}")
                created_count += 1

    print(f"\nBoard setup complete! {created_count} cards created, {skipped_count} skipped.")
    print(f"View: https://trello.com/b/{BOARD_ID}")


def status():
    lists = get(f"boards/{BOARD_ID}/lists")
    for lst in lists:
        cards = get(f"lists/{lst['id']}/cards")
        print(f"\n{lst['name']} ({len(cards)} cards)")
        for c in cards:
            print(f"  - {c['name']}")


def move(fragment, target_list_name):
    lists = get(f"boards/{BOARD_ID}/lists")
    target_id = next((l["id"] for l in lists if target_list_name.lower() in l["name"].lower()), None)
    if not target_id:
        print(f"List not found: {target_list_name}")
        return
    cards = get(f"boards/{BOARD_ID}/cards")
    matches = [c for c in cards if fragment.lower() in c["name"].lower()]
    if not matches:
        print(f"No card matching: {fragment}")
        return
    for card in matches:
        put(f"cards/{card['id']}", {"idList": target_id})
        print(f"Moved: {card['name']} → {target_list_name}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "setup":
        setup()
    elif cmd == "status":
        status()
    elif cmd == "move" and len(sys.argv) == 4:
        move(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
