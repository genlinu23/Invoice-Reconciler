# Usage

## Typical inputs
- Folder of invoice PDFs/images
- Mixed Chinese invoice screenshots and PDFs
- Reimbursement material folder needing cleanup and deduplication

## Typical command
```bash
python app.py "<input_folder>" "<output_folder>"
```

If output folder is omitted, the app creates `output/` under the input folder.

## Expected outputs
- Renamed files, grouped by invoice type
- `statistics.json` or equivalent processing summary when produced
- Optional Word report depending on workflow/tool usage

## Supported file types
- `.jpg`
- `.jpeg`
- `.png`
- `.pdf`

## Core extracted fields
Depending on document quality and OCR/LLM success:
- amount
- type/category
- date
- seller
- invoice_number

## Operational guidance
- Prefer batch processing over one-file loops when the user gives a folder.
- Preserve originals; the current app copies into output folders rather than mutating source files.
- If OCR or PDF conversion fails, inspect dependencies before rewriting logic.
