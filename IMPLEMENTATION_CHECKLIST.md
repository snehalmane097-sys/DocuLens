# Integrated implementation checklist

Scope follows the user's current Phase 2/3/4 acceptance criteria; older README phase roadmaps are historical.

- [ ] Repair missing PDF Unicode maps using embedded font evidence, with failure-safe unknowns.
- [ ] Add actual PDF/raw-text regressions, invoice heading/sign labels, vertical tax summaries.
- [ ] Add SQLite document persistence, content-hash idempotency, history/retrieval.
- [ ] Preserve immutable extraction; add versioned human review and recalculated review validation.
- [ ] Add deterministic reconciliation, duplicate candidates, evidence and discrepancy review.
- [ ] Integrate real history/detail/review/reconciliation/analytics; explicitly separate demos.
- [ ] Run parser/storage/reconciliation/API tests and frontend tests/typecheck/lint/build.
- [ ] Exercise upload-to-save-to-review-to-reconcile acceptance where execution permits.
- [ ] Document exact outcomes and blockers; no unit-only end-to-end success claims.

Storage: SQLite (stdlib), configured by DOCULENS_DB_PATH, local backend/data by default.
No database/cloud service or new package is required. PDFs are processed in memory; metadata,
extracted text/fields and reviews are persisted locally. Original PDF bytes are not stored.
