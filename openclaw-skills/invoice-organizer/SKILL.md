---
name: invoice-organizer
description: Use when the user asks to extract invoice information, OCR invoice PDFs/images, classify invoices by type, rename invoice files by amount/type/date/seller, deduplicate by invoice number, summarize invoice totals, or generate Word reports from invoice batches. Also use for Chinese invoice reimbursement folder cleanup and receipt/invoice organization workflows.
---

# Invoice Organizer

This skill operates the repository's existing invoice processing pipeline instead of rewriting it.

## Use when
- The user wants to batch-process invoice PDFs/images.
- The user wants OCR extraction of invoice fields.
- The user wants invoices renamed and grouped by category.
- The user wants duplicate invoice detection by invoice number.
- The user wants summary stats or a Word reimbursement report.

## Repository entrypoints
- Main app: `app.py`
- Extraction core: `src/invoice_extractor.py`
- Organizer logic: `src/invoice_organizer.py`
- Word report generator: `tools/generate_word.py`

## Default workflow
1. Confirm or locate the input folder containing invoices.
2. Confirm an output folder if the user cares about where results land.
3. Check whether `.env` is configured for the LLM endpoint.
4. Run the existing app/script instead of reimplementing invoice OCR from scratch.
5. Report:
   - processed count
   - success/failed/duplicate count
   - output path
   - generated summary/report files

## Environment expectations
The current project expects these env vars in `.env`:
- `API_BASE_URL`
- `API_KEY`
- `MODEL_NAME`

Optional runtime knobs may also be read by the extraction module.

## Run patterns
### Batch process a folder
Use:
`python app.py <input_folder> <output_folder>`

### Generate or inspect report outputs
After processing, inspect generated JSON / Word outputs if present.

## Implementation note
Prefer the repository's built-in code path over ad hoc scripts. Only patch code when the current implementation clearly fails the user's request.

## Files to read as needed
- For usage details: `references/usage.md`
- For architecture and outputs: `references/project-map.md`
