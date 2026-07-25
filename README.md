# Media Intelligence Agent

> Give it a media outlet. Get back a validated competitive benchmark.

Autonomous AI agent that researches a named media outlet, benchmarks it against two automatically identified competitors, tracks editorial drift over time, and generates a structured competitive intelligence report — without human intervention.

**Ironhack AI Engineering Programme · Module 3 Capstone · July 2026**

---

## What it does

Given a media outlet name (e.g. Reuters, Der Spiegel, The Guardian), the agent:

1. **Identifies competitors** automatically using Wikipedia + LLM reasoning
2. **Researches all 3 outlets** across 3 time windows using 6 data sources
3. **Retrieves industry context** from a pre-loaded RAG knowledge base (Pinecone)
4. **Detects temporal drift** — which topics are emerging, fading, or stable
5. **Scores all 3 outlets** across 6 dimensions using consensus scoring (3 independent LLM evaluations per score)
6. **Validates scores** using Krippendorff's Alpha (inter-rater reliability)
7. **Generates a structured report** with scorecard, drift analysis, and flagged dimensions

---

## Architecture

```
Webhook trigger (N8N) or CLI
        │
        ▼
identify_competitors_node
  → Wikipedia profile + LLM reasoning
  → Returns 2 closest competitors
        │
        ▼
research_node  [runs for target + 2 competitors]
  → ReAct agent per outlet
  → Tools: Tavily · NewsAPI · Guardian · MediaStack · RSS · Wikipedia
  → Fetches articles across 3 time windows (30d / 90d / 180d)
        │
        ▼
retrieve_node
  → Pinecone RAG: 11 industry documents
  → Returns relevant context per outlet
        │
        ▼
drift_analysis_node
  → Topic clustering per time window (LLM)
  → Set mathematics: emerging / fading / stable
  → LLM interpretation of drift pattern
        │
        ▼
consensus_scoring_node
  → 3 independent LLM evaluations per dimension per outlet
  → Krippendorff's Alpha calculated per score
  → Dimensions flagged if α < 0.4 (human review recommended)
        │
        ▼
report_node
  → Competitive scorecard (Markdown table)
  → Per-outlet narrative + drift + RAG context
  → Flagged dimensions + methodology note
        │
        ▼
N8N returns report  /  CLI saves to /reports/
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent framework | LangChain + LangGraph | ReAct pattern, graph workflow |
| Vector database | Pinecone | RAG retrieval |
| LLM | OpenAI gpt-4o-mini | Reasoning, synthesis, scoring |
| Tool 1 | Tavily | Open web search |
| Tool 2 | NewsAPI | Recent articles (30-day window) |
| Tool 3 | Guardian API | Cross-reference coverage (180-day) |
| Tool 4 | GDELT Project | Historical articles + themes + timeline (built, rate-limited in dev environment) |
| Tool 5 | Wayback Machine | Historical snapshots + web presence metrics (since 1996, unlimited) |
| Tool 6 | Wikipedia | Factual profiles, competitor identification |
| Tool 7 | RSS feeds | Real-time current articles |
| IRR library | krippendorff | Inter-rater reliability (Krippendorff's Alpha) |
| Orchestration | N8N | Webhook trigger, Execute Command node |
| Language | Python 3.11+ | All agent code |

---

## Project Structure

```
Media_Intelligence_Layer/
├── src/
│   ├── app.py                    # FastAPI REST service (independent web service)
│   ├── run_agent.py              # CLI entry point for N8N Execute Command node
│   ├── tools/
│   │   ├── tavily_tool.py        # Tavily web search wrapper
│   │   ├── newsapi_tool.py       # NewsAPI wrapper (30-day window)
│   │   ├── guardian_tool.py      # Guardian API wrapper
│   │   ├── gdelt_tool.py         # GDELT historical articles + themes + timeline
│   │   ├── wayback_tool.py       # Wayback Machine snapshots + frequency
│   │   ├── wikipedia_tool.py     # Wikipedia REST API wrapper
│   │   └── rss_tool.py           # RSS feed parser with SSL fallback
│   ├── agent/
│   │   ├── state.py              # AgentState TypedDict definition
│   │   ├── nodes.py              # Node orchestration (thin wrappers)
│   │   ├── graph.py              # Graph assembly + run_pipeline()
│   │   ├── react_agent.py        # ReAct agent with 6 tools
│   │   └── competitor_identifier.py  # LLM-based competitor identification
│   ├── rag/
│   │   ├── ingest.py             # Load corpus into Pinecone (run once)
│   │   └── retriever.py          # Query Pinecone for context
│   ├── scoring/
│   │   ├── dimensions.py         # 6 dimension definitions + prompts
│   │   └── consensus.py          # Krippendorff's Alpha + scoring logic
│   └── report/
│       ├── template.py           # Report section structure
│       └── generator.py          # Markdown report assembly
├── scripts/
│   ├── trello_setup.py           # Trello board management
│   └── add_cards.py              # Add new cards to Trello
├── n8n/
│   └── workflow.json             # Exported N8N workflow
├── corpus/                       # RAG source documents (11 files)
│   ├── rsf_press_freedom_2026.txt
│   ├── reuters_institute_digital_news_report.txt
│   ├── media_outlets_profiles.txt
│   ├── media_industry_trends.txt
│   ├── editorial_standards_and_metrics.txt
│   ├── media_ownership_map.txt
│   ├── public_broadcasters_comparison.txt
│   ├── digital_advertising_market.txt
│   ├── european_media_regulation.txt
│   ├── podcast_audio_news_landscape.txt
│   └── cjr_journalistic_access.txt
├── reports/                      # Generated sample reports
│   ├── the_guardian.md
│   ├── reuters.md
│   └── der_spiegel.md
├── .env.example
├── requirements.txt
├── MILESTONE_PLAN.md
├── PROJECT_DOCUMENT.md
├── LEARNING_DOCUMENT.md
└── README.md
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ioannarenta/media-intelligence-agent.git
cd media-intelligence-agent
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Fill in all API keys in .env
```

Required keys:

| Variable | Where to get it | Free tier |
|----------|----------------|-----------|
| `OPENAI_API_KEY` | platform.openai.com | Pay per use |
| `PINECONE_API_KEY` | app.pinecone.io | Yes |
| `PINECONE_INDEX_NAME` | Set to `media-intelligence` | — |
| `TAVILY_API_KEY` | app.tavily.com | 1000 searches/month |
| `NEWSAPI_KEY` | newsapi.org/register | 100 requests/day, 30-day history |
| `GUARDIAN_API_KEY` | open-platform.theguardian.com | Unlimited |
| `MEDIASTACK_API_KEY` | mediastack.com/signup | 500 requests/month, 1 year history |

### 4. Load RAG corpus into Pinecone

Run this once before the first research run:

```bash
python3 src/rag/ingest.py
```

This embeds 11 industry documents and uploads them to Pinecone. You only need to re-run if you add new documents to `/corpus/`.

### 5. Run the agent

**Via CLI (module):**
```bash
python3 -m src.agent.graph "Der Spiegel"
python3 -m src.agent.graph "Reuters"
python3 -m src.agent.graph "BBC News"
```

**Via CLI entry point (used by N8N):**
```bash
python3 src/run_agent.py --outlet "Reuters"
python3 src/run_agent.py --outlet "Der Spiegel" --output markdown
```

**Via FastAPI service (local):**
```bash
python3 src/app.py
# UI at:           http://localhost:8000
# API docs at:     http://localhost:8000/docs
# Health check at: http://localhost:8000/health
```

**Via ngrok (public URL, shareable):**
```bash
# Terminal 1 — start the server
python3 src/app.py

# Terminal 2 — open a public tunnel
ngrok http 8000
# → https://gloater-unrevised-extradite.ngrok-free.dev
```

**Via Render (permanent deployment):**
See [Deployment](#deployment) section below.

Reports are saved to `/reports/` as Markdown files.

**Via N8N:** See [N8N Integration](#n8n-integration) below.

---

## How to run individual components

Test each tool independently:

```bash
python3 src/tools/tavily_tool.py
python3 src/tools/newsapi_tool.py
python3 src/tools/guardian_tool.py
python3 src/tools/mediastack_tool.py
python3 src/tools/wikipedia_tool.py
python3 src/tools/rss_tool.py
python3 src/rag/retriever.py
python3 -m src.agent.competitor_identifier
python3 -m src.agent.react_agent
```

---

## The Scoring System

Each outlet is scored across 6 dimensions using **consensus scoring with inter-rater reliability**:

| Dimension | What it measures |
|-----------|----------------|
| Editorial Independence | Ownership structure, separation from commercial/political influence |
| Coverage Breadth & Depth | Range of topics, investigative capacity, international coverage |
| Audience Trust Signals | Track record for accuracy, correction policies, public perception |
| Investigative Capacity | Dedicated team, major investigations, awards, resources |
| Digital & Audio Positioning | Digital product quality, podcast presence, social media reach |
| Competitive Differentiation | Unique editorial voice, exclusive content, brand strength |

**How consensus scoring works:**
1. 3 independent LLM evaluations per dimension using **3 different model architectures:**
   - GPT-4o-mini / conservative analyst perspective (temperature 0.3)
   - Claude Sonnet 4.6 / progressive editorial perspective (temperature 0.5)
   - GPT-4o-mini / industry veteran perspective (temperature 0.9)
2. Krippendorff's Alpha calculated across the 3 scores
3. Agreement classified:
   - **CONSENSUS** (α = 1.0) — all evaluators agree, unambiguous signal
   - **HIGH** (α ≥ 0.6) — evaluators broadly agree
   - **MODERATE** (α 0.4–0.6) — some divergence
   - **CONTESTED** (α < 0.4) — significant disagreement, flagged as analytically contested
4. Contested dimensions are not failures — they reveal where genuine expert opinion diverges

This applies the academic **Inter-Annotator Agreement (IAA)** framework to AI scoring, making every score auditable and transparent about its own uncertainty.

**References:**
- [Inter-rater reliability (Wikipedia)](https://en.wikipedia.org/wiki/Inter-rater_reliability)
- [Inter-Annotator Agreement (Innovatiana)](https://www.innovatiana.com/en/post/inter-annotator-agreement)

---

## Temporal Drift Analysis

For each outlet, the agent compares article topic clusters across 3 time windows:

| Window | Period | Source |
|--------|--------|--------|
| Window A | Last 30 days | NewsAPI + RSS |
| Window B | Last 90 days | MediaStack + Guardian |
| Window C | Last 180 days | MediaStack + Guardian |

Topic clusters are extracted by LLM from article titles, then compared using Python set mathematics:

- **Emerging:** topics in Window A not present in B or C
- **Fading:** topics strong in Window C, absent in Window A
- **Stable:** topics consistent across all three windows
- **Volume shift:** article count change across windows

---

## Deployment

### Option A — Local + ngrok (demo-ready, no server needed)

**What this gives you:** A public URL anyone can open from any device, tunnelled to your local machine. Free, takes 30 seconds to set up.

**Prerequisites:** ngrok installed and authtoken configured (one-time setup).

**First-time setup:**
```bash
# Install ngrok (macOS)
brew install ngrok/ngrok/ngrok

# Register at https://dashboard.ngrok.com and get your authtoken
ngrok config add-authtoken YOUR_AUTHTOKEN
```

**Every time you want a public URL:**
```bash
# Terminal 1 — start the pipeline server
python3 src/app.py

# Terminal 2 — open the tunnel
ngrok http 8000
```

ngrok prints your public URL:
```
Forwarding   https://gloater-unrevised-extradite.ngrok-free.dev -> http://localhost:8000
```

This URL is now accessible from anywhere. Share it with your instructor, a colleague, or open it on your phone. The pipeline runs on your local machine but is reachable globally.

**Important notes:**
- Keep both terminals open while the demo is running
- The URL `gloater-unrevised-extradite.ngrok-free.dev` is your stable named URL (persists across restarts when logged in)
- Free tier: 1 concurrent tunnel, no custom domain
- If you see "invalid token" errors: run `ngrok config add-authtoken YOUR_TOKEN` again

---

### Option B — Render (permanent deployment, always-on)

**What this gives you:** A permanent public URL that works even when your laptop is off. Free tier is sufficient for a capstone project.

**Steps:**

1. Push your project to GitHub:
```bash
git init
git add .
git commit -m "Initial deployment"
git remote add origin https://github.com/ioannarenta/media-intelligence-agent.git
git push -u origin main
```

2. Go to `https://render.com` → **New** → **Web Service**

3. Connect your GitHub repository

4. Render detects `render.yaml` automatically. Confirm:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python src/app.py`

5. Add all environment variables in the **Environment** tab:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME` = `media-intelligence`
   - `TAVILY_API_KEY`
   - `NEWSAPI_KEY`
   - `GUARDIAN_API_KEY`

6. Click **Deploy**. Your app will be live at:
   `https://media-intelligence-agent.onrender.com`

**Important notes:**
- Free tier spins down after 15 minutes of inactivity (first request takes ~30s to wake up)
- Paid tier ($7/month) keeps it always-on
- The `render.yaml` file in the project root configures everything automatically

---

### Which option to use for the presentation

| Scenario | Recommendation |
|----------|---------------|
| Live demo on your own laptop | Local (`python3 src/app.py`) |
| Sharing with instructor remotely | ngrok tunnel |
| Permanent URL for submission | Render free tier |
| Production use | Render paid tier or Railway |

---

## N8N Integration

### Workflow

1. **Webhook node** — accepts `POST /research` with body `{"outlet": "Reuters"}`
2. **Execute Command node** — runs `python3 -m src.agent.graph "{{$json.outlet}}"`
3. **IF node** — checks exit code (0 = success, other = failure)
4. **Respond to Webhook** — returns report on success
5. **Error handler** — logs failure on error

### Import the workflow

Import `n8n/workflow.json` into your N8N instance. Configure the Execute Command node with the correct path to your project.

### Trigger

```bash
curl -X POST https://your-n8n-instance/webhook/research \
  -H "Content-Type: application/json" \
  -d '{"outlet": "Reuters"}'
```

---

## RAG Knowledge Base

The agent's analysis is grounded in 11 pre-loaded industry documents:

| Document | Content |
|----------|---------|
| RSF Press Freedom Index 2026 | Country rankings, methodology, press freedom context |
| Reuters Institute Digital News Report | News consumption trends, trust data, platform dependency |
| Major Media Outlet Profiles | Reuters, BBC, Guardian, Der Spiegel, NYT, AP profiles |
| Media Industry Trends | AI in journalism, subscription economy, audience fragmentation |
| Editorial Standards & Metrics | Quality assessment frameworks, bias indicators |
| Media Ownership Map | Bertelsmann, Axel Springer, Murdoch, Vivendi ownership structures |
| Public Broadcasters Comparison | BBC, ARD/ZDF, France Télévisions, NHK — funding and editorial models |
| Digital Advertising Market | Platform dominance, publisher revenue collapse, responses |
| European Media Regulation | EMFA, DSA, GDPR, SLAPP directive |
| Podcast & Audio Landscape | News podcast strategy, platform dynamics |
| CJR Journalistic Access | Access journalism dynamics, editorial independence |

---

## Sample Reports

Three sample reports are included in `/reports/`:

- [`the_guardian.md`](reports/the_guardian.md) — The Guardian vs The Independent vs The Times
- [`reuters.md`](reports/reuters.md) — Reuters vs Bloomberg vs Associated Press
- [`der_spiegel.md`](reports/der_spiegel.md) — Der Spiegel vs Focus vs Die Zeit

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| LLM | gpt-4o-mini | Cost-efficient, sufficient for synthesis |
| Embedding model | text-embedding-3-small (1536 dims) | Good quality, low cost |
| Competitor count | 2 | Manageable API calls within free tier |
| Time windows | 30 / 90 / 180 days | Captures short, medium, and long-term drift |
| Scoring dimensions | 6 | Covers editorial, audience, digital, competitive |
| IRR method | Krippendorff's Alpha (ordinal) | Correct for 1-5 Likert scales; handles 3+ raters |
| IRR threshold | α > 0.6 = HIGH confidence | Standard academic benchmark |
| Consensus evaluations | 3 per dimension | Temperature 0.1 / 0.5 / 0.9 for genuine independence |
| Report format | Markdown | Human-readable, renders on GitHub, works with N8N |
| Competitor ID | LLM reasoning + Wikipedia | Better than hardcoded — handles geography and format correctly |

---

## Known Limitations

### NewsAPI Free Tier (30-day history only)
The free tier restricts article search to the last 30 days. Requests for 90-day and 180-day windows return HTTP 400 errors — this is expected and handled gracefully. The agent logs the error and uses MediaStack for extended date ranges. A paid NewsAPI subscription removes this restriction.

### MediaStack Free Tier (500 requests/month)
MediaStack supports the 90-day and 180-day article windows. The free tier allows approximately 55 full benchmark runs per month (9 MediaStack calls per run). Sufficient for development and demonstration; production use requires a paid tier.

### Reddit API (not integrated)
Reddit was planned for audience sentiment data. Network access was blocked during development (corporate VPN restriction). The architecture supports adding it as a 7th tool with no graph changes required.

### Krippendorff's Alpha with identical scores
When all 3 LLM evaluations agree perfectly (e.g. all return 4.0), Krippendorff's library raises an error. This is handled upfront — identical scores return α = 1.0 (perfect agreement) directly.

### RSS SSL certificates
Some outlets use HTTPS feeds with self-signed or unverified certificates. The RSS tool includes an SSL fallback handler. HTTP feed URLs are used where available (BBC, Reuters).

### Paywalled outlets with no public RSS
The Times and The Independent operate behind hard paywalls and do not publish public RSS feeds. The RSS tool returns empty results for these outlets gracefully. Research for these outlets relies on Guardian API historical windows and Wikipedia instead.

### Multi-model consensus scoring
The consensus scoring framework uses three different model architectures:
- **Evaluator 1:** gpt-4o-mini (conservative analytical perspective, temperature 0.3)
- **Evaluator 2:** claude-sonnet-4-6 (progressive editorial perspective, temperature 0.5)
- **Evaluator 3:** gpt-4o-mini (industry veteran perspective, temperature 0.9)

Dimensions showing α = 1.0 across all evaluators indicate **strong consensus** — the outlet's position on that dimension is unambiguous. Dimensions with α < 0.4 are flagged as **analytically contested** — this reflects genuine expert disagreement, not a system failure. These are the most nuanced dimensions and warrant human analyst judgment.

### GDELT rate limiting -- development environment fallback
GDELT enforces 1 request per 5 seconds and applies extended blocks (15-60 minutes) when limits are exceeded. During development, repeated testing exhausted the allowed request rate. The pipeline falls back to **Guardian API for all historical windows** (30d/90d/180d), which is unlimited and proven reliable.

GDELT tools (`gdelt_tool.py`, `gdelt_cache.py`) remain in the codebase and will work correctly in a production environment with controlled request rates. The GDELT cache layer (24h TTL) ensures each outlet is queried at most once per day in production.

**Fallback data sources for historical windows:**
- Window A (30 days): Guardian API + RSS feeds
- Window B (90 days): Guardian API
- Window C (180 days): Guardian API

---

## Evaluation Criteria Mapping

| Requirement | Implementation |
|-------------|---------------|
| ReAct pattern | `src/agent/react_agent.py` — LangGraph `create_react_agent` with 6 tools |
| LangGraph workflow | `src/agent/graph.py` — 6 nodes, conditional edges, state management |
| RAG system with Pinecone | `src/rag/ingest.py` + `src/rag/retriever.py` — 11 corpus documents |
| Minimum 3 MCP tools | 7 tools: Tavily, NewsAPI, Guardian, GDELT, Wayback Machine, Wikipedia, RSS |
| N8N deployment | `n8n/workflow.json` — webhook → Execute Command → respond |
| Autonomous operation | Single `run_pipeline("outlet")` call — no human intervention |
| Comprehensive reports | 10,000+ char reports with scorecard, drift, RAG, methodology |
| Error handling | Retry logic in all tools; conditional error routing in graph |
| Consensus scoring (bonus) | Krippendorff's Alpha per dimension, flagging system |
| Temporal drift (bonus) | 3-window topic cluster comparison with LLM interpretation |
| Comparative analysis (bonus) | 3-outlet benchmarking with automatic competitor identification |

---

## Author

**Ioanna Renta** — VP Engineering
[LinkedIn](https://linkedin.com/in/ioannarenta) · [GitHub](https://github.com/ioannarenta)

*Ironhack AI Engineering Programme · Module 3 Capstone · July 2026*

---

## N8N Integration

### Workflow overview

The N8N workflow orchestrates the full pipeline end-to-end:

```
Webhook (POST)
    → Parse Input (validate)
    → Check Notion (existing report?)
    → Check Cache (< 7 days old?)
        ├── YES → serve from cache
        └── NO  → Start Pipeline (POST /research)
                  → Poll Job Status every 30s
                  → Job complete
    → Extract Report Data
    → Build HTML Email
        ├── recipient provided → Send Gmail → Respond
        └── no recipient      → Respond (Notion only)
```

### Import

1. Open N8N → New Workflow → `...` → Import from file
2. Select `n8n/workflow.json`
3. Update the **Check Notion** node with your credentials:
   - URL: `https://api.notion.com/v1/databases/YOUR_DB_ID/query`
   - Authorization header: `Bearer YOUR_NOTION_TOKEN`
4. Update **Start Pipeline** and **Poll Job Status** URLs to your ngrok or Render URL
5. Connect your Gmail credential to the **Send Gmail** node
6. Activate the workflow

### Trigger

```bash
# Research + email delivery
curl -X POST https://YOUR_N8N_URL/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "outlet": "Reuters",
    "recipient_email": "analyst@company.com"
  }'

# Research + Notion only (no email)
curl -X POST https://YOUR_N8N_URL/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{"outlet": "BBC News"}'

# Force fresh run (ignore 7-day cache)
curl -X POST https://YOUR_N8N_URL/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{"outlet": "Reuters", "force_refresh": true}'
```

### Response

```json
{
  "status": "success",
  "outlet": "Reuters",
  "recipient": "analyst@company.com",
  "notion_url": "https://notion.so/...",
  "source": "cache",
  "message": "Brief delivered to analyst@company.com"
}
```

### Cache behaviour
Reports are cached in Notion for 7 days. If a report for the requested outlet exists and is less than 7 days old, the workflow serves it from Notion instead of running the full pipeline. Use `force_refresh: true` to override.
