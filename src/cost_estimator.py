"""
Cost Estimator — Media Intelligence Agent
Estimates LLM API cost for a fresh analysis vs serving from cache.

Pricing (OpenAI, as of mid-2026):
    gpt-4o-mini:  $0.15 / 1M input tokens,  $0.60 / 1M output tokens
    gpt-5.6-sol:  $2.00 / 1M input tokens,  $8.00 / 1M output tokens  (estimated)
    gpt-5.6-luna: $2.00 / 1M input tokens,  $8.00 / 1M output tokens  (estimated)

We use static token budgets per node -- close enough for display purposes.
"""

# ── Pricing per 1M tokens (USD) ─────────────────────────
PRICING = {
    "gpt-4o-mini": {"input": 0.15,  "output": 0.60},
    "gpt-5.6-sol":  {"input": 2.00,  "output": 8.00},
    "gpt-5.6-luna": {"input": 2.00,  "output": 8.00},
}


def _cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model, PRICING["gpt-4o-mini"])
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


def estimate_fresh_cost(n_outlets: int = 3) -> dict:
    """
    Estimate the cost of a fresh analysis for n outlets (target + 2 competitors).

    Returns a dict with per-step breakdown and total.
    """
    n = n_outlets

    # Node 1: competitor identification
    # 1 call, ~400 input + 100 output tokens
    node1 = _cost("gpt-4o-mini", 400, 100)

    # Node 2: ReAct research agent
    # Per outlet: ~8 reasoning+tool steps × ~600 input + 200 output tokens
    node2 = n * 8 * _cost("gpt-4o-mini", 600, 200)

    # Node 4: drift analysis
    # Per outlet: 4 topic extractions × (300in + 150out) + 1 interpretation × (400in + 200out)
    node4 = n * (4 * _cost("gpt-4o-mini", 300, 150) + _cost("gpt-4o-mini", 400, 200))

    # Node 5: consensus scoring (biggest cost)
    # Per outlet × 6 dimensions × 3 evaluators:
    #   - evaluator 1: gpt-4o-mini  (~2500in + 350out)
    #   - evaluator 2: gpt-5.6-sol  (~2500in + 350out)
    #   - evaluator 3: gpt-5.6-luna (~2500in + 350out)
    n_dims = 6
    node5 = n * n_dims * (
        _cost("gpt-4o-mini",  2500, 350) +
        _cost("gpt-5.6-sol",  2500, 350) +
        _cost("gpt-5.6-luna", 2500, 350)
    )

    # Node 6: report generation
    # executive summary + competitive position
    node6 = (
        _cost("gpt-4o-mini", 1500, 900) +   # executive summary
        _cost("gpt-4o-mini", 2000, 1500)     # competitive position
    )

    total = node1 + node2 + node4 + node5 + node6

    return {
        "total":         round(total, 4),
        "breakdown": {
            "competitor_identification": round(node1, 4),
            "research_react_agent":      round(node2, 4),
            "drift_analysis":            round(node4, 4),
            "consensus_scoring_54_evals": round(node5, 4),
            "report_generation":         round(node6, 4),
        },
        "n_outlets":     n_outlets,
        "n_evaluations": n_outlets * 6 * 3,
    }


CACHE_COST = 0.0001   # Notion API read + minimal overhead


def format_cost_summary(cost_dict: dict) -> str:
    """Format cost breakdown as a compact string for the report footer."""
    b = cost_dict["breakdown"]
    lines = [
        f"**Estimated API cost:** ${cost_dict['total']:.4f}",
        f"- Competitor identification: ${b['competitor_identification']:.4f}",
        f"- Research agent ({cost_dict['n_outlets']} outlets): ${b['research_react_agent']:.4f}",
        f"- Drift analysis: ${b['drift_analysis']:.4f}",
        f"- Consensus scoring ({cost_dict['n_evaluations']} evaluations): ${b['consensus_scoring_54_evals']:.4f}",
        f"- Report generation: ${b['report_generation']:.4f}",
    ]
    return "\n".join(lines)
