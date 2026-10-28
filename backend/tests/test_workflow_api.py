from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from test_pdf_analysis import make_pdf

def pdf(total="118"):
    return make_pdf(["Supplier: Synthetic Acceptance", "Invoice No: ACCEPT-1", "Invoice Date: 2026-10-28", "Description | Qty | Rate | Amount", "Part | 2 | 50 | 100", "Subtotal: 100", "IGST: 18", "GST Total: 18", "Grand Total: "+total])

def test_complete_upload_review_reconciliation_restart(tmp_path):
    database=tmp_path/"acceptance.sqlite3"
    with TestClient(create_app(database)) as client:
        assert client.get("/api/health").status_code==200
        def upload(data):
            r=client.post("/api/documents/analyze",files={"file":("acceptance.pdf",data,"application/pdf")})
            assert r.status_code==200,r.text
            return r.json()
        a=upload(pdf()); b=upload(pdf("119"))
        assert a["stored"] and a["fields"]["subtotal"]["evidence"]
        assert upload(pdf())["document_id"]==a["document_id"]
        assert client.get("/api/documents").json()["total"]==2
        detail=client.get("/api/documents/"+a["document_id"]).json()
        assert detail["duplicate_candidates"][0]["id"]==b["document_id"]
        payload={"version":1,"fields":{},"notes":"Verified synthetic invoice evidence","status":"approved"}
        r=client.post("/api/documents/"+a["document_id"]+"/review",json=payload)
        assert r.status_code==200,r.text
        assert r.json()["version"]==2
        assert client.post("/api/documents/"+a["document_id"]+"/review",json=payload).status_code==409
        r=client.post("/api/reconciliations",json={"expected_id":a["document_id"],"observed_id":b["document_id"]})
        assert r.status_code==200,r.text
        report=r.json(); assert report["mismatches"]==1
        notes={row["id"]:"Source discrepancy verified" for row in report["rows"] if row["status"]!="matched"}
        r=client.post("/api/reconciliations/"+report["id"]+"/review",json={"version":1,"decisions":notes})
        assert r.status_code==200 and r.json()["status"]=="reviewed"
        assert client.get("/api/analytics").json()["total"]==2
        assert client.get("/api/reconciliations").json()["items"][0]["id"]==report["id"]
        wrong=client.post("/api/documents/"+a["document_id"]+"/reprocess?version=2",files={"file":("wrong.pdf",pdf("999"),"application/pdf")})
        assert wrong.status_code==409
        processed=client.post("/api/documents/"+a["document_id"]+"/reprocess?version=2",files={"file":("original.pdf",pdf(),"application/pdf")})
        assert processed.status_code==200,processed.text
        assert processed.json()["version"]==3 and processed.json()["review_status"]=="pending"
        assert client.get("/api/reconciliations/"+report["id"]).json()["stale"]
        assert client.get("/api/documents").json()["total"]==2
        assert client.post("/api/documents/"+a["document_id"]+"/review",json=payload,headers={"Origin":"https://untrusted.example"}).status_code==403
    with TestClient(create_app(database)) as restarted:
        assert restarted.get("/api/documents").json()["total"]==2
        assert restarted.get("/api/documents/"+a["document_id"]).json()["review_status"]=="pending"
        assert restarted.get("/api/reconciliations/"+report["id"]).json()["status"]=="reviewed"

def test_actual_pdf_http_response(tmp_path):
    path=Path("C:/ACCUTECH BILLS/AE262709004.pdf")
    if not path.exists():
        import pytest
        pytest.skip("Private invoice is not available")
    with TestClient(create_app(tmp_path/"real.sqlite3")) as client:
        r=client.post("/api/documents/analyze",files={"file":(path.name,path.read_bytes(),"application/pdf")})
        assert r.status_code==200,r.text
        body=r.json()
        assert body["stored"] and body["fields"]["grand_total"]["value"]=="15505.00"
        assert body["fields"]["cgst"]["value"]=="1182.60"
        assert body["validation"]["mismatches"]==0
        assert client.get("/api/documents/"+body["document_id"]).json()["analysis"]["fields"]==body["fields"]
