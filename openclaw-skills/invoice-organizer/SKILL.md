---
name: invoice-organizer
description: Use when the user asks to extract invoice information from invoice PDFs/images, OCR Chinese invoices, classify invoice files, rename invoices by amount/type/date/seller, detect duplicates by invoice number, summarize invoice totals, or generate invoice Word reports from batches. This skill is for invoice organization only; it does not cover receipt/water-slip reconciliation workflows.
metadata: {"openclaw":{"emoji":"🧾","os":["linux"],"requires":{"bins":["python3"],"config":["skills.entries.invoice-organizer.enabled"]}}}
---

# Invoice Organizer

Operate the existing invoice processing project instead of reimplementing OCR or renaming logic from scratch.

## Trigger when
- The user wants to batch-process invoice PDFs/images.
- The user wants OCR extraction of invoice fields.
- The user wants invoices renamed, categorized, deduplicated, or summarized.
- The user wants an invoice-only reimbursement folder cleaned up.
- The user wants a Word report generated from invoice batches.

## Do not use for
- receipt/water-slip reconciliation
- payment-slip matching
- mixed voucher matching workflows outside invoice organization

## Project entrypoints
- Main app: `{baseDir}/../../app.py`
- Extraction core: `{baseDir}/../../src/invoice_extractor.py`
- Organizer logic: `{baseDir}/../../src/invoice_organizer.py`
- Word generator: `{baseDir}/../../tools/generate_word.py`
- Wrapper script: `{baseDir}/scripts/run_invoice_tool.py`

## Default workflow
1. Identify the input folder and desired output folder.
2. Check whether runtime config/env for the LLM endpoint exists.
3. Prefer the repository's built-in app flow.
4. Preserve originals; write outputs to a separate folder.
5. Report processed count, duplicates, failures, totals, and output path.

## Environment
The underlying project expects these env vars when LLM extraction is enabled:
- `API_BASE_URL`
- `API_KEY`
- `MODEL_NAME`

If these are missing, inspect the project config before promising full extraction quality.

## Common tasks
### Batch organize invoice folder
Run the wrapper script with an input folder and optional output folder.

### Invoice summary / Word output
After processing, inspect generated JSON/Word outputs and summarize them for the user.

### Debugging extraction quality
If fields are wrong, inspect OCR output and prompts in the extraction module before changing business rules.

## What not to do
- Do not rewrite the whole pipeline unless the existing code clearly cannot satisfy the request.
- Do not mutate or rename originals in place unless the user explicitly asks.
- Do not add water-slip or receipt matching behavior into this skill.

## Read as needed
- Usage and outputs: `references/usage.md`
- Project map: `references/project-map.md`
