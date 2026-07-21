"""
CLI Entry Point — Media Intelligence Agent
Standalone script called by N8N Execute Command node.

Usage:
    python3 src/run_agent.py --outlet "Reuters"
    python3 src/run_agent.py --outlet "Der Spiegel" --output json
    python3 src/run_agent.py --outlet "BBC News" --output markdown

Arguments:
    --outlet    Required. Name of the media outlet to research.
    --output    Optional. Output format: 'json' (default) or 'markdown'.

Output:
    JSON mode:     Prints JSON to stdout with keys: outlet, report, saved_to, char_count
    Markdown mode: Prints the raw Markdown report to stdout

Exit codes:
    0 = success
    1 = failure (error message printed to stderr)

N8N Execute Command node configuration:
    Command: python3 src/run_agent.py --outlet={{$json.outlet}}
    Working directory: /path/to/Media_Intelligence_Layer
"""
import os
import sys
import json
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.graph import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Media Intelligence Agent — CLI Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 src/run_agent.py --outlet "Reuters"
  python3 src/run_agent.py --outlet "Der Spiegel" --output markdown
  python3 src/run_agent.py --outlet "BBC News" --output json
        """
    )

    parser.add_argument(
        "--outlet",
        type=str,
        required=True,
        help="Name of the media outlet to research (e.g. 'Reuters', 'Der Spiegel')"
    )

    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "markdown"],
        default="json",
        help="Output format: 'json' (default) or 'markdown'"
    )

    args = parser.parse_args()
    outlet = args.outlet.strip()

    if not outlet:
        print("Error: --outlet cannot be empty", file=sys.stderr)
        sys.exit(1)

    print(f"[run_agent] Starting pipeline for: {outlet}", file=sys.stderr)

    try:
        report = run_pipeline(outlet_name=outlet, save_report=True)

        if not report:
            print("Error: Pipeline produced no report", file=sys.stderr)
            sys.exit(1)

        filename = outlet.lower().replace(" ", "_").replace("/", "_")
        saved_to = f"reports/{filename}.md"

        if args.output == "markdown":
            print(report)
        else:
            # JSON output — what N8N reads
            output = {
                "outlet":     outlet,
                "report":     report,
                "saved_to":   saved_to,
                "char_count": len(report),
                "status":     "success",
            }
            print(json.dumps(output, ensure_ascii=False))

        print(f"[run_agent] Complete. Report: {len(report)} chars", file=sys.stderr)
        sys.exit(0)

    except Exception as e:
        error_output = {
            "outlet": outlet,
            "status": "error",
            "error":  str(e),
        }
        print(json.dumps(error_output), file=sys.stdout)
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
