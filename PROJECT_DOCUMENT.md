# Media Intelligence Agent — Project Document

**Module 3 Capstone · Ironhack AI Engineering**
**Author:** Ioanna Renta
**Date:** July 2026
**Presentation:** August 4, 2026

---

## Project Overview

The Media Intelligence Agent is an autonomous competitive intelligence system for the media industry. Given a media outlet name, it autonomously researches that outlet and two competitors, scores them across 6 editorial dimensions using inter-annotator agreement methodology, detects editorial drift over time, and delivers a structured intelligence brief via web UI, Notion, Slack, and Gmail.

**The core thesis:** Competitive media analysis should be repeatable, evidence-based, and statistically validated — not dependent on individual analyst judgment.

---

## Why Inter-Annotator Agreement?

The instructor pointed to two academic frameworks:
- Wikipedia's IRR (Inter-Rater Reliability) documentation
- Innovatiana's IAA (Inter-Annotator Agreement) paper

The key insight: a single AI evaluator giving a score is unreliable. Three independent evaluators with different models, temperatures, and analytical perspectives — with Krippendorff's Alpha measuring their agreement — turns a single opinion into a statistically grounded assessment.

**α < 0.4 doesn't mean the system failed.** It means the dimension is genuinely contested across analytical perspectives. That's the most interesting finding — it tells the analyst exactly where expert opinion diverges.

---

## Technical Architecture

### Pipeline (LangGraph — 6 nodes)

```
START
  ↓
Node 1: identify_competitors
  Wikipedia lookup + LLM reasoning
  Output: [outlet, competitor_1, competitor_2]
  ↓
Node 2: research (× 3 outlets)
  ReAct agent, max 15 iterations, 7 tools
  Per outlet: web search, news articles, historical windows, Wikipedia, Wayback, RSS
  ↓
Node 3: retrieve (RAG)
  5 semantic queries per outlet × 3 outlets
  Pinecone index: media-intelligence, 11 documents, 1536 dims
  ↓
Node 4: drift_analysis
  Guardian API: 30/90/180-day article windows
  LLM categorises topics as: emerging / fading / stable
  ↓
Node 5: consensus_scoring
  3 evaluators × 6 dimensions × 3 outlets = 54 LLM calls
  Krippendorff's Alpha per dimension
  Flagged if α < 0.4 (analytically contested)
  ↓
Node 6: report
  generate_report() → Markdown ~35-40k chars
  save_to_notion() → batched blocks (80 per call)
  notify_n8n() → background thread
END
```

Error routing: any node failure → error_node

### Evaluator Models

| Evaluator | Model | Temperature | Persona |
|-----------|-------|-------------|---------|
| 1 | gpt-4o-mini | 0.3 | Conservative media analyst |
| 2 | gpt-5.6-sol | 1.0 | Progressive editorial critic |
| 3 | gpt-5.6-luna | 1.0 | Industry veteran |

Note: GPT-5.6 models only support temperature=1. gpt-4o-mini fallback activates automatically if GPT-5.6 fails.

### FastAPI Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| / | GET | Serve web UI |
| /research | POST | Start pipeline job, return job_id |
| /job/{job_id} | GET | Poll for completion |
| /view/{outlet} | GET | Standalone rendered report page (no Notion login needed) |
| /send-report | POST | Trigger email-only notification |
| /reports-library | GET | Fetch all reports from Notion |
| /report/{outlet} | GET | Fetch saved .md report (raw markdown) |
| /health | GET | Health check |

### Async Job Pattern

The pipeline takes 5-8 minutes. To avoid ngrok/proxy timeouts:

```
POST /research → job_id (< 1 second)
UI polls GET /job/{job_id} every 8 seconds
When complete → render report
```

Background thread monitors job completion and fires N8N webhook.

### Cache Logic

Before running the pipeline, FastAPI checks Notion for a report generated in the last 7 days:
- **Cache HIT** → return report instantly + fire N8N (Slack + Gmail)
- **Cache MISS** → run full pipeline
- **force_refresh=true** → bypass cache always

### N8N Workflow 1 (Notifications)

Triggered by FastAPI after every completion (cache hit or fresh run):
```
Webhook → Fetch from Notion (get real URL) → Prepare Messages →
  Slack (always: IP, outlet, score, email status, Notion link) →
  Has Recipient? → Gmail (if email provided)
```

Slack message always fires. Email is optional.

---

## UI Design

Four screens:

1. **Home** — outlet input, optional email, force refresh toggle, outlet chips
2. **Searching** — spinner while cache is checked
3. **Cache Found** — shows existing report details, two options: "Show this report" / "Run fresh analysis"
4. **Loading** — 6-step animated progress (only shown for fresh runs)
5. **Report** — full rendered brief with sidebar navigation, notification bar, send-to-email form
6. **Past Reports** — cards fetched from Notion database

Notification bar after report:
- With email: green bar — "Open full report → · Brief sent to X · Slack notified"
- Without email: blue bar — "Open full report → · Report ready · [Send to email] · [Download] · Slack notified"

---

## Hard Problems Solved

### 1. ngrok 30-second timeout
**Problem:** Pipeline takes 7 minutes. ngrok closes connections after 30 seconds.
**Solution:** Async job queue. POST /research returns job_id instantly. UI polls every 8 seconds.

### 2. α = 1.00 everywhere (fake consensus)
**Problem:** Three evaluations of the same model at similar temperatures always agreed.
**Solution:** Three different model generations (gpt-4o-mini, gpt-5.6-sol, gpt-5.6-luna) with different personas produce genuine variance.

### 3. Double Slack notifications
**Problem:** Cache hit fired N8N immediately; background thread also fired N8N when it detected completion.
**Solution:** `n8n_notified` flag on job dict. Background thread checks flag before firing.

### 4. GPT-5.6 temperature error
**Problem:** GPT-5.6 models only support temperature=1, not 0.3/0.5/0.7.
**Solution:** Set temperature=1 for GPT-5.6 evaluators. gpt-4o-mini fallback if model fails.

### 5. JavaScript onclick undefined
**Problem:** Functions defined in `<script>` tag not accessible from dynamically injected innerHTML buttons.
**Solution:** `window.functionName = function(){}` makes functions globally accessible.

### 6. GitHub push blocked by secret scanning
**Problem:** Notion API token committed inside N8N workflow JSON file.
**Solution:** Added .env and problematic N8N file to .gitignore. All API keys rotated.

### 7. N8N Execute Command unavailable on Cloud
**Problem:** N8N Cloud does not expose the Execute Command node.
**Solution:** N8N calls FastAPI via HTTP Request instead. Cleaner architecture — N8N is the orchestrator, Python is the engine.

### 9. Cache screen never appeared on Render / slow Notion
**Problem:** `startAnalysis()` did one immediate poll after POST /research. Notion lookup took longer than that poll, so status was still `running`. `pollJob()` returned `cached` but the code went straight to `renderReport()`, skipping the cache decision screen entirely.
**Solution:** Added cache screen routing inside the `pollJob()` return path -- if `data.status === 'cached'`, show the cache screen regardless of when Notion finished.

### 10. Ephemeral storage on Render
**Problem:** Render's free tier resets the filesystem on every deploy. `reports/*.md` files don't persist, so `/view/{outlet}` returned 404 and cache hits served empty reports.
**Solution:** Added `get_report_content_from_notion()` to `notion_client.py` -- fetches page blocks and reconstructs markdown on demand. `app.py` now fetches from Notion and saves locally when the local file is missing. Subsequent requests in the same session use the cached local file.

---

## Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| 5-8 min pipeline | Slow for first run | 7-day cache; cache screen shows existing report with cost comparison |
| NewsAPI 30-day limit | No historical news via NewsAPI | Guardian API covers 30/90/180d windows |
| GDELT rate-limited | Dev environment blocked | 24h JSON cache; Guardian as primary fallback |
| GPT-5.6 temp=1 only | Less evaluator diversity | gpt-4o-mini at temp=0.3 still provides variance |
| Render free tier cold start | 30s wake-up after 15min inactivity | Open URL before presenting; UptimeRobot ping option |
| Ephemeral Render storage | reports/ folder resets on redeploy | Notion blocks fetched and reconstructed on demand |
| The Times hard paywall | No RSS available | Removed from RSS map; graceful fallback |

---

## Planned Extensions (Post-Submission)

1. **Daily media briefing service** — N8N scheduled workflow, topic selection, autonomous curation, email delivery
2. **International outlets** — Le Monde, FAZ, El País, Corriere della Sera; multilingual reports
3. **Speed modes** — Quick (2-3 min) / Standard / Deep with configurable depth
4. **Signal detection** — Scheduled monitoring; Slack alert on significant editorial drift
5. **UptimeRobot keep-alive** — Ping Render every 5 minutes to prevent cold starts

---

## RAG Corpus (11 documents)

1. Press freedom and editorial independence frameworks
2. Digital news trends and audience behaviour
3. Outlet profiles: BBC, Guardian, Reuters, Der Spiegel
4. Media ownership and funding models
5. Public broadcaster landscape (EU)
6. Digital advertising market and media economics
7. EU media regulation (DSA, Media Freedom Act)
8. Podcast and audio journalism trends
9. CJR journalistic standards and access frameworks
10. AI in newsrooms — risks and opportunities
11. Competitive dynamics in European media

---

## Deployment Setup

### ngrok (demo)
```bash
# Terminal 1
python3 src/app.py

# Terminal 2
ngrok http 8000 --request-header-add "ngrok-skip-browser-warning:true"
```
Stable URL: `https://gloater-unrevised-extradite.ngrok-free.dev`
Authtoken configured. Persists across restarts when logged in.

### Render (production)
render.yaml in project root. Connect GitHub repo → add env vars → deploy.
Free tier spins down after 15 min inactivity (30s cold start).

---

## Session Log

- **Session 1–2:** Project scoping, tool selection, LangGraph pipeline design
- **Session 3–4:** Data source integration (7 tools), RAG corpus ingestion
- **Session 5–6:** Consensus scoring, Krippendorff Alpha, multi-model evaluators
- **Session 7–8:** Report generator, competitive position analysis, drift analysis
- **Session 9–10:** FastAPI, async job queue, ngrok deployment
- **Session 11:** Notion integration, N8N Workflow 1, Slack + Gmail delivery
- **Session 12:** UI rebuild (5 screens), email validation, stop modal, cache flow
- **Session 13:** Hard problem resolution (double Slack, datetime scope, onclick undefined)
- **Session 14:** Executive summary expansion, GPT-5.6 temperature fix, documentation
- **Session 15:** Cache screen race condition fix, interactive waiting panel (ethics quiz + media facts), "Run fresh analysis" buttons, Past Reports back navigation, /view/ endpoint replacing Notion links, drift section cleanup, cost estimator, Render deployment (Frankfurt, Python 3.11), Notion block reconstruction for ephemeral storage
