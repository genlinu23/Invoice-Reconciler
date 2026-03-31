# Project Map

## Main files
- `app.py`: primary CLI / folder-processing entrypoint
- `src/invoice_extractor.py`: OCR + LLM extraction logic
- `src/invoice_organizer.py`: legacy/alternate organization flow
- `tools/generate_word.py`: Word report generation helper

## Current behavior
- scans invoice folders recursively
- skips output folders during traversal
- extracts invoice data
- deduplicates by normalized invoice number when available
- copies files into categorized output directories
- tracks summary stats

## Notes for agents
- This repository already contains the business logic; use it before adding new scripts.
- Keep SKILL.md lean; use this file for orientation.
- If adding automation wrappers later, place them under `openclaw-skills/invoice-organizer/scripts/`.
