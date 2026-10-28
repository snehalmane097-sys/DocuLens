"""Deterministic comparison of reviewed values. Extraction is never overwritten."""
import json
import uuid
from decimal import Decimal
from .storage import Conflict, normalize, now

NUMERIC={"quantity","unit_rate","shipping_amount","subtotal","cgst","sgst","igst","gst_total","round_off","grand_total"}

def compare_records(expected,observed):
    rows=[]
    keys=["invoice_number","supplier_name","supplier_gstin","invoice_date","quantity","unit_rate","shipping_amount","subtotal","cgst","sgst","igst","gst_total","round_off","grand_total"]
    for key in keys:
        a=expected["effective_fields"].get(key,{})
        b=observed["effective_fields"].get(key,{})
        av,bv=a.get("value"),b.get("value")
        status="unknown"
        if av is not None and bv is not None:
            equal=(Decimal(av)==Decimal(bv)) if key=="quantity" else (abs(Decimal(av)-Decimal(bv))<=Decimal("0.02")) if key in NUMERIC else normalize(av)==normalize(bv)
            status="matched" if equal else "mismatch"
        rows.append({"id":str(len(rows)),"field":key,"expected":av,"observed":bv,"expected_evidence":a.get("evidence"),"observed_evidence":b.get("evidence"),"status":status,"review_status":"not_required" if status=="matched" else "pending","review_note":""})
    # Compare only unambiguous, same-description item identities; never silently align by row number.
    left=expected["analysis"]["line_items"];right=observed["analysis"]["line_items"]
    names=sorted(set(normalize(i["description"]) for i in left+right))
    for name in names:
        a=[i for i in left if normalize(i["description"])==name]
        b=[i for i in right if normalize(i["description"])==name]
        for key in ("quantity","unit_rate","line_total","tax_amount","tax_rate"):
            av=a[0].get(key) if len(a)==1 else None
            bv=b[0].get(key) if len(b)==1 else None
            status="unknown" if av is None or bv is None else "matched" if abs(Decimal(av)-Decimal(bv)) <= (Decimal(0) if key in ("quantity","tax_rate") else Decimal("0.02")) else "mismatch"
            rows.append({"id":str(len(rows)),"field":"item."+name+"."+key,"expected":av,"observed":bv,"expected_evidence":a[0]["evidence"] if len(a)==1 else None,"observed_evidence":b[0]["evidence"] if len(b)==1 else None,"status":status,"review_status":"not_required" if status=="matched" else "pending","review_note":""})
    return rows

def create_report(store,expected_id,observed_id):
    if expected_id==observed_id:
        raise ValueError("Choose two different persisted documents.")
    expected,observed=store.get(expected_id),store.get(observed_id)
    report={"id":"rec-"+uuid.uuid4().hex,"expected_id":expected_id,"observed_id":observed_id,"expected_version":expected["version"],"observed_version":observed["version"],"created_at":now(),"version":1,"status":"pending","rows":compare_records(expected,observed)}
    report["mismatches"]=sum(r["status"]=="mismatch" for r in report["rows"])
    report["unknown"]=sum(r["status"]=="unknown" for r in report["rows"])
    if all(r["status"]=="matched" for r in report["rows"]):
        report["status"]="matched"
    with store.connect() as db:
        db.execute("INSERT INTO reconciliations VALUES(?,?,?,?,?,?)",(report["id"],expected_id,observed_id,report["created_at"],1,json.dumps(report)))
    return report

def get_report(store,identifier):
    with store.connect() as db:
        row=db.execute("SELECT payload FROM reconciliations WHERE id=?",(identifier,)).fetchone()
    if not row:
        raise KeyError("Reconciliation not found")
    report=json.loads(row["payload"])
    report["stale"]=(store.get(report["expected_id"])["version"]!=report["expected_version"] or store.get(report["observed_id"])["version"]!=report["observed_version"])
    return report

def review_report(store,identifier,version,decisions):
    report=get_report(store,identifier)
    if report["stale"]:
        raise Conflict("Source documents changed. Create a new reconciliation.")
    valid_ids={row["id"] for row in report["rows"] if row["status"]!="matched"}
    if not set(decisions).issubset(valid_ids) or any(not 5<=len(note.strip())<=2000 for note in decisions.values()):
        raise ValueError("Review only discrepancy IDs and provide a note of 5-2000 characters.")
    for row in report["rows"]:
        if row["id"] in decisions:
            row["review_status"]="reviewed";row["review_note"]=decisions[row["id"]].strip()
    report["version"]=version+1
    report["status"]="reviewed" if all(r["review_status"]!="pending" for r in report["rows"]) else "pending"
    with store.connect() as db:
        cursor=db.execute("UPDATE reconciliations SET payload=?,version=? WHERE id=? AND version=?",(json.dumps(report),version+1,identifier,version))
        if cursor.rowcount!=1:
            raise Conflict("Report changed; reload before saving.")
    return report
