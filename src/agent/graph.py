"""
LangGraph Graph — Media Intelligence Agent
Assembles all nodes into a compiled, executable graph.

What this file does:
    1. Creates a StateGraph using AgentState as the state schema
    2. Adds all nodes (functions from nodes.py)
    3. Connects nodes with edges (linear flow + conditional error routing)
    4. Compiles the graph into an executable object
    5. Provides helper functions to run the graph and export diagrams

The graph structure:
    START
      → identify_competitors_node
      → research_node
      → retrieve_node
      → drift_analysis_node
      → consensus_scoring_node
      → report_node
      → END

    Any node that sets state["error"] routes to error_node,
    which clears the error and routes back to the failed node
    (up to MAX_RETRIES times, then continues to the next node).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END

from src.agent.state import AgentState, initial_state, state_summary
from src.agent.nodes import (
    identify_competitors_node,
    research_node,
    retrieve_node,
    drift_analysis_node,
    consensus_scoring_node,
    report_node,
    error_node,
)

load_dotenv()

MAX_RETRIES = 2


# ── Conditional routing function ──────────────────────────

def route_after_node(state: AgentState) -> str:
    """
    After each node, check if an error occurred.
    If yes and retries remain: go to error_node.
    If yes and retries exhausted: continue to next node anyway.
    If no error: continue normally.

    This function is used as the conditional edge after each node.
    LangGraph calls it with the current state and uses the returned
    string to decide which node to go to next.
    """
    if state.get("error") and state.get("retry_count", 0) < MAX_RETRIES:
        return "error_node"
    return "continue"


# ── Graph builder ─────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Build and compile the Media Intelligence Agent graph.

    Returns:
        A compiled LangGraph graph ready to invoke.
    """
    # Create the graph with our state schema
    graph = StateGraph(AgentState)

    # ── Add all nodes ─────────────────────────────────────
    graph.add_node("identify_competitors", identify_competitors_node)
    graph.add_node("research",             research_node)
    graph.add_node("retrieve",             retrieve_node)
    graph.add_node("drift_analysis",       drift_analysis_node)
    graph.add_node("consensus_scoring",    consensus_scoring_node)
    graph.add_node("report",               report_node)
    graph.add_node("error_node",           error_node)

    # ── Add edges (the flow between nodes) ────────────────

    # Entry point: START → first node
    graph.add_edge(START, "identify_competitors")

    # After identify_competitors: check for error or continue
    graph.add_conditional_edges(
        "identify_competitors",
        route_after_node,
        {
            "error_node": "error_node",
            "continue":   "research",
        }
    )

    # After research: check for error or continue
    graph.add_conditional_edges(
        "research",
        route_after_node,
        {
            "error_node": "error_node",
            "continue":   "retrieve",
        }
    )

    # After retrieve: continue to drift analysis
    graph.add_conditional_edges(
        "retrieve",
        route_after_node,
        {
            "error_node": "error_node",
            "continue":   "drift_analysis",
        }
    )

    # After drift analysis: continue to scoring
    graph.add_conditional_edges(
        "drift_analysis",
        route_after_node,
        {
            "error_node": "error_node",
            "continue":   "consensus_scoring",
        }
    )

    # After consensus scoring: continue to report
    graph.add_conditional_edges(
        "consensus_scoring",
        route_after_node,
        {
            "error_node": "error_node",
            "continue":   "report",
        }
    )

    # After report: END
    graph.add_edge("report", END)

    # Error node always routes back to research
    # (simplified recovery: retry from research stage)
    graph.add_edge("error_node", "research")

    # ── Compile ───────────────────────────────────────────
    compiled = graph.compile()

    print("[graph] Graph compiled successfully")
    return compiled


# ── Run function ──────────────────────────────────────────

def run_pipeline(outlet_name: str, save_report: bool = True) -> str:
    """
    Run the full Media Intelligence pipeline for a named outlet.

    Args:
        outlet_name:  The target outlet to research (e.g. "Der Spiegel")
        save_report:  If True, save the report to /reports/ folder

    Returns:
        The final Markdown report as a string.
    """
    print(f"\n{'#'*60}")
    print(f"# MEDIA INTELLIGENCE AGENT")
    print(f"# Target: {outlet_name}")
    print(f"{'#'*60}")

    # Build the graph
    graph = build_graph()

    # Create initial state
    state = initial_state(outlet_name)

    # Run the graph
    config = {"recursion_limit": 50}

    try:
        result = graph.invoke(state, config=config)

        report = result.get("report", "")

        if not report:
            print("[run] WARNING: No report generated")
            return "Report generation failed."

        print(f"\n{'#'*60}")
        print(f"# PIPELINE COMPLETE")
        print(f"# Report: {len(report)} chars")
        print(f"{'#'*60}")

        # Save report to file
        if save_report and report:
            os.makedirs("reports", exist_ok=True)
            filename = outlet_name.lower().replace(" ", "_").replace("/", "_")
            filepath = f"reports/{filename}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"[run] Report saved: {filepath}")

        return report

    except Exception as e:
        print(f"[run] Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return f"Pipeline failed: {str(e)}"


# ── Diagram export ────────────────────────────────────────

def export_diagram(output_path: str = "reports/pipeline_diagram.png"):
    """
    Export the graph as a PNG diagram.
    Requires: pip install pygraphviz or pip install playwright

    Falls back to Mermaid text if PNG export fails.
    """
    graph = build_graph()

    # Try PNG first
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(png_bytes)
        print(f"[diagram] PNG saved: {output_path}")
        return output_path
    except Exception as e:
        print(f"[diagram] PNG export failed ({e}), falling back to Mermaid text")

    # Fallback: Mermaid text
    try:
        mermaid = graph.get_graph().draw_mermaid()
        mermaid_path = output_path.replace(".png", ".md")
        os.makedirs(os.path.dirname(mermaid_path), exist_ok=True)
        with open(mermaid_path, "w") as f:
            f.write("```mermaid\n" + mermaid + "\n```")
        print(f"[diagram] Mermaid saved: {mermaid_path}")
        return mermaid_path
    except Exception as e:
        print(f"[diagram] Mermaid export also failed: {e}")
        return None


# ── Standalone test ───────────────────────────────────────

if __name__ == "__main__":
    import sys

    # Allow outlet name as command line argument
    outlet = sys.argv[1] if len(sys.argv) > 1 else "The Guardian"

    print(f"\nRunning full pipeline for: {outlet}")
    print("This will take several minutes — the agent calls multiple APIs.\n")

    # Export diagram first
    print("Exporting pipeline diagram...")
    export_diagram()

    # Run pipeline
    report = run_pipeline(outlet)

    # Print first 3000 chars of report
    print("\n" + "="*60)
    print("REPORT PREVIEW (first 3000 chars):")
    print("="*60)
    print(report[:3000])
    print(f"\n[Full report: {len(report)} chars]")
