"""
Notion Integration — Media Intelligence Agent
Saves generated reports to a Notion database and fetches past reports.

What this does:
    After every pipeline run, creates a new page in the Notion
    "Media Intelligence Reports" database with:
    - Outlet name (title)
    - Date generated
    - Overall score
    - Competitors analysed
    - Top scoring dimension
    - Full report content (as Notion blocks)

    Also provides a function to list all past reports from Notion,
    enabling the UI to show a "Reports Library" page.

Setup:
    NOTION_TOKEN       = ntn_... (from notion.so/my-integrations)
    NOTION_DATABASE_ID = 3a6c7c0e0a7780c48213db9209ce20a9

Requires: pip install notion-client
"""
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN       = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "3a6c7c0e0a7780c48213db9209ce20a9")


def _get_client():
    """Get Notion client -- imported lazily so missing library doesn't crash startup."""
    try:
        from notion_client import Client
        return Client(auth=NOTION_TOKEN)
    except ImportError:
        raise ImportError("notion-client not installed. Run: pip install notion-client")


def _markdown_to_blocks(markdown: str, max_blocks: int = 80) -> list:
    """
    Convert Markdown text to Notion block objects.
    Notion has a 100-block limit per request -- we cap at 80 to be safe.
    Handles: headings, paragraphs, bullet lists, horizontal rules.
    """
    blocks  = []
    lines   = markdown.split("\n")

    for line in lines:
        if len(blocks) >= max_blocks:
            break

        line = line.rstrip()

        # Heading 1
        if line.startswith("# "):
            blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "text": {"content": line[2:][:2000]}}]}
            })
        # Heading 2
        elif line.startswith("## "):
            blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": line[3:][:2000]}}]}
            })
        # Heading 3
        elif line.startswith("### "):
            blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": line[4:][:2000]}}]}
            })
        # Bullet list
        elif line.startswith("- ") or line.startswith("* "):
            text = line[2:].strip()[:2000]
            blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]}
            })
        # Horizontal rule
        elif line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        # Blockquote
        elif line.startswith("> "):
            blocks.append({
                "object": "block", "type": "quote",
                "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:][:2000]}}]}
            })
        # Non-empty paragraph
        elif line.strip():
            # Strip markdown bold/italic for cleaner Notion display
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            clean = re.sub(r'\*(.+?)\*', r'\1', clean)
            clean = clean[:2000]
            blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": clean}}]}
            })

    return blocks


def _get_top_dimension(scores: dict, outlet: str) -> str:
    """Find the highest-scoring dimension for the target outlet."""
    from src.scoring.dimensions import SCORING_DIMENSIONS
    outlet_scores = scores.get(outlet, {})
    best_dim      = ""
    best_score    = 0.0

    for dim_key in SCORING_DIMENSIONS:
        score = outlet_scores.get(dim_key, {}).get("score", 0.0)
        if score > best_score:
            best_score = score
            best_dim   = SCORING_DIMENSIONS[dim_key]["label"]

    return best_dim


def save_report_to_notion(
    outlet_name:  str,
    report:       str,
    scores:       dict,
    competitors:  list[str],
    report_url:   str = "",
) -> str | None:
    """
    Save a generated report to the Notion database.

    Args:
        outlet_name:  Target outlet name
        report:       Full Markdown report string
        scores:       Scores dict from consensus_scoring_node
        competitors:  List of competitor names
        report_url:   Optional URL to the hosted report

    Returns:
        URL of the created Notion page, or None if failed.
    """
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("[notion] No credentials configured -- skipping Notion save")
        return None

    try:
        notion        = _get_client()
        overall_score = scores.get(outlet_name, {}).get("overall_score", 0.0)
        top_dim       = _get_top_dimension(scores, outlet_name)
        competitors_str = ", ".join(competitors)
        today         = datetime.now().strftime("%Y-%m-%d")

        # Create the database page
        page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Outlet": {
                    "title": [{"type": "text", "text": {"content": outlet_name}}]
                },
                "Generated": {
                    "date": {"start": today}
                },
                "Overall Score": {
                    "number": float(overall_score)
                },
                "Competitors": {
                    "rich_text": [{"type": "text", "text": {"content": competitors_str}}]
                },
                "Top Dimension": {
                    "rich_text": [{"type": "text", "text": {"content": top_dim}}]
                },
                "Status": {
                    "select": {"name": "Complete"}
                },
                **({"Report URL": {"url": report_url}} if report_url else {}),
            }
        )

        page_id  = page["id"]
        page_url = page["url"]
        print(f"[notion] Page created: {page_url}")

        # Append report content in batches of 80 blocks (Notion API limit)
        all_blocks = _markdown_to_blocks(report, max_blocks=500)
        batch_size = 80
        total      = 0
        for i in range(0, len(all_blocks), batch_size):
            batch = all_blocks[i:i + batch_size]
            notion.blocks.children.append(page_id, children=batch)
            total += len(batch)
        print(f"[notion] Appended {total} content blocks ({len(all_blocks)//batch_size + 1} batches)")

        return page_url

    except Exception as e:
        print(f"[notion] Error saving report: {e}")
        return None


def list_reports_from_notion() -> list[dict]:
    """
    Fetch all reports from the Notion database, sorted by date (newest first).

    Returns:
        List of dicts with keys: outlet, generated, overall_score,
        competitors, top_dimension, notion_url, status
    """
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("[notion] No credentials configured")
        return []

    try:
        import requests as req
        # Use raw HTTP request -- works across all notion-client versions
        url  = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
        hdrs = {
            "Authorization":  f"Bearer {NOTION_TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type":   "application/json",
        }
        body = {"sorts": [{"property": "Generated", "direction": "descending"}]}
        resp = req.post(url, headers=hdrs, json=body, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        reports = []
        for page in data.get("results", []):
            props = page.get("properties", {})

            def get_title(p):
                items = p.get("title", [])
                return items[0]["text"]["content"] if items else ""

            def get_text(p):
                items = p.get("rich_text", [])
                return items[0]["text"]["content"] if items else ""

            def get_date(p):
                d = p.get("date")
                return d["start"] if d else ""

            def get_number(p):
                return p.get("number") or 0.0

            def get_select(p):
                s = p.get("select")
                return s["name"] if s else ""

            def get_url(p):
                return p.get("url") or ""

            reports.append({
                "outlet":        get_title(props.get("Outlet", {})),
                "generated":     get_date(props.get("Generated", {})),
                "overall_score": get_number(props.get("Overall Score", {})),
                "competitors":   get_text(props.get("Competitors", {})),
                "top_dimension": get_text(props.get("Top Dimension", {})),
                "notion_url":    page.get("url", ""),
                "status":        get_select(props.get("Status", {})),
            })

        print(f"[notion] Retrieved {len(reports)} reports")
        return reports

    except Exception as e:
        print(f"[notion] Error fetching reports: {e}")
        return []


def list_reports_from_notion_legacy() -> list[dict]:
    """Legacy version using notion-client library."""
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return []

    try:
        notion   = _get_client()
        # Support both old and new notion-client API versions
        try:
            response = notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                sorts=[{"property": "Generated", "direction": "descending"}],
            )
        except AttributeError:
            # Newer notion-client versions use different syntax
            response = notion.databases.query(
                **{
                    "database_id": NOTION_DATABASE_ID,
                    "sorts": [{"property": "Generated", "direction": "descending"}],
                }
            )

        reports = []
        for page in response.get("results", []):
            props = page.get("properties", {})

            def get_title(p):
                items = p.get("title", [])
                return items[0]["text"]["content"] if items else ""

            def get_text(p):
                items = p.get("rich_text", [])
                return items[0]["text"]["content"] if items else ""

            def get_date(p):
                d = p.get("date")
                return d["start"] if d else ""

            def get_number(p):
                return p.get("number") or 0.0

            def get_select(p):
                s = p.get("select")
                return s["name"] if s else ""

            reports.append({
                "outlet":        get_title(props.get("Outlet", {})),
                "generated":     get_date(props.get("Generated", {})),
                "overall_score": get_number(props.get("Overall Score", {})),
                "competitors":   get_text(props.get("Competitors", {})),
                "top_dimension": get_text(props.get("Top Dimension", {})),
                "notion_url":    page.get("url", ""),
                "status":        get_select(props.get("Status", {})),
            })

        print(f"[notion] Retrieved {len(reports)} reports")
        return reports

    except Exception as e:
        print(f"[notion] Error fetching reports: {e}")
        return []


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing Notion integration...\n")
    print(f"Token:    {'configured' if NOTION_TOKEN else 'MISSING'}")
    print(f"Database: {NOTION_DATABASE_ID}")

    # Test fetching (should return empty list for new database)
    reports = list_reports_from_notion()
    print(f"\nExisting reports: {len(reports)}")

    # Test saving a dummy report
    test_report = """# Media Intelligence Brief: Test Outlet
*Generated by Media Intelligence Agent | 2026-07-20*

## Executive Summary
This is a test report to verify the Notion integration is working correctly.

## Competitive Scorecard
| Dimension | Test Outlet |
|-----------|-------------|
| Editorial Independence | 4.0/5 |

## Methodology
Test methodology note.
"""

    print("\nSaving test report to Notion...")
    url = save_report_to_notion(
        outlet_name  = "Test Outlet",
        report       = test_report,
        scores       = {"Test Outlet": {"overall_score": 4.0}},
        competitors  = ["Competitor A", "Competitor B"],
    )
    if url:
        print(f"Success! Notion page: {url}")
    else:
        print("Failed -- check token and database ID in .env")
