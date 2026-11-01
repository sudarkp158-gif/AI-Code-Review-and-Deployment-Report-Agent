"""Deterministic, explainable risk rules for issues, PRs, and releases."""
from datetime import date, datetime
from typing import Any


def parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def level_for(score: int) -> str:
    return "high" if score >= 70 else "medium" if score >= 35 else "low"


def finding(rule_id: str, entity_type: str, entity: dict, title: str,
            severity: str, points: int, evidence: list[str], recommendations: list[str]) -> dict:
    return {"rule_id": rule_id, "entity_type": entity_type,
            "entity_id": str(entity.get("id", "unknown")), "title": title,
            "severity": severity, "points": points, "evidence": evidence,
            "recommendations": recommendations}


def analyze_issue(issue: dict, today: date) -> dict:
    state = str(issue.get("state", "open")).lower()
    title = str(issue.get("title", "Untitled issue"))
    entity_id = str(issue.get("id", "unknown"))
    if state not in {"open", "opened", "in_progress", "blocked"}:
        return {"entity_type": "issue", "entity_id": entity_id, "title": title,
                "score": 0, "level": "low", "findings": []}
    findings = []
    severity = str(issue.get("severity", "medium")).lower()
    if severity in {"critical", "blocker"}:
        findings.append(finding("ISSUE-001", "issue", issue, "Open critical-severity issue", "high", 45,
            [f"Severity is '{severity}'", f"State is '{state}'"],
            ["Confirm an accountable owner and mitigation plan.", "Assess release and downstream dependency impact."]))
    elif severity == "high":
        findings.append(finding("ISSUE-002", "issue", issue, "Open high-severity issue", "high", 25,
            [f"Severity is '{severity}'", f"State is '{state}'"],
            ["Confirm priority, owner, and target resolution date."]))
    due = parse_date(issue.get("due_date"))
    if due and due < today:
        findings.append(finding("ISSUE-003", "issue", issue, "Issue is past its due date", "high", 30,
            [f"Due date was {due.isoformat()}", f"Overdue by {(today-due).days} day(s)"],
            ["Reconfirm the delivery date and document the recovery plan."]))
    elif due and 0 <= (due-today).days <= 3:
        findings.append(finding("ISSUE-004", "issue", issue, "Issue due within three days", "medium", 15,
            [f"Due date is {due.isoformat()}", f"Days remaining: {(due-today).days}"],
            ["Check remaining work and escalate dependencies that threaten the due date."]))
    opened = parse_date(issue.get("opened_at"))
    if opened and (today-opened).days >= 14:
        findings.append(finding("ISSUE-005", "issue", issue, "Issue has been open for at least 14 days", "medium", 15,
            [f"Opened {(today-opened).days} day(s) ago"],
            ["Check for stale status, unresolved blockers, or missing next actions."]))
    labels = {str(x).lower() for x in issue.get("labels", [])}
    if state == "blocked" or "blocked" in labels:
        findings.append(finding("ISSUE-006", "issue", issue, "Issue is marked blocked", "high", 20,
            ["State or label indicates blocked work"],
            ["Record the blocking dependency, owner, and next checkpoint."]))
    if not issue.get("assignee"):
        findings.append(finding("ISSUE-007", "issue", issue, "Issue has no assigned owner", "medium", 10,
            ["No assignee supplied in the snapshot"],
            ["Assign an accountable owner or confirm why ownership is intentionally unassigned."]))
    score = min(100, sum(x["points"] for x in findings))
    return {"entity_type": "issue", "entity_id": entity_id, "title": title,
            "score": score, "level": level_for(score), "findings": findings}


def analyze_pull_request(pr: dict, today: date) -> dict:
    state = str(pr.get("state", "open")).lower()
    title = str(pr.get("title", "Untitled pull request"))
    entity_id = str(pr.get("id", "unknown"))
    if state not in {"open", "opened"}:
        return {"entity_type": "pull_request", "entity_id": entity_id, "title": title,
                "score": 0, "level": "low", "findings": []}
    findings = []
    ci = str(pr.get("ci_status", "unknown")).lower()
    if ci in {"failed", "failure", "error", "red"}:
        findings.append(finding("PR-001", "pull_request", pr, "Pull request has failing CI", "high", 35,
            [f"CI status is '{ci}'"],
            ["Inspect failed checks and determine whether the cause is flaky, environmental, or change-related."]))
    elif ci in {"pending", "in_progress", "unknown", "none"}:
        findings.append(finding("PR-002", "pull_request", pr, "CI is not confirmed green", "medium", 15,
            [f"CI status is '{ci}'"], ["Wait for required checks or investigate missing check status."]))
    if pr.get("draft", False):
        findings.append(finding("PR-003", "pull_request", pr, "Pull request is still a draft", "medium", 15,
            ["Draft flag is true"], ["Confirm whether this work in progress affects the release critical path."]))
    approvals = int(pr.get("approvals", 0) or 0)
    if approvals < 1:
        findings.append(finding("PR-004", "pull_request", pr, "No approvals recorded", "medium", 20,
            [f"Approval count is {approvals}"], ["Request required reviewers; do not bypass branch protections."]))
    changed_files = int(pr.get("changed_files", 0) or 0)
    if changed_files >= 30:
        findings.append(finding("PR-005", "pull_request", pr, "Large change surface", "medium", 15,
            [f"{changed_files} changed files"], ["Consider splitting the change and ensure affected components are tested."]))
    opened = parse_date(pr.get("opened_at"))
    if opened and (today-opened).days >= 7:
        findings.append(finding("PR-006", "pull_request", pr, "Pull request has been open for at least seven days", "medium", 10,
            [f"Opened {(today-opened).days} day(s) ago"], ["Check for missing reviews, unresolved conversations, or blocked dependencies."]))
    labels = {str(x).lower() for x in pr.get("labels", [])}
    critical_labels = labels.intersection({"release-blocker", "critical"})
    if critical_labels:
        findings.append(finding("PR-007", "pull_request", pr, "PR carries a release-critical label", "high", 20,
            [f"Labels include: {', '.join(sorted(critical_labels))}"],
            ["Confirm release ownership, test coverage, and rollback or mitigation plan."]))
    score = min(100, sum(x["points"] for x in findings))
    return {"entity_type": "pull_request", "entity_id": entity_id, "title": title,
            "score": score, "level": level_for(score), "findings": findings}


def analyze_snapshot(snapshot: dict, today: date | None = None) -> dict:
    today = today or date.today()
    issues = [analyze_issue(x, today) for x in snapshot.get("issues", [])]
    prs = [analyze_pull_request(x, today) for x in snapshot.get("pull_requests", [])]
    all_items = issues + prs
    with_findings = [x for x in all_items if x["findings"]]
    high = [x for x in with_findings if x["level"] == "high"]
    release = snapshot.get("release") or {}
    release_findings = []
    release_date = parse_date(release.get("date"))
    if release_date:
        days = (release_date-today).days
        if days < 0:
            release_findings.append({"rule_id": "REL-001", "severity": "high",
                "title": "Release date is in the past", "evidence": [f"Release date was {release_date.isoformat()}"],
                "recommendations": ["Confirm whether the release date should be updated and document the current plan."]})
        elif days <= 7 and high:
            release_findings.append({"rule_id": "REL-002", "severity": "high",
                "title": "Release is within seven days with high-risk work open",
                "evidence": [f"Days to release: {days}", f"High-risk issues/PRs: {len(high)}"],
                "recommendations": ["Review the critical path, mitigation owners, and go/no-go criteria."]})
    total_findings = sum(len(x["findings"]) for x in with_findings)
    if high:
        summary = f"{snapshot.get('project_name', 'Unnamed project')}: {len(high)} high-risk item(s) need attention. {len(with_findings)} item(s) have risk signals."
    elif with_findings:
        summary = f"{snapshot.get('project_name', 'Unnamed project')}: no high-risk items detected by these rules, but {len(with_findings)} item(s) have medium/low risk signals."
    else:
        summary = f"{snapshot.get('project_name', 'Unnamed project')}: no risk signals detected by the configured MVP rules."
    return {
        "project_name": snapshot.get("project_name", "Unnamed project"),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "analysis_date": today.isoformat(), "summary": summary,
        "counts": {"issues_analyzed": len(issues), "pull_requests_analyzed": len(prs),
                   "items_with_findings": len(with_findings), "findings_total": total_findings,
                   "entity_risk_levels": {level: sum(1 for x in with_findings if x["level"] == level) for level in ("high", "medium", "low")}},
        "release": {"name": release.get("name"), "date": release.get("date"), "findings": release_findings},
        "top_risks": [x for x in sorted(with_findings, key=lambda x: (x["score"], x["entity_id"]), reverse=True)[:5]],
        "items": sorted(all_items, key=lambda x: x["score"], reverse=True),
        "methodology": {"type": "deterministic_heuristics",
            "risk_score_note": "Scores are heuristic prioritization points, not probabilities of failure.",
            "limitations": ["Input may be stale or incomplete.", "Rules are not calibrated against historical incidents.", "No findings do not guarantee a release is safe."]}
    }
