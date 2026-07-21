"""
Consensus Scoring — Media Intelligence Agent
Implements the inter-rater reliability (IRR) scoring framework.

What this module does:
    For each outlet × dimension, runs 3 independent LLM evaluations
    at different temperature settings, calculates Krippendorff's Alpha
    across the 3 scores, and classifies the agreement level.

Why 3 evaluations at different temperatures:
    Temperature controls LLM randomness (0=deterministic, 1=creative).
    Running the same prompt at 0.1, 0.5, and 0.9 produces genuinely
    different scores -- simulating 3 independent human raters.
    This implements the Inter-Annotator Agreement (IAA) framework.

References:
    - https://en.wikipedia.org/wiki/Inter-rater_reliability
    - https://www.innovatiana.com/en/post/inter-annotator-agreement
"""
import os
import json
import time
import numpy as np
import krippendorff
from openai import OpenAI
from anthropic import Anthropic
from dotenv import load_dotenv

from src.scoring.dimensions import SCORING_DIMENSIONS

load_dotenv()

_openai    = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
LLM_MODEL  = "gpt-4o-mini"

# Three different models for genuine independent evaluation
# Different architectures produce genuinely different scores
EVALUATORS = [
    {
        "model":       "gpt-4o-mini",
        "provider":    "openai",
        "temperature": 0.3,
        "persona":     "You are a conservative media analyst who values evidence and precision above all.",
    },
    {
        "model":       "claude-sonnet-4-6",
        "provider":    "anthropic",
        "temperature": 0.5,
        "persona":     "You are a progressive media critic who focuses on editorial mission and societal impact.",
    },
    {
        "model":       "gpt-4o-mini",
        "provider":    "openai",
        "temperature": 0.9,
        "persona":     "You are an industry veteran who weighs commercial sustainability alongside editorial quality.",
    },
]

# Sleep between LLM calls to avoid rate limiting
EVAL_SLEEP_SECONDS = 0.5

# Krippendorff's Alpha thresholds
ALPHA_HIGH       = 0.6   # above this = HIGH confidence
ALPHA_MODERATE   = 0.4   # above this = MODERATE confidence
                          # below ALPHA_MODERATE = CONTESTED


def _call_openai(prompt: str, temperature: float, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI and return response text."""
    response = _openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=350,
    )
    return response.choices[0].message.content.strip()


def _call_anthropic(prompt: str, temperature: float) -> str:
    """Call Claude and return response text."""
    response = _anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=350,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def single_evaluation(
    outlet: str,
    dimension_key: str,
    context: str,
    evaluator: dict,
) -> dict:
    """
    Run one LLM evaluation for one dimension of one outlet.

    Args:
        outlet:        Outlet name (e.g. "Der Spiegel")
        dimension_key: One of the 6 dimension keys
        context:       Research findings + RAG context for this outlet
        evaluator:     Dict with model, provider, temperature, persona

    Returns:
        Dict with keys: score (float 1-5), reasoning (str), evidence (list)
    """
    from src.scoring.dimensions import get_dimension_prompt

    prompt_text  = get_dimension_prompt(dimension_key, outlet)
    persona      = evaluator.get("persona", "")
    temperature  = evaluator.get("temperature", 0.5)
    provider     = evaluator.get("provider", "openai")
    persona_line = (persona + "\n\n") if persona else ""

    full_prompt = f"""{persona_line}{prompt_text}

Context about {outlet}:
{context[:2500]}

Important scoring guidance:
- Use your general knowledge about {outlet} if the context above is limited
- Score based on the outlet's known reputation and industry standing
- Do not default to 3.0 simply because context is limited — use what you know
- A score of 3.0 means genuinely average, not "unknown"
- Provide 2-3 specific evidence bullets that justify the score
- Each evidence bullet should reference a verifiable fact with a source URL where possible

Return ONLY a JSON object in this exact format, nothing else:
{{
  "score": <number 1-5>,
  "reasoning": "<one sentence summary of the score>",
  "evidence": [
    {{"fact": "<specific verifiable fact>", "url": "<source URL or empty string>"}},
    {{"fact": "<specific verifiable fact>", "url": "<source URL or empty string>"}}
  ]
}}"""

    try:
        if provider == "anthropic":
            raw = _call_anthropic(full_prompt, temperature)
        else:
            model = evaluator.get("model", "gpt-4o-mini")
            raw = _call_openai(full_prompt, temperature, model)

        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
        return {
            "score":     float(max(1.0, min(5.0, data.get("score", 3.0)))),
            "reasoning": data.get("reasoning", "No reasoning provided."),
            "evidence":  data.get("evidence", []),
        }

    except json.JSONDecodeError:
        print(f"[consensus] JSON parse error for {outlet}/{dimension_key} at temp={temperature}")
        return {"score": 3.0, "reasoning": "Evaluation parse failed.", "evidence": []}

    except Exception as e:
        print(f"[consensus] Evaluation error for {outlet}/{dimension_key}: {e}")
        return {"score": 3.0, "reasoning": "Evaluation failed.", "evidence": []}


def calculate_alpha(scores: list[float]) -> float:
    """
    Calculate Krippendorff's Alpha for a list of scores from 3 raters.

    Args:
        scores: List of 3 float scores (e.g. [4.0, 3.0, 4.0])

    Returns:
        Krippendorff's Alpha as a float between 0 and 1.

    Alpha interpretation:
        > 0.8  = excellent agreement
        > 0.6  = good agreement     → HIGH confidence
        > 0.4  = moderate agreement → MODERATE confidence
        < 0.4  = poor agreement     → CONTESTED (flag for human review)
    """
    # Perfect agreement: all scores identical → alpha = 1.0
    # krippendorff library raises an error in this case, handle upfront
    if len(set(scores)) == 1:
        return 1.0

    try:
        # krippendorff expects matrix: rows=raters, cols=items
        # We have 3 raters, 1 item → shape (3, 1) transposed to (1, 3)
        reliability_data = np.array([[s] for s in scores]).T
        alpha = krippendorff.alpha(
            reliability_data=reliability_data,
            level_of_measurement="ordinal",  # correct for 1-5 Likert scales
        )
        return round(float(alpha), 3)

    except Exception:
        # Fallback: variance-based agreement
        # variance=0 (perfect) → alpha=1.0
        # variance=4 (max on 1-5 scale) → alpha=0.0
        variance = float(np.var(scores))
        return round(max(0.0, 1.0 - variance / 4.0), 3)


def classify_agreement(alpha: float) -> tuple[str, bool]:
    """
    Classify the agreement level and whether to flag for human review.

    Args:
        alpha: Krippendorff's Alpha value

    Returns:
        Tuple of (level_string, flagged_bool)
        - level_string: "HIGH", "MODERATE", or "CONTESTED"
        - flagged_bool: True if alpha < ALPHA_MODERATE (human review recommended)
    """
    if alpha >= ALPHA_HIGH:
        return "HIGH", False
    elif alpha >= ALPHA_MODERATE:
        return "MODERATE", False
    else:
        return "CONTESTED", True


def score_outlet_dimension(
    outlet: str,
    dimension_key: str,
    context: str,
) -> dict:
    """
    Score one dimension for one outlet using 3 independent evaluations.

    Args:
        outlet:        Outlet name
        dimension_key: One of the 6 dimension keys
        context:       Research findings + RAG context

    Returns:
        DimensionScore dict with keys:
            score, scores_raw, alpha, level, flagged, reasoning
    """
    evals = []
    for evaluator in EVALUATORS:
        result = single_evaluation(outlet, dimension_key, context, evaluator)
        evals.append(result)
        time.sleep(EVAL_SLEEP_SECONDS)

    raw_scores = [e["score"] for e in evals]
    mean_score = round(float(np.mean(raw_scores)), 2)
    alpha      = calculate_alpha(raw_scores)
    level, flagged = classify_agreement(alpha)

    # Collect evidence from all 3 evaluations, deduplicate by fact text
    all_evidence = []
    seen_facts   = set()
    for e in evals:
        for ev in e.get("evidence", []):
            fact = ev.get("fact", "").strip()
            if fact and fact not in seen_facts:
                seen_facts.add(fact)
                all_evidence.append(ev)

    return {
        "score":      mean_score,
        "scores_raw": raw_scores,
        "alpha":      alpha,
        "level":      level,
        "flagged":    flagged,
        "reasoning":  evals[1]["reasoning"],
        "evidence":   all_evidence[:6],  # cap at 6 evidence bullets
    }


def score_outlet(outlet: str, context: str) -> dict:
    """
    Score all 6 dimensions for one outlet.

    Args:
        outlet:  Outlet name
        context: Research findings + RAG context

    Returns:
        OutletScores dict with all 6 dimensions + overall_score
    """
    print(f"[consensus] Scoring: {outlet}")
    outlet_scores    = {"outlet_name": outlet}
    dimension_values = []

    for dim_key in SCORING_DIMENSIONS:
        print(f"[consensus]   {dim_key}...", end=" ", flush=True)
        dim_result = score_outlet_dimension(outlet, dim_key, context)
        outlet_scores[dim_key] = dim_result
        dimension_values.append(dim_result["score"])

        flag_str = " ⚠️  CONTESTED" if dim_result["flagged"] else ""
        print(f"{dim_result['score']}/5 "
              f"(α={dim_result['alpha']:.2f}, {dim_result['level']}){flag_str}")

    outlet_scores["overall_score"] = round(float(np.mean(dimension_values)), 2)
    print(f"[consensus] ✓ {outlet} overall: {outlet_scores['overall_score']}/5")
    return outlet_scores


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing consensus scoring...\n")

    context = """
    The Guardian is a British daily newspaper owned by the Scott Trust Limited.
    It is known for its liberal editorial stance, investigative journalism,
    and open-access publishing model funded by reader contributions.
    The paper has strong digital presence and a successful podcast strategy.
    """

    result = score_outlet_dimension("The Guardian", "editorial_independence", context)
    print(f"\nResult for editorial_independence:")
    print(f"  Score:      {result['score']}/5")
    print(f"  Raw scores: {result['scores_raw']}")
    print(f"  Alpha:      {result['alpha']}")
    print(f"  Level:      {result['level']}")
    print(f"  Flagged:    {result['flagged']}")
    print(f"  Reasoning:  {result['reasoning']}")
