"""Optional local OCR via bounded stdin/stdout pipes; no original bytes persisted."""
import csv
import io
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import threading
import time
import zlib
from fastapi import HTTPException

MAX_PIXELS = 12_000_000
MAX_EDGE = 8000
MAX_OCR_PAGES = 8
OCR_SECONDS = 45
MAX_OUTPUT = 8 * 1024 * 1024
MIN_CONFIDENCE = 80
SLOTS = threading.BoundedSemaphore(2)


def executable(name):
    key = 'DOCULENS_TESSERACT_PATH' if name == 'tesseract' else 'DOCULENS_PDFTOPPM_PATH'
    configured = os.getenv(key)
    if configured:
        return str(Path(configured)) if Path(configured).is_file() else None
    found = shutil.which(name)
    if not found and name == 'tesseract':
        path = Path(os.getenv('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR/tesseract.exe'
        found = str(path) if path.is_file() else None
    return found


def require_engine():
    engine = executable('tesseract')
    if not engine:
        raise HTTPException(503, 'Local OCR unavailable. Install Tesseract with eng language data; set DOCULENS_TESSERACT_PATH to tesseract.exe or add it to PATH. Text-based PDFs still work.')
    return engine


def image_dimensions(data):
    width = height = 0
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        if len(data) < 33 or data[8:16] != b'\x00\x00\x00\rIHDR' or zlib.crc32(data[12:29]) != int.from_bytes(data[29:33], 'big'):
            raise HTTPException(422, 'Malformed PNG header.')
        width, height = struct.unpack('>II', data[16:24])
        pos = 8
        ended = False
        while pos + 12 <= len(data):
            size = int.from_bytes(data[pos:pos+4], 'big')
            kind = data[pos+4:pos+8]
            if size > len(data)-pos-12:
                raise HTTPException(422, 'Truncated PNG chunk.')
            if zlib.crc32(data[pos+4:pos+8+size]) != int.from_bytes(data[pos+8+size:pos+12+size], 'big'):
                raise HTTPException(422, 'Invalid PNG checksum.')
            if kind == b'acTL':
                raise HTTPException(422, 'Animated PNG is unsupported. Supply a single image.')
            pos += size + 12
            if kind == b'IEND':
                ended = True
                break
        if not ended:
            raise HTTPException(422, 'PNG has no complete end chunk.')
    elif data.startswith(b'\xff\xd8'):
        pos = 2
        while pos < len(data):
            if data[pos] != 255:
                break
            while pos < len(data) and data[pos] == 255:
                pos += 1
            if pos >= len(data):
                break
            marker = data[pos]; pos += 1
            if marker in (0xD9, 0xDA):
                break
            if marker == 1 or 0xD0 <= marker <= 0xD7:
                continue
            if pos+2 > len(data):
                break
            size = int.from_bytes(data[pos:pos+2], 'big')
            if size < 2 or pos+size > len(data):
                break
            if marker in (0xC0, 0xC1, 0xC2):
                if size >= 8:
                    height, width = struct.unpack('>HH', data[pos+3:pos+7])
                break
            pos += size
        if not data.endswith(b'\xff\xd9'):
            raise HTTPException(422, 'Truncated JPEG.')
    else:
        raise HTTPException(415, 'Image signature must be PNG or JPEG.')
    if not width or not height:
        raise HTTPException(422, 'Unsupported or malformed image dimensions.')
    if width > MAX_EDGE or height > MAX_EDGE or width*height > MAX_PIXELS:
        raise HTTPException(413, 'Image exceeds 12 million pixels or 8000 pixels per edge. Resize before upload.')
    return width, height


def run_command(args, data, deadline):
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        raise HTTPException(504, 'Local OCR exceeded the 45-second processing limit.')
    try:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except OSError:
        raise HTTPException(503, 'OCR executable could not start. Check its path and permissions.') from None
    output = bytearray()
    overflow = threading.Event()
    def read_output():
        while True:
            chunk = process.stdout.read(65536)
            if not chunk:
                break
            if len(output)+len(chunk)>MAX_OUTPUT:
                overflow.set()
                process.kill()
                break
            output.extend(chunk)
    def discard_errors():
        # Drain diagnostics without retaining or logging private native output.
        while process.stderr.read(65536):
            pass
    def write_input():
        try:
            process.stdin.write(data)
            process.stdin.flush()
        except (BrokenPipeError,OSError):
            pass
        finally:
            process.stdin.close()
    threads = [threading.Thread(target=target,daemon=True) for target in (read_output,discard_errors,write_input)]
    for thread in threads:
        thread.start()
    timed_out = False
    try:
        process.wait(timeout=max(0.001,deadline-time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()
    finally:
        for thread in threads:
            thread.join()
        process.stdout.close()
        process.stderr.close()
    if timed_out:
        raise HTTPException(504, 'Local OCR exceeded the 45-second processing limit.')
    if overflow.is_set():
        raise HTTPException(422, 'OCR/renderer output exceeds the safe local limit.')
    if process.returncode:
        raise HTTPException(422, 'Local OCR/renderer failed. Check installation, eng language data and input file.')
    return bytes(output)


def parse_tsv(data, page, width, height):
    groups = {}
    count = 0
    try:
        rows = csv.DictReader(io.StringIO(data.decode('utf-8')), delimiter='\t', quoting=csv.QUOTE_NONE)
        if not rows.fieldnames or not {'level','text','conf','left','top','width','height','block_num','par_num','line_num'}.issubset(rows.fieldnames):
            raise ValueError('Missing TSV headers')
        for row in rows:
            if row['level'] != '5' or not row['text'].strip():
                continue
            count += 1
            if count > 12000:
                raise ValueError('Too many words')
            confidence = float(row['conf'])
            x,y,w,h = (int(row[k]) for k in ('left','top','width','height'))
            if not math.isfinite(confidence) or not 0 <= confidence <= 100 or min(x,y,w,h)<0 or x+w>width or y+h>height:
                raise ValueError('Invalid geometry/confidence')
            text = row['text'].strip()
            if len(text)>1000 or any(ord(c)<32 for c in text):
                raise ValueError('Invalid text')
            key = (row['block_num'],row['par_num'],row['line_num'])
            groups.setdefault(key,[]).append((text,confidence,x,y,w,h))
    except (KeyError,ValueError,UnicodeError,TypeError,csv.Error,AttributeError):
        raise HTTPException(422, 'Local OCR returned unsupported TSV output.') from None
    lines = []
    for words in groups.values():
        confidence = min(w[1] for w in words)
        left,top = min(w[2] for w in words),min(w[3] for w in words)
        right,bottom = max(w[2]+w[4] for w in words),max(w[3]+w[5] for w in words)
        lines.append({'text':' '.join(w[0] for w in words),'accepted':confidence>=MIN_CONFIDENCE,
                      'confidence':confidence,'bbox':[left,top,right-left,bottom-top]})
    return {'page':page,'width':width,'height':height,'lines':lines}


def recognize(data, page, deadline):
    width,height = image_dimensions(data)
    output = run_command([require_engine(),'stdin','stdout','-l','eng','--psm','3','tsv'],data,deadline)
    return parse_tsv(output,page,width,height)


def ocr_document(data, page_numbers=None):
    require_engine()
    if page_numbers and len(page_numbers)>MAX_OCR_PAGES:
        raise HTTPException(422, 'OCR supports at most 8 scanned pages per document.')
    renderer = executable('pdftoppm') if page_numbers else None
    if page_numbers and not renderer:
        raise HTTPException(503, 'Scanned PDF OCR needs Poppler pdftoppm. Set DOCULENS_PDFTOPPM_PATH or add it to PATH.')
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(503, 'Local OCR is busy. Retry when another document finishes.')
    try:
        deadline = time.monotonic()+OCR_SECONDS
        if page_numbers is None:
            return [recognize(data,1,deadline)]
        pages = []
        for page in page_numbers:
            image = run_command([renderer,'-f',str(page),'-l',str(page),'-singlefile','-scale-to','2200','-gray','-png','-'],data,deadline)
            pages.append(recognize(image,page,deadline))
        return pages
    finally:
        SLOTS.release()
