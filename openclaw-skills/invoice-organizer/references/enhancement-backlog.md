# Enhancement Backlog

## Scope guard
This skill is invoice-only.
Do not expand it to receipt matching or water-slip reconciliation unless the project itself adds that capability again and the user explicitly asks for it.

## High-value next improvements
1. Better command wrappers
- Add a wrapper for Word report generation.
- Add a wrapper for cleanup/reset flows.
- Add one-shot scripts for common invoice folder conventions.

2. Config hardening
- Move API/endpoint assumptions into a documented config contract.
- Add startup validation for missing env vars and dependencies.

3. Test fixtures
- Add a tiny anonymized invoice-only sample set.
- Add smoke tests for batch processing and output structure.

4. OpenClaw integration
- Keep this skill mirrored into the active workspace `skills/` folder so the current agent can load it automatically.
