"""Synthetic PDFs only: manually generated object streams/xref, no personal data."""
from io import BytesIO
import pytest
pytest.importorskip("pypdf", reason="Install backend requirements to run PDF integration tests")
pytest.importorskip("python_multipart", reason="Install backend requirements to run multipart integration tests")
from pypdf import PdfReader, PdfWriter
from fastapi.testclient import TestClient
from app.main import create_app
from app import pdf_analysis


def make_pdf(lines=None):
    lines = lines or []
    escaped = [line.replace("\\","\\\\").replace("(","\\(").replace(")","\\)") for line in lines]
    stream = ("BT /F1 10 Tf 50 760 Td 14 TL " + " ".join("("+line+") Tj T*" for line in escaped) + " ET").encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects,1):
        offsets.append(len(data)); data += str(index).encode()+b" 0 obj\n"+obj+b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    data += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"+str(xref).encode()+b"\n%%EOF\n"
    return data


@pytest.fixture
def client():
    return TestClient(create_app())


def send(client, data, name="invoice.pdf", media="application/pdf"):
    return client.post("/api/documents/analyze", files={"file":(name,data,media)})


def test_readable_pdf(client):
    response = send(client, make_pdf(["Supplier: Synthetic Supplies","Invoice No: SYN-1","Invoice Date: 2026-10-28","Description | Qty | Rate | Amount","Paper | 2 | 100 | 200","Subtotal: 200","IGST: 36","GST Total: 36","Grand Total: 236"]))
    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["invoice_number"]["value"] == "SYN-1"
    assert body["fields"]["grand_total"]["value"] == "236.00"
    assert body["validation"]["mismatches"] == 0
    assert body["status"] == "analyzed"
    assert body["stored"] is True


def test_missing_fields_and_image_only_pdf(client):
    missing = send(client, make_pdf(["This synthetic document deliberately has no supported invoice labels."]))
    assert missing.status_code == 200
    assert missing.json()["fields"]["grand_total"]["value"] is None
    assert missing.json()["validation"]["unknown"] > 0
    empty = send(client, make_pdf())
    assert empty.status_code == 200
    assert empty.json()["status"] == "needs_ocr"
    assert any("OCR" in warning for warning in empty.json()["warnings"])


def test_encrypted_and_malformed(client):
    writer = PdfWriter()
    writer.append(PdfReader(BytesIO(make_pdf(["Test invoice"]))))
    writer.encrypt("secret")
    buffer = BytesIO();writer.write(buffer)
    response = send(client, buffer.getvalue())
    assert response.status_code == 422
    assert "Encrypted" in response.json()["detail"]
    assert send(client,b"%PDF-malformed").status_code == 422


def test_extension_mime_signature_and_multiple_files(client):
    assert send(client,make_pdf(),"invoice.exe").status_code == 415
    assert send(client,make_pdf(),media="image/png").status_code == 415
    assert send(client,b"not a pdf").status_code == 415
    assert send(client,make_pdf(),"../invoice.pdf").status_code == 415
    response = client.post("/api/documents/analyze", files=[("file",("a.pdf",make_pdf(),"application/pdf")),("file",("b.pdf",make_pdf(),"application/pdf"))])
    assert response.status_code == 422


def test_streamed_size_and_page_limit(client,monkeypatch):
    monkeypatch.setattr(pdf_analysis,"MAX_FILE_BYTES",50)
    assert send(client,make_pdf()).status_code == 413
    monkeypatch.setattr(pdf_analysis,"MAX_FILE_BYTES",10*1024*1024)
    monkeypatch.setattr(pdf_analysis,"MAX_PAGES",0)
    assert send(client,make_pdf()).status_code == 422


def test_incomplete_multipart_and_missing_file(client):
    assert client.post("/api/documents/analyze",content=b"broken",headers={"Content-Type":"multipart/form-data; boundary=x"}).status_code in (400,422)
    assert client.post("/api/documents/analyze",json={}).status_code == 415


def test_post_preflight(client):
    response=client.options("/api/documents/analyze",headers={"Origin":"http://localhost:3000","Access-Control-Request-Method":"POST"})
    assert response.status_code == 200


def test_uvicorn_export_registers_once_and_accepts_pdf():
    """Exercise the actual app.main:app export, not only a fresh app factory."""
    from app.main import app
    matches = [route for route in app.routes
               if route.path == "/api/documents/analyze" and "POST" in route.methods]
    assert len(matches) == 1
    with TestClient(app) as client:
        response = client.post(
            "/api/documents/analyze",
            files={"file": ("registration-test.pdf", make_pdf([
                "Supplier: Synthetic Route Test",
                "Invoice No: ROUTE-001",
                "Invoice Date: 2026-10-28",
                "Description | Qty | Rate | Amount",
                "Test service | 2 | 100 | 200",
                "Subtotal: 200", "IGST: 36", "GST Total: 36",
                "Grand Total: 236",
            ]), "application/pdf")},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "analyzed"
    assert body["fields"]["invoice_number"]["value"] == "ROUTE-001"
    assert body["fields"]["grand_total"]["value"] == "236.00"
    assert body["line_items"][0]["quantity"] == "2"
    assert body["validation"]["mismatches"] == 0
    assert body["stored"] is True


def test_pdf_extraction_function_with_synthetic_invoice():
    # Synchronous extraction test also runs where Windows prevents asyncio socketpair.
    result = pdf_analysis.analyze_pdf("synthetic.pdf", make_pdf([
        "Supplier: Synthetic Supplies", "Invoice No: DIRECT-1",
        "Invoice Date: 2026-10-28", "Subtotal: 100",
        "IGST: 18", "GST Total: 18", "Grand Total: 118",
    ]))
    assert result["status"] == "analyzed"
    assert result["fields"]["invoice_number"]["value"] == "DIRECT-1"
    assert result["fields"]["grand_total"]["value"] == "118.00"
    assert result["validation"]["mismatches"] == 0
