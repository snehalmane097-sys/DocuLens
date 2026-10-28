# Frontend redesign acceptance — 28 October 2026

## Scope and preservation

Continued the existing working tree without reset/revert. Viewed the supplied eight-second finance dashboard video, including its overview, cards and directory compositions. Adapted its cream sidebar, slim search header, white rounded surfaces, restrained typography, sage accents and main-chart/secondary-summary proportions to invoice intelligence. No payroll functions, mock live metrics, new framework, dependencies or lockfile changes were introduced. Backend/OCR changes already present in the working tree were preserved.

## Files changed for the redesign

- frontend/src/app/globals.css
- frontend/src/app/layout.tsx
- frontend/src/app/documents/page.tsx
- frontend/src/app/upload/page.tsx
- frontend/src/app/analytics/page.tsx
- frontend/src/app/reconciliation/page.tsx
- frontend/src/components/shell.tsx
- frontend/src/components/real-workspace.tsx
- frontend/src/components/upload-preview.tsx
- frontend/src/components/analysis-results.tsx
- frontend/src/components/saved-document.tsx
- frontend/src/components/real-reconciliation.tsx
- frontend/src/components/charts.tsx
- frontend/src/components/ui.tsx
- frontend/src/lib/workspace-metrics.mjs (new)
- frontend/tests/workspace-metrics.test.mjs (new)
- README.md
- FRONTEND_REDESIGN_RESULTS.md
- acceptance/redesign-upload-desktop.png
- acceptance/redesign-upload-mobile.png

The overview route and document-details route inherit the redesigned shared components. Existing OCR API types/upload adapter/tests and backend files were earlier work, not replaced by the redesign.

## Implemented behavior

Shared responsive shell and working global invoice search; four essential dashboard metrics, real activity and recent invoices; searchable/filterable saved documents; minimal upload flow with real processing/error/result states; summary-first saved details with expandable evidence, line items, review, original extraction and archived reprocessing history; reconciliation findings with prominent discrepancies, expandable source evidence/notes, saved history and unchanged stale-report checks; real analytics and extraction coverage.

Financial totals are aggregated only when every included known amount has an explicit shared ISO currency. Current stored records lack that currency evidence, so the combined value is visibly unavailable. Extracted unknowns remain unknown. Material discrepancies remain visible outside collapsed details. Fonts use locally available Inter/Manrope when present, then system fallbacks; no font download or new package.

## Browser acceptance

Checked all six main views at 1440x1000 desktop and 390x844 mobile: overview, documents, upload, saved document details, reconciliation and analytics. Root scroll width did not exceed viewport after fixing table containment; wide tables remain internally scrollable. Mobile drawer opens, Escape closes it, and focus returns to the menu button. Desktop analytics and mobile saved summary were inspected populated, not only loading placeholders. Temporary viewport override was reset.

Real global search for /004 opened its saved record, showing 15,505.00 and revision 3. Review action opens and focuses the manual form; no existing invoice review decision was changed. Real /004-to-/006 comparison created report rec-bdb80a99e23a4874917ec20d38e9ac61 with six discrepancies and six unknowns. One explicit UI acceptance note was saved to that new report; other findings remain pending and no invoice was approved. Existing upload /004 idempotency and real results were exercised during this continuing implementation. OCR engine availability/handwriting accuracy are not newly certified by a frontend redesign.

## Executed verification

From C:\Doculens\frontend:

- npm test — 19 passed, 0 failed, exit 0.
- npm run typecheck — passed, exit 0.
- npm run lint — passed, exit 0.
- npm run build — final result recorded below.

From C:\Doculens:

- git diff --check — passed, exit 0 (only Git LF/CRLF notices).

Production build attempts encountered Windows EPERM while creating generated .next route/chunk directories. Targeted Node fs.mkdirSync probes succeeded; retries did not change dependencies, source permissions or remove existing work. Backend tests were not rerun for this frontend-only redesign; the earlier OCR checkpoint is documented separately.

Build-directory probe commands (from frontend; generated output only):

```powershell
node -e "const fs=require('fs'); for(const base of ['.next/server/app','.next/static/chunks/app']) for(const route of ['documents','documents/[id]','reconciliation','analytics','upload','review','review/[id]']) fs.mkdirSync(base+'/'+route,{recursive:true});"
node -e "const fs=require('fs'); for(const route of ['analytics','upload','reconciliation','_not-found','_global-error']) fs.mkdirSync('.next/server/app/'+route+'.segments/'+route,{recursive:true}); fs.mkdirSync('.next/server/app/index.segments',{recursive:true});"
npm run build
```

The repeated EPERM locations included server/app/documents, static/chunks/app/documents/[id], and server/app/analytics.segments/analytics. Compilation and TypeScript completed on the latter attempt before prerender output creation failed. No broad cleanup or privilege escalation was used.

An additional retry failed creating .next/types/app/documents/[id]. The final directory probe also covered .next/types/app for all existing routes, followed by npm run build. All probes used the current unprivileged process and succeeded.

## Final build outcome

Final npm run build completed with **exit 1**: Windows EPERM creating C:\Doculens\frontend\.next\server\app\reconciliation. This persisted after successful unprivileged directory probes. Production build acceptance is therefore **blocked**, not passed. The final source still has 19 passing frontend tests, passing standalone typecheck/lint and verified browser routes. No full acceptance claim is made. The working application and all changes are preserved; resolving the Windows output-directory access issue and completing a clean build remains outstanding.
