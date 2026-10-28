# Outstanding acceptance results — 28 October 2026

## Scope and preservation

`git status --short` was empty on entry; `git rev-parse --show-toplevel` returned C:/Doculens. Existing code, styling, dependencies and lockfiles were preserved. Only acceptance documentation and a local proof screenshot were added/updated during this continuation. The live database changed only through the supported browser reprocessing action.

## Commands executed

From C:/Doculens/frontend:

```powershell
npm run build
npm test
npm run typecheck
npm run lint
```

Results: build exit 0, all six application route patterns generated; 16 frontend tests passed; typecheck exit 0; lint exit 0. Build was completed before standalone typecheck. No generated-folder EPERM occurred.

From C:/Doculens/backend:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -c "import app.main; print('backend import passed')"
.\.venv\Scripts\python.exe -c "import faulthandler; faulthandler.dump_traceback_later(30,exit=True); import pytest; raise SystemExit(pytest.main(['-q','--basetemp=.test-tmp/acceptance-resume','-o','faulthandler_timeout=15']))"
.\.venv\Scripts\python.exe -c "import faulthandler; faulthandler.dump_traceback_later(10,exit=True); import asyncio; loop=asyncio.new_event_loop(); print(type(loop).__name__); loop.run_until_complete(asyncio.sleep(0)); loop.close(); print('asyncio initialized and ran successfully')"
```

Results: compile/import exit 0; **82 tests passed, 0 skipped, 0 failed in 6.91s**, exit 0; asyncio probe printed ProactorEventLoop and completed, exit 0. The warning is Starlette's use of the deprecated anyio.abc.BlockingPortal alias. No dependency updates were attempted.

The faulthandler deadlines are diagnostic only; neither fired. Earlier evidence showed socketpair().accept() blocking during event-loop initialization, independently of FastAPI. It does not reproduce now. The exact underlying Windows policy/process condition from the previous disconnected context cannot be proven retrospectively.

## Actual /006 source and supported reprocessing

Source: C:/ACCUTECH BILLS/AE262709006.pdf.
SHA-256: de8672094cc202e99cce5231dc8d0dc59bb97f9a40f69e8363d4688add9ac343.
Saved ID: real-8cf556d6da1f49148f462dbe541a7280.

Before mutation, direct analyze_pdf extraction and read-only DocumentStore retrieval confirmed that the source hash matched revision 1. The source yielded a shipping field; the older saved analysis did not contain that field. Its payable discrepancy was 800.00. Its subtotal was 53767.50 throughout.

Browser action: open saved details, choose the matching original in Explicit reprocessing, click Reprocess and reset review. This invokes POST /api/documents/{id}/reprocess?version=1 with multipart file. The page then displayed revision 2, shipping 800.00 with source evidence, and a passing stated-tax payable check. No direct SQL updates were used.

Read-only post-action verification through DocumentStore asserted revision=2, one matching content hash, shipping value=800.00, zero arithmetic mismatches, and an archived previous_analysis without shipping in the latest review event. A separate Decimal calculation asserted:

53767.50 + 9822.16 + 800.00 + 0.34 = 64390.00.

| Extracted field | Value | Source evidence |
| --- | ---: | --- |
| Subtotal | 53767.50 | Sub Total / rupee 53,767.50 |
| Tax total | 9822.16 | Tax Amount (+) / rupee 9,822.16 |
| Shipping | 800.00 | Shipping Amount (+) / rupee 800.00 |
| Round-off | 0.34 | Round Off (+) / rupee 0.34 |
| Final total | 64390.00 | TOTAL AMOUNT / rupee 64,390.00 |

CGST/SGST component totals remain unsupported for this multi-row vertical summary; no zeroes or inferred components were inserted. Document quantity/rate from the first row are no longer misrepresented as document-wide values. Line items, generic GSTIN and pre-round total remain unknown where evidence is insufficient. The record stays pending review. Previously saved comparisons referencing revision 1 become stale by design; create a fresh comparison to use revision 2.

## Responsive checks

Browser viewport capability set desktop 1440x900 and mobile 390x844, then reset. Desktop details showed side-by-side evidence and review panels. Mobile details stacked; the menu opened and navigating to history closed it. Mobile populated history and overview showed three persisted records and zero arithmetic discrepancies. Upload, analytics and reconciliation route shells also rendered.

Mobile DOM measurement: innerWidth=390, document scrollWidth=375; the overview's table container clientWidth=341 and scrollWidth=775, providing local overflow without widening the page. No redesign was required. These were representative spot checks, not every interaction at every viewport. Browser state was observed via accessibility snapshots and screenshots. Proof screenshot: acceptance/006-revision2.png (private invoice information; do not publish).

## Acceptance status

All nine requested continuation tasks were completed: inspection, source/state verification, supported reprocessing/archive verification, arithmetic, production build, full-suite investigation, responsive spot checks, README update and test reruns. No current execution blocker remains. Human-review requirements and extraction limits remain product limitations, not fabricated successes.
