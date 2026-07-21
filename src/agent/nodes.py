"""
LangGraph Nodes — Media Intelligence Agent
All node functions for the research pipeline graph.

Architecture:
    This file contains ONLY orchestration logic.
    Heavy logic lives in dedicated modules:
    - src/scoring/consensus.py  → consensus scoring + Krippendorff's Alpha
    - src/report/generator.py   → report assembly
    - src/scoring/dimensions.py → 6 dimension definitions

Node execution order:
    identify_competitors_node
        → research_node
            → retrieve_node
                → drift_analysis_node
                    → consensus_scoring_node
                        → report_node
    Any failure → error_node (graceful degradation)
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from openai import OpenAI

from src.agent.state import AgentState
from src.agent.competitor_identifier import get_research_targets
from src.agent.react_agent import research_outlet
from src.rag.retriever import retrieve_for_outlet, format_context
from src.tools.guardian_tool import get_guardian_historical_windows, get_guardian_competitive_coverage
from src.tools.wayback_tool  import get_wayback_profile
from src.tools.guardian_tool import get_guardian_historical_windows
from src.tools.rss_tool import get_rss_articles
from src.scoring.consensus import score_outlet
from src.report.generator import generate_report, save_report

load_dotenv()

_openai     = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL   = "gpt-4o-mini"
MAX_RETRIES = 2


# ════════════════════════════════════════════════════════
# NODE 1 — Identify Competitors
# ════════════════════════════════════════════════════════

def identify_competitors_node(state: AgentState) -> dict:
    """
    Node 1: Identify 2 closest competitors for the target outlet.
    Reads:  state["outlet_name"]
    Writes: state["competitors"], state["all_outlets"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 1: Identifying competitors for '{state['outlet_name']}'")
    print(f"{'='*60}")

    try:
        targets     = get_research_targets(state["outlet_name"])
        competitors = targets[1:]
        print(f"[node1] Competitors: {competitors}")
        return {
            "competitors": competitors,
            "all_outlets": targets,
        }
    except Exception as e:
        print(f"[node1] ERROR: {e}")
        return {
            "error":       str(e),
            "failed_node": "identify_competitors_node",
            "competitors": [],
            "all_outlets": [state["outlet_name"]],
        }


# ════════════════════════════════════════════════════════
# NODE 2 — Research
# ════════════════════════════════════════════════════════

def research_node(state: AgentState) -> dict:
    """
    Node 2: Run ReAct agent + fetch article windows for each outlet.
    Reads:  state["all_outlets"]
    Writes: state["raw_research"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 2: Researching {len(state['all_outlets'])} outlets")
    print(f"{'='*60}")

    raw_research = {}

    for outlet in state["all_outlets"]:
        print(f"\n[node2] Researching: {outlet}")

        for attempt in range(MAX_RETRIES + 1):
            try:
                findings      = research_outlet(outlet)
                guardian_hist = get_guardian_historical_windows(outlet)
                wayback_data  = get_wayback_profile(outlet)
                rss_articles  = get_rss_articles(outlet, max_results=20)

                raw_research[outlet] = {
                    "outlet_name":    outlet,
                    "findings":       findings,
                    # Guardian API for all 3 historical windows (unlimited, no rate limit)
                    "articles_30d":   guardian_hist.get("window_a", []),
                    "articles_90d":   guardian_hist.get("window_b", []),
                    "articles_180d":  guardian_hist.get("window_c", []),
                    "gdelt_timeline": [],   # GDELT rate-limited in this env; kept for future use
                    "gdelt_themes":   {"30d": [], "90d": [], "180d": []},
                    "guardian_30d":   guardian_hist.get("window_a", []),
                    "guardian_90d":   guardian_hist.get("window_b", []),
                    "guardian_180d":  guardian_hist.get("window_c", []),
                    "wayback":        wayback_data,
                    "rss_articles":   rss_articles,
                }

                guard_a  = len(guardian_hist.get("window_a", []))
                guard_b  = len(guardian_hist.get("window_b", []))
                guard_c  = len(guardian_hist.get("window_c", []))
                wb_snaps = wayback_data.get("frequency", {}).get("total_snapshots", 0)
                print(f"[node2] ✓ {outlet}: {len(findings)} chars | "
                      f"Guardian {guard_a}/{guard_b}/{guard_c} articles (30d/90d/180d) | "
                      f"Wayback {wb_snaps} snapshots | RSS {len(rss_articles)}")
                break

            except Exception as e:
                print(f"[node2] Attempt {attempt+1} failed for {outlet}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(3)
                else:
                    raw_research[outlet] = {
                        "outlet_name":    outlet,
                        "findings":       f"Research failed: {str(e)}",
                        "articles_30d":   [],
                        "articles_90d":   [],
                        "articles_180d":  [],
                        "gdelt_timeline": [],
                        "gdelt_themes":   {"30d": [], "90d": [], "180d": []},
                        "guardian_30d":   [],
                        "guardian_90d":   [],
                        "guardian_180d":  [],
                        "wayback":        {},
                        "rss_articles":   [],
                    }

    return {"raw_research": raw_research}


# ════════════════════════════════════════════════════════
# NODE 3 — RAG Retrieval
# ════════════════════════════════════════════════════════

def retrieve_node(state: AgentState) -> dict:
    """
    Node 3: Query Pinecone for industry context for each outlet.
    Reads:  state["all_outlets"]
    Writes: state["rag_context"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 3: Retrieving RAG context")
    print(f"{'='*60}")

    rag_context = {}

    for outlet in state["all_outlets"]:
        try:
            chunks  = retrieve_for_outlet(outlet)
            context = format_context(chunks, max_chars=2000)
            rag_context[outlet] = context
            print(f"[node3] ✓ {outlet}: {len(chunks)} chunks")
        except Exception as e:
            print(f"[node3] ERROR for {outlet}: {e}")
            rag_context[outlet] = "No RAG context available."

    return {"rag_context": rag_context}


# ════════════════════════════════════════════════════════
# NODE 4 — Drift Analysis
# ════════════════════════════════════════════════════════

def _extract_topics(articles: list, max_topics: int = 15) -> list[str]:
    """Extract topic keywords from article titles using LLM."""
    if not articles:
        return []

    titles = "\n".join([f"- {a.get('title', '')}" for a in articles[:20]])

    prompt = f"""Analyse these news article titles and extract the main topics covered.
Return a JSON array of topic strings (2-4 words each), maximum {max_topics} topics.
Focus on substantive topics (politics, economy, sport, environment etc.).
Return ONLY the JSON array, nothing else.

Article titles:
{titles}

Example: ["UK politics", "climate change", "technology regulation"]"""

    try:
        response = _openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        topics = json.loads(content)
        return [t.lower().strip() for t in topics if isinstance(t, str)]
    except Exception as e:
        print(f"[drift] Topic extraction error: {e}")
        return []


def _interpret_drift(outlet: str, emerging: list, fading: list, stable: list, volumes: dict) -> str:
    """Generate an editorial interpretation of the drift pattern."""
    prompt = f"""You are a media analyst. Interpret the editorial drift for '{outlet}':

Emerging topics (new in last 30 days): {emerging}
Fading topics (declining over 6 months): {fading}
Stable topics (consistent): {stable}
Article volumes: 30d={volumes.get('30d',0)}, 90d={volumes.get('90d',0)}, 180d={volumes.get('180d',0)}

Write 2-3 sentences interpreting what this reveals about editorial strategy. Be specific."""

    try:
        response = _openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Drift interpretation unavailable."


def drift_analysis_node(state: AgentState) -> dict:
    """
    Node 4: Temporal drift analysis across 3 time windows per outlet.
    Reads:  state["raw_research"]
    Writes: state["drift_results"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 4: Drift analysis")
    print(f"{'='*60}")

    drift_results = {}

    for outlet in state["all_outlets"]:
        research = state["raw_research"].get(outlet, {})
        print(f"\n[node4] Analysing: {outlet}")

        try:
            # Primary: LLM topic extraction from Guardian historical windows + RSS
            # GDELT themes kept in state for future use when rate limits allow
            topics_30d  = _extract_topics(research.get("guardian_30d",  []))
            topics_90d  = _extract_topics(research.get("guardian_90d",  []))
            topics_180d = _extract_topics(research.get("guardian_180d", []))
            rss_topics  = _extract_topics(research.get("rss_articles",  []))

            # Merge all sources
            all_30d  = list(set(topics_30d  + rss_topics))
            all_90d  = list(set(topics_90d))
            all_180d = list(set(topics_180d))

            set_30d  = set(all_30d)
            set_90d  = set(all_90d)
            set_180d = set(all_180d)

            emerging = list(set_30d - set_90d - set_180d)
            fading   = list(set_180d - set_30d)
            stable   = list(set_30d & set_90d & set_180d)

            volumes = {
                "30d":  len(research.get("articles_30d",  [])),
                "90d":  len(research.get("articles_90d",  [])),
                "180d": len(research.get("articles_180d", [])),
            }

            interpretation = _interpret_drift(outlet, emerging, fading, stable, volumes)

            # Store article examples for each topic cluster (Problem 2 fix)
            def find_articles_for_topic(topic: str, articles: list, max_examples: int = 3) -> list:
                """Find articles that likely relate to a topic keyword."""
                topic_lower = topic.lower()
                matches = []
                for a in articles:
                    title = a.get("title", "").lower()
                    if any(word in title for word in topic_lower.split() if len(word) > 3):
                        matches.append({
                            "title": a.get("title", ""),
                            "url":   a.get("url", ""),
                            "date":  a.get("published_at", ""),
                        })
                    if len(matches) >= max_examples:
                        break
                return matches

            all_articles_30d = (research.get("articles_30d", []) +
                                research.get("guardian_30d", []) +
                                research.get("rss_articles", []))

            emerging_with_examples = []
            for topic in emerging[:8]:
                examples = find_articles_for_topic(topic, all_articles_30d)
                emerging_with_examples.append({
                    "topic":    topic,
                    "examples": examples,
                })

            fading_with_examples = []
            all_articles_180d = research.get("articles_180d", []) + research.get("guardian_180d", [])
            for topic in fading[:8]:
                examples = find_articles_for_topic(topic, all_articles_180d)
                fading_with_examples.append({
                    "topic":    topic,
                    "examples": examples,
                })

            drift_results[outlet] = {
                "outlet_name":    outlet,
                "emerging":       emerging[:8],
                "fading":         fading[:8],
                "stable":         stable[:8],
                "emerging_with_examples": emerging_with_examples,
                "fading_with_examples":   fading_with_examples,
                "volume_change":  volumes,
                "gdelt_timeline": research.get("gdelt_timeline", []),
                "wayback_snapshots": research.get("wayback", {}).get("snapshots", []),
                "interpretation": interpretation,
            }

            print(f"[node4] ✓ {outlet}: {len(emerging)} emerging, "
                  f"{len(fading)} fading, {len(stable)} stable")

        except Exception as e:
            print(f"[node4] ERROR for {outlet}: {e}")
            drift_results[outlet] = {
                "outlet_name":    outlet,
                "emerging":       [],
                "fading":         [],
                "stable":         [],
                "volume_change":  {"30d": 0, "90d": 0, "180d": 0},
                "interpretation": f"Drift analysis failed: {str(e)}",
            }

    return {"drift_results": drift_results}


# ════════════════════════════════════════════════════════
# NODE 5 — Consensus Scoring
# ════════════════════════════════════════════════════════

def consensus_scoring_node(state: AgentState) -> dict:
    """
    Node 5: Score each outlet using consensus scoring with Krippendorff's Alpha.
    Delegates all scoring logic to src/scoring/consensus.py.
    Reads:  state["raw_research"], state["rag_context"]
    Writes: state["scores"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 5: Consensus scoring")
    print(f"{'='*60}")

    all_scores = {}

    for outlet in state["all_outlets"]:
        research_text = state["raw_research"].get(outlet, {}).get("findings", "")
        rag_text      = state["rag_context"].get(outlet, "")
        context       = f"{research_text[:2500]}\n\n{rag_text[:1000]}"

        try:
            outlet_scores        = score_outlet(outlet, context)
            all_scores[outlet]   = outlet_scores
        except Exception as e:
            print(f"[node5] ERROR for {outlet}: {e}")
            all_scores[outlet] = {"outlet_name": outlet, "overall_score": 0.0}

    return {"scores": all_scores}


# ════════════════════════════════════════════════════════
# NODE 6 — Report Generation
# ════════════════════════════════════════════════════════

def report_node(state: AgentState) -> dict:
    """
    Node 6: Generate the final Markdown report.
    Delegates all assembly logic to src/report/generator.py.
    Reads:  all state fields
    Writes: state["report"]
    """
    print(f"\n{'='*60}")
    print(f"NODE 6: Generating report")
    print(f"{'='*60}")

    try:
        report = generate_report(state)
        save_report(report, state["outlet_name"])
        return {"report": report}
    except Exception as e:
        print(f"[node6] ERROR: {e}")
        return {
            "report":      f"Report generation failed: {str(e)}",
            "error":       str(e),
            "failed_node": "report_node",
        }


# ════════════════════════════════════════════════════════
# ERROR NODE
# ════════════════════════════════════════════════════════

def error_node(state: AgentState) -> dict:
    """
    Error handler: called when any node sets state["error"].
    Increments retry count, clears error, allows graph to continue.
    """
    print(f"\n[ERROR NODE] Failure in: {state.get('failed_node', 'unknown')}")
    print(f"[ERROR NODE] Error: {state.get('error', 'unknown')}")
    print(f"[ERROR NODE] Retry count: {state.get('retry_count', 0)}")

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "error":       None,
        "failed_node": None,
    }
