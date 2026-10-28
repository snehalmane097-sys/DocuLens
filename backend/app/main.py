import importlib.util
import os
import sqlite3
from urllib.parse import urlsplit
from collections import Counter
from fastapi import FastAPI, APIRouter, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .schemas import DocumentList, Health, InvoiceAnalysis, ReviewRequest, ReconcileRequest, ReportReviewRequest
from .storage import DocumentStore, Conflict
from .reconciliation import create_report, get_report, review_report


def cors_origins():
    raw=os.getenv("CORS_ORIGINS","http://localhost:3000,http://127.0.0.1:3000")
    origins=[]
    for value in raw.split(","):
        origin=value.strip()
        if not origin:
            continue
        parsed=urlsplit(origin)
        if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment or "*" in origin:
            raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths or wildcards")
        _=parsed.port
        origins.append(origin)
    return origins


def create_app(database_path=None):
    app=FastAPI(title="DocuLens AI API",version="0.4.0",description="Local PDF extraction, SQLite history, human review and deterministic reconciliation. Optional local OCR; no cloud.")
    store=DocumentStore(database_path)
    origins=cors_origins()
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Accept","Content-Type"])
    @app.middleware("http")
    async def local_write_origin(request,call_next):
        origin=request.headers.get("origin")
        if request.method=="POST" and origin and origin not in origins:
            return JSONResponse({"detail":"Origin is not allowed for local changes."},status_code=403)
        return await call_next(request)
    @app.exception_handler(KeyError)
    async def missing(request,exc):
        return JSONResponse({"detail":"Document or report not found."},status_code=404)
    @app.exception_handler(Conflict)
    async def conflict(request,exc):
        return JSONResponse({"detail":str(exc)},status_code=409)
    @app.exception_handler(ValueError)
    async def invalid(request,exc):
        return JSONResponse({"detail":str(exc)},status_code=422)
    @app.exception_handler(OSError)
    @app.exception_handler(sqlite3.Error)
    async def database_error(request,exc):
        return JSONResponse({"detail":"Local database is unavailable. Check its path and permissions."},status_code=503)
    router=APIRouter(prefix="/api")

    @router.get("/health",response_model=Health,tags=["health"])
    def health():
        return Health(phase=4,processing_available=all(importlib.util.find_spec(n) is not None for n in ("pypdf","python_multipart")))

    @router.get("/ocr/status",tags=["health"])
    def ocr_status():
        from .ocr import executable
        return {"engine":"tesseract", "engine_found":bool(executable('tesseract')),
                "pdf_renderer_found":bool(executable('pdftoppm')), "language":"eng",
                "handwriting_verified":False, "message":"Executable discovery only. A real upload verifies language data and operation. No external upload."}

    @router.get("/documents",response_model=DocumentList,tags=["documents"])
    def list_documents(offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=500)):
        rows=store.list()
        return DocumentList(mode="persistent",items=rows[offset:offset+limit],total=len(rows),processing_available=True,message="Local persisted records only; fictional frontend fixtures are excluded.")

    @router.get("/documents/{identifier}",tags=["documents"])
    def get_document(identifier:str):
        record=store.get(identifier)
        record["duplicate_candidates"]=store.duplicates(identifier)
        return record

    @router.get("/documents/{identifier}/history",tags=["documents"])
    def history(identifier:str):
        return {"items":store.history(identifier)}

    @router.post("/documents/{identifier}/review",tags=["documents"])
    def save_review(identifier:str,body:ReviewRequest):
        return store.review_document(identifier,body.version,body.fields,body.notes,body.status)

    @router.post("/documents/analyze",response_model=InvoiceAnalysis,tags=["documents"],openapi_extra={"requestBody":{"required":True,"content":{"multipart/form-data":{"schema":{"type":"object","required":["file"],"properties":{"file":{"type":"string","format":"binary"}}}}}}})
    async def analyze_document(request:Request,reprocess_version:int | None=Query(None,ge=1)):
        try:
            from .pdf_analysis import receive_pdf,analyze_pdf
        except ImportError:
            raise HTTPException(503,"PDF analysis dependencies are unavailable. Install backend requirements.") from None
        filename,data=await receive_pdf(request)
        analysis=await run_in_threadpool(analyze_pdf,filename,data)
        document=await run_in_threadpool(store.save,analysis,data,reprocess_version)
        duplicates=await run_in_threadpool(store.duplicates,document["id"])
        return {**document["analysis"],"stored":True,"document_id":document["id"],"version":document["version"],"review_status":document["review_status"],"duplicate_candidates":duplicates}

    @router.get("/reconciliations",tags=["reconciliation"])
    def list_reports():
        import json
        with store.connect() as db:
            rows=db.execute("SELECT payload FROM reconciliations ORDER BY created_at DESC LIMIT 100").fetchall()
        return {"items":[{k:v for k,v in json.loads(row["payload"]).items() if k!="rows"} for row in rows]}

    @router.post("/documents/{identifier}/reprocess",tags=["documents"])
    async def reprocess_document(identifier:str,request:Request,version:int=Query(...,ge=1)):
        import hashlib
        from .pdf_analysis import receive_pdf,analyze_pdf
        document=await run_in_threadpool(store.get,identifier)
        filename,data=await receive_pdf(request)
        if hashlib.sha256(data).hexdigest()!=document["content_hash"]:
            raise HTTPException(409,"Reprocessing requires the original document bytes for this document.")
        analysis=await run_in_threadpool(analyze_pdf,filename,data)
        return await run_in_threadpool(store.save,analysis,data,version)

    @router.post("/reconciliations",tags=["reconciliation"])
    def reconcile(body:ReconcileRequest):
        return create_report(store,body.expected_id,body.observed_id)

    @router.get("/reconciliations/{identifier}",tags=["reconciliation"])
    def report(identifier:str):
        return get_report(store,identifier)

    @router.post("/reconciliations/{identifier}/review",tags=["reconciliation"])
    def report_review(identifier:str,body:ReportReviewRequest):
        return review_report(store,identifier,body.version,body.decisions)

    @router.get("/analytics",tags=["analytics"])
    def analytics():
        rows=store.list()
        days=Counter(r["created_at"][:10] for r in rows)
        review=Counter(r["review_status"] for r in rows)
        findings=Counter(c["name"] for r in rows for c in r["review_validation"]["checks"] if c["status"]=="mismatch")
        return {"total":len(rows),"review_status":dict(review),"needs_ocr":sum(r["processing_status"]=="needs_ocr" for r in rows),
                "mismatches":sum(r["review_validation"]["mismatches"] for r in rows),
                "unknown_checks":sum(r["review_validation"]["unknown"] for r in rows),
                "volume":[{"date":day,"count":days[day]} for day in sorted(days)],"discrepancies":dict(findings),"source":"sqlite"}
    app.include_router(router)
    return app

app=create_app()
