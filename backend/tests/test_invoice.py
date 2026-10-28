from decimal import Decimal
from app.invoice import parse_invoice, validate_invoice, decimal

INVOICE = """Supplier: Example Test Supplies
Invoice No: TEST-001
Invoice Date: 2026-10-28
GSTIN: 27ABCDE1234F1Z5
Description | Qty | Rate | Amount | Tax % | Tax
Test paper | 2 | 100.00 | 200.00 | 18 | 36.00
Subtotal: 200.00
CGST 9%: 18.00
SGST 9%: 18.00
GST Total: 36.00
Grand Total: 236.00
"""


def test_readable_invoice_fields_and_line_items():
    # Colon after tax label is the supported convention; tax rate precedes amount.
    fields, items, warnings = parse_invoice(INVOICE.replace("CGST 9%:", "CGST: 9%").replace("SGST 9%:", "SGST: 9%"))
    assert fields["invoice_number"]["value"] == "TEST-001"
    assert fields["invoice_date"]["value"] == "2026-10-28"
    assert fields["supplier_name"]["value"] == "Example Test Supplies"
    assert fields["gstin"]["value"] == "27ABCDE1234F1Z5"
    assert fields["cgst"]["value"] == "18.00"
    assert fields["invoice_number"]["evidence"] == "Invoice No: TEST-001"
    assert items[0]["quantity"] == "2"
    checks = validate_invoice(fields, items)
    assert checks["mismatches"] == 0
    assert checks["unknown"] == 0
    assert checks["passed"] == 5


def test_missing_and_conflicting_values_remain_unknown():
    fields, items, _ = parse_invoice("Invoice No: A\nInvoice No: B\nSupplier GSTIN: 27ABCDE1234F1Z5\nhello")
    assert fields["invoice_number"]["value"] is None
    assert fields["supplier_name"]["value"] is None
    assert fields["grand_total"]["value"] is None
    checks = validate_invoice(fields, items)
    assert checks["unknown"] > 0
    assert checks["mismatches"] == 0


def test_igst_and_stated_gst_not_counted_twice():
    fields, items, _ = parse_invoice("Subtotal: 100\nIGST: 18\nGST Total: 18\nGrand Total: 118")
    result = validate_invoice(fields, items)
    grand = next(c for c in result["checks"] if c["name"] == "Grand total")
    assert grand["calculated"] == "118.00"
    assert grand["status"] == "pass"


def test_mixed_taxes_and_incomplete_split_are_unknown():
    for taxes in ("CGST: 9\nSGST: 9\nIGST: 18", "CGST: 9"):
        fields, items, _ = parse_invoice("Subtotal: 100\nGST Total: 18\nGrand Total: 118\n"+taxes)
        result = validate_invoice(fields, items)
        assert next(c for c in result["checks"] if c["name"] == "Grand total")["status"] == "unknown"


def test_mismatch_and_rounding_tolerance():
    for total, expected in (("118.02","pass"), ("118.03","mismatch")):
        fields, items, _ = parse_invoice("Subtotal: 100\nIGST: 18\nGrand Total: "+total)
        assert next(c for c in validate_invoice(fields, items)["checks"] if c["name"] == "Grand total")["status"] == expected
    fields, items, _ = parse_invoice("Description | Qty | Rate | Amount\nTest | 2 | 10 | 25\nSubtotal: 25")
    assert validate_invoice(fields, items)["checks"][0]["status"] == "mismatch"


def test_tax_total_only_and_unknown_currency_not_assumed():
    fields, items, _ = parse_invoice("Subtotal: 100\nGST Total: 18\nGrand Total: 118")
    result = validate_invoice(fields, items)
    assert next(c for c in result["checks"] if c["name"] == "Grand total")["status"] == "pass"
    assert next(c for c in result["checks"] if c["name"].startswith("GST components"))["status"] == "unknown"


def test_numeric_bounds_and_bad_dates():
    for raw in ("1e999", "-1", "NaN", "Infinity", "9999999999999999999999999999999"):
        assert decimal(raw) is None
    assert decimal("1,234.50") == Decimal("1234.50")
    fields, _, _ = parse_invoice("Invoice Date: 31/02/2026\nGrand Total: nonsense")
    assert fields["invoice_date"]["value"] is None
    assert fields["grand_total"]["value"] is None


def test_currency_prefix_and_percentage_evidence():
    fields, _, _ = parse_invoice("Subtotal: INR 1,000.00\nCGST: 9% \u20b9 90.00\nSGST: Rs. 90.00\nGrand Total: 1180.00")
    assert fields["subtotal"]["value"] == "1000.00"
    assert fields["cgst"]["value"] == "90.00"
    assert fields["sgst"]["value"] == "90.00"