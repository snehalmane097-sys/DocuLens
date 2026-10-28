"""Controlled-engine tests are not OCR accuracy tests. Native tests skip explicitly without Tesseract."""
from io import BytesIO
from pathlib import Path
import subprocess
import time
import struct
import zlib
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, NumberObject, DictionaryObject
from app import ocr, pdf_analysis
from app.main import create_app

FIXTURES = Path(__file__).parent/'fixtures'
LINES = ['Supplier: Synthetic Printed Supplies','Invoice No: OCR-100','Invoice Date: 2026-10-28',
         'Subtotal: 100.00','IGST: 18.00','GST Total: 18.00','Grand Total: 118.00']


def tsv(lines=LINES, weak=None):
    rows=['level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext']
    for i,line in enumerate(lines,1):
        for j,word in enumerate(line.split(),1):
            rows.append(f'5\t1\t1\t1\t{i}\t{j}\t{j*100}\t{i*100}\t90\t40\t{30 if i==weak else 96}\t{word}')
    return '\n'.join(rows).encode()


def scan_pdf(count=1):
    writer=PdfWriter()
    for _ in range(count):
        page=writer.add_blank_page(300,300)
        image=DecodedStreamObject();image.set_data(b'\xff'*30000)
        image.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),
                      NameObject('/Width'):NumberObject(100),NameObject('/Height'):NumberObject(100),
                      NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8)})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Im0'):writer._add_object(image)})})
        content=DecodedStreamObject();content.set_data(b'q 300 0 0 300 0 0 cm /Im0 Do Q')
        page[NameObject('/Contents')]=writer._add_object(content)
    output=BytesIO();writer.write(output);return output.getvalue()


@pytest.fixture
def controlled(monkeypatch):
    monkeypatch.setattr(ocr,'executable',lambda name: name)
    def command(args,data,deadline):
        return (FIXTURES/'printed-ocr.png').read_bytes() if args[0]=='pdftoppm' else tsv()
    monkeypatch.setattr(ocr,'run_command',command)


@pytest.mark.parametrize('filename,media',[('printed-ocr.png','image/png'),('printed-ocr.jpg','image/jpeg')])
def test_image_upload_persistence_idempotency_reprocess(controlled,tmp_path,filename,media):
    with TestClient(create_app(tmp_path/'ocr.sqlite3')) as client:
        data=(FIXTURES/filename).read_bytes()
        def upload():
            response=client.post('/api/documents/analyze',files={'file':(filename,data,media)})
            assert response.status_code==200,response.text
            return response.json()
        first=upload();second=upload()
        assert first['document_id']==second['document_id'] and first['version']==1
        assert first['ocr_used'] and first['review_required'] and first['review_status']=='pending'
        assert first['fields']['grand_total']['value']=='118.00'
        assert 'OCR page(s) 1' in first['fields']['subtotal']['evidence']
        assert 'local_ocr_requires_review' in first['fields']['subtotal']['method']
        assert first['ocr_pages'][0]['lines'][0]['bbox']
        assert first['validation']['mismatches']==0
        response=client.post('/api/documents/'+first['document_id']+'/reprocess?version=1',files={'file':(filename,data,media)})
        assert response.status_code==200,response.text
        assert response.json()['version']==2
        assert client.get('/api/documents').json()['total']==1
        assert len(client.get('/api/documents/'+first['document_id']+'/history').json()['items'])==1
        assert client.post('/api/documents/'+first['document_id']+'/reprocess?version=1',files={'file':(filename,data,media)}).status_code==409


@pytest.mark.parametrize('count',[1,3])
def test_scanned_pdf_pages_and_locations(controlled,count):
    result=pdf_analysis.analyze_pdf('scanned.pdf',scan_pdf(count))
    assert result['ocr_used'] and result['pages']==count
    assert [p['page'] for p in result['ocr_pages']]==list(range(1,count+1))
    assert result['fields']['subtotal']['value']=='100.00'


def test_low_confidence_amount_is_not_parsed(monkeypatch,controlled):
    monkeypatch.setattr(ocr,'run_command',lambda *args:tsv(weak=4))
    result=pdf_analysis.analyze_pdf('blur.png',(FIXTURES/'printed-ocr.png').read_bytes())
    assert result['fields']['subtotal']['value'] is None
    assert not result['ocr_pages'][0]['lines'][3]['accepted']
    assert result['ocr_pages'][0]['lines'][3]['text']=='Subtotal: 100.00'
    assert next(c for c in result['validation']['checks'] if c['name']=='Grand total')['status']=='unknown'


def test_all_blurry_or_blank_is_not_success(monkeypatch,controlled):
    for data in (tsv().replace(b'\t96\t',b'\t20\t'),tsv([])):
        monkeypatch.setattr(ocr,'run_command',lambda *args:data)
        result=pdf_analysis.analyze_pdf('blur.png',(FIXTURES/'printed-ocr.png').read_bytes())
        assert result['status']=='needs_ocr'
        assert result['fields']['grand_total']['value'] is None
        assert result['review_required']


def test_engine_unavailable_preserves_text_pdf(monkeypatch,tmp_path):
    monkeypatch.setattr(ocr,'executable',lambda name:None)
    from test_pdf_analysis import make_pdf
    assert pdf_analysis.analyze_pdf('text.pdf',make_pdf(LINES))['fields']['grand_total']['value']=='118.00'
    assert pdf_analysis.analyze_pdf('scan.pdf',scan_pdf())['status']=='needs_ocr'
    with TestClient(create_app(tmp_path/'test.sqlite3')) as client:
        response=client.post('/api/documents/analyze',files={'file':('image.png',(FIXTURES/'printed-ocr.png').read_bytes(),'image/png')})
        assert response.status_code==503 and 'Tesseract' in response.json()['detail']
        assert client.get('/api/ocr/status').json()['engine_found'] is False
        assert client.get('/api/documents').json()['total']==0


def test_renderer_unavailable_and_limits(monkeypatch,controlled):
    monkeypatch.setattr(ocr,'executable',lambda name:'tesseract' if name=='tesseract' else None)
    assert pdf_analysis.analyze_pdf('scan.pdf',scan_pdf())['status']=='needs_ocr'
    with pytest.raises(HTTPException) as error:
        ocr.ocr_document(b'pdf',list(range(1,10)))
    assert error.value.status_code==422
    with pytest.raises(HTTPException):
        pdf_analysis.analyze_pdf('scan.pdf',scan_pdf(31))
    with pytest.raises(HTTPException) as error:
        pdf_analysis.analyze_pdf('image.png',b'x'*(10*1024*1024+1))
    assert error.value.status_code==413


@pytest.mark.parametrize('data',[b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff',b'not an image'])
def test_malformed_images(data):
    with pytest.raises(HTTPException):ocr.image_dimensions(data)


def test_oversized_dimensions_before_engine():
    data=bytearray((FIXTURES/'printed-ocr.png').read_bytes())
    data[16:24]=struct.pack('>II',9000,9000)
    data[29:33]=struct.pack('>I',zlib.crc32(data[12:29]))
    with pytest.raises(HTTPException) as error:ocr.image_dimensions(data)
    assert error.value.status_code==413


def test_real_poppler_rasterizes_image_pdf():
    renderer=ocr.executable('pdftoppm')
    if not renderer:pytest.skip('Native Poppler renderer is unavailable')
    image=ocr.run_command([renderer,'-f','1','-l','1','-singlefile','-scale-to','2200','-gray','-png','-'],scan_pdf(),time.monotonic()+20)
    assert ocr.image_dimensions(image)==(2200,2200)


def test_timeout_failure_and_output_errors(monkeypatch):
    class TimedOut:
        def __init__(self,*args,**kwargs):
            self.stdin=BytesIO();self.stdout=BytesIO();self.stderr=BytesIO();self.returncode=0
        def wait(self,timeout=None):
            if timeout is not None:raise subprocess.TimeoutExpired('tesseract',timeout)
        def kill(self):self.returncode=-1
    monkeypatch.setattr(subprocess,'Popen',TimedOut)
    with pytest.raises(HTTPException) as error:ocr.run_command(['tesseract'],b'',time.monotonic()+1)
    assert error.value.status_code==504
    with pytest.raises(HTTPException):ocr.parse_tsv(b'garbage',1,100,100)
    with pytest.raises(HTTPException):ocr.parse_tsv(tsv().replace(b'\t96\t',b'\tnan\t'),1,1500,1000)


def test_native_printed_image_recognition():
    if not ocr.executable('tesseract'):pytest.skip('Tesseract executable missing: native OCR accuracy not tested')
    for name in ('printed-ocr.png','printed-ocr.jpg'):
        result=pdf_analysis.analyze_pdf(name,(FIXTURES/name).read_bytes())
        assert result['ocr_used']
        assert result['fields']['subtotal']['value']=='100.00'
        assert result['fields']['grand_total']['value']=='118.00'

def test_native_pipe_bounds_and_timeout(monkeypatch):
    import sys
    value=ocr.run_command([sys.executable,'-c','import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'],b'pipe check',time.monotonic()+5)
    assert value==b'pipe check'
    monkeypatch.setattr(ocr,'MAX_OUTPUT',100)
    with pytest.raises(HTTPException) as error:
        ocr.run_command([sys.executable,'-c','print("x"*10000)'],b'',time.monotonic()+5)
    assert error.value.status_code==422
    with pytest.raises(HTTPException) as error:
        ocr.run_command([sys.executable,'-c','import time; time.sleep(3)'],b'',time.monotonic()+0.1)
    assert error.value.status_code==504


def test_image_mime_signature_validation_and_busy_gate(controlled,tmp_path):
    with TestClient(create_app(tmp_path/'validation.sqlite3')) as client:
        image=(FIXTURES/'printed-ocr.png').read_bytes()
        for filename,data,media in [('wrong.jpg',image,'image/jpeg'),('image.png',image,'application/pdf'),('image.png',b'not PNG','image/png')]:
            assert client.post('/api/documents/analyze',files={'file':(filename,data,media)}).status_code==415
        assert client.get('/api/documents').json()['total']==0
    assert ocr.SLOTS.acquire(False) and ocr.SLOTS.acquire(False)
    try:
        with pytest.raises(HTTPException) as error:ocr.ocr_document(image)
        assert error.value.status_code==503
    finally:
        ocr.SLOTS.release();ocr.SLOTS.release()
