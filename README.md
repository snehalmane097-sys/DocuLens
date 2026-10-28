# DocuLens AI

DocuLens is a local document-understanding application built with Next.js, TypeScript, Tailwind CSS, FastAPI and SQLite. It extracts evidence-backed fields from digitally generated PDF invoices, validates arithmetic, saves analysis history, supports versioned human review, and compares saved documents deterministically. Fictional demonstrations remain available in explicitly labelled separate views.

## Windows setup

Use Windows 10/11, VS Code, Node.js 22 LTS with npm, and Python 3.12. Keep the existing frontend lockfile. No PostgreSQL, cloud account, OCR engine or external AI key is required.

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
| POST /api/documents/analyze | Multipart **file** containing one PDF; optional explicit reprocess_version query |
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

Upload restrictions: one PDF, 10 MiB maximum, extension/content-type/signature checks, 30 pages and bounded extracted text. Images can be selected for a local preview, but are not processed. Errors: 400 malformed multipart; 413 oversized; 415 wrong file type/signature; 422 encrypted/malformed/unsupported PDF or invalid review; 404 missing record; 409 stale revision/wrong reprocessing file; 503 unavailable dependency/storage.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/documents/analyze -F "file=@C:\path\invoice.pdf;type=application/pdf"
```

## Extraction, validation and limits

Label/party/table rules are independent from validation and reconciliation. They support common invoice-number/date aliases, bounded wrapped labels, Indian/international comma grouping, CGST/SGST or IGST, tax total, signed round-off, explicit shipping, final payable labels, and single-row vertical tax summaries. Party-position associations and all GSTIN candidates remain reviewable. Unknown/conflicting fields are never filled from expected regression values.

For Type0 Identity-H financial fonts lacking ToUnicode, the extractor can recover unambiguous financial characters from the embedded TrueType Unicode cmap when CID-to-glyph mapping is identity. It never guesses glyph shifts or edits the uploaded PDF. Unsupported font formats/mappings remain unknown. No OCR, ML inference or external AI is used.

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

OCR for scanned documents, broader table/font coverage, currency-aware reconciliation, richer line-item review, evaluation on held-out invoices, authenticated multi-user deployment and a production storage/retention strategy. None is represented as implemented.

Earlier Phase 1/2A notes and checkpoints are preserved in README_HISTORY.md; this README describes the integrated current implementation.
