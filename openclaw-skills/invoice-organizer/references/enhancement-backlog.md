# Enhancement Backlog

## High-value next improvements

1. Receipt / water-slip reconciliation
- Define how water slips are matched to invoices.
- Produce a structured reconciliation report.
- Flag unmatched invoices and unmatched receipts.

2. Better command wrappers
- Add a wrapper for Word report generation.
- Add a wrapper for cleanup/reset flows.
- Add one-shot scripts for common folder conventions.

3. Config hardening
- Move API/endpoint assumptions into a documented config contract.
- Add startup validation for missing env vars and dependencies.

4. Test fixtures
- Add a tiny anonymized sample set.
- Add smoke tests for batch processing and output structure.

5. OpenClaw integration
- Mirror this skill into the active workspace `skills/` folder so the current agent can load it automatically.
- Optionally add `skills.entries.invoice-organizer` config in `openclaw.json` when runtime gating/config is desired.
