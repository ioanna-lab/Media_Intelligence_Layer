# Media Intelligence Agent

> Autonomous competitive benchmarking for media outlets. Give it an outlet. Get back a validated benchmark.

**Ironhack AI Engineering · Module 3 Capstone · Ioanna Renta · July 2026**

---

## What it does

The Media Intelligence Agent is a fully autonomous pipeline that:

1. Takes a media outlet name as input (e.g. "Reuters")
2. Identifies 2 competitors automatically (Wikipedia + LLM reasoning)
3. Researches all 3 outlets across 7 data sources and 3 historical time windows
4. Retrieves industry context via Pinecone RAG (11 curated documents)
5. Analyses temporal editorial drift (30/90/180-day windows)
6. Scores all outlets across 6 dimensions using 3 independent AI evaluators
7. Calculates Krippendorff's Alpha for inter-rater agreement
8. Generates a structured intelligence brief (~35-40k characters)
9. Saves to Notion, notifies via Slack, and sends by Gmail

**No human input required between trigger and report.**

---

## Architecture

```
Web UI (localhost / ngrok / Render)
    ↓
FastAPI /research
    ├── Check Notion cache (7 days)
    │   ├── HIT  → return instantly + notify N8N
    │   └── MISS → run pipeline
    ↓
LangGraph Pipeline (6 nodes)
    ├── Node 1: Identify competitors
    ├── Node 2: Research 3 outlets (ReAct agent, 7 tools)
    ├── Node 3: RAG retrieval (Pinecone)
    ├── Node 4: Drift analysis
    ├── Node 5: Consensus scoring (54 LLM evaluations)
    └── Node 6: Generate report → save to Notion
    ↓
N8N Workflow 1 (Notifications)
    ├── Fetch real Notion URL
    ├── Send Slack (always — IP, outlet, score, email status)
    └── Send Gmail (if recipient provided)
```

---

## Data Sources (7)

| Source | Purpose | Notes |
|--------|---------|-------|
| Tavily | Web search | Primary research |
| NewsAPI | Recent articles | 30-day free tier |
| Guardian API | Historical articles | 30/90/180-day windows |
| Wikipedia | Outlet profiles | Competitor identification |
| Wayback Machine | Archive snapshots | CDX API |
| RSS feeds | Real-time headlines | SSL fallback handler |
| GDELT | Global coverage | Rate-limited in dev; 24h cache |

---

## Consensus Scoring

Three independent AI evaluators score each outlet across 6 dimensions:

| Evaluator | Model | Temperature | Perspective |
|-----------|-------|-------------|-------------|
| 1 | gpt-4o-mini | 0.3 | Conservative analyst |
| 2 | gpt-5.6-sol | 1.0 | Progressive editorial critic |
| 3 | gpt-5.6-luna | 1.0 | Industry veteran |

**6 Dimensions:** Editorial Independence · Coverage Breadth · Audience Trust · Investigative Capacity · Digital Positioning · Competitive Differentiation

**Krippendorff's Alpha:**
- α = 1.0 → CONSENSUS (unambiguous signal)
- α ≥ 0.6 → HIGH agreement
- α 0.4–0.6 → MODERATE
- α < 0.4 → CONTESTED (genuine expert disagreement — not a failure)

---

## Stack

```
Python 3.11         FastAPI + Uvicorn
LangGraph            LangChain
OpenAI GPT-4o-mini / GPT-5.6-Sol / GPT-5.6-Luna
Pinecone             text-embedding-3-small
N8N Cloud            Notion API
Slack API            Gmail OAuth2
Render (Frankfurt)
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Ingest RAG corpus
python3 src/rag/ingest.py

# Start the server
python3 src/app.py
```

Open `http://localhost:8000` in your browser.

---

## Deployment

### Local (development)

```bash
# Terminal 1
python3 src/app.py
```

Open `http://localhost:8000` in your browser.

### Render (production)

Live at: **https://media-intelligence-layer.onrender.com**

`render.yaml` and `.python-version` are in the project root. To deploy your own instance:
connect your GitHub repo at render.com → New Web Service → add environment variables → deploy.

> **Note:** Free tier spins down after 15 minutes of inactivity. Open the URL ~1 minute before presenting to wake it up.

---

## Environment Variables

```
OPENAI_API_KEY
ANTHROPIC_API_KEY
PINECONE_API_KEY
PINECONE_INDEX_NAME=media-intelligence
TAVILY_API_KEY
NEWSAPI_KEY
GUARDIAN_API_KEY
NOTION_TOKEN
NOTION_DATABASE_ID
N8N_WEBHOOK_URL
N8N_EMAIL_WEBHOOK_URL
PUBLIC_URL=https://your-ngrok-url
```

---

## N8N Workflows

| Workflow | Path | Purpose |
|----------|------|---------|
| workflow_notify.json | /webhook/media-intelligence-notify | Called by FastAPI after completion. Slack + Gmail. |
| workflow_email_only.json | /webhook/media-intelligence-email | Called by /send-report endpoint. Email only, no Slack. |

**Import:** N8N → New Workflow → ··· → Import from file → update Notion token in Check Notion node → connect Slack + Gmail credentials → Activate.

---

## Known Limitations

- NewsAPI: 30-day free tier only
- GDELT: rate-limited in dev; Guardian API is primary historical source
- The Times: hard paywall, no public RSS
- GPT-5.6 models: temperature must be 1 (no fine-grained control)
- Pipeline: 5-8 minutes per fresh run (cache reduces to instant for repeat queries)
- Render free tier: 30s cold start after 15 minutes of inactivity

---

## File Structure

```
src/
├── app.py                    FastAPI service + async job queue
├── run_agent.py              CLI entry point
├── cost_estimator.py         API cost estimation per run
├── agent/
│   ├── graph.py              LangGraph pipeline
│   ├── nodes.py              6 pipeline nodes
│   ├── state.py              AgentState TypedDict
│   ├── react_agent.py        ReAct agent with 6 tools
│   └── competitor_identifier.py
├── tools/                    7 data source tools
├── rag/                      Pinecone ingest + retriever
├── scoring/                  Consensus scoring + Krippendorff Alpha
├── report/                   Report generator + templates
├── integrations/
│   └── notion_client.py      Notion save + fetch (with block reconstruction)
└── web/
    └── index.html            Single-page UI (5 screens)
n8n/
├── workflow_notify.json      Workflow 1: Slack + Gmail notifications
└── workflow_email_only.json  Workflow 1b: Email only
corpus/                       11 RAG documents
reports/                      Generated .md reports (ephemeral on Render)
render.yaml                   Render deployment config
.python-version               Pins Python 3.11.9
```
