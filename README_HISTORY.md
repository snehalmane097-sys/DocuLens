# DocuLens AI

A final-year CSE AIML project for document understanding, financial validation, and invoice–purchase-order reconciliation.

**Current scope: Phase 2A.** The upload page performs real in-memory text-PDF invoice analysis through the local backend when dependencies are installed. Other document views remain labelled fictional demos. No OCR, ML, database or persistent uploads are included.

## Phase 2A: real text-based PDF invoice analysis

The upload page now has a separate real-analysis workflow. The Overview, Documents, reconciliation demo and analytics still use fictional fixtures. Real results never replace those fixtures. Existing Phase 1 verification checkpoints below are historical.

### Setup and endpoint

The actual existing virtual environment in this workspace is `backend\.venv` (not `backend.venv`). From a terminal with permitted PyPI access:

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env
```

The runtime requirements now include maintained `pypdf>=6.4.0,<8` and `python-multipart>=0.0.30,<0.1`. Existing package pins and frontend lockfiles are preserved. Bind only to loopback. `NEXT_PUBLIC_API_URL` defaults to `http://127.0.0.1:8000`; the frontend accepts loopback URLs only. CORS permits GET and POST from configured exact origins.

`POST /api/documents/analyze` accepts multipart/form-data with exactly one field named `file` containing a PDF. No other fields are accepted. OpenAPI at `/docs` includes the binary file request schema.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/documents/analyze -F "file=@C:\path\to\invoice.pdf;type=application/pdf"
```

Successful HTTP 200 response shape (values shown here are illustrative, not actual extraction output):

```json
{
  "filename": "invoice.pdf",
  "status": "analyzed",
  "method": "pypdf_text_and_labelled_rules",
  "pages": 1,
  "fields": {
    "invoice_number": {
      "value": "EXAMPLE-1",
      "evidence": "Invoice No: EXAMPLE-1",
      "method": "labelled_text_rule"
    }
  },
  "line_items": [],
  "validation": {
    "tolerance": "0.02",
    "checks": [],
    "mismatches": 0,
    "unknown": 0,
    "passed": 0
  },
  "warnings": [],
  "text_excerpt": "",
  "stored": false
}
```

The full response always includes fields for invoice number/date, supplier name, GSTIN, subtotal, CGST, SGST, IGST, GST total and grand total. Amounts and quantities are decimal strings, not floating-point numbers. Missing or conflicting extracted values and evidence are null. Checks have `name`, `status` (pass/mismatch/unknown), `calculated`, `extracted`, and `explanation`. Extracted values are not replaced with calculated totals.

Insufficient text returns HTTP 200 with `status: "needs_ocr"`, unknown fields and an explicit OCR-not-supported warning. Error responses use FastAPI's `{"detail":"message"}`: 400 malformed multipart; 413 size exceeded; 415 wrong type/signature; 422 malformed/encrypted/unsupported/page-limit PDF; 503 missing PDF dependencies. Missing dependencies do not break the existing GET routes. `GET /api/health` now returns phase 2 and reports whether the analysis packages are installed. `GET /api/documents` remains an empty stored-document list; it is not analysis history.

### Parsing and validation rules

- Label-based fields only. Supported labels include Invoice No/Number/#, Invoice Date, Supplier/Seller/Vendor (colon or equals required), GSTIN/Supplier GSTIN, Subtotal/Taxable Amount/Taxable Value, CGST, SGST, IGST, Total GST/GST Total/Total Tax, and Grand Total/Invoice Total/Total Amount/Amount Payable/Total.
- A label and value must be on the same extracted line. Repeated identical values are allowed; conflicting values stay unknown. Supplier names are not guessed from page headings.
- Dates support ISO YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY and DD Month YYYY. Slash dates use day/month/year; no US-style month/day inference.
- Numeric label values support plain or comma-grouped non-negative amounts with optional INR/Rs prefix and optional tax percentage before the amount. Unsupported currencies, negative amounts, malformed values and extreme numbers remain unknown.
- Line items require explicit supported headers and pipe, tab, or stable double-space columns. See the conservative multi-format update below for continuation rows, aliases and limits.
- Each recognized line checks quantity × unit rate versus the extracted pre-tax line amount. Tax is checked when a line provides both tax rate and amount. Recognized line amounts are compared with subtotal, but the parser cannot guarantee table completeness.
- Decimal arithmetic uses an absolute tolerance of **0.02 monetary units** and two-decimal display rounding. A difference at or below tolerance passes; greater differences mismatch. This is a local arithmetic aid, not GST compliance or legal verification.
- GST components use CGST + SGST **or** IGST, never their combined sum plus the stated GST total. Mixed non-zero structures and incomplete split structures stay unknown. With no component labels, an explicitly stated GST total can be used for the grand-total check.
- Grand total uses subtotal plus selected tax and an explicitly extracted signed round-off when present. Pre-round/final totals and unknown adjustments are handled separately; see the update below.
- Text is untrusted data. No instructions, scripts, attachments, URLs or embedded actions are executed. React renders evidence as text.

### Limits and storage

The receiver streams multipart bytes into bounded memory without Starlette UploadFile disk spooling. Limits: one PDF, 10 MiB file content, 64 KiB extra request overhead, bounded multipart headers, PDF signature and extension, allowed MIME type (PDF or unspecified/octet-stream), at most 30 pages, and at most 200,000 extracted characters. Evidence is bounded; the text excerpt is limited to 4,000 characters. No file contents are logged intentionally or persisted by application code.

Parsing compressed/malicious PDFs can still consume CPU and memory inside pypdf before text limits are checked; these guards are not a hardened process sandbox. Use trusted local invoices only. No public deployment, OCR, database, external AI, cloud upload or persistent file history is implemented. The client timeout is 60 seconds; a disconnected client does not guarantee cancellation of an already-running extraction thread.

PNG/JPG selection remains a local preview; only PDF has an Analyze action. Up to five files may be selected, but analysis sends one PDF at a time. Results/errors are per file, kept only in page state, and cleared on refresh/navigation. The page shows the configured backend before submission.

### Phase 2A test commands

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_invoice.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_pdf_analysis.py -q -rs
cd C:\Doculens\frontend
npm test
npm run typecheck
npm run lint
npm run build
```

PDF integration tests generate synthetic PDFs in memory; they include readable/missing fields, no-text PDFs, encryption, malformed input, upload limits, MIME/signature validation, and CORS. They explicitly skip if PDF dependencies are missing. Frontend tests exercise multipart request construction and loading/result/error transitions using injected fetch, not browser automation.



### Phase 2A verification checkpoint (28 October 2026)

Changes are saved, but full runtime acceptance is **blocked in this execution environment**.

| Command / check | Observed result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pip install 'pypdf>=6.4.0,<8' 'python-multipart>=0.0.30,<0.1' --retries 0 --timeout 10 --disable-pip-version-check` | Failed: no distributions reachable; subsequent socket.getaddrinfo('pypi.org',443) returned DNS error 11001. No repeated installation attempts. |
| `npm test` in frontend | PASS: 12 tests, including all original 8 |
| `npm run typecheck` in frontend | PASS, including final label changes |
| `npm run lint` in frontend | PASS, no warnings |
| `npm run build` in frontend | Compile and build TypeScript stages passed, but production build exited 1 on generated output EPERM. Initial failure: upload.segments/upload; targeted directory retry failed on _not-found.segments/_not-found. No source/dependency changes to mask it. |
| `python -m pytest tests/test_invoice.py tests/test_analysis_contract.py -q` in backend venv | PASS: 11 tests (8 parser/arithmetic + 3 handler/schema contracts) |
| `python -m pytest tests/test_api.py -k 'invalid_cors or schema' -q` | PASS: 5 tests, 4 deselected; one existing Starlette/anyio deprecation warning |
| `python -m pytest tests/test_pdf_analysis.py -q -rs` | SKIPPED module: pypdf unavailable. This is not a passing PDF integration suite. |
| Full `python -m pytest -q` | Interrupted after rule tests when async TestClient stalled. Standalone asyncio creation with a 5-second faulthandler deadline reproduced the hang in Windows socketpair.accept / ProactorEventLoop self-pipe. No async/network controls were bypassed. |
| Python AST parsing and OpenAPI generation | PASS; analyze route and InvoiceAnalysis schema registered |
| Real PDF upload / browser interactions / live HTTP endpoints | NOT VERIFIED; dependencies missing and local asyncio/socket access restricted |

Thus **16 distinct synchronous backend tests passed**, not the full backend suite. PDF synthetic-fixture integration tests are saved for execution once dependencies and normal localhost/event-loop access are available. Health/list handler functions and the missing-dependency 503 branch were tested directly, not through HTTP.

An additional pytest invocation from the project root failed collection because app was not on that working directory's import path; rerunning from backend as documented passed all 11 targeted tests.

Changed files in this phase:
- Backend: app/main.py, app/schemas.py, requirements.txt; new app/invoice.py and app/pdf_analysis.py.
- Backend tests: updated tests/test_api.py; new tests/test_invoice.py, tests/test_analysis_contract.py and tests/test_pdf_analysis.py.
- Frontend: app/upload/page.tsx, components/upload-preview.tsx, components/shell.tsx (truthful labels only), app/globals.css (new results styles); new components/analysis-results.tsx, lib/analysis-types.ts, lib/analyze-upload.mjs and tests/analyze-upload.test.mjs.
- Documentation: README.md. Existing frontend dependencies and package-lock.json were not edited.

Once permitted PyPI and localhost access are available, run the installation and full tests above, restart Uvicorn on 127.0.0.1, upload a synthetic text PDF via /upload, and verify actual results. Do not treat the feature as runtime-verified until those checks pass.

## Architecture

| Location | Responsibility |
| --- | --- |
| `frontend/src/app/` | Next.js App Router pages, shared layout, loading/error/not-found boundaries |
| `frontend/src/components/` | Existing dashboard shell, panels, document table, charts, preview workflows |
| `frontend/src/lib/types.ts` | Frontend document metadata types |
| `frontend/src/lib/mock-data.ts` | Fictional documents, shared summaries, attention items, activity range |
| `frontend/src/lib/demo-logic.mjs` | Pure aggregation, full-date grouping, comparison, review validation |
| `frontend/src/lib/reconciliation-data.ts` | Documented fictional pair and sample issue categories |
| `frontend/src/lib/upload-*.mjs` | Local metadata/header checks and selection limits |
| `frontend/tests/` | Node built-in test runner tests; no extra test framework |
| `backend/app/main.py` | FastAPI app factory, CORS, health and document router |
| `backend/app/schemas.py` | Pydantic response and document schemas |
| `backend/tests/` | pytest endpoint, response-contract, validation, and CORS tests |

Frontend: Next.js, React, TypeScript, Tailwind CSS v4, Lucide icons.
Backend: Python, FastAPI, Uvicorn, Pydantic (through FastAPI).
The upload page calls the local backend for real analysis. Other pages read fixtures directly. Real results do not replace the sample library.

Preserve the existing dashboard design and reuse its components and CSS tokens when extending the project.

## Windows prerequisites

- Windows, VS Code, and PowerShell.
- Node.js 22 LTS with npm; use the existing `package-lock.json`.
- Python 3.12 recommended, with pip and the Python launcher installed.
- Git recommended for version control.
- Internet access to npm and PyPI for first-time dependency installation.

Check tools in a VS Code terminal:

```powershell
node --version
npm --version
py -3.12 --version
git --version
```

If `python` opens the Microsoft Store or `py` finds no interpreter, install Python or select a real interpreter in VS Code. An existing interpreter can be called directly:

```powershell
& "C:\path\to\Python312\python.exe" -m venv .venv
```

Do not use that placeholder path literally. Avoid installing backend packages into your global Python environment.

## Initial frontend setup

```powershell
cd C:\Doculens\frontend
npm ci
Copy-Item .env.example .env.local
```

Copy the environment example only when the local file does not already exist; preserve existing settings. If dependencies are already installed and unchanged, do not reinstall or upgrade them.

## Initial backend setup

```powershell
cd C:\Doculens\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

If `.venv` already works, reuse it. `requirements-dev.txt` includes runtime requirements and pytest/httpx. For runtime-only installation, use `requirements.txt` instead. These commands use the virtual environment interpreter directly, so activation and PowerShell execution-policy changes are unnecessary.

In VS Code, select `backend\.venv\Scripts\python.exe` as the Python interpreter.

## Run in two separate terminals

Terminal 1 — frontend:

```powershell
cd C:\Doculens\frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Terminal 2 — backend:

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for API documentation. Stop either service with Ctrl+C.

For a frontend production build, stop the dev server before building in the same checkout:

```powershell
cd C:\Doculens\frontend
npm run build
npm run start
```

## Environment configuration

| File / variable | Default | Behavior |
| --- | --- | --- |
| `frontend/.env.local`: `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Loopback API URL used for real PDF analysis |
| `backend/.env`: `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Exact comma-separated browser origins allowed for GET and POST requests |

The documented Uvicorn command loads `.env`. Importing the app directly reads process environment variables; it does not automatically load that file. If `CORS_ORIGINS` is unset, safe local defaults apply; an empty value disables cross-origin access. Wildcards, paths, trailing slashes, and embedded credentials are rejected. Credentials are disabled. CORS is browser access policy, not authentication.

Keep secrets out of source control and out of `NEXT_PUBLIC_*` variables. Local environment files, virtual environments, generated output, and `uploads/` are ignored. No API keys are needed in Phase 1.

## Frontend routes

| Route | Current behavior |
| --- | --- |
| `/` | Overview cards, activity chart, attention items, searchable/filterable recent documents |
| `/documents` | Shared fictional library with filename/vendor search and type/status filters |
| `/upload` | File selection, validation and real PDF analysis with separate results |
| `/documents/[id]` | Metadata, authored findings, editable demo fields and notes, save/reset indicators |
| `/reconciliation` | Deterministic field comparison for the Acme sample pair; empty state for unsupported pairs |
| `/analytics` | Fixture-derived volume/status charts and discrepancy breakdown |

Valid sample IDs are `doc-001` through `doc-006`. Unknown IDs use the shared not-found view. Shared loading and error views are included.

## Existing metadata API contract (Phase 1 compatibility)

| Method / path | Response |
| --- | --- |
| `GET /api/health` | HTTP 200 process-liveness response |
| `GET /api/documents` | HTTP 200 empty document list with explicit Phase 1 capability flags |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | Generated API schema |

Health:

```json
{"status":"ok","service":"doculens-api","phase":2,"processing_available":false}
```

Documents:

```json
{
  "mode": "empty",
  "items": [],
  "total": 0,
  "processing_available": false,
  "message": "Phase 2A: no storage configured. Analyze PDFs separately; uploads are not listed."
}
```

The typed document schema reserves `id`, `filename`, nullable `reference`/`vendor`, `type`, timezone-capable `uploaded_at`, `status`, nullable non-negative `total`, `currency`, and non-negative `issues`. JSON API metadata uses `uploaded_at`; frontend fixtures currently use `uploadedAt`. Map that field explicitly when integrating later.

The health processing_available flag is true only when PDF analysis dependencies are installed; the example above shows the unavailable case. The list response flag refers to stored-document processing and remains false. Health verifies that the API process can respond; it does not verify a database or OCR readiness. The document endpoint always returns zero stored documents. POST `/api/documents/analyze` provides transient analysis; POST to `/api/documents` still returns 405. There is no persistent document-detail API.

## Fictional sample views and limitations

- All six document records, statuses, vendors, amounts, and findings are fictional. No accuracy or confidence metrics are claimed.
- File selection accepts PDF, PNG, JPG/JPEG, up to 10 MiB (10 × 1024 × 1024 bytes) per file and five files total. Basic metadata and header bytes are checked locally. This is not full file validation or malware scanning.
- Files are submitted to the loopback backend only when Analyze PDF is clicked. They are processed transiently without persistent storage. Image selection remains preview-only.
- Review edits and saved snapshots exist only in React state. They disappear on navigation/refresh and do not change the library, reconciliation, analytics, or API.
- No original sample PDF/image files are bundled. Document review shows metadata and an explicitly labelled viewer placeholder.
- Reconciliation is an exact comparison of a selected fictional pair, not automatic document matching or financial advice. Severity labels are fixed demo rules.
- Acme invoice: 10 units × INR 10,400 = INR 104,000; 20% tax = INR 20,800; total INR 124,800.
- Acme purchase order: 10 units × INR 10,000 = INR 100,000; 18% tax = INR 18,000; total INR 118,000.
- Two independent differences (unit price and tax rate) produce a total difference of INR 6,800. Tax amount/subtotal/total consequences are not counted again as independent issues. One additional authored missing-reference finding belongs to Studio Stationery.
- Activity groups full calendar dates in Asia/Kolkata. The Overview date badge describes the fixture range; it is not an interactive date filter.
- No authentication, database, durable storage, OCR, ML, or cloud services are included. Use locally for Phase 1 development.

Phase 2 must validate uploads server-side, enforce streaming size limits and allowed file types, use generated storage identifiers instead of user filenames, prevent path traversal, and keep uploads outside executable/public directories. Client checks alone are insufficient.

## Verification commands

Frontend:

```powershell
cd C:\Doculens\frontend
npm test
npm run typecheck
npm run lint
npm run build
```

The frontend suite covers upload utilities, multi-file selection, review input validation, date aggregation, summaries, and deterministic comparison. It is not a browser end-to-end suite. The original three upload tests are retained.

Backend:

```powershell
cd C:\Doculens\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Runtime API smoke checks (while Uvicorn is running):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/documents
```

Browser checks: open all routes, use both table filters and search, select/remove files, reject a wrong format and an oversized batch, edit/save/reset review fields, visit an unknown ID, and switch reconciliation pairs. Check keyboard navigation and narrow layouts. Passing a production build does not establish that these browser interactions were tested.

If npm/PyPI DNS or connectivity fails, keep saved work and report the blocked check. Do not repeatedly retry or alter dependency versions to disguise a network problem.

## Planned future phases

1. **Phase 1:** Frontend demo and minimal backend foundation (current scope).
2. **Phase 2:** Real secure upload/storage, PostgreSQL, document metadata APIs.
3. **Phase 3:** OCR extraction to structured JSON, confidence values, editable extracted fields.
4. **Phase 4:** Financial validation, duplicate detection, explainable invoice–PO matching.
5. **Phase 5:** Held-out evaluation, broader testing, analytics, deployment, and project documentation.

No future-phase functionality should be represented as already operational.

## Verification checkpoint — 28 October 2026

This checkpoint records observed results, not a claim of complete runtime verification.

| Check | Result |
| --- | --- |
| `npm test` in frontend | PASS: 8 tests, including the original 3 upload tests |
| `npm run typecheck` in frontend | PASS |
| `npm run lint` in frontend | PASS: no warnings after the date badge and PostCSS export fixes |
| `npm run build` in frontend | BLOCKED: process exited with EPERM creating generated directories under `.next/types/app/` |
| Python source syntax | PASS: AST parsing of app and test Python files |
| Backend dependency setup | PARTIAL: Python 3.12.4 and local pip 24.0 available; PyPI connectivity check failed; offline install found no FastAPI distribution |
| `.venv/Scripts/python.exe -m pytest -q` | BLOCKED: pytest is not installed; FastAPI and Uvicorn are also unavailable |
| Frontend HTTP smoke checks | BLOCKED: fetch attempts to localhost ports 3000 and 3100 returned EACCES |
| Backend live endpoints | NOT RUN: dependencies unavailable |
| Routes/navigation | Source inspection confirms all six route patterns and existing navigation targets; no browser click verification |

An attempted second dev server reported an existing Next.js server on port 3000. That server was left running. Stop development servers in your own terminal before rerunning the production build. If EPERM persists, check workspace permissions and locks on generated output. Do not delete source files or change dependency versions to work around it.

Once network access is available, install backend requirements with the existing pinned files and rerun pytest and the documented endpoint smoke checks. No frontend dependencies or lockfiles were intentionally changed during final verification.

## Latest Windows diagnostic checkpoint

The subsequent production build passed with exit code 0; the earlier EPERM did not reproduce. All eight frontend tests, TypeScript, and lint passed. Localhost runtime requests and PyPI DNS access remain blocked in the execution context; backend tests remain blocked by missing dependencies. See [WINDOWS_DIAGNOSTICS.md](WINDOWS_DIAGNOSTICS.md) for commands, observations, and limits. No application code or dependencies were changed during diagnosis.

## PDF analysis 404 diagnosis and restart

The current `C:\Doculens\backend\app\main.py` exports `app = create_app()`; its router registers POST /documents/analyze under prefix /api before include_router runs. Importing that exact module reports **one** POST /api/documents/analyze route. Missing PDF dependencies would return 503, not 404. The reported 404 therefore does not match this saved application's route table; a stale Uvicorn process or another imported app is the likely explanation, not a proven process identity. Process inspection was denied and localhost HTTP was blocked (WinError 10013), so the running server's module could not be confirmed or restarted safely here.

A new `backend/run.ps1` launcher sets the backend directory, uses its .venv interpreter, prints app.main.__file__, asserts exactly one analysis route, and passes an absolute --app-dir and explicit reload directory to Uvicorn. It binds only to 127.0.0.1. It does not kill existing servers or bypass PowerShell policy.

Stop the old Uvicorn process with Ctrl+C in its owning terminal, then:

```powershell
cd C:\Doculens\backend
.\run.ps1
```

Equivalent direct command if your existing script policy does not permit .ps1 execution (no policy change needed):

```powershell
C:\Doculens\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir C:\Doculens\backend --reload --reload-dir C:\Doculens\backend\app --host 127.0.0.1 --port 8000
```

That direct command uses default CORS settings; add --env-file C:\Doculens\backend\.env only if that file exists and you need its settings. Do not start another listener on an occupied port or assume it replaced the old server. Check http://127.0.0.1:8000/openapi.json for /api/documents/analyze before uploading.

Added regression tests:
- tests/test_analysis_contract.py::test_uvicorn_export_has_exactly_one_analysis_route: passed.
- tests/test_pdf_analysis.py::test_uvicorn_export_registers_once_and_accepts_pdf: posts multipart field file with a synthetic PDF against the exported app.main:app and asserts HTTP 200 plus real extracted invoice fields. Saved, but async execution remains blocked here; no passing endpoint response is claimed.
- tests/test_pdf_analysis.py::test_pdf_extraction_function_with_synthetic_invoice: passed using real pypdf; extracted DIRECT-1 and grand total 118.00. This proves the extraction function, not HTTP handling.

Verification command from backend (18 passed, 4 deselected, one existing Starlette/anyio deprecation warning):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_invoice.py tests/test_analysis_contract.py tests/test_pdf_analysis.py::test_pdf_extraction_function_with_synthetic_invoice tests/test_api.py -k "not test_health and not test_empty_document_contract and not test_no_upload_or_processing_endpoint and not test_cors_allows_only_configured_origin" -q
```

A full pytest run with a 45-second faulthandler deadline exited before completing when it reached async TestClient execution. In a normal terminal run the full suite and the new HTTP regression:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_pdf_analysis.py::test_uvicorn_export_registers_once_and_accepts_pdf -q
```

The PDF packages are now installed in the existing virtual environment (superseding older dependency-blocked checkpoints). No endpoint, dependency, dashboard, or frontend source was duplicated or rewritten during this diagnosis. main.py was already correctly registered and was left unchanged.


## Conservative multi-format parser update (28 October 2026)

This update is based on inspected source, reported real-invoice symptoms, and **synthetic regressions**. It does not establish that AE262709004.pdf now parses correctly. Upload the actual PDF again and inspect values and evidence.

### Supported and deliberately unsupported layouts

| Layout | Support |
| --- | --- |
| Complete labelled values on one line | Supported aliases: Invoice No/Number/Num/ID/#, Inv #, Tax Invoice Number; Invoice Date/Dt, Dated, Date; Subtotal/Taxable Amount/Value; CGST/SGST/IGST (including dotted labels); Tax Amount/GST Total; final/payable/grand totals |
| Invoice identifiers with spaces | Accepted only in an invoice-number label context, with a digit and restricted identifier characters |
| Numeric dates and English month dates | ISO, day-first numeric, DD Month YYYY and DD-Mon-YYYY; an English weekday prefix is checked against the date |
| Bounded wrapped labels and values | Supported without joining across blank lines, page breaks or another known label; next-line bare monetary integers remain unknown |
| Party and GSTIN associations | Existing explicit and bounded positional rules retained; positional associations require human review; conflicting IDs are never silently resolved |
| Indian/international grouping | Complete properly grouped tokens, optional INR/Rs/rupee prefix, optional /- suffix; no numeric substring scanning |
| Taxes | Complete explicit amounts only; a percentage alone is unknown. Explicit labelled zero is allowed, but missing/invalid/conflicting tax values never become zero |
| Round-off | Explicit signed adjustment, including Unicode minus and sign before/after currency; pre-round total is separate from final payable total |
| Line tables | Explicit Description/Qty/Rate/Amount headers with supported aliases, reordered columns, and pipes, tabs or stable two-or-more-space separators |
| Wrapped descriptions | Supported only as an explicit same-column continuation row with empty other columns following an identified item |
| Arbitrary single-space/flattened tables, unlabeled numbers, general wrapped paragraphs | Unsupported or partially extracted; no invented items or totals |
| Scanned/image-only PDFs | Require OCR, outside current scope |

Bare generic "Total" is intentionally not a grand-total label: it can be a count or a pre-tax value. Explicit final/rounded labels outrank payable/grand labels, which outrank generic invoice/total-amount labels. Other extracted total evidence produces a review warning; conflicting values at the same priority remain unknown.

Numeric parsing consumes the complete value. GSTINs, phone fragments, malformed grouped amounts, incomplete percentages and trailing arbitrary text are not amounts. Recognized but unparseable/conflicting values keep bounded evidence and warnings. A wrapped bare 0 or 1 is not treated as tax. No global search for a nearby numeric substring is used.

Validation remains separate from extraction with a 0.02-unit tolerance. Known subtotal plus unambiguous GST components (or a separately stated GST total when no component labels exist) gives a pre-round calculation. An explicitly extracted signed round-off is then added for the final check. A present but unreadable round-off or GST component blocks calculation instead of defaulting to zero. When no adjustment label exists, the check explicitly states that no adjustment was found; unrecognized charges still require review. No compliance or legal verification is claimed.

### Synthetic regression results

The fixture uses unrelated synthetic companies/IDs, a spaced identifier ZX 26-27/09/004, Wednesday 09 September 2026, and one explicit item row. It extracts:
- Invoice number ZX 26-27/09/004; invoice date 2026-09-09; supplier Aster Precision Works; buyer Birch Trading India Pvt. Ltd.
- Quantity 36, rate 365.00, line amount/subtotal 13140.00.
- CGST and SGST 1182.60 each, GST total 2365.20.
- Pre-round total 15505.20, round-off -0.20, final total 15505.00.
- IGST remains unknown. Distinct GSTIN candidates remain separate, and the generic GSTIN stays unknown.
The synthetic arithmetic checks pass. A synchronous test generates a real text PDF in memory and runs pypdf plus the parser on it; this is not the user's real PDF and not a browser/HTTP test.

Other fixtures cover different identifiers/dates, explicit seller/customer arrangements, IGST, currency/grouping variants, optional/invalid adjustments, conflicting values, missing fields, unrelated numbers, and supported table delimiters. No company name, identifier, GSTIN or amount is a parser special case.

### Verification and changed files

Backend command (run from backend with .venv Python):

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_invoice.py tests/test_invoice_layout.py tests/test_invoice_formats.py tests/test_analysis_contract.py tests/test_pdf_analysis.py::test_pdf_extraction_function_with_synthetic_invoice tests/test_api.py -k "not test_health and not test_empty_document_contract and not test_no_upload_or_processing_endpoint and not test_cors_allows_only_configured_origin" -q
```

57 passed, 4 deselected; one existing Starlette/anyio deprecation warning. This is a selected non-HTTP suite, not the entire backend suite. A full pytest run was attempted with a 35-second faulthandler deadline and exited while stalled at async TestClient execution; full HTTP tests remain blocked by the execution environment.

Frontend: npm test passed 12 tests; npm run lint passed without warnings. An initial overlapping typecheck/build run hit deleted generated types; a subsequent standalone npm run typecheck passed. npm run build failed with EPERM creating frontend/.next/server/app/documents. No source/config/dependency changes were made to mask that filesystem failure. No new frontend interactions are claimed.

Files changed for this update: backend/app/invoice_rules.py, backend/app/invoice.py, new backend/app/invoice_tables.py, new backend/tests/test_invoice_formats.py, README.md. The existing dashboard, frontend source, schemas and dependencies are preserved.
