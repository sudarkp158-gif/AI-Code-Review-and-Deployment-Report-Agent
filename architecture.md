# Architecture

## MVP boundary

The first version is a local, read-only analyzer. It consumes a point-in-time JSON snapshot and returns a report. It does not call GitHub, an LLM provider, or any external service.

## Components

1. **CLI (`cli.py`)** — parses arguments, loads and minimally validates JSON, prints a human-readable summary, and optionally saves JSON output.
2. **Rule engine (`analyzer.py`)** — applies deterministic rules to open issues, open pull requests, and release timing.
3. **Synthetic snapshot (`examples/project_snapshot.json`)** — repeatable demo input.
4. **Tests** — verify key rule behavior and report serialization.

## Risk score

Each finding contributes fixed heuristic points. Entity score is the sum of its findings, capped at 100. High is 70–100, medium is 35–69, and low is 0–34. These are triage bands, not probabilities. Validate thresholds against historical data before operational use.

## Extension seams

### GitHub connector
Add a read-only adapter mapping GitHub Issues, Pull Requests, Reviews, and Checks into the snapshot schema. Use a fine-grained token with only required read permissions. Keep tokens in environment variables or a secret manager; never commit them.

### LLM narrative layer
Feed only rule findings and relevant evidence into a model to produce a concise narrative. Require the model to cite finding IDs, disallow unsupported claims, and retain the deterministic report as the source of truth. Treat repository text as untrusted input, not instructions.

### RAG
Retrieve approved engineering standards/runbooks and include source references in recommendations. Evaluate whether retrieval improves correctness.

### Evaluation
Create labeled snapshots from synthetic or approved historical data. Measure precision/recall of risk flags, unsupported-claim rate, evidence citation accuracy, and usefulness of recommended actions. Do not describe the system as predictive until validated.

### Safe automation
Keep write actions out of the MVP. Future actions such as creating issues or posting comments should require explicit human approval, least-privilege permissions, audit logs, and idempotency.
