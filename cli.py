"""Command-line interface."""
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from engineering_agent.analyzer import analyze_snapshot


def load_snapshot(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Snapshot root must be a JSON object.")
    if not isinstance(data.get("issues", []), list) or not isinstance(data.get("pull_requests", []), list):
        raise ValueError("'issues' and 'pull_requests' must be lists.")
    return data


def print_summary(report: dict) -> None:
    print(f"\n{report['project_name']} — Engineering Risk Summary")
    print("=" * (len(report['project_name']) + 32))
    print(report["summary"])
    counts = report["counts"]
    print(f"\nIssues analyzed: {counts['issues_analyzed']}\nPull requests analyzed: {counts['pull_requests_analyzed']}\nItems with findings: {counts['items_with_findings']}\nTotal findings: {counts['findings_total']}")
    print("\nTop risks:")
    if not report["top_risks"]:
        print("  No findings from configured rules.")
    for risk in report["top_risks"]:
        print(f"  [{risk['level'].upper():6}] {risk['entity_type']} {risk['entity_id']}: {risk['title']} (score {risk['score']})")
        for item in risk["findings"][:3]:
            print(f"      - {item['title']} [{item['rule_id']}]")
            if item["recommendations"]:
                print(f"        Next: {item['recommendations'][0]}")
    for item in report["release"]["findings"]:
        print(f"\nRELEASE [{item['severity'].upper()}]: {item['title']}")
        for line in item["evidence"]:
            print(f"  Evidence: {line}")
        for line in item["recommendations"]:
            print(f"  Next: {line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engineering-agent", description="Analyze a local engineering snapshot for explainable delivery risks.")
    subs = parser.add_subparsers(dest="command", required=True)
    command = subs.add_parser("analyze", help="Analyze a JSON project snapshot")
    command.add_argument("input", type=Path)
    command.add_argument("--output", type=Path, help="Save full JSON report")
    args = parser.parse_args(argv)
    try:
        report = analyze_snapshot(load_snapshot(args.input))
        print_summary(report)
        serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(serialized, encoding="utf-8")
            print(f"\nFull JSON report written to: {args.output}")
        else:
            print("\nUse --output report.json to save the full JSON report.")
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
