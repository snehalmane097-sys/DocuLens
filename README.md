# DocuLens AI

DocuLens is a local document-understanding application built with Next.js, TypeScript, Tailwind CSS, FastAPI and SQLite. It extracts evidence-backed fields from digitally generated PDF invoices, validates arithmetic, saves analysis history, supports versioned human review, and compares saved documents deterministically. Fictional demonstrations remain available in explicitly labelled separate views.

## Windows setup

Use Windows 10/11, VS Code, Node.js 22 LTS with npm, and Python 3.12. Keep the existing frontend lockfile. No PostgreSQL, cloud account or external AI key is required. Optional OCR needs the separate native tools documented below.

From PowerShell:

```powershell
cd C:\Doculens\frontend
npm ci
Copy-Item .env.example .env.local
cd ..\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

If the virtual environment or environment files already exist, reuse them; do not overwrite local settings. Dependency installation needs permitted registry access. The existing environment is **backend\.venv**, not backend.venv. Using its Python executable directly avoids PowerShell activation-policy changes.

Terminal 1, backend:

```powershell
cd C:\Doculens
.\backend\run.ps1
```

Alternatively:

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

Terminal 2, frontend:

```powershell
cd C:\Doculens\frontend
npm run dev
```

Open http://localhost:3000. API documentation is at http://127.0.0.1:8000/docs. Bind the backend only to loopback; this local application has no multi-user authentication.

## Configuration and storage

- Frontend `NEXT_PUBLIC_API_URL`: defaults to `http://127.0.0.1:8000`; loopback URLs only. Restart Next.js after changing it. Public variables must never contain secrets.
- Backend `CORS_ORIGINS`: exact comma-separated origins, default `http://localhost:3000,http://127.0.0.1:3000`. Wildcards, credentials and URL paths are rejected. Foreign browser origins cannot perform writes.
- Backend `DOCULENS_DB_PATH`: optional SQLite file path, e.g. `C:\Doculens\backend\data\doculens.sqlite3`. Default is backend/data/doculens.sqlite3, independent of the terminal working directory. Parent directory must be writable.
- SQLite is the smallest storage choice for this single-machine project and uses Python's standard library. No dependency or database server was added. Tables initialize on first access. Records survive process restarts.
- SHA-256 of PDF bytes provides exact-upload idempotency. Repeated uploads return the original record and preserve reviews. Different bytes can produce duplicate-invoice candidates based on invoice number and supplier identity; candidates are never silently merged.
- PDF bytes are processed in memory and **not stored**. Extracted text excerpts, field evidence, analysis JSON, review overrides, history and comparisons **are stored** and may contain sensitive invoice information. Keep the database private. Stop the backend before copying the SQLite file for backup. No deletion/retention or automatic encryption policy is implemented.
- Review and reprocessing writes use version checks; stale writes return 409. Reprocessing requires the original PDF and explicit action, archives previous extraction/review, increments version, and resets review to pending. Ordinary uploads never overwrite an analysis.

## Routes and workflow

| Frontend route | Function |
| --- | --- |
| / | Saved-document overview, with separately labelled fictional dashboard |
| /upload | PDF selection, signature/size checks, real analysis and evidence |
| /documents | Saved history, supplier/identifier search and review filter |
| /documents/real-{id} | Original extraction, reviewed fields, arithmetic, duplicate candidates, review history and explicit reprocessing |
| /documents/doc-001 (and other fixture IDs) | Clearly labelled fictional review; temporary edits |
| /reconciliation | Expected-versus-observed document comparison, discrepancy notes and saved report retrieval; separate fictional example |
| /analytics | Persisted counts and discrepancy summaries; separate fixture demonstration |

Upload a PDF, inspect source evidence and warnings, open the saved document, enter verified corrections and notes, and save a pending/approved/rejected review. Original extraction is retained separately. Approval requires known invoice number/date/supplier/subtotal/grand total and no detected arithmetic mismatches; unknown checks still require human assessment. Compare two distinct saved documents, inspect mismatches/unknowns, and save discrepancy review notes. Reviewing a discrepancy does not change its detected values.

## API contract

| Method and endpoint | Contract |
| --- | --- |
| GET /api/health | Genuine service status, phase 4 and PDF dependency availability |
| POST /api/documents/analyze | Multipart **file** containing one PDF, PNG or JPEG; optional explicit reprocess_version query |
| GET /api/documents?offset=0&limit=100 | mode=persistent, items, total; limit 1–500 |
| GET /api/documents/{id} | Analysis, effective reviewed fields, current validation, revision and duplicate candidates |
| GET /api/documents/{id}/history | Versioned review/reprocessing events |
| POST /api/documents/{id}/review | JSON version, fields (nullable decimal/text strings), notes, status |
| POST /api/documents/{id}/reprocess?version=N | Multipart file; exact original bytes and matching revision required |
| POST /api/reconciliations | JSON expected_id and observed_id |
| GET /api/reconciliations | Latest 100 saved report summaries |
| GET /api/reconciliations/{id} | Evidence-backed rows and stale-source indicator |
| POST /api/reconciliations/{id}/review | JSON version and decisions mapping discrepancy IDs to notes |
| GET /api/analytics | Persisted totals, review statuses, daily volume, mismatches and unknown-check counts |

Analysis HTTP 200 returns filename, status (analyzed/needs_ocr), method, pages, fields, gstin_candidates, line_items, validation, warnings, text_excerpt, stored=true, document_id, version and review_status. Each extracted field has nullable value/evidence and method. Money is a decimal string. Calculated values appear only in validation checks. A successful extraction is not approval.

Upload restrictions: one PDF, 10 MiB maximum, extension/content-type/signature checks, 30 pages and bounded extracted text. PNG/JPEG images can be processed with optional local OCR; see the current OCR section below. Errors: 400 malformed multipart; 413 oversized; 415 wrong file type/signature; 422 encrypted/malformed/unsupported PDF or invalid review; 404 missing record; 409 stale revision/wrong reprocessing file; 503 unavailable dependency/storage.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/documents/analyze -F "file=@C:\path\invoice.pdf;type=application/pdf"
```

## Extraction, validation and limits

Label/party/table rules are independent from validation and reconciliation. They support common invoice-number/date aliases, bounded wrapped labels, Indian/international comma grouping, CGST/SGST or IGST, tax total, signed round-off, explicit shipping, final payable labels, and single-row vertical tax summaries. Party-position associations and all GSTIN candidates remain reviewable. Unknown/conflicting fields are never filled from expected regression values.

For Type0 Identity-H financial fonts lacking ToUnicode, the extractor can recover unambiguous financial characters from the embedded TrueType Unicode cmap when CID-to-glyph mapping is identity. It never guesses glyph shifts or edits the uploaded PDF. Unsupported font formats/mappings remain unknown. Optional local OCR is available; no external AI service is used.

Pipe/tab/stable double-space line-item tables are supported with explicit headers. A single clearly delimited vertical item can supply quantity/unit rate; tax-inclusive or ambiguous line amounts are not invented as pre-tax line items. Multi-row vertical tables with omitted repeated identifiers remain partially supported. Missing/unreadable values require human review. Source text is treated as data, never instructions.

Validation uses Decimal and an absolute tolerance of 0.02 monetary units. Checks include quantity × rate for supported items, item totals versus subtotal, GST components versus stated tax, explicit pre-round total where present, shipping, signed round-off and final payable total. A separate stated-tax-total check may reconcile a payable amount while component checks remain unknown. Neither that check nor human approval establishes GST/legal compliance. Currency conversion and inferred discounts/charges are unsupported.

Reconciliation uses reviewed values, records expected and observed evidence, compares amounts within tolerance and quantities exactly, and matches item identities only by unique normalized descriptions. Missing values are unknown, not matches. Reports become stale when source versions change.

Known regression invoice /004 has recoverable embedded financial glyphs. Its explicitly labelled pre-round total remains unknown; ambiguous tax-inclusive item rows are not fabricated. The separate /006 includes an explicit shipping charge and a partially unsupported multi-row tax summary. See ACCEPTANCE_RESULTS.md for executed results.

## Architecture

- frontend/src/app: existing App Router routes and dashboard styling.
- frontend/src/components: shared shell, real workspace, upload/results, saved review and reconciliation interfaces; separate demo views.
- frontend/src/lib: typed contracts, loopback API client, existing fixtures and file validation.
- backend/app/main.py: API registration, CORS, error responses and endpoint orchestration.
- backend/app/pdf_analysis.py and pdf_fonts.py: bounded in-memory reception and evidence-based text/font extraction.
- backend/app/invoice_rules.py and invoice_tables.py: conservative field and table rules.
- backend/app/invoice.py: independent financial checks.
- backend/app/storage.py: SQLite records, idempotency, versioned reviews and history.
- backend/app/reconciliation.py: deterministic comparisons and reviewed discrepancy reports.
- backend/tests and frontend/tests: synthetic fixtures, actual extracted-text regressions and endpoint/client tests.

## Verification commands

```powershell
cd C:\Doculens\backend
New-Item -ItemType Directory -Force .test-tmp | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp\manual
cd ..\frontend
npm test
npm run typecheck
npm run lint
npm run build
npm run start
```

Run typecheck and build sequentially. Do not run a production build against the same generated output while diagnosing a dev-server lock. A Windows EPERM failure is a failed build until rerun succeeds; do not delete source files or relax system protections. Some managed environments restrict loopback requests or asyncio socket initialization; report actual errors rather than claiming runtime success. Actual PDF tests skip when the private source file is unavailable; decoded-text regressions still run. Real fixtures contain private invoice information and must not be published without authorization.

## Future work

Validated handwriting recognition, broader OCR/table/font coverage, currency-aware reconciliation, richer line-item review, evaluation on held-out invoices, authenticated multi-user deployment and a production storage/retention strategy. None is represented as implemented.

Earlier Phase 1/2A notes and checkpoints are preserved in README_HISTORY.md; this README describes the integrated current implementation.


## Acceptance checkpoint — 28 October 2026

The outstanding acceptance tasks were executed against this checkout without application, dependency, lockfile, or dashboard changes. See [ACCEPTANCE_RESULTS.md](ACCEPTANCE_RESULTS.md) for commands and observed results.

- Full backend suite: **82 passed**, one upstream Starlette/AnyIO deprecation warning; no skips or failures. API tests include actual PDF upload, persistence, review conflicts, reprocessing, reconciliation and restart retrieval.
- Frontend: **16 passed**; typecheck and lint passed; production build completed with exit 0 and all six application route patterns.
- The prior Windows asyncio stall did not recur: a standalone ProactorEventLoop initialized and ran, and the full TestClient suite completed. Previous evidence placed the stall inside Python socketpair initialization before request handling; this is consistent with a transient execution-context restriction, not a demonstrated application defect. No event-loop, firewall or security changes were made.
- Live `/006` was explicitly reprocessed through its document-details form using the matching original PDF. It is revision **2**, review **pending**, with one record and the revision-1 analysis/review archived. PDF bytes remain unstored. Ordinary uploads remain idempotent and do not automatically refresh older analyses.
- `/006` source evidence states subtotal **53,767.50**, tax **9,822.16**, shipping **800.00**, round-off **+0.34**, payable **64,390.00**. Their sum is 64,390.00. The old record omitted shipping; no evidence supported the reported 5,767.50 subtotal. No values were corrected directly in SQLite.
- The stated-tax payable check passes with zero detected arithmetic mismatches. CGST/SGST component checks, item-table completeness, and unlabelled pre-round total remain unknown. Passing the payable check is not full invoice validation or approval.
- Responsive spot checks used 1440x900 desktop and 390x844 mobile. Saved details, mobile navigation/history and populated overview were inspected; upload/analytics/reconciliation shells also rendered at mobile width. The mobile page stayed within the viewport and wide tables used local horizontal scroll. This is a spot check, not an exhaustive browser/device/accessibility audit. Temporary viewport overrides were reset.

Start the existing local services in separate PowerShell terminals:

```powershell
cd C:\Doculens
.\backend\run.ps1
```

```powershell
cd C:\Doculens\frontend
npm run dev
```

SQLite defaults to `backend/data/doculens.sqlite3`; override with `DOCULENS_DB_PATH` if needed. Backend `.env` is loaded by the launcher. Frontend `NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000`. Keep both services local. No additional setup or dependency change was needed for this checkpoint.

## Optional local OCR (current implementation)

PDF, PNG and JPEG can use the existing analysis and explicit-reprocessing endpoints. Earlier acceptance checkpoints above predate OCR. No Python wrappers, packages, frontend dependencies or lockfiles were added/changed. SQLite, financial validation and review workflows are reused; original bytes are not persisted.

### Native setup

Tesseract is NOT installed on this implementation machine. Poppler pdftoppm is available through the runtime bundle. Installing pytesseract would not install the engine; this adapter does not need that wrapper. Install a trusted Windows Tesseract build with English eng.traineddata using the [official installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html). Scanned PDFs also require Poppler pdftoppm. Keep native tools updated.

Add executables to PATH or configure backend .env with actual absolute executable paths:

```dotenv
DOCULENS_TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
# If pdftoppm is not on PATH:
# DOCULENS_PDFTOPPM_PATH=C:\tools\poppler\Library\bin\pdftoppm.exe
```

Verify the actual installation (list-langs must include eng), then restart the backend:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --version
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
pdftoppm -v
cd C:\Doculens
.\backend\run.ps1
```

In another terminal:

```powershell
cd C:\Doculens\frontend
npm run dev
```

GET /api/ocr/status reports executable discovery only, not language-data readiness or recognition accuracy. Image uploads return an actionable 503 if OCR is unavailable. PDFs requiring missing optional tools retain needs_ocr results and setup warnings, preserving digital text. Text-based PDFs still work. No external service receives invoice contents.

### OCR processing, evidence and limits

PDF text is assessed per page. pypdf and existing font recovery remain the digital path. Pages without usable text render individually through Poppler to grayscale PNG with maximum edge 2200 pixels. Tesseract uses English automatic segmentation (--psm 3) and native image processing. Images have signature/header/dimension checks before native decoding. Animated PNGs are rejected. Inputs and intermediate rasters use pipes; originals and raster files are not written to disk by this adapter. Native diagnostics are discarded instead of exposing invoice content or paths.

Limits: unchanged 10 MiB uploads; 30 total PDF pages; at most 8 OCR pages; 12 million image pixels and 8000 pixels per edge; two concurrent OCR jobs; one 45-second rendering/OCR deadline; capped 8 MiB native output, 12,000 words per page and 200,000 parsed characters. Native decoder memory is not an OS sandbox. Keep this local-only. Large documents may need splitting/resizing. Errors: 413 size/dimensions, 422 malformed/native failure/page count, 503 unavailable/busy tools, 504 timeout.

Responses add ocr_used, ocr_pages and review_required. OCR pages contain page number, raster dimensions, recognized lines, minimum word confidence and pixel bbox x/y/width/height. Boxes refer to the OCR raster, not PDF coordinates. OCR-derived fields include page evidence and method markers. Lines containing any word below 80 confidence are excluded entirely from parsing; rejected text remains visible for review. High confidence does not prove correctness. Empty/unreadable OCR returns needs_ocr and unknown fields. Recognized text/evidence/locations persist in existing analysis JSON and can be sensitive. Original image/PDF bytes are not saved.

All OCR results start pending human review. Existing Decimal checks never replace missing extracted fields with calculated values. Reprocessing archives previous analysis/review; identical ordinary uploads retain old results. Use explicit reprocessing after OCR setup changes.

### OCR and handwriting limitations

Handwriting is NOT verified. The engine can attempt it, but Tesseract is primarily for printed text. No dedicated handwriting model, model download or external API was introduced. No actual handwritten invoice fixture was provided/tested. Never rely on handwritten amounts/identifiers without checking the source.

Supply upright images. Custom deskew, arbitrary-rotation search, EXIF correction and contrast enhancement are not implemented. PDF rotation metadata is respected by Poppler. Small, blurred, faint or rotated inputs may fail. Partially scanned regions on otherwise readable PDF pages may not trigger OCR. Existing label/table-layout limits still apply.

### Executed OCR checkpoint (28 October 2026)

- Backend syntax/import passed. Full suite: 98 passed, 1 skipped, one upstream Starlette/AnyIO deprecation warning. The native Tesseract recognition test is the explicit skip; /004 and /006 regressions passed.
- Frontend: 17 tests passed; typecheck and lint passed. Production build completed with exit 0 and all routes. Two prior build attempts hit EPERM in generated folders; targeted Node mkdir probes succeeded, and the final rerun completed without permission/dependency changes.
- Browser: PNG selection and real submission executed. Missing Tesseract produced the clear setup error rather than a success/fixture fallback. Native OCR recognition was NOT executed.
- Actual /004 PDF rasterization succeeded at 1557x2200 pixels. This is renderer verification, not recognition. Synthetic controlled-TSV tests are not real-world OCR accuracy evidence.
- Printed OCR on a real invoice image: not tested. Handwriting on an actual handwritten invoice: not tested. Tesseract installation with English data and real-document evaluation remain blockers to full OCR/handwriting acceptance.

Commands: backend `.venv\Scripts\python.exe -m compileall -q app`, `.venv\Scripts\python.exe -m pytest -q --basetemp=.test-tmp\ocr-final`; frontend `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`. For native recognition after setup, run `.venv\Scripts\python.exe -m pytest -q tests/test_ocr.py -k native_printed_image_recognition`. A skipped test is not a pass. See OCR_IMPLEMENTATION_RESULTS.md for the exact changed-file inventory.

### Frontend redesign checkpoint (28 October 2026)

The shared shell, overview, saved documents, Analyze page, document details/review, reconciliation and analytics now use the supplied finance-dashboard reference's warm ivory, white and sage design language. Analyze uses one file action, real processing states and a concise summary; extracted details, evidence and review are expandable. Material discrepancies remain visible. Global search and review filters link to real saved documents. No backend contracts, dependencies or lockfiles were changed for the redesign.

Financial aggregates require explicit common currency evidence; missing/mixed currencies are not guessed or combined. Local Inter/Manrope faces are preferred when installed, with system font fallbacks. Frontend tests: 19 passed; typecheck and lint passed. Desktop 1440x1000 and mobile 390x844 main-route checks passed without page-level horizontal overflow. See FRONTEND_REDESIGN_RESULTS.md for exact changed files, build outcome and browser checks. Existing OCR limitations above still apply.

Latest redesign production-build result: exit 1, Windows EPERM creating generated `.next/server/app/reconciliation`, despite successful directory probes. Build acceptance remains blocked; compilation/typecheck success in an intermediate retry is not a completed production build. See the redesign report for retries and exact results.
