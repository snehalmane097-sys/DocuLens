"""User-reported OCR transcript regression, not a native recognition accuracy test."""
from pathlib import Path
from app.invoice import parse_invoice, validate_invoice
from app.invoice_rules import parse_fields
from app.pdf_analysis import analysis_result

TEXT = (Path(__file__).parent / 'fixtures' / 'acme-browser-ocr.txt').read_text(encoding='utf-8-sig')
EXPECTED = {
    'supplier_name': 'ACME OFFICE SUPPLIES', 'buyer_name': 'Example Manufacturing Pvt Ltd',
    'invoice_number': 'TEST-INV-1042', 'invoice_date': '2026-10-28',
    'subtotal': '3800.00', 'cgst': '342.00', 'sgst': '342.00',
    'grand_total': '4484.00',
}


def test_exact_browser_transcript_fields_and_arithmetic():
    fields, items, _ = parse_invoice(TEXT)
    for key, value in EXPECTED.items():
        assert fields[key]['value'] == value, (key, fields[key])
        assert fields[key]['evidence'] in TEXT
    assert fields['supplier_name']['method'] == 'header_position_rule_requires_review'
    assert fields['buyer_name']['value'] == 'Example Manufacturing Pvt Ltd'
    assert fields['buyer_name']['method'] == 'bill_to_position_rule_requires_review'
    assert fields['gst_total']['value'] is None  # Calculated tax must not become extracted tax.
    assert items == []  # Unreadable headers/loose OCR rows do not prove table columns.
    grand = next(c for c in validate_invoice(fields, items)['checks'] if c['name'] == 'Grand total')
    assert grand['status'] == 'pass' and grand['calculated'] == '4484.00'


def test_ocr_provenance_review_and_confidence_are_retained():
    # Controlled metadata: original native confidence was not included in the report.
    lines = [{'text': line, 'confidence': 91.25, 'accepted': line != '[unreadable OCR line]',
              'bbox': {'x': 10, 'y': n*20, 'width': 500, 'height': 18}}
             for n, line in enumerate(TEXT.splitlines())]
    page = {'page': 1, 'width': 1000, 'height': 1200, 'lines': lines}
    result = analysis_result('fictional.png', [TEXT], [page], [])
    assert result['ocr_pages'] == [page] and result['review_required']
    for key, value in EXPECTED.items():
        field = result['fields'][key]
        assert field['value'] == value
        assert field['evidence'].startswith('OCR page(s) 1:\n')
        assert field['method'].startswith('local_ocr_requires_review:')
    assert result['text_excerpt'].count('[unreadable OCR line]') == 2


def test_multiple_explicit_fields_and_conflicts_on_one_line():
    fields, _, _ = parse_fields('Invoice No. TEST-INV-1042 Invoice Date 28/10/2026\nSubtotal 3,800.00 CGST (9%) 342.00 SGST (9%) 342.00 Grand Total 4,484.00')
    for key, value in EXPECTED.items():
        if key not in ('supplier_name', 'buyer_name'):
            assert fields[key]['value'] == value, (key, fields[key])
    fields, _, _ = parse_fields('Invoice No. A-1 Invoice No. B-2 Invoice Date 28/10/2026')
    assert fields['invoice_number']['value'] is None
    assert fields['invoice_number']['method'] == 'conflicting_evidence'


def test_no_supplier_association_across_combined_buyer_heading_or_unreadable_line():
    for header in ('', 'ACME OFFICE SUPPLIES\n[unreadable OCR line]\n'):
        fields, _, _ = parse_fields(header+'BILL TO TAX INVOICE\nExample Manufacturing Pvt Ltd\nGSTIN: 27ABCDE1234F1Z5')
        assert fields['supplier_name']['value'] is None
    fields, _, _ = parse_fields(TEXT.replace('28/10/2026', '[unreadable OCR line]'))
    assert fields['invoice_date']['value'] is None
    assert fields['invoice_number']['value'] == 'TEST-INV-1042'
