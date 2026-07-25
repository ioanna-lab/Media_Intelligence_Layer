# Media Intelligence Agent — Project Document
**Version:** 0.2 (living document — updated as we build)
**Presentation date:** August 1, 2026
**Start date:** July 14, 2026

---

## What This Project Is

An autonomous AI agent that benchmarks a media outlet against its competitors, tracks how its editorial focus has shifted over time, produces validated consensus scores across key dimensions, and detects emerging signals — all without human intervention.

**In one sentence:** Give it a media outlet name and get back a validated competitive intelligence benchmark — comparative scores, temporal drift analysis, and weak signal detection — grounded in industry context and statistically reliable.

**Why this matters for the grade:** It demonstrates every required pattern — ReAct reasoning, LangGraph state management, RAG retrieval, MCP tool integration, and N8N deployment — and goes beyond by applying academic inter-rater reliability frameworks to make AI-generated scores trustworthy and auditable.

---

## The Enhanced Scenario

**Input:** One target media outlet name (e.g. Reuters, Der Spiegel, BBC)

**What the agent does autonomously:**
1. Identifies the 2 closest competitors to the target outlet
2. Researches all 3 outlets across 3 time windows (30 / 90 / 180 days)
3. Retrieves industry context from Pinecone RAG
4. Detects topic drift — what each outlet is starting to cover, dropping, or intensifying
5. Scores all 3 outlets across 6 dimensions using consensus scoring (3 independent LLM evaluations per score)
6. Calculates inter-rater agreement (Krippendorff's Alpha) for every score
7. Flags low-agreement dimensions as "contested — human review recommended"
8. Generates a structured report with scorecard, narrative, drift analysis, and signals

**Output:** A structured Markdown report with:
- Competitive Scorecard (all 3 outlets, 6 dimensions, consensus scores + agreement levels)
- Executive Summary
- Temporal Drift Analysis (emerging, fading, stable topics per outlet)
- Editorial Focus & Topic Clusters
- Competitive Positioning
- Audience Signals
- Industry Context (from RAG)
- Weak Signals & Opportunities
- Sources

**Who would use this in the real world:** A media strategist, publisher, or M&A advisor who needs a validated, evidence-based competitive benchmark — not a one-off summary but a reliable, reproducible scoring system.

---

## The 5 Enhancement Layers

### Layer 1 — Comparative Analysis (MVP)
The agent doesn't just research one outlet. It identifies 2 competitors automatically and researches all 3 in parallel. The output is a side-by-side benchmark, not an isolated profile.

### Layer 2 — Temporal Drift (MVP)
NewsAPI is queried across 3 time windows per outlet:
- Last 30 days → what the outlet is covering NOW
- 31–90 days ago → last quarter
- 91–180 days ago → 6 months ago

Topic clusters are extracted per window. The drift analysis shows:
- **Emerging topics**: appeared in last 30 days, not before
- **Fading topics**: strong 6 months ago, declining now
- **Stable core**: consistent editorial identity
- **Volume shifts**: covering more or less overall

### Layer 3 — Scoring & Benchmarking (MVP)
Each outlet is scored 1–5 on 6 dimensions:
- Editorial independence
- Coverage breadth and depth
- Audience trust signals
- Investigative capacity
- Digital and audio positioning
- Competitive differentiation

### Layer 4 — Consensus Scoring / IRR (MVP)
For every score on every dimension, the agent runs **3 independent LLM evaluations** with different prompts and temperature settings. It then calculates **Krippendorff's Alpha** (the standard inter-rater reliability metric) across the 3 scores.

- α > 0.6 → HIGH CONSENSUS — score reported with confidence
- α 0.4–0.6 → MODERATE CONSENSUS — score reported with caveat
- α < 0.4 → LOW CONSENSUS — flagged as "contested, human review recommended"

This applies the academic Inter-Annotator Agreement (IAA) framework to AI scoring, making every score auditable and honest about its own uncertainty.

**References:**
- Inter-rater reliability: https://en.wikipedia.org/wiki/Inter-rater_reliability
- Inter-Annotator Agreement: https://www.innovatiana.com/en/post/inter-annotator-agreement

### Layer 5 — Signal Detection (Stretch)
A dedicated node looks for patterns the standard synthesis misses:
- Topics the outlet just started covering in the last 30 days
- Unusual spikes or drops in article volume
- Cross-outlet signals (all 3 outlets shifting in the same direction = industry trend; only 1 = outlet-specific)

### Layer 6 — Event-Triggered Monitoring (Stretch)
Beyond on-demand research, N8N runs a weekly scheduled check. When a trigger event is detected (ownership change, editorial leadership change, major retraction, coverage spike), the agent automatically generates a brief and posts a Slack notification.

---

## Architecture

```
Webhook trigger (on-demand) OR Schedule trigger (weekly, N8N)
        │
        ▼
identify_competitors_node
  → agent finds 2 competitors for the target outlet
        │
        ▼
research_node  [runs for target + 2 competitors]
  → ReAct agent per outlet
  → Tools: Tavily + NewsAPI (3 time windows) + Guardian
        │
        ▼
retrieve_node
  → Pinecone RAG: industry context for all 3 outlets
        │
        ▼
drift_analysis_node
  → topic clustering per time window per outlet
  → emerging / fading / stable / volume shift
        │
        ▼
synthesise_node
  → merges research + RAG + drift per outlet
        │
        ▼
consensus_scoring_node  ← IRR/IAA LAYER
  → 3 independent LLM evaluations per dimension per outlet
  → Krippendorff's Alpha calculated per score
  → low-agreement dimensions flagged
        │
        ▼
report_node
  → structured Markdown: scorecard + narrative + drift + signals + sources
        │
        ▼
IF event-triggered → Slack notification (stretch)
IF on-demand → return report via N8N webhook
```

---

## Project Structure

```
Media_Intelligence_Layer/
├── src/
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tavily_tool.py
│   │   ├── newsapi_tool.py
│   │   └── guardian_tool.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── react_agent.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── ingest.py        ✅ DONE
│   │   └── retriever.py
│   ├── report/
│   │   ├── __init__.py
│   │   ├── template.py
│   │   └── generator.py
│   ├── scoring/             ← NEW
│   │   ├── __init__.py
│   │   ├── dimensions.py    # 6 scoring dimensions defined here
│   │   └── consensus.py     # Krippendorff's Alpha calculation
│   └── run_agent.py
├── scripts/
│   └── trello_setup.py      ✅ DONE
├── n8n/
│   └── workflow.json
├── corpus/                  ✅ DONE (11 documents)
├── reports/
├── tests/
├── .env                     ✅ DONE
├── .env.example
├── .gitignore
├── requirements.txt
├── MILESTONE_PLAN.md
├── PROJECT_DOCUMENT.md
└── README.md
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent framework | LangChain + LangGraph | ReAct pattern, graph workflow |
| Vector database | Pinecone | RAG retrieval |
| LLM | OpenAI gpt-4o-mini | Reasoning, synthesis, scoring |
| Tool 1 | Tavily | Open web search |
| Tool 2 | NewsAPI | Article volume, 3 time windows |
| Tool 3 | Guardian API | Cross-reference coverage themes |
| IRR library | krippendorff (Python) | Inter-rater reliability calculation |
| Orchestration | N8N | Webhook + Execute Command + Slack |
| Language | Python 3.11+ | All agent code |

---

## API Keys

| Key | Status |
|-----|--------|
| OPENAI_API_KEY | ✅ Working |
| PINECONE_API_KEY | ✅ Working |
| TAVILY_API_KEY | ✅ Working |
| NEWSAPI_KEY | ✅ Working |
| GUARDIAN_API_KEY | ✅ Working |
| SLACK (existing) | ✅ Available for stretch |

---

## Milestone Plan

### Phase 1 — RAG Foundation
**Target: July 18 — STATUS: COMPLETE ✅**

- [x] P1.1 API keys (Tavily, NewsAPI, Guardian)
- [x] P1.2 Project repo and folder structure
- [x] P1.3 RAG corpus assembled (11 documents)
- [x] P1.4 Pinecone index setup and embedding pipeline

---

### Phase 2 — Agent & Tools
**Target: July 24 — STATUS: COMPLETE ✅**

- [ ] P2.1 Build Tavily web search tool (MCP)
- [ ] P2.2 Build NewsAPI tool with 3 time windows (MCP)
- [ ] P2.3 Build Guardian API tool (MCP)
- [ ] P2.4 Build retriever.py (Pinecone query function)
- [ ] P2.5 Build ReAct agent with all 3 tools
- [ ] P2.6 Build competitor identification node

**Done when:** Agent researches a named outlet across 3 time windows and returns structured raw findings.

---

### Phase 3 — LangGraph Workflow & Reports
**Target: July 28 — STATUS: IN PROGRESS**

- [ ] P3.1 Design and implement full LangGraph workflow (all nodes)
- [ ] P3.2 Build drift_analysis_node (topic clustering across time windows)
- [ ] P3.3 Build consensus_scoring_node (3 LLM evals + Krippendorff's Alpha)
- [ ] P3.4 Build report template (scorecard + narrative + drift + signals)
- [ ] P3.5 Generate 3 sample reports (Reuters, Der Spiegel, The Guardian)

**Done when:** Full pipeline runs end-to-end, 3 sample reports committed to /reports/.

---

### Phase 4 — N8N & Polish
**Target: August 1 — STATUS: NOT STARTED**

- [ ] P4.1 Wrap agent as standalone Python script (run_agent.py)
- [ ] P4.2 Build N8N workflow (webhook → Execute Command → respond)
- [ ] P4.3 Error handling audit (5 consecutive runs without crash)
- [ ] P4.4 README + architecture diagram
- [ ] P4.5 Demo video (5–7 min)
- [ ] P4.6 [STRETCH] Event-triggered monitoring + Slack notification
- [ ] P4.7 [STRETCH] Signal detection node

**Done when:** POST to webhook returns a full validated benchmark report.

---

## Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| LLM | gpt-4o-mini | Cost-efficient, sufficient for synthesis |
| Embedding model | text-embedding-3-small | 1536 dims, good quality, low cost |
| Competitor count | 2 | Manageable API calls within free tier limits |
| Time windows | 30 / 90 / 180 days | Captures short, medium, and long-term drift |
| Scoring dimensions | 6 | Covers editorial, audience, digital, and competitive vectors |
| IRR method | Krippendorff's Alpha | Handles ordinal scales, works for 3+ raters |
| IRR threshold | α > 0.6 = high confidence | Standard academic benchmark |
| Consensus evaluations | 3 per dimension | Minimum for meaningful IRR calculation |
| Report format | Markdown | Human-readable, easy to render, works with N8N |

---

## Known Limitations

- Free tier NewsAPI: 100 requests/day limits how many outlets can be researched per run
- Competitor identification is LLM-based — agent may not always identify the most relevant competitors
- Temporal drift requires sufficient article volume to be meaningful; niche outlets may have sparse data
- Krippendorff's Alpha with only 3 evaluations has wider confidence intervals than academic standards (which use many human raters)

---

## Evaluation Checklist

- [ ] ReAct pattern implemented
- [ ] LangGraph workflow with state management and conditional routing
- [ ] Pinecone RAG system ✅
- [ ] Minimum 3 MCP tool integrations (Tavily, NewsAPI, Guardian) ✅
- [ ] N8N deployment via Execute Command node
- [ ] Agent operates autonomously without human intervention
- [ ] Comprehensive reports generated
- [ ] Error handling on all tool calls
- [ ] GitHub repo with commit history
- [ ] README with setup instructions
- [ ] 2–3 sample reports submitted
- [ ] Demo video (5–7 min)
- [ ] Architecture diagram
- [ ] Consensus scoring with IRR/IAA (Krippendorff's Alpha)
- [ ] Temporal drift analysis
- [ ] Comparative benchmarking (3 outlets)

---

## Phase 2 Completion Notes
**Completed: July 17, 2026**

### What was built

| File | Status | Notes |
|------|--------|-------|
| `src/tools/tavily_tool.py` | ✅ Tested | 5 results for BBC editorial focus query |
| `src/tools/newsapi_tool.py` | ✅ Tested | 20 articles (30d window); 90d/180d blocked by free tier |
| `src/tools/guardian_tool.py` | ✅ Tested | 20 results; 19 direct mentions of Der Spiegel |
| `src/tools/mediastack_tool.py` | ✅ Tested | Solves date limit; all 3 windows return data |
| `src/tools/wikipedia_tool.py` | ✅ Tested | Summary works; sections via parse API (mobile-sections deprecated) |
| `src/tools/rss_tool.py` | ✅ Tested | SSL fallback added; BBC 30 articles, Guardian 30, Spiegel 20 |
| `src/rag/retriever.py` | ✅ Tested | 7 unique chunks for Reuters; scores 0.52-0.59 |
| `src/agent/competitor_identifier.py` | ✅ Tested | BBC→[ITV, Channel 4]; Spiegel→[Die Zeit, Focus]; Reuters→[Bloomberg, AP] |
| `src/agent/react_agent.py` | ✅ Tested | Full research on The Guardian: 2868 chars, all 5 areas covered |

### Key findings and design decisions made in Phase 2

- **MediaStack added** to solve NewsAPI free tier date restriction (30 days only). MediaStack supports up to 1 year on free tier.
- **Wikipedia added** for factual grounding and competitor identification. Uses MediaWiki parse API (mobile-sections endpoint was decommissioned by Wikimedia).
- **RSS added** for real-time current articles. SSL fallback handler added for macOS certificate issues.
- **Reddit dropped** -- network access blocked by home VPN. Noted as known limitation.
- **Guardian dropped as date-limited source** -- Guardian API has no date restriction, used for 90d/180d cross-reference data.
- **Competitor identifier uses LLM reasoning** not a lookup table -- produces better results than hardcoded fallbacks (BBC → ITV/Channel 4, not Reuters/Guardian).
- **ReAct agent import fix** -- `sys.path.insert` added so file runs with both `python3 src/agent/react_agent.py` and `python3 -m src.agent.react_agent`.
- **Corpus re-ingested** -- 6 new documents added (media ownership map, public broadcasters, digital advertising, EU regulation, podcasts, CJR journalistic access). Total: 11 documents.

---

## Phase 3 — LangGraph Workflow
**Target: July 28 — STATUS: IN PROGRESS**

### What Phase 3 builds

Phase 3 is where all the Phase 2 components get connected into a single autonomous pipeline. We build the LangGraph state graph -- the workflow that runs from trigger to final report without any human intervention.

### The LangGraph state

The state is a TypedDict (a Python dictionary with fixed, typed keys) that flows through every node. Each node reads from it and writes back to it.

```python
class AgentState(TypedDict):
    # Input
    outlet_name:    str          # e.g. "Der Spiegel"

    # Set by identify_competitors_node
    competitors:    list[str]    # e.g. ["Focus", "Die Zeit"]
    all_outlets:    list[str]    # [target] + competitors

    # Set by research_node
    raw_research:   dict         # {outlet_name: findings_string}

    # Set by retrieve_node
    rag_context:    dict         # {outlet_name: formatted_context_string}

    # Set by drift_analysis_node
    drift_results:  dict         # {outlet_name: {emerging, fading, stable, volume}}

    # Set by consensus_scoring_node
    scores:         dict         # {outlet_name: {dimension: {score, alpha, level}}}

    # Set by report_node
    report:         str          # final Markdown report

    # Error handling
    error:          str          # error message if something fails
    retry_count:    int          # number of retries attempted
```

### The graph structure

```
START
  │
  ▼
identify_competitors_node
  → finds 2 competitors for target outlet
  → sets: competitors, all_outlets
  │
  ▼
research_node
  → runs ReAct agent for each outlet in all_outlets
  → sets: raw_research
  │
  ▼
retrieve_node
  → queries Pinecone for each outlet
  → sets: rag_context
  │
  ▼
drift_analysis_node  ← NEW in Phase 3
  → extracts topic clusters per time window
  → compares windows: emerging / fading / stable
  → sets: drift_results
  │
  ▼
consensus_scoring_node  ← NEW in Phase 3
  → 3 independent LLM evaluations per dimension per outlet
  → calculates Krippendorff's Alpha
  → flags low-agreement dimensions
  → sets: scores
  │
  ▼
report_node
  → fills report template with all state data
  → sets: report
  │
  ▼
END → returns report

Error handling:
  Any node failure → error_node → retry or graceful degradation
```

### Files to build in Phase 3

| File | Purpose |
|------|---------|
| `src/agent/state.py` | AgentState TypedDict definition |
| `src/agent/nodes.py` | All node functions (identify, research, retrieve, drift, score, report) |
| `src/agent/graph.py` | LangGraph graph assembly and compilation |
| `src/scoring/dimensions.py` | 6 scoring dimensions with prompts |
| `src/scoring/consensus.py` | Krippendorff's Alpha calculation |
| `src/report/template.py` | Report section definitions |
| `src/report/generator.py` | Report assembly from state data |

### Steps in order

- [ ] P3.1 Build `state.py` -- AgentState definition
- [ ] P3.1 Build `nodes.py` -- all node functions
- [ ] P3.1 Build `graph.py` -- assemble and compile the graph
- [ ] P3.2 Build `drift_analysis_node` -- topic clustering across 3 time windows
- [ ] P3.3 Build `consensus_scoring_node` -- 3 LLM evals + Krippendorff's Alpha
- [ ] P3.4 Build report template and generator
- [ ] P3.5 Run end-to-end test -- full pipeline on The Guardian
- [ ] P3.5 Generate 3 sample reports (Reuters, Der Spiegel, The Guardian)

### Done means
Full pipeline runs end-to-end. Input: "Reuters". Output: complete Markdown report with scorecard, drift analysis, and consensus scores. 3 sample reports committed to `/reports/`.

---

## Phase 3 Build Notes
**Started: July 18, 2026**

### Files built

| File | Purpose | Status |
|------|---------|--------|
| `src/agent/state.py` | AgentState TypedDict + helper functions | ✅ Tested |
| `src/agent/nodes.py` | All 6 node functions + error node | ✅ Built |
| `src/agent/graph.py` | Graph assembly, run_pipeline(), export_diagram() | ✅ Built |

### Architecture decisions made in Phase 3

**State structure:** 11 keys in AgentState. Nested TypedDicts (OutletResearch, DriftResult, DimensionScore, OutletScores) make each layer's data shape explicit and IDE-friendly.

**Error routing:** Conditional edges after every node check `state["error"]`. If error + retries remaining → error_node. After MAX_RETRIES → continue to next node anyway (graceful degradation, not crash).

**Drift detection via set mathematics:** Topic clusters extracted by LLM per window, then Python set operations detect emerging (A - B - C), fading (C - A), and stable (A ∩ B ∩ C) topics. Fast, deterministic, no extra LLM calls.

**Consensus scoring:** 54 LLM calls total (3 outlets × 6 dimensions × 3 temperatures). Temperature variation (0.1, 0.5, 0.9) simulates independent raters. Krippendorff's Alpha calculated per dimension. Scores below α=0.4 flagged for human review.

**Report structure:** Executive summary (LLM), comparative scorecard (Markdown table), per-outlet sections, flagged dimensions, methodology note. All assembled in report_node from state data.

### Key function: `run_pipeline(outlet_name)`

This is the single entry point for the entire system:
```python
from src.agent.graph import run_pipeline
report = run_pipeline("Der Spiegel")
```

Internally: build_graph() → initial_state() → graph.invoke() → save to /reports/ → return report string.

This is what Phase 4's `run_agent.py` and N8N Execute Command node will call.

### Evaluation checklist progress

- [x] ReAct pattern implemented (`react_agent.py`)
- [x] LangGraph workflow with state management and conditional routing (`graph.py`)
- [x] Pinecone RAG system (`ingest.py`, `retriever.py`)
- [x] Minimum 3 MCP tool integrations (Tavily, NewsAPI, Guardian, MediaStack, Wikipedia, RSS -- 6 total)
- [ ] N8N deployment via Execute Command node (Phase 4)
- [ ] Agent operates autonomously without human intervention (testing in progress)
- [ ] Comprehensive reports generated (testing in progress)
- [ ] Error handling on all tool calls (implemented, testing in progress)
- [ ] GitHub repo with commit history (Phase 4)
- [ ] README with setup instructions (Phase 4)
- [ ] 2-3 sample reports submitted (Phase 4)
- [ ] Demo video (Phase 4)
- [ ] Architecture diagram (export_diagram() built, will generate after first run)
- [x] Consensus scoring with IRR/IAA (Krippendorff's Alpha)
- [x] Temporal drift analysis (drift_analysis_node)
- [x] Comparative benchmarking (3 outlets)

---

## The 54 LLM Evaluations -- Consensus Scoring Breakdown

The consensus scoring node runs **54 independent LLM evaluations** per benchmark run. Here is exactly what they are:

### Structure

```
3 outlets × 6 dimensions × 3 temperatures = 54 evaluations
```

### The 3 Outlets (per run)
1. Target outlet (e.g. Der Spiegel)
2. Competitor 1 (e.g. Focus)
3. Competitor 2 (e.g. Die Zeit)

### The 6 Dimensions (per outlet)
1. **Editorial Independence** — ownership structure, separation from commercial/political influence
2. **Coverage Breadth & Depth** — range of topics, investigative capacity, international coverage
3. **Audience Trust Signals** — track record for accuracy, correction policies, public perception
4. **Investigative Capacity** — dedicated team, major investigations published, awards, resources
5. **Digital & Audio Positioning** — digital product quality, podcast presence, social media reach
6. **Competitive Differentiation** — unique editorial voice, exclusive content, brand strength

### The 3 Independent Evaluations (per dimension per outlet)

Each dimension is evaluated 3 times with different temperature settings to simulate independent raters:

| Evaluation | Temperature | Behaviour |
|------------|-------------|-----------|
| Eval 1 | 0.1 | Near-deterministic — most conservative, fact-driven score |
| Eval 2 | 0.5 | Balanced — moderate variation, considered judgement |
| Eval 3 | 0.9 | More exploratory — surfaces edge cases and nuance |

### What each evaluation returns

```json
{
  "score": 4.0,
  "reasoning": "The Guardian's Scott Trust ownership structure..."
}
```

### How the consensus is calculated

```
scores_raw = [4.0, 4.0, 3.0]         ← 3 evaluations
mean_score = 3.67                      ← reported score
alpha      = krippendorff.alpha(...)   ← inter-rater agreement
level      = "MODERATE"                ← HIGH / MODERATE / CONTESTED
flagged    = False                     ← True if alpha < 0.4
```

### Full breakdown for one benchmark run (e.g. Der Spiegel)

| # | Outlet | Dimension | Temp |
|---|--------|-----------|------|
| 1 | Der Spiegel | Editorial Independence | 0.1 |
| 2 | Der Spiegel | Editorial Independence | 0.5 |
| 3 | Der Spiegel | Editorial Independence | 0.9 |
| 4 | Der Spiegel | Coverage Breadth | 0.1 |
| 5 | Der Spiegel | Coverage Breadth | 0.5 |
| 6 | Der Spiegel | Coverage Breadth | 0.9 |
| 7 | Der Spiegel | Audience Trust | 0.1 |
| 8 | Der Spiegel | Audience Trust | 0.5 |
| 9 | Der Spiegel | Audience Trust | 0.9 |
| 10 | Der Spiegel | Investigative Capacity | 0.1 |
| 11 | Der Spiegel | Investigative Capacity | 0.5 |
| 12 | Der Spiegel | Investigative Capacity | 0.9 |
| 13 | Der Spiegel | Digital Positioning | 0.1 |
| 14 | Der Spiegel | Digital Positioning | 0.5 |
| 15 | Der Spiegel | Digital Positioning | 0.9 |
| 16 | Der Spiegel | Competitive Differentiation | 0.1 |
| 17 | Der Spiegel | Competitive Differentiation | 0.5 |
| 18 | Der Spiegel | Competitive Differentiation | 0.9 |
| 19 | Focus | Editorial Independence | 0.1 |
| 20 | Focus | Editorial Independence | 0.5 |
| 21 | Focus | Editorial Independence | 0.9 |
| 22 | Focus | Coverage Breadth | 0.1 |
| 23 | Focus | Coverage Breadth | 0.5 |
| 24 | Focus | Coverage Breadth | 0.9 |
| 25 | Focus | Audience Trust | 0.1 |
| 26 | Focus | Audience Trust | 0.5 |
| 27 | Focus | Audience Trust | 0.9 |
| 28 | Focus | Investigative Capacity | 0.1 |
| 29 | Focus | Investigative Capacity | 0.5 |
| 30 | Focus | Investigative Capacity | 0.9 |
| 31 | Focus | Digital Positioning | 0.1 |
| 32 | Focus | Digital Positioning | 0.5 |
| 33 | Focus | Digital Positioning | 0.9 |
| 34 | Focus | Competitive Differentiation | 0.1 |
| 35 | Focus | Competitive Differentiation | 0.5 |
| 36 | Focus | Competitive Differentiation | 0.9 |
| 37 | Die Zeit | Editorial Independence | 0.1 |
| 38 | Die Zeit | Editorial Independence | 0.5 |
| 39 | Die Zeit | Editorial Independence | 0.9 |
| 40 | Die Zeit | Coverage Breadth | 0.1 |
| 41 | Die Zeit | Coverage Breadth | 0.5 |
| 42 | Die Zeit | Coverage Breadth | 0.9 |
| 43 | Die Zeit | Audience Trust | 0.1 |
| 44 | Die Zeit | Audience Trust | 0.5 |
| 45 | Die Zeit | Audience Trust | 0.9 |
| 46 | Die Zeit | Investigative Capacity | 0.1 |
| 47 | Die Zeit | Investigative Capacity | 0.5 |
| 48 | Die Zeit | Investigative Capacity | 0.9 |
| 49 | Die Zeit | Digital Positioning | 0.1 |
| 50 | Die Zeit | Digital Positioning | 0.5 |
| 51 | Die Zeit | Digital Positioning | 0.9 |
| 52 | Die Zeit | Competitive Differentiation | 0.1 |
| 53 | Die Zeit | Competitive Differentiation | 0.5 |
| 54 | Die Zeit | Competitive Differentiation | 0.9 |

### Why 54 and not fewer

The minimum for a meaningful Krippendorff's Alpha calculation is 2 raters. We use 3 because:
- 2 raters can only agree or disagree -- no middle ground
- 3 raters allow partial agreement to be detected and measured
- 3 is the minimum that gives the alpha statistic statistical meaning
- Academic IAA studies typically use many more raters -- we acknowledge this as a limitation

Additionally, 0.5s sleep between evaluations to respect API rate limits adds ~27 seconds to the scoring phase alone, on top of the research time.

---

## Architecture Refactoring — Clean Separation of Concerns
**Completed: July 18, 2026**

### Problem
Phase 3 initial implementation placed all logic in `nodes.py` -- scoring, report assembly, formatting, everything. This violated separation of concerns and made the file 500+ lines of mixed responsibilities.

### Solution
Refactored into dedicated modules:

| Module | Responsibility | Before |
|--------|---------------|--------|
| `src/scoring/dimensions.py` | 6 dimension definitions + prompts | Inside nodes.py |
| `src/scoring/consensus.py` | Krippendorff's Alpha + 3-eval scoring | Inside nodes.py |
| `src/report/template.py` | Report section structure + methodology text | Inside nodes.py |
| `src/report/generator.py` | Markdown assembly + executive summary | Inside nodes.py |
| `src/agent/nodes.py` | Thin orchestration only | Everything |
| `src/run_agent.py` | CLI entry point for N8N | Missing |
| `src/app.py` | FastAPI REST service | Missing |

### nodes.py is now a thin orchestrator
Each node function is now ~20 lines. It receives state, calls the right module, returns the result. No formatting, no LLM scoring logic, no Markdown assembly.

### MediaStack rate limiting fix
**Problem:** MediaStack free tier (500 req/month) was exhausted during development, causing constant 429 errors and 14-second waits per outlet.

**Fix 1 -- One call per outlet:** `get_articles_all_windows()` now makes 1 API call (180 days) and filters locally by date to produce the 3 windows. Reduced from 9 calls per run to 3 calls per run.

**Fix 2 -- Session-level flag:** Once MediaStack returns 429 after retries, a `_rate_limited` module flag is set. All subsequent calls skip immediately with one log line. No more 14-second waits.

**Graceful degradation:** When MediaStack quota is exhausted, drift analysis uses NewsAPI (30d) + RSS only. Pipeline continues, report is generated, limitation noted in output.

### FastAPI service (`src/app.py`)
Four endpoints:
- `POST /research` -- run full pipeline, returns JSON with report
- `GET /health` -- service health check
- `GET /report/{outlet_name}` -- fetch saved report as Markdown
- `GET /reports` -- list all generated reports

Auto-generated interactive documentation at `http://localhost:8000/docs`.

Start: `python3 src/app.py`

### CLI entry point (`src/run_agent.py`)
Called by N8N Execute Command node:
```
python3 src/run_agent.py --outlet "Reuters"
```
- Outputs JSON to stdout (N8N reads this)
- Logs progress to stderr (N8N shows this separately)
- Exit code 0 = success, 1 = failure
- Saves report to `/reports/` automatically

### Current file count
```
src/ -- 15 Python files across 5 modules
corpus/ -- 11 .txt files (RAG knowledge base)
reports/ -- 3 .md files (sample reports)
scripts/ -- 2 utility scripts
```

---

## Historical Sources Upgrade
**Completed: July 18, 2026**

### MediaStack removed
MediaStack free tier (500 req/month) exhausted during development. Removed completely. Replaced with three unlimited sources.

### New historical data stack

| Source | Type | Coverage | Quota | Key feature |
|--------|------|----------|-------|-------------|
| GDELT | Articles + themes + timeline | Last 3 months | None (1 req/5s) | Domain queries for outlet's own content |
| Wayback Machine | Snapshot frequency + archive links | Since 1996 | None | Historical homepage evidence links |
| Guardian API (extended) | Peer journalism coverage | Since 2000 | None | 180d window GDELT cannot cover |

### GDELT lessons learned

**Domain queries are essential:**
```
Wrong: '"BBC News"'     → returns TV schedules mentioning BBC
Right: 'domain:bbc.co.uk' → returns articles published BY BBC
```

The `OUTLET_DOMAINS` dict in `gdelt_tool.py` maps outlet names to domains.

**Rate limits:** 1 request per 5 seconds. 6-second sleep before every call. Exceeding this triggers a 15-minute block. Tool now includes proper `Retry-After` header handling.

**3-month maximum:** GDELT DOC 2.0 API covers only the last 3 months. Windows adjusted to 30d/60d/90d. Guardian covers the 180-day window.

### Wayback Machine usage
- Snapshot frequency = proxy for outlet's web prominence
- Historical snapshot URLs = clickable evidence in the report
- CDX API, no key, no quota

### Guardian extended historical
- `get_guardian_historical_windows()` -- 30d/90d/180d coverage
- `get_guardian_competitive_coverage()` -- all 3 outlets simultaneously

### Drift analysis upgrade
- GDELT themes as primary topic source (structured, reliable taxonomy)
- LLM topic extraction as supplement
- Article examples with URLs now stored per topic cluster
- Wayback snapshot links included in drift section
- Result: every drift topic has evidence, not just a label

### Current tool inventory

| File | Tool | Free | Key needed |
|------|------|------|-----------|
| `tavily_tool.py` | Tavily web search | 1000/mo | Yes |
| `newsapi_tool.py` | NewsAPI articles | 100/day, 30d | Yes |
| `guardian_tool.py` | Guardian API | Unlimited | Yes |
| `gdelt_tool.py` | GDELT historical | Unlimited (1/5s) | No |
| `wayback_tool.py` | Wayback Machine | Unlimited | No |
| `wikipedia_tool.py` | Wikipedia | Unlimited | No |
| `rss_tool.py` | RSS feeds | Unlimited | No |

7 tools total. 4 require API keys, 3 are completely open.

### Remaining quality improvements (in progress)

- [ ] Problem 1: Evidence layer on every score (URLs per dimension)
- [ ] Problem 4: Competitive position rebuilt (5-question framework, comparative)
- [ ] Problem 5: Outlet categorisation by sector
- [ ] Problem 6: Competitive narrative section (cross-outlet comparison)
- [ ] FastAPI output formatting (currently plain JSON, needs structured response)

---

## Planned Extensions (Post-Submission)

### Daily Personalised Media Briefing Service

**Concept:** A second application built on the same infrastructure. Instead of researching one outlet competitively, the agent curates the top 5 stories per topic every morning and delivers them via email.

**User experience:**
1. User selects topics of interest (climate, AI regulation, geopolitics, finance, leadership, culture)
2. User selects preferred outlets or outlet categories
3. Every morning at 7am: N8N triggers the agent
4. Agent queries GDELT + Guardian + RSS for top stories per topic
5. Agent ranks by relevance, source quality, and recency
6. Curation quality handled autonomously (no human filtering)
7. Formatted email delivered with article titles, 2-sentence summaries, and links

**Two implementation options:**
- Option A: Standalone N8N workflow (separate from competitive brief pipeline)
- Option B: Add-on to competitive assessment ("you assessed Der Spiegel -- subscribe to daily Der Spiegel briefing on your topics")

**Why it fits the existing infrastructure:**
- GDELT already fetches articles by topic and domain
- Guardian API already returns structured article metadata
- RSS already provides real-time outlet content
- N8N already has scheduling and can send email
- Outlet categorisation (planned for current project) becomes the topic taxonomy

**Quality curation strategy (autonomous):**
- Deduplicate stories appearing across multiple sources
- Weight by outlet trust score from competitive brief
- Deprioritise opinion/commentary vs news reporting
- Score relevance to selected topics using LLM classification
- Flag stories covered by 3+ outlets as "high consensus" (reliable)

**Status:** Planned post-submission. Architecture designed, not yet built.

---

## Quality Improvements Round 1
**Completed: July 18, 2026**

### Problem 1 -- Evidence layer on scores
Every dimension score now includes:
- Score + Krippendorff Alpha + confidence level
- One-sentence reasoning
- 2-6 evidence bullets with source URLs
- Evidence collected from all 3 evaluations and deduplicated

Implementation: `src/scoring/consensus.py` -- `single_evaluation()` returns evidence JSON.
Rendering: `src/report/generator.py` -- `format_outlet_section()` renders clickable links.

### Problem 4 -- Competitive position rebuilt
New function: `src/report/generator.py` -- `generate_competitive_position()`

5-question framework:
1. Market Position (LEADING/CHALLENGING/FOLLOWING + confidence)
2. Editorial Differentiation (unique topics + coverage gaps)
3. Reputation Signals (peer journalism perception)
4. Trajectory (IMPROVING/STABLE/DECLINING + confidence)
5. Strategic Assessment (vulnerabilities + opportunities)

Cross-outlet context: all 3 outlets' data passed to LLM simultaneously.
Structured JSON output ensures consistent format across all runs.

### GDELT caching
New file: `src/tools/gdelt_cache.py`
- JSON file cache in `/cache/gdelt/`
- 24-hour TTL
- Transparent to callers -- same interface as direct API
- Eliminates repeated rate-limit blocks during development

### Report structure now (8 sections)
1. Header
2. Executive Summary
3. Competitive Scorecard (table)
4. **Competitive Position Analysis** ← NEW
5. Per-outlet sections (scores + evidence + drift + RAG)
6. Flagged dimensions (if any α < 0.4)
7. Methodology

---

## GDELT Fallback Decision
**Date: July 19, 2026**

### Problem
GDELT applied persistent rate limit blocks (60+ minutes) during development, making it unusable for repeated pipeline testing. Even with 6-second sleeps between requests and a 24-hour cache, the development environment triggered blocks that prevented forward progress.

### Decision
Replace GDELT as the active historical data source with Guardian API for all 3 time windows. Guardian is already integrated, tested, proven reliable, and has no rate limits or quotas.

### What stays
- `src/tools/gdelt_tool.py` -- kept in repo, fully functional
- `src/tools/gdelt_cache.py` -- kept in repo, 24h TTL cache
- GDELT documented in README, PROJECT_DOCUMENT, LEARNING_DOCUMENT
- GDELT mentioned in architecture as the production-intended historical source

### What changes
- `nodes.py` -- research_node uses `get_guardian_historical_windows()` instead of GDELT
- drift_analysis_node uses Guardian articles for topic extraction
- `gdelt_timeline` and `gdelt_themes` remain in state schema (empty in dev, populated in production)

### Production path
In production with controlled request rates:
1. GDELT cache ensures max 1 set of API calls per outlet per 24 hours
2. 7 GDELT calls × 6s sleep = 42 seconds per outlet (acceptable for production)
3. GDELT themes provide richer structured topic taxonomy than LLM extraction alone
4. Volume timeline data enables quantitative trend charts

### Historical window coverage (current)
| Window | Primary source | Fallback |
|--------|---------------|---------|
| 30 days | Guardian API + RSS | NewsAPI |
| 90 days | Guardian API | — |
| 180 days | Guardian API | — |
| Wayback snapshots | Wayback Machine CDX API | — |

---

## Deployment Setup
**Completed: July 20, 2026**

### Web UI

Built `src/web/index.html` -- a single-page application served by FastAPI at `/`.

Three screens:
- **Home:** Clean input, outlet suggestions, feature cards
- **Loading:** Animated step-by-step progress (6 steps, timed to match pipeline)
- **Report:** Full report rendered with sticky sidebar navigation, download button

Key design decisions:
- Fluid layout: fills any screen width, no fixed max-width constraint
- Sticky header: `position: sticky; top: 0; z-index: 200` -- stays in place on scroll
- Sidebar: `position: sticky; top: var(--header-h)` -- independent scroll from main content
- Visual hierarchy: h2 serif + border, h3 red left border, h4 background pill, coloured alpha values
- Alpha highlighting: GREEN for HIGH/✓, AMBER for MODERATE, RED for CONTESTED

### Option A -- ngrok (demo-ready)

**URL:** `https://gloater-unrevised-extradite.ngrok-free.dev`

**Setup (one-time):**
```bash
ngrok config add-authtoken YOUR_TOKEN
# Token at: https://dashboard.ngrok.com/get-started/your-authtoken
```

**Every session:**
```bash
# Terminal 1
python3 src/app.py

# Terminal 2
ngrok http 8000
```

The stable named URL persists across restarts when logged in to ngrok.

### Option B -- Render (permanent)

`render.yaml` in project root configures everything.

Steps: push to GitHub → Render → New Web Service → connect repo → add env vars → deploy.

URL pattern: `https://media-intelligence-agent.onrender.com`

Free tier: spins down after 15min inactivity (30s cold start).

---

## N8N Workflow
**Completed: July 25, 2026**

### Architecture decision
N8N Cloud does not support Execute Command node. Pipeline is called via HTTP Request to the FastAPI service instead. This is cleaner architecture -- N8N is the orchestration layer, Python is the intelligence layer.

### Workflow file
`n8n/workflow.json` -- import directly into N8N

### Nodes (in order)

| Node | Type | Purpose |
|------|------|---------|
| Webhook | Webhook | Receives POST /media-intelligence |
| Parse Input | Code | Validates outlet + recipient_email |
| Check Notion | HTTP Request | Queries Notion database for existing report |
| Check Cache | Code | Checks if report < 7 days old |
| Report in Notion? | IF | Routes: cache hit → Extract Data, miss → pipeline |
| Start Pipeline | HTTP Request | POST /research → returns job_id instantly |
| Store Job ID | Code | Extracts job_id from response |
| Poll Job Status | HTTP Request | GET /job/{job_id} every 30 seconds |
| Job Complete? | IF | Routes: complete → Extract Data, running → Wait |
| Wait 30s | Wait | Waits 30 seconds before polling again |
| Extract Report Data | Code | Pulls summary + scores from report or cache |
| Build Email | Code | Generates professional HTML email |
| Has Recipient? | IF | Routes: email provided → Gmail, none → Notion only |
| Send Gmail | Gmail | Sends formatted HTML brief to recipient |
| Respond Success | Respond to Webhook | Returns success JSON |
| Respond No Email | Respond to Webhook | Returns saved-to-Notion JSON |

### Trigger
```bash
# With email delivery
curl -X POST https://ac-pt-26-04-14.n8n.irn.hk/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{"outlet": "Reuters", "recipient_email": "ioanna@irenta.io"}'

# Without email (Notion only)
curl -X POST https://ac-pt-26-04-14.n8n.irn.hk/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{"outlet": "Reuters"}'

# Force fresh run (ignore cache)
curl -X POST https://ac-pt-26-04-14.n8n.irn.hk/webhook/media-intelligence \
  -H "Content-Type: application/json" \
  -d '{"outlet": "Reuters", "force_refresh": true, "recipient_email": "ioanna@irenta.io"}'
```

### Cache logic
- Report found in Notion AND < 7 days old → serve from cache (fast path, no pipeline)
- Report not found OR > 7 days old → run full pipeline (5-8 minutes)
- `force_refresh: true` → always run pipeline regardless of cache

### Polling strategy
- Pipeline returns job_id immediately (< 1 second)
- N8N polls GET /job/{job_id} every 30 seconds
- Maximum ~14 polls for a 7-minute run
- On complete → extract data → build email → send

### Important notes
- Notion credentials hardcoded in Check Notion node (N8N Cloud plan has no Variables feature)
- ngrok must be running for N8N to reach the local FastAPI
- Production deployment on Render would use a permanent URL instead of ngrok
- Wait node set to 30 seconds (not 10) to avoid excessive polling
