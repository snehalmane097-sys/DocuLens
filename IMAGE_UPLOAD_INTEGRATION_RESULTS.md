# Image upload integration acceptance — 28 October 2026

## Root cause established from the live application

The browser was returning persisted analysis revision 1 of `doculens_sample_printed_invoice.png` (document `real-5e829466c6e147d7a2e2c6ce26348983`). Its saved OCR transcript had the expected labels, but its field results were produced by the older parser. The ordinary upload endpoint computes an analysis then `DocumentStore.save` deliberately returns the existing analysis for the same content hash. A repeated upload therefore does not refresh an old analysis. This is intentional idempotency/review preservation, not a frontend field mapping error.

The current parser, run against the actual PNG through installed Tesseract, extracted all requested fields except buyer. OCR flattens the Bill To name and the adjacent Invoice No. column onto one line. The remaining buyer rule rejected that whole line as a name. The fix bounds a directly adjacent Bill To company name at an explicit invoice-number/date label, retains the original unsplit evidence, and marks the association as requiring review. No arbitrary nearby names or unreadable values are inferred.

The prior inline-label, header/address and parenthesized-percentage fixes remain in place. No OCR engine rewrite, UI redesign, field-name remapping, schema/storage changes or dependency/lockfile changes were needed.

## Traced path

`UploadPreview` -> `submitAnalysis` -> multipart `file` POST `/api/documents/analyze` -> `receive_pdf` signature/size/dimension checks -> threadpool `analyze_pdf` -> image `ocr_document`/Tesseract TSV/accepted-line text OR PDF text with scanned-page OCR -> shared `analysis_result` -> `parse_invoice`/`parse_fields` and `validate_invoice` -> `DocumentStore.save` -> `InvoiceAnalysis` response model -> `AnalysisResults` using `fields[key].value`.

Both images and PDFs already use the shared extraction/validation path. OCR text shown to the parser excludes rejected-confidence lines using unreadable placeholders; full recognized lines/confidence/locations remain in `ocr_pages`. The response schema retains the canonical field keys. Saved details use the same analysis fields plus explicit human overrides.

## Actual integrated verification

Located and visually inspected the actual 1600x2100 fictional PNG from Downloads; copied its unchanged bytes to the test fixtures. Native Tesseract was installed and executed, not mocked, for both the new native endpoint test and live browser verification.

1. Selected the original PNG in the real browser Analyze page and submitted it. Reproduced the old Unknown fields and zero passing arithmetic checks, returning the existing document ID.
2. Opened its saved record, expanded History & reprocessing, selected the original PNG and used Reprocess and reset review.
3. Verified revision 2, pending human review, with all eight requested fields populated.
4. Retrieved the record and history through the actual API. The previous unknown-field analysis is archived. Previous and current OCR page metadata are identical, including confidence and geometry.
5. Repeated an ordinary image upload in the browser. It returned the corrected saved result and the same document ID, retaining idempotency.

| Field | Verified native/browser/API value |
|---|---|
| supplier_name | ACME OFFICE SUPPLIES |
| buyer_name | Example Manufacturing Pvt Ltd |
| invoice_number | TEST-INV-1042 |
| invoice_date | 2026-10-28 |
| subtotal | 3800.00 |
| cgst | 342.00 |
| sgst | 342.00 |
| grand_total | 4484.00 |

The source does not explicitly state GST total. `gst_total.value` remains null. The validation check calculates CGST + SGST = 684.00, but comparison to an unstated GST total remains unknown. Grand total passes: 3800.00 + 342.00 + 342.00 = 4484.00. Line-item extraction remains empty because the OCR table header was excluded/unsupported. Result: one passing check, two legitimately unknown checks, zero mismatches. Review remains required; no invoice was approved.

## Tests and actual results

From `C:\Doculens\backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_image_upload_integration.py tests/test_browser_ocr_fields.py --basetemp=.test-tmp/image-upload-integration2
# 9 passed, exit 0
.\.venv\Scripts\python.exe -m pytest -q tests/test_ocr.py tests/test_browser_ocr_fields.py tests/test_image_upload_integration.py tests/test_invoice.py tests/test_invoice_layout.py tests/test_invoice_formats.py --basetemp=.test-tmp/integrated-focused
# 73 passed, exit 0
.\.venv\Scripts\python.exe -m compileall -q app
# exit 0
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp/integrated-full -o faulthandler_timeout=60
# 108 passed, zero skipped, 14.49 seconds, exit 0
```

Each backend run reported one upstream Starlette/AnyIO deprecation warning. The new tests cover multipart image uploads, controlled scanned-PDF OCR, digital-PDF extraction, response-model mapping, saved retrieval/effective fields, old-analysis idempotency, explicit reprocessing/archive/version conflict and installed-Tesseract recognition of the actual image through the browser's backend endpoint. Controlled OCR tests inject synthetic TSV/confidence at the native-command boundary; they are not native recognition tests. The separately named installed-Tesseract test uses the actual engine with no OCR mocks and an isolated test database. Native scanned-PDF rendering was not verified here; the live backend reports its renderer unavailable.

From `C:\Doculens\frontend`:

```powershell
npm test
# 19 passed, exit 0
npm run typecheck
# exit 0
npm run lint
# exit 0
npm run build
# exit 0; all seven routes built, static generation 7/7 completed
```

The production build completed on this run without directory probes or permission changes. This supersedes the earlier report's build blocker for this checkout at this checkpoint; it does not guarantee Windows EPERM cannot recur. `git diff --check` also passed.

## Files changed/preserved

- backend/app/invoice_rules.py — retained prior fixes; added bounded Bill To buyer prefix handling.
- backend/tests/test_browser_ocr_fields.py — added buyer expectation and provenance assertion to the existing transcript tests.
- backend/tests/test_image_upload_integration.py — new real-endpoint/native/controlled/archive tests.
- backend/tests/fixtures/acme-printed-invoice.png — unchanged actual fictional source PNG.
- README.md — integrated-test/restart checkpoint.
- IMAGE_UPLOAD_INTEGRATION_RESULTS.md — this report.
- acceptance/image-ocr-integrated-result.png — live browser result screenshot.

Preexisting uncommitted transcript fixture, parser changes and OCR_FIELD_EXTRACTION_RESULTS.md were preserved. No UI source, API adapter, OCR engine, schema, storage implementation, dependencies or lockfiles changed for this task. The actual fictional sample was explicitly reprocessed through the normal UI; no direct SQLite edits or unrelated saved-record changes occurred.

## Restart and retest

In the terminal running the backend, press Ctrl+C, then:

```powershell
cd C:\Doculens
.\backend\run.ps1
```

The script imports this checkout's app and starts Uvicorn with reload on 127.0.0.1:8000. The current live process loaded the changes successfully during this verification; no process was force-killed. Keep installed Tesseract/English data available, or configure DOCULENS_TESSERACT_PATH before starting.

With the frontend at http://localhost:3000/upload, choose a PNG/JPEG and click Analyze invoice. Selection alone is not analysis. New file contents create a new stored result; identical contents reuse the saved result even if renamed. For an older result, open its saved details -> History & reprocessing -> select the identical original file -> Reprocess and reset review. This increments the revision, archives analysis/review and returns review to pending. Refresh an already open tab after reprocessing.

If the frontend is not running:

```powershell
cd C:\Doculens\frontend
npm run dev
```

This acceptance demonstrates the supplied fictional printed document only. Handwriting and general OCR accuracy are not certified. Low-confidence lines remain excluded; no unreadable identifiers, GSTINs, tax totals or table rows were fabricated.
