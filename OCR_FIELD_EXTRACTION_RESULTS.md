# OCR-to-field extraction fix — 28 October 2026

## Changes

Inspected Git status (clean on entry), shared parser rules, PDF/OCR analysis adapter, existing OCR integration tests and parser tests. No OCR engine, UI, API contract, persistence, dependency or lockfile changes.

Changed files:

- backend/app/invoice_rules.py — explicit labels can appear inside OCR lines and multiple fields share a line; boundaries come from recognized labels. Original full lines remain evidence. Parenthesized tax percentages are supported without treating a percentage alone as an amount. The unlabeled INVOICE-heading fallback no longer competes with an explicit Invoice No. label. Header supplier association permits one numbered address line before GSTIN, stops before the recognized combined BILL TO TAX INVOICE boundary, and retains requires-review methods.
- backend/tests/fixtures/acme-browser-ocr.txt — exact supplied fictional printed-invoice transcript, including both unreadable placeholders and disclaimer.
- backend/tests/test_browser_ocr_fields.py — four regression tests: exact requested fields/arithmetic; OCR source/evidence/review/confidence preservation; multiple labeled fields/conflicts on one line; conservative buyer boundaries and unreadable dates.
- OCR_FIELD_EXTRACTION_RESULTS.md — this report.

## Verified transcript output

| Field | Value |
|---|---|
| Supplier | ACME OFFICE SUPPLIES |
| Invoice number | TEST-INV-1042 |
| Invoice date | 2026-10-28 |
| Subtotal | 3800.00 |
| CGST | 342.00 |
| SGST | 342.00 |
| Grand total | 4484.00 |

Grand-total arithmetic passes: 3800.00 + 342.00 + 342.00 = 4484.00. No GST-total field is fabricated from the components. Buyer and unsupported loose line-item rows remain unknown/unparsed. The two unreadable lines are retained. Header supplier identification remains a positional hypothesis requiring review, not a verified identity.

## Actual commands and results

From C:\Doculens\backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_browser_ocr_fields.py tests/test_invoice.py tests/test_invoice_layout.py tests/test_invoice_formats.py tests/test_ocr.py --basetemp=.test-tmp/ocr-fields-focused3
# 68 passed, one upstream Starlette/AnyIO deprecation warning; exit 0
.\.venv\Scripts\python.exe -m compileall -q app
# exit 0
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp/ocr-fields-full -o faulthandler_timeout=60
# 103 passed, one upstream Starlette/AnyIO deprecation warning, 11.01 seconds; exit 0
```

From C:\Doculens\frontend:

```powershell
npm test
# 19 passed, 0 failed; exit 0
npm run typecheck
# exit 0
npm run lint
# exit 0
```

From C:\Doculens: `git diff --check` passed. An initial test command from the repository root failed collection because `app` was not importable; rerunning from the documented backend directory resolved that command error. The initial expanded regression found a competing invoice-heading candidate; that defect was fixed before the passing focused/full runs.

Production build was not rerun: this fix changes backend parser rules/tests only and does not affect frontend source or contracts. The prior frontend report's Windows EPERM production-build limitation is unchanged and not claimed resolved.

## Limits and saved records

This verifies field extraction from the supplied OCR transcript, not new native recognition of its source image. Original native OCR confidence values were not provided; the provenance test uses explicitly controlled metadata and verifies that it is retained unchanged. No OCR confidence or unreadable text is invented. No new handwriting accuracy claim is made. Existing native OCR tests are part of the completed backend suite, but do not establish general OCR accuracy or accuracy for this source image.

Previously persisted analyses are not silently rewritten. Use the existing explicit reprocessing workflow with the original file to update an old analysis while preserving archival/review rules; a repeated ordinary upload remains idempotent. No saved records were modified during this task.
