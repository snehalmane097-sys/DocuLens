"""Bounded multipart reception in memory; no UploadFile disk spooling."""
from io import BytesIO
from fastapi import HTTPException, Request
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from pypdf import PdfReader
from .invoice import parse_invoice, validate_invoice
from .invoice_rules import parse_fields
from .pdf_fonts import recover_financial_fonts
from .ocr import image_dimensions, ocr_document

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 65536
MAX_PAGES = 30
MAX_TEXT = 200000


async def receive_pdf(request: Request):
    kind, options = parse_options_header(request.headers.get("content-type", ""))
    boundary = options.get(b"boundary")
    if kind != b"multipart/form-data" or not boundary or len(boundary) > 200:
        raise HTTPException(415, "Use multipart/form-data with one PDF, PNG or JPEG field named file.")
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Request exceeds the 10 MiB document limit plus multipart overhead.")
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
        if len(filename) > 255 or "/" in filename or "\\" in filename or any(ord(c) < 32 for c in filename) or not filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
            raise HTTPException(415, "Only PDF, PNG or JPEG filenames without path components are accepted.")
        expected = "application/pdf" if filename.lower().endswith(".pdf") else "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        if media_type not in ("", expected, "application/octet-stream"):
            raise HTTPException(415, "File content type does not match its extension.")
    def part_data(chunk, start, end):
        if len(data) + end-start > MAX_FILE_BYTES:
            raise HTTPException(413, "Document exceeds the 10 MiB file limit.")
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
                raise HTTPException(413, "Request exceeds the 10 MiB document limit plus multipart overhead.")
            parser.write(chunk)
        parser.finalize()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Malformed multipart upload.") from None
    if not ended or part_count != 1 or not data:
        raise HTTPException(422, "A complete, non-empty file is required.")
    expected = b"%PDF-" if filename.lower().endswith(".pdf") else b"\x89PNG\r\n\x1a\n" if filename.lower().endswith(".png") else b"\xff\xd8\xff"
    if not data.startswith(expected):
        raise HTTPException(415, "File signature does not match its extension.")
    if not filename.lower().endswith(".pdf"):
        image_dimensions(data)
    return filename, bytes(data)


def usable_text(text):
    return sum(c.isalnum() for c in text) >= 20 and sum(ord(c)<32 and c not in "\r\n\t\f" for c in text) < max(1,len(text)//20)


def analysis_result(filename, texts, ocr_pages, warnings, unresolved=False):
    text = "\n\f\n".join(texts)
    if len(text)>MAX_TEXT:
        raise HTTPException(422, "Document contains too much text for local analysis.")
    fields, items, parser_warnings = parse_invoice(text)
    _, candidates, _ = parse_fields(text)
    used = bool(ocr_pages)
    if used:
        warnings.append("Local Tesseract OCR: every recognized value requires human review. Lines with any word below 80 confidence are excluded from parsing. Confidence is not a guarantee; handwriting recognition is unverified.")
        for field in fields.values():
            if field['value'] is None:
                continue
            evidence = field['evidence'] or ''
            sources = [page['page'] for page in ocr_pages if evidence.split('\n')[0] in [line['text'] for line in page['lines'] if line['accepted']]]
            if sources:
                field['evidence'] = 'OCR page(s) '+','.join(map(str,sources))+':\n'+evidence
                field['method'] = 'local_ocr_requires_review:'+field['method']
        for item in items:
            item['evidence'] = 'Local OCR; human review required: '+item['evidence']
        for candidate in candidates:
            candidate['method'] = 'local_ocr_requires_review:'+candidate['method']
    empty = not usable_text(text.replace("[unreadable OCR line]", ""))
    if empty:
        warnings.append("Insufficient readable text. OCR may be unavailable or unable to read this image. Supply a clearer upright scan or review manually; no values were guessed.")
    return {'filename':filename,'status':'needs_ocr' if empty or unresolved else 'analyzed',
            'method':'local_tesseract_and_labelled_rules' if used else 'pypdf_text_and_labelled_rules',
            'pages':len(texts),'fields':fields,'gstin_candidates':candidates,'line_items':items,
            'validation':validate_invoice(fields,items),'warnings':warnings+parser_warnings,
            'text_excerpt':text[:4000],'stored':False,'ocr_used':used,'ocr_pages':ocr_pages,'review_required':True}


def analyze_pdf(filename, data):
    # Historical function name retained for compatibility; accepts all supported documents.
    if len(data)>MAX_FILE_BYTES:
        raise HTTPException(413, "Document exceeds the 10 MiB file limit.")
    if not filename.lower().endswith('.pdf'):
        image_dimensions(data)
        pages = ocr_document(data)
        texts = ['\n'.join(line['text'] if line['accepted'] else '[unreadable OCR line]' for line in page['lines']) for page in pages]
        return analysis_result(filename,texts,pages,[])
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "Encrypted PDFs are not supported. Supply an unencrypted copy.")
        if not 1 <= len(reader.pages) <= MAX_PAGES:
            raise HTTPException(422, "PDF must contain between 1 and 30 pages.")
        texts, warnings = [], []
        for page in reader.pages:
            if recover_financial_fonts(page):
                warnings.append('Missing Unicode maps: financial glyphs recovered from embedded font cmap evidence; human review required.')
            texts.append(page.extract_text() or '')
            if sum(map(len,texts))>MAX_TEXT:
                raise HTTPException(422, "PDF contains too much text for local invoice analysis.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "PDF is malformed or uses unsupported features; text extraction failed.") from None
    missing = [index+1 for index,text in enumerate(texts) if not usable_text(text)]
    pages = []
    unresolved = False
    if missing:
        try:
            pages = ocr_document(data,missing)
        except HTTPException as exc:
            if exc.status_code != 503:
                raise
            # Preserve the historical needs_ocr response for unavailable optional tools.
            warnings.append(exc.detail)
            unresolved = True
        for page in pages:
            texts[page['page']-1] = '\n'.join(line['text'] if line['accepted'] else '[unreadable OCR line]' for line in page['lines'])
    return analysis_result(filename,texts,pages,warnings,unresolved)
