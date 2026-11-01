# AI-Code-Review-and-Deployment-Report-Agent
A practical MVP for engineering teams and Technical Program Managers. It analyzes a structured snapshot of GitHub issues, pull requests, CI status, and release milestones to produce an explainable engineering-risk report.
Current scope: deterministic, rule-based analysis over local JSON data. This is the reliable baseline before adding an LLM, GitHub API integration, or autonomous actions. It does not connect to GitHub or change repositories.

What it does
- Flags stale or overdue issues.
- Identifies risky pull requests (draft, failing CI, missing approvals, large change surface).
- Highlights open critical/high-severity work and release-date pressure.
- Produces risk scores, evidence, recommended actions, and an executive summary.
- Emits a JSON report that can be piped into other tools.
