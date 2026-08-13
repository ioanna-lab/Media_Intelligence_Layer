"""
Report Template — Media Intelligence Agent
Defines the structure and section definitions for the output report.

What this module does:
    Defines the report schema -- which sections exist, what each section
    contains, and how they are ordered. The generator.py module uses
    this structure to assemble the final Markdown report.

Report structure:
    1. Header (title, metadata, benchmark context)
    2. Executive Summary (LLM-generated, 3 sentences)
    3. Competitive Scorecard (Markdown table, all outlets × all dimensions)
    4. Per-outlet sections:
       a. Research Findings (from ReAct agent)
       b. Temporal Drift Analysis (emerging/fading/stable topics)
       c. Industry Context (from RAG/Pinecone)
    5. Analytically Contested Dimensions (genuine expert disagreement)
    6. Methodology Note
"""
from dataclasses import dataclass


@dataclass
class ReportSection:
    """
    Defines one section of the report.

    Attributes:
        key:         Unique identifier for this section
        title:       Markdown heading text
        level:       Heading level (2 = ##, 3 = ###, 4 = ####)
        description: What this section contains
        required:    Whether this section must appear in every report
    """
    key:         str
    title:       str
    level:       int
    description: str
    required:    bool = True


# ── Report section definitions ────────────────────────────

REPORT_SECTIONS = [
    ReportSection(
        key         = "header",
        title       = "",  # special -- handled by generator
        level       = 1,
        description = "Title, generation date, outlets benchmarked",
        required    = True,
    ),
    ReportSection(
        key         = "executive_summary",
        title       = "Executive Summary",
        level       = 2,
        description = "3-sentence LLM-generated summary of key findings",
        required    = True,
    ),
    ReportSection(
        key         = "scorecard",
        title       = "Competitive Scorecard",
        level       = 2,
        description = "Markdown table: all outlets × all dimensions with α values",
        required    = True,
    ),
    ReportSection(
        key         = "outlet_sections",
        title       = "",  # per-outlet heading generated dynamically
        level       = 2,
        description = "Per-outlet: research findings, drift analysis, RAG context",
        required    = True,
    ),
    ReportSection(
        key         = "flagged_dimensions",
        title       = "🔍 Analytically Contested Dimensions",
        level       = 2,
        description = "Dimensions with α < 0.4 flagged for human validation",
        required    = False,  # only included if flagged dimensions exist
    ),
    ReportSection(
        key         = "methodology",
        title       = "Methodology",
        level       = 2,
        description = "Data sources, scoring approach, RAG corpus, limitations",
        required    = True,
    ),
]

# ── Scorecard column definitions ──────────────────────────

SCORECARD_DIMENSIONS = [
    ("editorial_independence",      "Editorial Independence"),
    ("coverage_breadth",            "Coverage Breadth"),
    ("audience_trust",              "Audience Trust"),
    ("investigative_capacity",      "Investigative Capacity"),
    ("digital_positioning",         "Digital Positioning"),
    ("competitive_differentiation", "Competitive Diff."),
]

# ── Methodology text ──────────────────────────────────────

METHODOLOGY_TEXT = """**Data sources:** Tavily web search · NewsAPI · Guardian API (historical windows: 30d/90d/180d) · Wayback Machine · RSS feeds · Wikipedia · GDELT (production environment)

**RAG corpus:** 11 industry documents — RSF Press Freedom Index, Reuters Institute Digital News Report, media outlet profiles, media ownership map, public broadcasters comparison, digital advertising market, European media regulation, podcast landscape, CJR journalistic access, media industry trends, editorial standards and metrics.

**Scoring framework:** Each of 6 dimensions scored by 3 independent LLM evaluations (gpt-4o-mini) at temperatures 0.1, 0.5, and 0.9. Consensus score = arithmetic mean. Inter-rater reliability = Krippendorff's Alpha (ordinal scale).

| Agreement level | Alpha threshold | Interpretation |
|----------------|----------------|----------------|
| STRONG CONSENSUS (α = 1.0) | All 3 evaluators identical | Clear, unambiguous signal |
| HIGH (α ≥ 0.6) | Evaluators broadly agree | Score reported with confidence |
| MODERATE (α 0.4–0.6) | Some evaluator divergence | Score reported with caveat |
| CONTESTED (α < 0.4) | Significant disagreement | Analytically contested — genuine expert divergence |

*Note: STRONG CONSENSUS on well-known outlets is expected and positive — it means the outlet's position on this dimension is unambiguous across evaluator perspectives.*

**Temporal drift:** Article topic clusters extracted by LLM across 3 time windows (30/90/180 days). Python set operations detect emerging, fading, and stable editorial themes.

**Competitor identification:** Automatic — LLM analyses Wikipedia profile + RAG context to identify the 2 closest competitors by geography, format, audience, and editorial positioning.

---

> **⚠️ AI-Generated Content — Article 50(4) EU AI Act**  
> This report was produced autonomously by the Media Intelligence Agent using large language models (OpenAI GPT-4o-mini). It has not been reviewed by a human analyst. It is intended as a research aid and should be reviewed critically before use in editorial, commercial, or strategic decisions.

*References: [Inter-rater reliability](https://en.wikipedia.org/wiki/Inter-rater_reliability) · [Inter-Annotator Agreement](https://www.innovatiana.com/en/post/inter-annotator-agreement)*"""


def get_section(key: str) -> ReportSection | None:
    """Return a section definition by key."""
    return next((s for s in REPORT_SECTIONS if s.key == key), None)


def get_required_sections() -> list[ReportSection]:
    """Return only the required sections."""
    return [s for s in REPORT_SECTIONS if s.required]
