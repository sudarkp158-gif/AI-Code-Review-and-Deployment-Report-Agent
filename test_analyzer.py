import json
import unittest
from datetime import date
from pathlib import Path
from engineering_agent.analyzer import analyze_issue, analyze_pull_request, analyze_snapshot
from engineering_agent.cli import load_snapshot

TODAY = date(2026, 10, 24)

class AnalyzerTests(unittest.TestCase):
    def test_critical_overdue_issue_scores_high(self):
        issue = {"id": "ENG-1", "title": "Critical issue", "state": "open", "severity": "critical", "opened_at": "2026-10-01", "due_date": "2026-10-20", "assignee": "team-a"}
        result = analyze_issue(issue, TODAY)
        self.assertEqual(result["level"], "high")
        self.assertGreaterEqual(result["score"], 70)
        self.assertIn("ISSUE-001", {f["rule_id"] for f in result["findings"]})
        self.assertIn("ISSUE-003", {f["rule_id"] for f in result["findings"]})

    def test_closed_issue_is_not_flagged(self):
        result = analyze_issue({"id": "ENG-2", "title": "Done", "state": "closed"}, TODAY)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["findings"], [])

    def test_failing_unapproved_pr_has_findings(self):
        pr = {"id": "PR-1", "title": "Change", "state": "open", "ci_status": "failed", "approvals": 0, "changed_files": 4, "draft": False, "opened_at": "2026-10-22", "labels": []}
        result = analyze_pull_request(pr, TODAY)
        self.assertIn("PR-001", {f["rule_id"] for f in result["findings"]})
        self.assertIn("PR-004", {f["rule_id"] for f in result["findings"]})
        self.assertEqual(result["level"], "medium")

    def test_snapshot_report_is_json_serializable(self):
        report = analyze_snapshot({"project_name": "Test", "issues": [{"id": "I-1", "title": "No owner", "state": "open"}], "pull_requests": []}, TODAY)
        self.assertEqual(report["analysis_date"], "2026-10-24")
        self.assertEqual(report["counts"]["issues_analyzed"], 1)
        json.dumps(report)

    def test_example_snapshot_loads(self):
        path = Path(__file__).parents[1] / "examples" / "project_snapshot.json"
        snapshot = load_snapshot(path)
        self.assertEqual(snapshot["project_name"], "Atlas API v2 Release")
        self.assertEqual(len(snapshot["pull_requests"]), 4)

if __name__ == "__main__":
    unittest.main()
