"""
ReAct Agent — Media Intelligence Agent
The core reasoning agent that researches a media outlet using multiple tools.

What this does:
    Implements the ReAct (Reasoning + Acting) pattern using LangGraph's
    create_react_agent. The agent reasons about what information it needs,
    selects the right tool, observes the result, and repeats until it has
    enough data to produce comprehensive raw research findings.

What ReAct means:
    Reason:  "I need to find BBC's editorial focus. I'll use web_search first."
    Act:     Calls web_search("BBC News editorial focus 2026")
    Observe: Gets back 5 search results
    Reason:  "I have general info. Now I need recent articles. I'll use newsapi."
    Act:     Calls get_news_articles("BBC News", days_back=30)
    Observe: Gets back 20 articles
    ... and so on until research is complete.

Tools available to the agent:
    1. web_search              (Tavily)
    2. get_news_articles       (NewsAPI - last 30 days)
    3. get_guardian_coverage   (Guardian API)
    4. get_historical_articles (MediaStack - extended date range)
    5. get_rss_articles        (RSS feeds)
    6. get_wikipedia_info      (Wikipedia)

Note: The agent does NOT call the Pinecone retriever directly.
    RAG retrieval happens in a separate retrieve_node in the LangGraph
    workflow, after the agent has gathered its raw research.
"""
import os
import sys

# Fix import path so the file can be run directly OR as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent

from src.tools.tavily_tool     import web_search             as _web_search
from src.tools.newsapi_tool    import get_news_articles       as _get_news_articles
from src.tools.guardian_tool   import get_guardian_coverage   as _get_guardian_coverage
from src.tools.mediastack_tool import get_mediastack_articles as _get_mediastack_articles
from src.tools.rss_tool        import get_rss_articles        as _get_rss_articles
from src.tools.wikipedia_tool  import get_wikipedia_summary   as _get_wikipedia_summary

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL      = "gpt-4o-mini"
MAX_ITERATIONS = 15


# ── Tool definitions ──────────────────────────────────────

@tool
def web_search(query: str) -> str:
    """
    Search the open web for information about a media outlet.
    Use for: editorial history, recent news, ownership, general background.
    Input: a specific search query string.
    Returns: list of web results with titles, URLs, and snippets.
    """
    results = _web_search(query, max_results=5)
    if not results:
        return "No web search results found."
    return "\n\n".join([
        f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}"
        for r in results
    ])


@tool
def get_news_articles(outlet_name: str) -> str:
    """
    Get recent news articles (last 30 days) published by a named media outlet.
    Use for: understanding current editorial topics and coverage focus.
    Input: the outlet name (e.g. 'BBC News', 'Reuters', 'Der Spiegel').
    Returns: list of recent article titles, dates, and URLs.
    """
    articles = _get_news_articles(outlet_name, days_back=30, max_results=20)
    if not articles:
        return f"No recent articles found for {outlet_name}."
    lines = [f"- {a['title']} ({a['published_at']})" for a in articles[:15]]
    return f"Recent articles from {outlet_name}:\n" + "\n".join(lines)


@tool
def get_guardian_coverage(query: str) -> str:
    """
    Search The Guardian for articles about a media outlet or topic.
    Use for: how other quality journalists cover and discuss the target outlet.
    Input: search query (e.g. 'Reuters news agency', 'BBC editorial bias').
    Returns: Guardian article headlines, sections, dates, and tags.
    """
    results = _get_guardian_coverage(query, days_back=180, max_results=10)
    if not results:
        return f"No Guardian coverage found for: {query}"
    lines = [
        f"- {r['headline']} [{r['section']}] ({r['published_date']})"
        for r in results[:10]
    ]
    return f"Guardian coverage of '{query}':\n" + "\n".join(lines)


@tool
def get_historical_articles(outlet_name: str) -> str:
    """
    Get news articles from the past 6 months about a media outlet.
    Use for: temporal drift analysis — understanding how coverage has changed.
    Input: the outlet name (e.g. 'BBC News', 'Reuters').
    Returns: articles from 30, 90, and 180 days ago with counts per window.
    """
    w30  = _get_mediastack_articles(outlet_name, days_back=30,  max_results=20)
    w90  = _get_mediastack_articles(outlet_name, days_back=90,  max_results=20)
    w180 = _get_mediastack_articles(outlet_name, days_back=180, max_results=20)

    def summarise(articles, label):
        if not articles:
            return f"{label}: No articles found"
        titles = [a["title"] for a in articles[:5]]
        return f"{label} ({len(articles)} articles):\n" + "\n".join(f"  - {t}" for t in titles)

    return "\n\n".join([
        summarise(w30,  "Last 30 days"),
        summarise(w90,  "Last 90 days"),
        summarise(w180, "Last 180 days"),
    ])


@tool
def get_rss_feed(outlet_name: str) -> str:
    """
    Get the latest articles from a media outlet's RSS feed.
    Use for: the most current editorial topics straight from the source.
    Input: outlet name (e.g. 'BBC News', 'The Guardian', 'Der Spiegel').
    Returns: recent article titles with dates.
    """
    articles = _get_rss_articles(outlet_name, max_results=20)
    if not articles:
        return f"No RSS feed available for {outlet_name}."
    lines = [f"- {a['title']} ({a['published_at']})" for a in articles[:15]]
    return f"RSS feed from {outlet_name}:\n" + "\n".join(lines)


@tool
def get_wikipedia_info(outlet_name: str) -> str:
    """
    Get factual background information about a media outlet from Wikipedia.
    Use for: founding date, ownership, circulation, editorial orientation.
    Input: outlet name (e.g. 'BBC News', 'Der Spiegel', 'Reuters').
    Returns: structured Wikipedia summary.
    """
    result = _get_wikipedia_summary(outlet_name)
    if not result:
        return f"No Wikipedia information found for {outlet_name}."
    return f"Wikipedia — {result['title']}:\n{result['summary']}\nURL: {result['url']}"


# ── System prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """You are an autonomous media intelligence researcher. Your task is to conduct thorough research on a named media outlet and produce comprehensive raw findings.

For each outlet you research, you must gather:
1. EDITORIAL IDENTITY: What does the outlet cover? What is its editorial focus and values?
2. RECENT COVERAGE: What topics has it covered recently (last 30 days)?
3. HISTORICAL CONTEXT: How has its coverage changed over the past 6 months?
4. COMPETITIVE POSITION: How is it perceived by other outlets and the media industry?
5. FACTUAL PROFILE: Ownership, funding model, founding, audience size.

Research strategy:
- Start with Wikipedia for factual grounding
- Use web_search for editorial positioning and recent news
- Use get_news_articles for current topic focus
- Use get_historical_articles for temporal drift data
- Use get_rss_feed for the very latest articles
- Use get_guardian_coverage to see how quality journalism covers this outlet

Be thorough but efficient. After gathering sufficient data, summarise your findings in a structured format covering all 5 areas above."""


# ── Agent factory ─────────────────────────────────────────
def create_research_agent():
    """
    Create and return a ReAct agent with all research tools.
    The agent is stateless — create a new one per research run.
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0.3,
    )

    tools = [
        web_search,
        get_news_articles,
        get_guardian_coverage,
        get_historical_articles,
        get_rss_feed,
        get_wikipedia_info,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent


def research_outlet(outlet_name: str) -> str:
    """
    Run the ReAct agent to research a single media outlet.

    Args:
        outlet_name: Name of the outlet to research (e.g. "BBC News")

    Returns:
        String containing the agent's comprehensive research findings.
    """
    print(f"\n[react_agent] Starting research on: {outlet_name}")
    print(f"[react_agent] Model: {LLM_MODEL}, Max iterations: {MAX_ITERATIONS}")

    agent = create_research_agent()

    initial_message = {
        "messages": [{
            "role":    "user",
            "content": f"Research the media outlet '{outlet_name}' thoroughly using all available tools. Gather information on its editorial identity, recent coverage topics, historical coverage trends, competitive position, and factual profile. Be comprehensive."
        }]
    }

    config = {"recursion_limit": MAX_ITERATIONS}

    try:
        result    = agent.invoke(initial_message, config=config)
        messages  = result.get("messages", [])
        final_msg = messages[-1] if messages else None

        if final_msg and hasattr(final_msg, "content"):
            findings = final_msg.content
            print(f"[react_agent] Research complete for: {outlet_name}")
            print(f"[react_agent] Findings length: {len(findings)} chars")
            return findings
        else:
            return f"Research completed but no findings extracted for {outlet_name}."

    except Exception as e:
        print(f"[react_agent] Error researching {outlet_name}: {e}")
        return f"Research failed for {outlet_name}: {str(e)}"


# ── Standalone test ───────────────────────────────────────
if __name__ == "__main__":
    print("Testing ReAct agent...\n")
    print("Researching: The Guardian")
    print("=" * 60)

    findings = research_outlet("The Guardian")

    print("\n" + "=" * 60)
    print("RESEARCH FINDINGS:")
    print("=" * 60)
    print(findings[:2000])
    print(f"\n[Total findings: {len(findings)} chars]")
