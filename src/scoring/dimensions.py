"""
Scoring Dimensions — Media Intelligence Agent
Defines the 6 scoring dimensions used in consensus scoring.

Note: The scoring logic (3 LLM evaluations + Krippendorff's Alpha)
is implemented in src/agent/nodes.py → consensus_scoring_node().
This file defines the dimension metadata for reference and reuse.
"""

# The 6 scoring dimensions with their labels and evaluation prompts.
# These are imported by nodes.py → consensus_scoring_node().

SCORING_DIMENSIONS = {
    "editorial_independence": {
        "label": "Editorial Independence",
        "description": "Ownership structure, separation from commercial/political influence, transparency.",
        "prompt": (
            "Rate the editorial independence of '{outlet}' on a scale of 1-5. "
            "Consider: ownership structure, separation from commercial interests, "
            "political independence, transparency. "
            "1=highly compromised, 5=fully independent."
        ),
    },
    "coverage_breadth": {
        "label": "Coverage Breadth & Depth",
        "description": "Range of topics, investigative capacity, international coverage, specialist expertise.",
        "prompt": (
            "Rate the coverage breadth and depth of '{outlet}' on a scale of 1-5. "
            "Consider: range of topics, investigative capacity, international coverage, "
            "specialist expertise. "
            "1=very narrow/shallow, 5=very broad/deep."
        ),
    },
    "audience_trust": {
        "label": "Audience Trust Signals",
        "description": "Track record for accuracy, correction policies, transparency, public perception.",
        "prompt": (
            "Rate the audience trust signals for '{outlet}' on a scale of 1-5. "
            "Consider: track record for accuracy, correction policies, transparency, "
            "public perception, trust survey data. "
            "1=low trust, 5=high trust."
        ),
    },
    "investigative_capacity": {
        "label": "Investigative Capacity",
        "description": "Dedicated investigative team, major investigations published, awards, resources.",
        "prompt": (
            "Rate the investigative journalism capacity of '{outlet}' on a scale of 1-5. "
            "Consider: dedicated investigative team, major investigations published, "
            "awards, resources allocated. "
            "1=no investigative capacity, 5=world-class investigative journalism."
        ),
    },
    "digital_positioning": {
        "label": "Digital & Audio Positioning",
        "description": "Digital product quality, podcast presence, social media reach, newsletter strategy.",
        "prompt": (
            "Rate the digital and audio positioning of '{outlet}' on a scale of 1-5. "
            "Consider: digital product quality, podcast presence, social media reach, "
            "app, newsletter strategy. "
            "1=very weak digital presence, 5=leading digital/audio strategy."
        ),
    },
    "competitive_differentiation": {
        "label": "Competitive Differentiation",
        "description": "Unique editorial voice, exclusive content, distinctive positioning, brand strength.",
        "prompt": (
            "Rate how well '{outlet}' differentiates itself from competitors on a scale of 1-5. "
            "Consider: unique editorial voice, exclusive content, distinctive positioning, "
            "brand strength. "
            "1=highly commoditised, 5=highly distinctive."
        ),
    },
}


def get_dimension_labels() -> list[str]:
    """Return a list of all dimension labels for display."""
    return [v["label"] for v in SCORING_DIMENSIONS.values()]


def get_dimension_prompt(dimension_key: str, outlet: str) -> str:
    """Return the evaluation prompt for a dimension with the outlet name filled in."""
    dim = SCORING_DIMENSIONS.get(dimension_key)
    if not dim:
        raise ValueError(f"Unknown dimension: {dimension_key}")
    return dim["prompt"].format(outlet=outlet)


if __name__ == "__main__":
    print("Scoring dimensions defined:\n")
    for key, dim in SCORING_DIMENSIONS.items():
        print(f"  {key}:")
        print(f"    Label: {dim['label']}")
        print(f"    Description: {dim['description']}")
        print()
