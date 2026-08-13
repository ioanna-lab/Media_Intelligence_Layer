# EU AI Act Self-Audit: Media Intelligence Agent
**Author:** Ioanna Renta
**System:** Media Intelligence Agent (Ironhack Module 3 Capstone)
**Date:** August 2026
**Status:** First-pass compliance assessment

---

## Phase 1 — System Brief

### What the system does

The Media Intelligence Agent is an autonomous competitive intelligence tool for the media industry. A user enters the name of a media outlet -- for example, Reuters, Der Spiegel, or The Guardian -- and the system independently researches that outlet and two automatically identified competitors, then produces a structured intelligence report. The entire pipeline runs without human intervention between the initial input and the final output.

The report covers six editorial dimensions: topic coverage, geographic focus, editorial stance, output volume, audience positioning, and competitive differentiation. Each dimension is scored on a 1--5 scale using a consensus method: three separate language model evaluators independently assess the same evidence, and a statistical agreement measure (Krippendorff's Alpha) is calculated to flag dimensions where the evaluators disagree significantly. Those flagged dimensions are surfaced to the user as lower-confidence findings.

The system also tracks editorial drift over time -- comparing how a given outlet's coverage has shifted between an earlier and a more recent period -- and benchmarks the primary outlet's scores against its two competitors.

### Inputs

- A media outlet name (free text, entered by the user)
- Live news articles fetched from NewsAPI and The Guardian API
- Web search results fetched via Tavily
- A retrieval-augmented knowledge base of 11 documents covering press freedom, media ownership, digital news trends, EU media regulation, and outlet profiles, stored in Pinecone

None of the inputs are personal data about individuals. The system analyses news organisations, not people. The only personal data in the system is account-level data for users of the web interface (email address, optionally provided for report delivery).

### Outputs

- A structured Markdown intelligence report stored in Notion and served via a standalone HTML viewer
- An executive summary covering what the outlet is, where it stands competitively, how it compares to peers, what is changing editorially, and strategic implications
- Scored dimension tables with confidence indicators
- Temporal drift analysis
- A Slack notification and optional Gmail delivery of the completed report

The output is a research brief -- a recommendation for further analysis, not an automated decision about any person or organisation.

### Who is affected by the output

Media strategists, journalists, publishers, and researchers who use the report to inform editorial or competitive strategy decisions. The subjects of the reports are media organisations, not individual people. Individual journalists are not scored, profiled, or assessed. The system analyses aggregate editorial output at the outlet level only.

### Human review

There is no mandatory human review step between the pipeline completing and the report being delivered. The user receives the finished report directly. The consensus scoring framework flags low-agreement dimensions, which signals to the reader that those findings carry lower confidence -- but no human reviewer is required to check or approve the output before it reaches the user.

Users can trigger a fresh analysis at any time, overriding the 7-day cache if they believe the report is outdated.

### Who built it

Built by Ioanna Renta as an individual capstone project for the Ironhack AI Engineering Programme (Module 3, July 2026). No team, no client organisation. Third-party APIs and platforms are embedded: OpenAI (GPT-4o-mini and GPT-5.6 model series for generation and evaluation), Pinecone (vector database for RAG), Tavily (web search), NewsAPI, The Guardian API, Notion (report storage), N8N (notification workflows), and Render (cloud hosting).

### Who would use it in production

The intended production user is a media industry professional -- a strategy analyst, editorial director, or researcher at a news organisation -- who needs a rapid, evidence-based competitive brief. It could also be used by media researchers or journalism educators. It is not intended for use in hiring, credit, law enforcement, or any other regulated domain.

---

## Phase 2 — Risk Tier Classification

### Classification table

| Question | Answer |
|---|---|
| Does this system fall under any prohibited category (Article 5)? | No. The system does not perform biometric surveillance, social scoring, subliminal manipulation, or any other prohibited practice. It analyses news organisations, not individuals. |
| Does this system operate in any of the eight Annex III areas? | No. Annex III covers education, employment, credit, law enforcement, border control, administration of justice, democratic processes, and critical infrastructure. Media competitive intelligence does not fall within any of these areas. |
| If Annex III: does it "significantly influence" decisions in that area? | Not applicable. |
| Does this system interact with end users or generate content requiring disclosure under Article 50? | Partially. The system generates AI-produced reports delivered to human users. Article 50(4) applies if outputs could be mistaken for human-authored analysis. The system does not impersonate a human analyst, but the reports are presented as finished documents without an explicit AI-generated label. |
| First-pass risk tier | **Minimal risk**, with a light Article 50(4) transparency consideration |
| One-sentence justification | The system analyses media organisations at the aggregate editorial level, processes no personal data about individuals in its core pipeline, falls within no Annex III regulated area, and produces advisory research output that does not trigger any prohibited practice under Article 5. |

### Ambiguity note

The single genuine classification ambiguity is whether Article 50(4) applies. That article requires labelling of AI-generated content that could be mistaken for genuine human-produced content. A polished, structured intelligence report delivered without a visible AI-generated label could plausibly mislead a reader about its origin -- particularly if shared downstream by the original user without context. This is a light obligation, not a reclassification to limited risk, but it should be resolved before production deployment.

A secondary question worth flagging for legal review: if the system is ever extended to score or profile individual journalists rather than outlets as a whole, the classification would need to be reassessed. Individual profiling in a professional context could engage Annex III employment-adjacent obligations or GDPR Article 22 considerations. The current design does not do this, but the extension path is foreseeable.

---

## Phase 3 — Role Map

### Role map table

| Role | Entity | Key AI Act obligations |
|---|---|---|
| **Provider** | Ioanna Renta (individual developer) | If placing the system on the market or putting it into service: technical documentation, transparency to deployers, post-market monitoring. For a minimal-risk system, these are not mandatory under the AI Act but represent good practice. Article 50(4) labelling obligation applies to AI-generated content. |
| **Deployer** | The production user (media organisation or researcher using the tool) | Obligation to use the system in accordance with its intended purpose; to not deploy it in a higher-risk context than designed for; to inform end users of AI involvement where required. For a minimal-risk system, no specific AI Act deployer obligations apply beyond the general prohibition on prohibited uses. |
| **Vendor -- OpenAI** | OpenAI (GPT-4o-mini, GPT-5.6 series) | OpenAI is the provider of the underlying language models. Their own AI Act obligations depend on how their models are classified -- general-purpose AI models above the compute threshold carry transparency obligations under Article 53. Ioanna, as a downstream builder, inherits the responsibility of understanding what OpenAI's models can and cannot reliably do, and designing accordingly. |
| **Vendor -- Pinecone** | Pinecone (vector database) | Infrastructure provider. No AI Act obligations specific to Pinecone's role here -- it stores and retrieves embeddings but does not perform inference or make decisions. |
| **Vendor -- Tavily, NewsAPI, Guardian API** | Data source providers | Not AI systems. Standard data licensing and terms of service apply. |
| **Vendor -- N8N** | N8N (workflow automation) | Infrastructure/orchestration. Not an AI system in the AI Act sense. Standard platform terms apply. |

### Role map narrative

For the purposes of this audit, Ioanna Renta functions as the **provider** -- the entity that designed, built, and would place the system on the market or into service. If the system were adopted by a media organisation and run on their behalf, that organisation would become the **deployer** with its own set of (minimal, for this risk tier) obligations.

The most significant vendor relationship from a compliance standpoint is with OpenAI. The consensus scoring framework deliberately uses three different model generations to reduce dependence on any single model's biases or failure modes. This is a sound design choice from both a quality and a compliance perspective -- it partially addresses the reliability concern that would be mandatory to document under Article 15 for a high-risk system.

---

## Phase 4 — Obligation Checklist

The system is classified as minimal risk. The high-risk obligation checklist (Article 9--15, 43, 47--49, 72) does not apply. Proceeding directly to Phase 5.

---

## Phase 5 — Gap Analysis and Remediation Plan

The system has no mandatory AI Act obligations beyond the Article 50(4) transparency consideration and standard GDPR compliance for user email data. The gaps below are therefore a mix of the one applicable AI Act obligation and parallel legal and operational issues that a responsible provider should address before production deployment.

---

### Gap 1 — Article 50(4): AI-generated content not labelled

**Obligation:** Article 50(4) requires that AI-generated content which could be mistaken for human-produced content carries a clear indication of its synthetic origin.

**Status: ✅ Resolved**

**What was done:** Two changes made to close this gap:
- `src/report/generator.py` (`format_header()`): A prominent blockquote banner now appears at the top of every report immediately after the title, stating clearly that the content was produced autonomously by the Media Intelligence Agent using large language models, has not been reviewed by a human analyst, and should be treated as a research starting point.
- `src/report/template.py` (`METHODOLOGY_TEXT`): The previously buried single-line note at the bottom of the methodology section was replaced with a clearly labelled Article 50(4) compliance banner referencing the EU AI Act explicitly.

**Escalation needed:** No.

---

### Gap 2 — No mandatory human review before report delivery

**Obligation:** Not a mandatory AI Act obligation at minimal risk. Flagged as an operational quality and trust gap.

**Status: ✅ Resolved**

**What was done:** A "How to Use This Report" section was added to `src/report/generator.py` (`generate_report()`), inserted immediately after the header and before the executive summary. It appears in every report and covers: how to interpret the 🔍 confidence flags, how to assess data currency, the requirement to verify specific claims before acting on them, and the instruction not to present the report as human-authored analysis. The framing is explicitly "research aid, not finished analysis."

**Escalation needed:** No.

---

### Gap 3 — GDPR: User email addresses collected without a documented lawful basis

**Obligation:** GDPR Article 6 (lawful basis for processing) and Article 13 (information to be provided to data subjects).

**Status: ⚠️ Partially resolved — escalation still required**

**What was done:** A privacy notice was added directly below the email input field in `src/web/index.html`: "Your email address is used only to deliver this report and is not stored or shared after delivery." This closes the visible disclosure gap -- users are now informed at the point of collection what their email will be used for.

**What remains open:** The lawful basis for processing has not been formally documented, and no data subject rights mechanism (deletion request, access request) exists. These require legal review before production deployment at scale. The notice as implemented is consistent with a legitimate interests basis, but that basis must be assessed and documented by a privacy lawyer or DPO before the system is made available to external users beyond the course context.

**Escalation needed:** Yes -- privacy lawyer or DPO review required before production deployment.

---

### Gap 4 — No post-deployment monitoring or version control for model outputs

**Obligation:** Not mandatory at minimal risk. Flagged as an operational reliability gap with compliance implications if the system is ever reclassified.

**Current state:** The system uses three OpenAI model versions for consensus scoring. If OpenAI updates or deprecates a model, the scoring behaviour changes silently. There is no mechanism to detect output quality degradation over time, no logging of score distributions across runs, and no alert if the Krippendorff Alpha scores systematically worsen.

**Required state:** A production system whose outputs inform editorial strategy decisions should have basic output monitoring: a log of score distributions over time, an alert if consensus agreement drops below a threshold, and a documented process for handling model version changes.

**Remediation:** Implement a lightweight monitoring log that records per-run Krippendorff Alpha scores and average dimension scores. Set a threshold alert (e.g., if mean Alpha drops below 0.4 across five consecutive runs, flag for review). Document the OpenAI model versions in use and establish a review trigger when OpenAI announces deprecations.

**Escalation needed:** No -- engineering change only.

---

## Phase 6 — Compliance Memo

**To:** Head of Product, [Media Organisation]
**From:** Ioanna Renta, AI Systems Consultant
**Re:** EU AI Act Compliance Assessment -- Media Intelligence Agent
**Date:** August 2026
**Status:** First-pass assessment -- not a legal opinion

---

**System classification**

The Media Intelligence Agent is classified as **minimal risk** under the EU AI Act. It analyses media organisations at the aggregate editorial level, processes no personal data about individuals in its core pipeline, and produces advisory research output. It does not fall within any of the eight Annex III high-risk areas (education, employment, credit, law enforcement, etc.) and does not engage any prohibited practice under Article 5.

**Role map**

The developer (Ioanna Renta) functions as the **provider** for AI Act purposes -- the entity that built and would place the system on the market. Your organisation, as the operator of the tool in a professional context, functions as the **deployer**. The primary AI vendor is OpenAI, whose language models power the generation and evaluation pipeline. OpenAI carries its own obligations as a general-purpose AI model provider under Article 53 of the Act; your obligations as a downstream user are limited.

**Key findings**

Three issues require attention before production deployment, in order of priority:

First, the reports produced by the system carry no label identifying them as AI-generated. Article 50(4) of the EU AI Act requires that AI-produced content which could be mistaken for human-authored analysis be clearly marked as synthetic. A report forwarded internally or shared with an external party without context could mislead the recipient about its origin. This is a straightforward fix -- a standard header on every report -- but it must be in place before the system goes live.

Second, the system collects user email addresses without a privacy notice or documented lawful basis. Even optional collection of a single data point requires GDPR compliance: a notice at the point of collection, a clear retention policy, and a documented legal basis for processing. This is a gap that requires a brief legal review before deployment.

Third, there is no output monitoring in place. The consensus scoring framework is a sound design, but if the underlying models change or degrade, there is currently no mechanism to detect it. For a tool used to inform editorial strategy, silent quality degradation is a material risk.

**Recommended next steps**

1. Implement the Article 50(4) AI-generated content label on all report outputs immediately -- this requires no external input and should be done before any external user is given access.
2. Engage a privacy lawyer or data protection officer to confirm the lawful basis for email collection and draft a one-line privacy notice for the input field.
3. Implement a lightweight output monitoring log to track consensus agreement scores over time and alert when quality drops.
4. If the system is ever extended to score or profile individual journalists rather than outlets as a whole, commission a full compliance reassessment -- that extension would likely change the classification.

**Caveats**

This memo is a first-pass compliance assessment produced for planning purposes. It is not a legal opinion, a formal conformity assessment, or a certification of any kind. It does not constitute advice on GDPR compliance, data protection law, or any other area of law. Before production deployment, the organisation should seek independent legal advice on the points flagged above.

---

## Reinforce

### Components that might have been minimised

The most significant component to revisit is the OpenAI dependency. The system uses three model versions from the same provider for its consensus scoring framework. The intent is to simulate inter-annotator agreement across independent evaluators -- but if all three models share the same training data, the same provider biases, and the same failure modes, the independence assumption underlying Krippendorff's Alpha is weakened. Three evaluators from one provider are not equivalent to three genuinely independent human annotators.

This does not change the compliance classification -- it is a quality and methodology issue, not a regulatory one -- but it is worth naming in the compliance memo as a limitation. A future version using models from different providers (e.g., OpenAI, Anthropic, and Mistral) would have stronger claim to genuine consensus scoring.

### Design decision that creates a compliance burden in hindsight

The decision to deliver reports directly to users without any intermediate review step was made for user experience reasons -- a fully autonomous pipeline with instant delivery is the core value proposition. In hindsight, this design choice is the source of Gap 1 (no AI-generated label) and Gap 2 (no guidance on limitations). Both gaps exist because the system was designed to feel like a finished product rather than a research aid.

A better design for a production context would have separated the pipeline completion from the report delivery: the pipeline finishes, the report is held in Notion, and a notification tells the user it is ready -- exactly as the current system does -- but the report viewer would open with a mandatory acknowledgment screen: "This report was generated autonomously by an AI system. Review the confidence flags before acting on these findings." One click to proceed. This adds no meaningful friction but changes the framing entirely, closes Gap 1 and Gap 2 simultaneously, and protects both the provider and the deployer from downstream misuse.

---

## Stretch — Human Oversight Procedure

*Addressing Gap 2: the absence of guidance on how to review and interpret AI-generated reports before acting on findings.*

---

### Media Intelligence Agent — Report Review Procedure
**Version:** 1.0 draft
**Applies to:** All users receiving a Media Intelligence Agent report in a professional context

**Purpose**

This procedure ensures that intelligence reports generated by the Media Intelligence Agent are reviewed critically before being used as the basis for editorial, competitive, or strategic decisions.

**Who this applies to**

Any staff member who receives, acts on, or shares a Media Intelligence Agent report.

**Review steps**

Before acting on or sharing a report, the recipient must:

1. **Check the confidence flags.** Any dimension marked as low agreement (Krippendorff's Alpha below 0.6) should be treated as indicative, not definitive. Do not cite low-confidence findings in external communications without independent verification.

2. **Check the data currency.** The report header states the date range of the source articles. If the report is more than 7 days old and covers a fast-moving story or outlet, consider requesting a fresh analysis before acting on the findings.

3. **Verify any specific claims you intend to act on.** The report is a research starting point. If a specific finding -- a competitor's coverage shift, a topic cluster, a geographic focus change -- will inform a material editorial or commercial decision, verify it against at least one primary source before proceeding.

4. **Do not present the report as human-authored analysis.** If sharing the report internally or externally, make clear that it was produced by an AI system. The report header identifies it as AI-generated; do not remove or obscure this label.

**Override and escalation**

If a report contains findings that appear factually incorrect, internally inconsistent, or potentially harmful to an individual or organisation, do not share or act on those findings. Flag the report to the system administrator for review and, if necessary, request a fresh analysis or commission manual verification.

**Record-keeping**

Reports are stored in Notion with a timestamp and the outlet name as the record key. If a report is used as the basis for a material decision, note in the relevant decision record that AI-generated research was used and which report version was consulted.
