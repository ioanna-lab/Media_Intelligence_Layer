"""
Competitor Identification — Media Intelligence Agent
Automatically identifies the 2 closest competitors for a named media outlet.

What this does:
    Given a target outlet name, uses Wikipedia data + RAG context + LLM
    reasoning to identify the 2 most relevant competitors. These competitors
    are then researched in parallel alongside the target outlet.

Why this matters:
    The agent should not require the user to specify competitors manually.
    True autonomy means the agent decides which outlets to compare based
    on the target's type, geography, audience, and editorial positioning.

How it works:
    1. Fetch Wikipedia profile of target outlet (factual grounding)
    2. Retrieve RAG context about the outlet's category and market
    3. Ask LLM to identify 2 competitors with structured output
    4. Return competitor names as a clean list
"""
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL      = "gpt-4o-mini"

_openai = OpenAI(api_key=OPENAI_API_KEY)

# Known competitor mappings as fallback
# If LLM or Wikipedia fails, use these sensible defaults
FALLBACK_COMPETITORS = {
    "bbc":             ["Reuters", "The Guardian"],
    "bbc news":        ["Reuters", "The Guardian"],
    "reuters":         ["Associated Press", "Bloomberg"],
    "guardian":        ["BBC News", "The Independent"],
    "the guardian":    ["BBC News", "The Independent"],
    "der spiegel":     ["Focus", "Stern"],
    "spiegel":         ["Focus", "Stern"],
    "new york times":  ["Washington Post", "Wall Street Journal"],
    "nyt":             ["Washington Post", "Wall Street Journal"],
    "al jazeera":      ["BBC News", "Reuters"],
    "le monde":        ["Le Figaro", "Libération"],
    "financial times": ["Wall Street Journal", "The Economist"],
    "ft":              ["Wall Street Journal", "The Economist"],
    "cnn":             ["BBC News", "MSNBC"],
}


def identify_competitors(
    outlet_name: str,
    wikipedia_summary: str = "",
    rag_context: str = ""
) -> list[str]:
    """
    Identify the 2 closest competitors for a named media outlet.

    Args:
        outlet_name:       Name of the target outlet (e.g. "BBC News")
        wikipedia_summary: Wikipedia summary text for grounding (optional)
        rag_context:       RAG corpus context about the outlet (optional)

    Returns:
        List of exactly 2 competitor outlet names.
        Falls back to sensible defaults if LLM fails.

    Example:
        competitors = identify_competitors("Der Spiegel", wiki_summary, rag_ctx)
        # ["Focus", "Stern"]
    """
    print(f"\n[competitor_id] Identifying competitors for: {outlet_name}")

    # Build the prompt
    context_parts = []
    if wikipedia_summary:
        context_parts.append(f"Wikipedia summary:\n{wikipedia_summary[:800]}")
    if rag_context:
        context_parts.append(f"Industry context:\n{rag_context[:600]}")

    context_block = "\n\n".join(context_parts) if context_parts else "No additional context available."

    prompt = f"""You are a media industry analyst. Your task is to identify the 2 closest competitors to a named media outlet.

Target outlet: {outlet_name}

Context:
{context_block}

Instructions:
- Identify exactly 2 competitors that are most similar to {outlet_name}
- Consider: same geography, same audience type, same editorial format, same language
- Choose outlets that compete for the same readers/viewers
- Use well-known outlet names that can be found on NewsAPI, Wikipedia, and RSS feeds
- Return ONLY a JSON object in this exact format, nothing else:

{{"competitors": ["Competitor Name 1", "Competitor Name 2"], "reasoning": "One sentence explaining why these are the closest competitors."}}"""

    try:
        response = _openai.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # low temperature for consistent, factual output
            max_tokens=200,
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON response
        # Strip markdown code blocks if present
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        data        = json.loads(content)
        competitors = data.get("competitors", [])
        reasoning   = data.get("reasoning", "")

        if len(competitors) >= 2:
            result = competitors[:2]
            print(f"[competitor_id] Identified: {result}")
            print(f"[competitor_id] Reasoning: {reasoning}")
            return result
        else:
            print(f"[competitor_id] LLM returned fewer than 2 competitors, using fallback")
            return _fallback_competitors(outlet_name)

    except json.JSONDecodeError as e:
        print(f"[competitor_id] JSON parse error: {e} — using fallback")
        return _fallback_competitors(outlet_name)

    except Exception as e:
        print(f"[competitor_id] Error: {e} — using fallback")
        return _fallback_competitors(outlet_name)


def _fallback_competitors(outlet_name: str) -> list[str]:
    """
    Return hardcoded fallback competitors when LLM fails.
    Tries exact match, then partial match, then generic defaults.
    """
    key = outlet_name.lower().strip()

    # Exact match
    if key in FALLBACK_COMPETITORS:
        result = FALLBACK_COMPETITORS[key]
        print(f"[competitor_id] Using fallback: {result}")
        return result

    # Partial match
    for k, v in FALLBACK_COMPETITORS.items():
        if k in key or key in k:
            print(f"[competitor_id] Using partial fallback match '{k}': {v}")
            return v

    # Generic default
    default = ["Reuters", "BBC News"]
    print(f"[competitor_id] Using generic default: {default}")
    return default


def get_research_targets(outlet_name: str, wikipedia_summary: str = "", rag_context: str = "") -> list[str]:
    """
    Return the full list of outlets to research: target + 2 competitors.
    This is what the research_node uses to kick off parallel research.

    Returns:
        List of 3 outlet names: [target, competitor_1, competitor_2]
    """
    competitors = identify_competitors(outlet_name, wikipedia_summary, rag_context)
    targets     = [outlet_name] + competitors
    print(f"\n[competitor_id] Research targets: {targets}")
    return targets


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing competitor identification...\n")

    # Test 1: BBC News
    print("=" * 50)
    print("Test 1: BBC News")
    competitors = identify_competitors(
        "BBC News",
        wikipedia_summary="BBC News is the world's largest public broadcaster, funded by the UK licence fee.",
        rag_context="Public broadcasters compete with commercial outlets for audience trust and reach."
    )
    print(f"Result: {competitors}")

    # Test 2: Der Spiegel
    print("\n" + "=" * 50)
    print("Test 2: Der Spiegel")
    competitors = identify_competitors(
        "Der Spiegel",
        wikipedia_summary="Der Spiegel is Germany's most influential news magazine, published in Hamburg.",
    )
    print(f"Result: {competitors}")

    # Test 3: Full research targets
    print("\n" + "=" * 50)
    print("Test 3: Full research targets for Reuters")
    targets = get_research_targets("Reuters")
    print(f"Will research: {targets}")
