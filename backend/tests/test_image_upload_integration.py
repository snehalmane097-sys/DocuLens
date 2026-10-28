"""Multipart/schema/storage tests. Controlled OCR and native Tesseract are separate."""
import copy
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app import ocr, pdf_analysis
from app.main import create_app
from app.invoice import validate_invoice
from test_browser_ocr_fields import TEXT, EXPECTED
from test_ocr import scan_pdf
from test_pdf_analysis import make_pdf

IMAGE = Path(__file__).parent / 'fixtures' / 'acme-printed-invoice.png'


def controlled_tsv():
    # Supplied transcript with explicitly synthetic confidence/geometry.
    rows = ['level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext']
    for i, line in enumerate(TEXT.splitlines(), 1):
        confidence = 30 if line == '[unreadable OCR line]' else 93
        rows.append(f'5\t1\t1\t1\t{i}\t1\t10\t{i*30}\t1500\t20\t{confidence}\t{line}')
    return '\n'.join(rows).encode()


@pytest.fixture
def transcript_engine(monkeypatch):
    monkeypatch.setattr(ocr, 'executable', lambda name: name)
    monkeypatch.setattr(ocr, 'run_command', lambda args, data, deadline:
                        IMAGE.read_bytes() if args[0] == 'pdftoppm' else controlled_tsv())


def assert_analysis(result, native=True):
    for key, value in EXPECTED.items():
        assert result['fields'][key]['value'] == value, (key, result['fields'][key])
        assert result['fields'][key]['evidence']
        if native:
            assert result['fields'][key]['method'].startswith('local_ocr_requires_review:')
    assert result['fields']['gst_total']['value'] is None  # Not explicitly printed.
    assert result['line_items'] == []  # Table header was unreadable/unsupported.
    checks = {c['name']: c for c in result['validation']['checks']}
    assert checks['Grand total']['status'] == 'pass'
    assert checks['Grand total']['calculated'] == '4484.00'
    assert checks['GST components versus stated GST total']['calculated'] == '684.00'
    assert checks['GST components versus stated GST total']['extracted'] is None
    assert checks['GST components versus stated GST total']['status'] == 'unknown'
    assert checks['Line amounts versus subtotal']['status'] == 'unknown'
    assert result['review_required']


@pytest.mark.parametrize('kind', ['image', 'scanned_pdf', 'digital_pdf'])
def test_browser_multipart_path_transcript_mapping_and_retrieval(transcript_engine, tmp_path, kind):
    name, media, data = ('acme.png', 'image/png', IMAGE.read_bytes()) if kind == 'image' else (
        'acme.pdf', 'application/pdf', scan_pdf() if kind == 'scanned_pdf' else make_pdf(TEXT.splitlines()))
    with TestClient(create_app(tmp_path/'upload.sqlite3')) as client:
        response = client.post('/api/documents/analyze', files={'file': (name, data, media)},
                               headers={'Origin': 'http://localhost:3000'})
        assert response.status_code == 200, response.text
        result = response.json()
        assert_analysis(result, native=kind != 'digital_pdf')
        assert result['stored'] and result['version'] == 1 and result['review_status'] == 'pending'
        if kind != 'digital_pdf':
            assert result['ocr_pages'][0]['lines'][0]['confidence'] == 93
            assert not result['ocr_pages'][0]['lines'][6]['accepted']
        saved = client.get('/api/documents/'+result['document_id']).json()
        assert saved['analysis']['fields'] == result['fields']
        assert saved['effective_fields'] == result['fields']
        assert saved['review_validation'] == result['validation']


def test_stored_old_analysis_requires_explicit_archived_reprocessing(transcript_engine, monkeypatch, tmp_path):
    original = pdf_analysis.analyze_pdf
    data = IMAGE.read_bytes()
    old = original('acme.png', data)
    old = copy.deepcopy(old)
    for key in EXPECTED:
        if key != 'grand_total':
            old['fields'][key] = {'value': None, 'evidence': None, 'method': 'not_found_or_ambiguous'}
    old['validation'] = validate_invoice(old['fields'], [])
    monkeypatch.setattr(pdf_analysis, 'analyze_pdf', lambda *args: old)
    with TestClient(create_app(tmp_path/'archive.sqlite3')) as client:
        def upload():
            return client.post('/api/documents/analyze', files={'file': ('acme.png', data, 'image/png')}).json()
        first = upload()
        monkeypatch.setattr(pdf_analysis, 'analyze_pdf', original)
        repeated = upload()
        assert repeated['document_id'] == first['document_id']
        assert repeated['version'] == 1 and repeated['fields']['invoice_number']['value'] is None
        path = '/api/documents/'+first['document_id']
        updated = client.post(path+'/reprocess?version=1', files={'file': ('acme.png', data, 'image/png')})
        assert updated.status_code == 200, updated.text
        record = updated.json()
        assert record['version'] == 2 and record['review_status'] == 'pending'
        assert_analysis(record['analysis'])
        history = client.get(path+'/history').json()
        assert 'previous_analysis' in str(history) and 'reprocess' in str(history)
        assert client.post(path+'/reprocess?version=1', files={'file': ('acme.png', data, 'image/png')}).status_code == 409
        assert client.get('/api/documents').json()['total'] == 1


def test_installed_tesseract_actual_image_through_browser_endpoint(tmp_path):
    if not ocr.executable('tesseract'):
        pytest.skip('Installed Tesseract unavailable; native image integration not verified')
    with TestClient(create_app(tmp_path/'native.sqlite3')) as client:
        response = client.post('/api/documents/analyze', files={'file': (IMAGE.name, IMAGE.read_bytes(), 'image/png')},
                               headers={'Origin': 'http://localhost:3000'})
        assert response.status_code == 200, response.text
        result = response.json()
        assert_analysis(result)
        assert result['ocr_used'] and result['stored'] and result['review_status'] == 'pending'
        assert result['ocr_pages'][0]['width'] == 1600
        assert any(not line['accepted'] for line in result['ocr_pages'][0]['lines'])
        saved = client.get('/api/documents/'+result['document_id']).json()
        assert saved['analysis']['ocr_pages'] == result['ocr_pages']
        assert saved['effective_fields'] == result['fields']
