"""
Agent State — Media Intelligence Agent
Defines the shared state object that flows through every node in the LangGraph graph.

What is state?
    In LangGraph, state is a TypedDict — a Python dictionary with fixed, typed keys.
    Every node in the graph receives the full state, reads what it needs,
    does its work, and returns only the keys it changed. LangGraph merges
    the returned changes back into the state automatically.

    Think of it as a baton in a relay race. Each runner (node) receives
    the baton (state), adds something to it, and passes it to the next runner.

Why TypedDict?
    TypedDict gives us type hints without enforcement. Python won't crash
    if a key is missing — but our IDE will warn us, and we can write
    defensive code that checks for None values. It's a good balance
    between flexibility and structure.

State lifecycle:
    START
      → identify_competitors_node sets: competitors, all_outlets
      → research_node sets: raw_research
      → retrieve_node sets: rag_context
      → drift_analysis_node sets: drift_results
      → consensus_scoring_node sets: scores
      → report_node sets: report
    END
"""
from typing import TypedDict, Optional


class OutletResearch(TypedDict):
    """
    Research findings for a single outlet.
    Produced by the ReAct agent and stored in raw_research.
    """
    outlet_name:   str   # e.g. "The Guardian"
    findings:      str   # full research text from ReAct agent
    articles_30d:  list  # articles from last 30 days (NewsAPI/MediaStack)
    articles_90d:  list  # articles from last 90 days (MediaStack)
    articles_180d: list  # articles from last 180 days (MediaStack)
    rss_articles:  list  # current articles from RSS feed
    guardian_refs: list  # Guardian articles mentioning this outlet
    wiki_summary:  str   # Wikipedia summary text


class DriftResult(TypedDict):
    """
    Temporal drift analysis result for a single outlet.
    Produced by drift_analysis_node.
    """
    outlet_name:    str
    emerging:       list[str]  # topics appearing in last 30d not in 90d/180d
    fading:         list[str]  # topics strong 6mo ago, declining now
    stable:         list[str]  # consistent topics across all windows
    volume_change:  dict       # {"30d": int, "90d": int, "180d": int}
    interpretation: str        # LLM-generated interpretation of the drift


class DimensionScore(TypedDict):
    """
    Consensus score for one dimension of one outlet.
    Produced by consensus_scoring_node.
    """
    score:      float   # mean of 3 evaluations (1.0 - 5.0)
    scores_raw: list    # [score1, score2, score3] -- the 3 individual scores
    alpha:      float   # Krippendorff's Alpha (inter-rater agreement)
    level:      str     # "HIGH", "MODERATE", or "CONTESTED"
    flagged:    bool    # True if alpha < 0.4 (human review recommended)
    reasoning:  str     # LLM reasoning from the consensus evaluation


class OutletScores(TypedDict):
    """
    All 6 dimension scores for a single outlet.
    Produced by consensus_scoring_node.
    """
    outlet_name:              str
    editorial_independence:   DimensionScore
    coverage_breadth:         DimensionScore
    audience_trust:           DimensionScore
    investigative_capacity:   DimensionScore
    digital_positioning:      DimensionScore
    competitive_differentiation: DimensionScore
    overall_score:            float  # mean across all 6 dimensions


class AgentState(TypedDict):
    """
    The main state object passed between all nodes in the LangGraph graph.

    Every node receives this full state dict.
    Every node returns only the keys it changed.
    LangGraph merges changes back automatically.
    """

    # ── INPUT ─────────────────────────────────────────────
    outlet_name:  str             # target outlet provided by user
                                  # e.g. "Der Spiegel"

    # ── SET BY identify_competitors_node ──────────────────
    competitors:  list[str]       # 2 competitor outlet names
                                  # e.g. ["Focus", "Die Zeit"]

    all_outlets:  list[str]       # [target] + competitors (3 total)
                                  # e.g. ["Der Spiegel", "Focus", "Die Zeit"]

    # ── SET BY research_node ──────────────────────────────
    raw_research: dict            # {outlet_name: OutletResearch}
                                  # full research data per outlet

    # ── SET BY retrieve_node ──────────────────────────────
    rag_context:  dict            # {outlet_name: str}
                                  # formatted RAG context per outlet

    # ── SET BY drift_analysis_node ────────────────────────
    drift_results: dict           # {outlet_name: DriftResult}
                                  # temporal drift analysis per outlet

    # ── SET BY consensus_scoring_node ─────────────────────
    scores:       dict            # {outlet_name: OutletScores}
                                  # validated scores per outlet

    # ── SET BY report_node ────────────────────────────────
    report:       str             # final Markdown report (complete output)

    # ── ERROR HANDLING ────────────────────────────────────
    error:        Optional[str]   # error message if a node fails
    retry_count:  int             # number of retries attempted so far
    failed_node:  Optional[str]   # name of the node that failed


# ── Helper functions ──────────────────────────────────────

def initial_state(outlet_name: str) -> AgentState:
    """
    Create a clean initial state for a new research run.

    Args:
        outlet_name: The target outlet to research (e.g. "BBC News")

    Returns:
        AgentState with all fields initialised to empty/default values.
        Only outlet_name is set -- all other fields are filled by nodes.

    Example:
        state = initial_state("Der Spiegel")
        # Pass to graph.invoke(state)
    """
    return AgentState(
        outlet_name   = outlet_name,
        competitors   = [],
        all_outlets   = [outlet_name],
        raw_research  = {},
        rag_context   = {},
        drift_results = {},
        scores        = {},
        report        = "",
        error         = None,
        retry_count   = 0,
        failed_node   = None,
    )


def state_summary(state: AgentState) -> str:
    """
    Return a human-readable summary of the current state.
    Useful for debugging and logging.
    """
    lines = [
        f"Target outlet:  {state.get('outlet_name', 'not set')}",
        f"Competitors:    {state.get('competitors', [])}",
        f"All outlets:    {state.get('all_outlets', [])}",
        f"Raw research:   {list(state.get('raw_research', {}).keys())}",
        f"RAG context:    {list(state.get('rag_context', {}).keys())}",
        f"Drift results:  {list(state.get('drift_results', {}).keys())}",
        f"Scores:         {list(state.get('scores', {}).keys())}",
        f"Report length:  {len(state.get('report', ''))} chars",
        f"Error:          {state.get('error', 'none')}",
        f"Retry count:    {state.get('retry_count', 0)}",
    ]
    return "\n".join(lines)


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing state definition...\n")

    state = initial_state("Der Spiegel")
    print("Initial state:")
    print(state_summary(state))

    # Simulate what identify_competitors_node would return
    state["competitors"] = ["Focus", "Die Zeit"]
    state["all_outlets"] = ["Der Spiegel", "Focus", "Die Zeit"]

    print("\nAfter competitor identification:")
    print(state_summary(state))

    print("\nState keys:", list(state.keys()))
    print("\nAll TypedDicts imported successfully.")
