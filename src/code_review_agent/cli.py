"""CLI for the code review agent."""
import argparse
import json
import sys
from pathlib import Path

from code_review_agent import CodeReviewAgent, create_agent


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="LLM-powered code review agent using Strands and Bedrock"
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to repository or file to analyze",
    )
    parser.add_argument(
        "--commit",
        type=str,
        help="Git commit hash to analyze",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        help="Bedrock model ID",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (JSON)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Initializing code review agent...")
        print(f"Model: {args.model}")
        print(f"Region: {args.region}")

    agent = create_agent(
        model_id=args.model,
        aws_region=args.region,
    )

    if args.verbose:
        print(f"Analyzing: {args.path}")

    if path.is_file():
        content = path.read_text(encoding="utf-8")
        findings = agent.analyze_file(str(path), content)
        result = {
            "file": str(path),
            "findings": [f.to_dict() for f in findings],
            "total_findings": len(findings),
        }
    else:
        result = agent.analyze_repository(str(path), args.commit)
        result = result.to_dict()

    output = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        if args.verbose:
            print(f"Results written to: {args.output}")
    else:
        print(output)

    if args.verbose:
        summary = result.get("analysis_summary", {})
        print(f"\nAnalysis Summary:")
        print(f"  Files analyzed: {summary.get('total_files_analyzed', 'N/A')}")
        print(f"  Total findings: {summary.get('total_findings', 'N/A')}")
        print(f"  Risk score: {summary.get('risk_score', 'N/A')}")


if __name__ == "__main__":
    main()
