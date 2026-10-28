"""Bounded multipart reception in memory; no UploadFile disk spooling."""
from io import BytesIO
from fastapi import HTTPException, Request
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from pypdf import PdfReader
from .invoice import parse_invoice, validate_invoice
from .invoice_rules import parse_fields
from .pdf_fonts import recover_financial_fonts

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 65536
MAX_PAGES = 30
MAX_TEXT = 200000


async def receive_pdf(request: Request):
    kind, options = parse_options_header(request.headers.get("content-type", ""))
    boundary = options.get(b"boundary")
    if kind != b"multipart/form-data" or not boundary or len(boundary) > 200:
        raise HTTPException(415, "Use multipart/form-data with one PDF file field named file.")
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Request exceeds the 10 MiB PDF limit plus multipart overhead.")
        except ValueError:
            raise HTTPException(400, "Invalid Content-Length.")
    data = bytearray()
    headers = {}
    header_name = bytearray()
    header_value = bytearray()
    part_count = 0
    ended = False
    filename = ""
    media_type = ""
    header_size = 0
    def part_begin():
        nonlocal part_count
        part_count += 1
        if part_count > 1:
            raise HTTPException(422, "Send exactly one file and no extra fields.")
    def header_field(chunk, start, end):
        if header_size + len(header_name) + len(header_value) + end-start > 8192:
            raise HTTPException(413, "Multipart headers too large.")
        header_name.extend(chunk[start:end])
    def header_data(chunk, start, end):
        if header_size + len(header_name) + len(header_value) + end-start > 8192:
            raise HTTPException(413, "Multipart headers too large.")
        header_value.extend(chunk[start:end])
    def header_end():
        nonlocal header_size
        header_size += len(header_name) + len(header_value)
        if header_size > 8192:
            raise HTTPException(413, "Multipart headers too large.")
        headers[bytes(header_name).lower()] = bytes(header_value)
        header_name.clear()
        header_value.clear()
    def headers_done():
        nonlocal filename, media_type
        disposition, params = parse_options_header(headers.get(b"content-disposition", b""))
        if disposition != b"form-data" or params.get(b"name") != b"file" or b"filename" not in params:
            raise HTTPException(422, "Expected one file field named file.")
        filename = params[b"filename"].decode("utf-8", errors="replace")
        media_type = headers.get(b"content-type", b"").decode("ascii", errors="replace").split(";")[0].lower().strip()
        if len(filename) > 255 or "/" in filename or "\\" in filename or any(ord(c) < 32 for c in filename) or not filename.lower().endswith(".pdf"):
            raise HTTPException(415, "Only a PDF filename without path components is accepted.")
        if media_type not in ("", "application/pdf", "application/octet-stream"):
            raise HTTPException(415, "File content type must be application/pdf (or unspecified).")
    def part_data(chunk, start, end):
        if len(data) + end-start > MAX_FILE_BYTES:
            raise HTTPException(413, "PDF exceeds the 10 MiB file limit.")
        data.extend(chunk[start:end])
    def finish():
        nonlocal ended
        ended = True
    parser = MultipartParser(boundary, {"on_part_begin":part_begin, "on_header_field":header_field, "on_header_value":header_data, "on_header_end":header_end, "on_headers_finished":headers_done, "on_part_data":part_data, "on_end":finish})
    received = 0
    try:
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Request exceeds the 10 MiB PDF limit plus multipart overhead.")
            parser.write(chunk)
        parser.finalize()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Malformed multipart upload.") from None
    if not ended or part_count != 1 or not data:
        raise HTTPException(422, "A complete, non-empty PDF file is required.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(415, "File signature is not PDF.")
    return filename, bytes(data)


def analyze_pdf(filename, data):
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "Encrypted PDFs are not supported. Supply an unencrypted copy.")
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise HTTPException(422, "PDF must contain between 1 and 30 pages.")
        texts = []
        font_warnings = []
        for page in reader.pages:
            recovered = recover_financial_fonts(page)
            if recovered:
                font_warnings.append('Missing Unicode maps: financial glyphs recovered from embedded font cmap evidence; human review required.')
            text = page.extract_text() or ""
            texts.append(text)
            if sum(map(len, texts)) > MAX_TEXT:
                raise HTTPException(422, "PDF contains too much text for local invoice analysis.")
        text = "\n\f\n".join(texts)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "PDF is malformed or uses unsupported features; text extraction failed.") from None
    fields, items, warnings = parse_invoice(text)
    warnings += font_warnings
    _, gstin_candidates, _ = parse_fields(text)
    empty = sum(c.isalnum() for c in text) < 20
    if empty:
        fields, items, _ = parse_invoice("")
        gstin_candidates = []
        warnings.insert(0, "Insufficient extractable text. Scanned/image-only PDFs require OCR, which is not supported.")
    return {"filename":filename, "status":"needs_ocr" if empty else "analyzed", "method":"pypdf_text_and_labelled_rules", "pages":len(reader.pages), "fields":fields, "gstin_candidates":gstin_candidates, "line_items":items, "validation":validate_invoice(fields,items), "warnings":warnings, "text_excerpt":text[:4000], "stored":False}
