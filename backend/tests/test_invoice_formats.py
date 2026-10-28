"""Diverse synthetic layouts, not evidence of successful real-invoice parsing."""
import pytest
from app.invoice import parse_invoice, validate_invoice
from app.invoice_rules import money, tax_money

REGRESSION = """Aster Precision Works
GSTIN: 27ABCDE1234F1Z5
Birch Trading India Pvt. Ltd.
Bill To
12 Example Road
GSTIN: 29PQRSX9876L1Z2
Invoice No.: ZX 26-27/09/004
Date: Wednesday, 09 September 2026
Description | Qty | Unit Price | Amount
Machined bracket | 36 NOS | INR 365.00 | 13,140.00
Subtotal: INR 13,140.00
CGST: 9% INR 1,182.60
SGST: 9% INR 1,182.60
Tax Amount: 2,365.20
Total Before Round-off: 15,505.20
Round-off: -INR 0.20
Final Invoice Total: 15,505.00
"""


def check(fields,items,name="Grand total"):
    return next(c for c in validate_invoice(fields,items)["checks"] if c["name"] == name)


def test_regression_signed_roundoff_and_complete_tokens():
    fields,items,warnings = parse_invoice(REGRESSION)
    expected = {"invoice_number":"ZX 26-27/09/004","invoice_date":"2026-09-09",
                "supplier_name":"Aster Precision Works","buyer_name":"Birch Trading India Pvt. Ltd.",
                "subtotal":"13140.00","cgst":"1182.60","sgst":"1182.60",
                "gst_total":"2365.20","pre_round_total":"15505.20",
                "round_off":"-0.20","grand_total":"15505.00"}
    for key,value in expected.items():
        assert fields[key]["value"] == value, (key,fields[key])
        assert fields[key]["evidence"]
    assert items[0]["quantity"] == "36"
    assert items[0]["unit_rate"] == "365.00"
    assert check(fields,items)["status"] == "pass"
    assert check(fields,items,"Pre-round total")["status"] == "pass"
    assert validate_invoice(fields,items)["mismatches"] == 0


@pytest.mark.parametrize("text",[
    "SGSTIN: 27ABCDE1234F1Z5\nGSTIN: 29PQRSX9876L1Z2",
    "SGST:\n0\nContact: 123456\nGST Total:\n1",
    "SGST: 0XYZ\nGST Total: 1ABC",
    "SGST rate: 9%\nGST Total items: 1",
    "SGST: 27ABCDE1234F1Z5\nGST Total: 1234/567",
    "SGST: 9%\nGrand Total: 118.00",
    "SGST:\nCGST: 9.00\nGST Total:",
])
def test_unrelated_fragments_and_missing_taxes_never_become_zero_or_one(text):
    fields,items,_ = parse_invoice(text)
    assert fields["sgst"]["value"] is None
    assert fields["gst_total"]["value"] is None
    assert check(fields,items)["status"] == "unknown"


def test_zero_requires_explicit_evidence_and_conflicts_stay_unknown():
    fields,_,_ = parse_invoice("SGST: INR 0.00\nCGST: 0.00\nIGST: 0.00")
    assert fields["sgst"]["value"] == "0.00"
    fields,items,_ = parse_invoice("Subtotal: 100\nSGST: 9\nSGST: 10\nCGST: 9\nGST Total: 18\nGrand Total: 118")
    assert fields["sgst"]["value"] is None
    assert fields["sgst"]["evidence"]
    assert check(fields,items)["status"] == "unknown"


@pytest.mark.parametrize("label,identifier,date_label,date",[
    ("Inv #","T-2026/77","Dated","10-Sep-2026"),
    ("Tax Invoice Number","2026-008","Invoice Dt.","10.09.2026"),
    ("Invoice ID","Q 2026 18","Invoice Date","2026-09-10"),
])
def test_number_date_aliases_and_igst_layout(label,identifier,date_label,date):
    fields,items,_ = parse_invoice(f"Seller: Maple Services Ltd.\nCustomer: River Tools Ltd.\n{label}: {identifier}\n{date_label}: {date}\nTaxable Value: Rs. 1,00,000.00\nIGST: 18% 18,000.00\nGST Total: 18,000.00\nAmount Due: 1,18,000.00")
    assert fields["invoice_number"]["value"] == identifier
    assert fields["invoice_date"]["value"] == "2026-09-10"
    assert fields["supplier_name"]["value"] == "Maple Services Ltd."
    assert fields["buyer_name"]["value"] == "River Tools Ltd."
    assert fields["cgst"]["value"] is None
    assert check(fields,items)["status"] == "pass"


@pytest.mark.parametrize("raw,expected",[
    ("-\u20b90.20","-0.20"),("\u2212Rs. 0.20","-0.20"),
    ("INR -0.20","-0.20"),("+0.30","0.30"),("0.00","0.00")
])
def test_roundoff_sign_and_currency_variants(raw,expected):
    fields,_,_ = parse_invoice("Round Off: "+raw)
    assert fields["round_off"]["value"] == expected


def test_invalid_roundoff_and_weekday_are_unknown():
    fields,items,_ = parse_invoice("Date: Tuesday, 09 September 2026\nSubtotal: 100\nIGST: 18\nRound-off: contact 0.2\nGrand Total: 118")
    assert fields["invoice_date"]["value"] is None
    assert fields["round_off"]["value"] is None
    # Invalid adjustment must not silently default to zero.
    assert check(fields,items)["status"] == "unknown"


def test_total_priority_and_same_priority_conflicts():
    fields,_,warnings = parse_invoice("Invoice Total: 118.20\nRound Off: -0.20\nFinal Total: 118.00")
    assert fields["grand_total"]["value"] == "118.00"
    assert any("strongest" in w for w in warnings)
    fields,_,_ = parse_invoice("Final Total: 118\nFinal Invoice Total: 119")
    assert fields["grand_total"]["value"] is None
    assert fields["grand_total"]["evidence"]


@pytest.mark.parametrize("table",[
    "Description\tQuantity\tRate\tLine Total\nFastener\t2 PCS\tRs. 50.00\t100.00",
    "Particulars  Qty  Unit Price  Amount\nFastener  2 PCS  INR 50.00  100.00",
    "Qty | Description | Amount | Rate\n2 | Fastener | 100.00 | 50.00",
])
def test_explicit_alternative_table_layouts(table):
    fields,items,_ = parse_invoice(table+"\nSubtotal: 100\nIGST: 18\nGrand Total: 118")
    assert len(items) == 1
    assert items[0]["description"] == "Fastener"
    assert items[0]["quantity"] == "2"
    assert check(fields,items,"Line 1 amount")["status"] == "pass"


def test_wrapped_description_only_in_explicit_empty_numeric_columns():
    _,items,_ = parse_invoice("Description | Qty | Rate | Amount\nSteel bracket | 2 | 50 | 100\nwith zinc finish | | |")
    assert len(items) == 1
    assert items[0]["description"] == "Steel bracket with zinc finish"
    _,items,_ = parse_invoice("Description Qty Rate Amount\nSteel bracket\n2\n50\n100")
    assert items == []


@pytest.mark.parametrize("raw",["0XYZ","ID118.00","1,23","18%","9% 1XYZ","27ABCDE1234F1Z5","0 0","100\n200"])
def test_money_consumes_complete_value(raw):
    assert money(raw) is None
    assert tax_money(raw) is None


def test_pdf_synthetic_regression_uses_actual_text_extraction():
    pytest.importorskip("pypdf")
    pytest.importorskip("python_multipart")
    from test_pdf_analysis import make_pdf
    from app.pdf_analysis import analyze_pdf
    result = analyze_pdf("synthetic-regression.pdf",make_pdf(REGRESSION.splitlines()))
    assert result["fields"]["invoice_number"]["value"] == "ZX 26-27/09/004"
    assert result["fields"]["grand_total"]["value"] == "15505.00"
    assert result["validation"]["mismatches"] == 0


def test_tax_rate_separator_is_complete_and_never_backtracks_to_digit_fragment():
    assert tax_money("9%:18.00") == "18.00"
    assert tax_money("9%0.00") is None
    assert tax_money("9%") is None