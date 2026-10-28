"""Local SQLite metadata storage. Never persists uploaded PDF bytes."""
from contextlib import contextmanager
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
from .invoice import validate_invoice
from .invoice_rules import LABELS, GSTIN, money, parse_date, parse_number

class Conflict(ValueError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def normalize(value):
    return re.sub(r"\s+","",str(value or "")).casefold()

def effective(analysis,review):
    fields=json.loads(json.dumps(analysis["fields"]))
    for key,value in review.get("fields",{}).items():
        fields[key]={"value":value,"evidence":review["notes"],"method":"human_review_override"}
    return fields

class DocumentStore:
    def __init__(self,path=None):
        self.path=path

    @contextmanager
    def connect(self):
        path=Path(self.path or os.getenv("DOCULENS_DB_PATH",str(Path(__file__).resolve().parents[1]/"data"/"doculens.sqlite3")))
        path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(path,timeout=10)
        db.row_factory=sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY, content_hash TEXT NOT NULL UNIQUE, filename TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, version INTEGER NOT NULL,
          processing_status TEXT NOT NULL, review_status TEXT NOT NULL, analysis TEXT NOT NULL,
          review TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS review_events (
          id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
          created_at TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS documents_created ON documents(created_at);
        CREATE INDEX IF NOT EXISTS review_document ON review_events(document_id,id);
        CREATE TABLE IF NOT EXISTS reconciliations (
          id TEXT PRIMARY KEY, expected_id TEXT NOT NULL, observed_id TEXT NOT NULL,
          created_at TEXT NOT NULL, version INTEGER NOT NULL, payload TEXT NOT NULL);
        """)
        try:
            with db:
                yield db
        finally:
            db.close()

    def record(self,row):
        if row is None:
            raise KeyError("Document not found")
        record=dict(row)
        record["analysis"]=json.loads(record["analysis"])
        record["review"]=json.loads(record["review"])
        record["effective_fields"]=effective(record["analysis"],record["review"])
        record["review_validation"]=validate_invoice(record["effective_fields"],record["analysis"]["line_items"])
        return record

    def get(self,identifier):
        with self.connect() as db:
            return self.record(db.execute("SELECT * FROM documents WHERE id=?",(identifier,)).fetchone())

    def list(self):
        with self.connect() as db:
            return [self.record(row) for row in db.execute("SELECT * FROM documents ORDER BY created_at DESC,id")]

    def save(self,analysis,data,reprocess_version=None):
        digest=hashlib.sha256(data).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing=db.execute("SELECT * FROM documents WHERE content_hash=?",(digest,)).fetchone()
            if existing:
                if reprocess_version is None:
                    return self.record(existing)
                if existing["version"] != reprocess_version:
                    raise Conflict("Document changed; reload before explicit reprocessing.")
                db.execute("INSERT INTO review_events(document_id,created_at,version,payload) VALUES(?,?,?,?)",
                           (existing["id"],now(),existing["version"],json.dumps({"action":"reprocess","previous_analysis":json.loads(existing["analysis"]),"previous_review":json.loads(existing["review"])})))
                db.execute("UPDATE documents SET analysis=?,review=?,review_status='pending',processing_status=?,updated_at=?,version=version+1 WHERE id=?",
                           (json.dumps(analysis),json.dumps({"fields":{},"notes":""}),analysis["status"],now(),existing["id"]))
                identifier=existing["id"]
            else:
                if reprocess_version is not None:
                    raise Conflict("Cannot reprocess a document that has not been saved.")
                identifier="real-"+uuid.uuid4().hex
                stamp=now()
                db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (identifier,digest,analysis["filename"],stamp,stamp,1,analysis["status"],"pending",json.dumps(analysis),json.dumps({"fields":{},"notes":""})))
            return self.record(db.execute("SELECT * FROM documents WHERE id=?",(identifier,)).fetchone())

    def review_document(self,identifier,version,overrides,notes,status):
        if status not in ("pending","approved","rejected") or not 5 <= len(notes.strip()) <= 2000:
            raise ValueError("Choose a valid review status and provide a review note (5-2000 characters).")
        document=self.get(identifier)
        if document["version"] != version:
            raise Conflict("Document changed; reload before saving your review.")
        fields=document["analysis"]["fields"]
        cleaned={}
        for key,raw in overrides.items():
            if key not in fields and key not in ("quantity","unit_rate"):
                raise ValueError("Unsupported review field: "+key)
            if raw is None or raw.strip()=="":
                cleaned[key]=None;continue
            if len(raw)>250:
                raise ValueError("Review value is too long.")
            if key in ("shipping_amount","subtotal","cgst","sgst","igst","gst_total","grand_total","pre_round_total","round_off","unit_rate"):
                value=money(raw,signed=key=="round_off")
            elif key=="quantity":
                number=parse_number(raw);value=str(number) if number is not None else None
            elif key=="invoice_date":
                value=parse_date(raw)
            elif "gstin" in key:
                value=raw.upper() if re.fullmatch(GSTIN,raw.upper()) else None
            elif key=="invoice_number":
                value=raw.strip() if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_. -]{0,79}",raw.strip()) else None
            else:
                value=raw.strip()
            if value is None:
                raise ValueError("Invalid review value for "+key)
            cleaned[key]=value
        review={"fields":{**document["review"]["fields"],**cleaned},"notes":notes.strip()}
        proposed=effective(document["analysis"],review)
        validation=validate_invoice(proposed,document["analysis"]["line_items"])
        if status=="approved" and (validation["mismatches"] or any(proposed[k]["value"] is None for k in ("invoice_number","invoice_date","supplier_name","subtotal","grand_total"))):
            raise ValueError("Approval requires known key fields and no arithmetic mismatches. Unknown line checks still require explicit human review.")
        with self.connect() as db:
            cursor=db.execute("UPDATE documents SET review=?,review_status=?,version=version+1,updated_at=? WHERE id=? AND version=?",
                              (json.dumps(review),status,now(),identifier,version))
            if cursor.rowcount!=1:
                raise Conflict("Document changed; reload before saving your review.")
            db.execute("INSERT INTO review_events(document_id,created_at,version,payload) VALUES(?,?,?,?)",
                       (identifier,now(),version+1,json.dumps({"review":review,"status":status})))
        return self.get(identifier)

    def duplicates(self,identifier):
        source=self.get(identifier)
        fields=source["effective_fields"]
        number=fields.get("invoice_number",{}).get("value")
        supplier=fields.get("supplier_gstin",{}).get("value") or fields.get("supplier_name",{}).get("value")
        if not number or not supplier:
            return []
        results=[]
        for other in self.list():
            if other["id"]==identifier:
                continue
            candidate=other["effective_fields"]
            other_supplier=candidate.get("supplier_gstin",{}).get("value") or candidate.get("supplier_name",{}).get("value")
            if normalize(candidate.get("invoice_number",{}).get("value"))==normalize(number) and normalize(other_supplier)==normalize(supplier):
                results.append({"id":other["id"],"filename":other["filename"],"reason":"Same normalized invoice identifier and supplier identity; candidate requires review.","evidence":{"invoice_number":fields["invoice_number"],"supplier":supplier}})
        return results

    def history(self,identifier):
        self.get(identifier)
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT created_at,version,payload FROM review_events WHERE document_id=? ORDER BY id",(identifier,))]
