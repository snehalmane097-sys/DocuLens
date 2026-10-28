"""Synthetic layout approximations; not a copy or verification of a real invoice."""
from app.invoice import parse_invoice, validate_invoice, decimal
from app.invoice_rules import parse_fields

LAYOUT = """Orion Fabrication
GSTIN: 27ABCDE1234F1Z5
Cedar Components India Pvt. Ltd.
Bill To
12 Industrial Road
Contact: 9999999999
GSTIN:
29PQRSX9876L1Z2
Invoice No.:
INV/2026/042
Invoice
Date:
28/10/2026
Taxable
Amount:
INR
1,00,000.00
CGST @ 9%:
9,000.00
SGST Amount:
Rs. 9,000.00
GST Amount:
18,000.00
Grand Total (INR):
1,18,000.00
"""


def test_position_wrapped_labels_and_party_gstin_evidence():
    fields, candidates, warnings = parse_fields(LAYOUT)
    expected = {
        "supplier_name":"Orion Fabrication", "buyer_name":"Cedar Components India Pvt. Ltd.",
        "supplier_gstin":"27ABCDE1234F1Z5", "buyer_gstin":"29PQRSX9876L1Z2",
        "invoice_number":"INV/2026/042", "invoice_date":"2026-10-28",
        "subtotal":"100000.00", "cgst":"9000.00", "sgst":"9000.00",
        "gst_total":"18000.00", "grand_total":"118000.00",
    }
    for key,value in expected.items():
        assert fields[key]["value"] == value, (key, fields[key])
        assert fields[key]["evidence"]
    assert fields["igst"]["value"] is None
    assert fields["gstin"]["value"] is None
    assert [(c["value"],c["party"]) for c in candidates] == [
        ("27ABCDE1234F1Z5","supplier"),("29PQRSX9876L1Z2","buyer")]
    assert any("Multiple GSTIN" in warning for warning in warnings)
    assert "requires_review" in fields["supplier_name"]["method"]
    parsed, items, _ = parse_invoice(LAYOUT)
    assert items == []  # This layout description contains no reliable item table.
    result = validate_invoice(parsed,items)
    grand = next(c for c in result["checks"] if c["name"] == "Grand total")
    assert grand["status"] == "pass"
    assert grand["calculated"] == "118000.00"
    assert result["mismatches"] == 0
    assert result["unknown"] == 1  # No invented line sum.


def test_same_party_conflicts_and_unassociated_ids_are_retained():
    text = "Supplier: Example Test Company\nSupplier GSTIN: 27ABCDE1234F1Z5\nSupplier GSTIN: 29PQRSX9876L1Z2"
    fields,candidates,warnings = parse_fields(text)
    assert fields["supplier_gstin"]["value"] is None
    assert fields["gstin"]["value"] is None
    assert len(candidates) == 2
    assert all(c["party"] == "supplier" for c in candidates)
    fields,candidates,_ = parse_fields("GSTIN: 27ABCDE1234F1Z5\nGSTIN: 29PQRSX9876L1Z2")
    assert all(c["party"] == "unknown" for c in candidates)
    assert fields["supplier_name"]["value"] is None
    assert fields["buyer_gstin"]["value"] is None


def test_bill_to_name_after_label_and_ambiguous_adjacent_names():
    fields,_,_ = parse_fields("Supplier: Example Parts Company\nBill To:\nForest Supplies Ltd.\nBuyer GSTIN:\n29PQRSX9876L1Z2")
    assert fields["buyer_name"]["value"] == "Forest Supplies Ltd."
    assert fields["buyer_gstin"]["value"] == "29PQRSX9876L1Z2"
    fields,_,warnings = parse_fields("Before Company Ltd.\nBill To\nAfter Company Ltd.")
    assert fields["buyer_name"]["value"] is None
    assert any("buyer_name" in w for w in warnings)


def test_wrapping_never_consumes_another_label_blank_or_page():
    for text in ("Invoice No.:\nInvoice Date:\n2026-10-28",
                 "Invoice No.:\n\nINV-1",
                 "Invoice No.:\fINV-1"):
        fields,_,_ = parse_fields(text)
        assert fields["invoice_number"]["value"] is None
    fields,_,_ = parse_fields("Invoice No.:\nA-1\nInvoice Number: B-2\nSubtotal: 100\nTaxable Value: 200\nIGST: 18\nGrand Total: 118")
    assert fields["invoice_number"]["value"] is None
    assert fields["subtotal"]["value"] is None
    result = validate_invoice(fields,[])
    assert next(c for c in result["checks"] if c["name"] == "Grand total")["status"] == "unknown"


def test_indian_grouping_percentages_and_invalid_currency_are_not_guessed():
    for text,expected in (("1,23,456.78","123456.78"),("12,345.67","12345.67"),("12,34,567.89","1234567.89")):
        assert str(decimal(text)) == expected
    for raw in ("1,23","12,345,67","1 234","(100)","-100","1e6"):
        assert decimal(raw) is None
    fields,_,_ = parse_fields("Sub-total: \u20b9 1,23,456.78/-\nI.G.S.T.: 18% 22,222.22\nNet Payable: 1,45,679.00")
    assert fields["subtotal"]["value"] == "123456.78"
    assert fields["igst"]["value"] == "22222.22"
    assert fields["grand_total"]["value"] == "145679.00"
    assert next(c for c in validate_invoice(fields,[])["checks"] if c["name"] == "Grand total")["status"] == "pass"
    fields,_,_ = parse_fields("Subtotal: USD 100\nIGST: 18%\nGrand Total: 118")
    assert fields["subtotal"]["value"] is None
    assert fields["igst"]["value"] is None


def test_missing_financial_fields_and_incomplete_rows_remain_unknown():
    fields, items, warnings = parse_invoice("Example Engineering\nGSTIN: 27ABCDE1234F1Z5\nOther Parts Ltd.\nBill To\nContact: 12345\nGSTIN: 29PQRSX9876L1Z2\nDescription Qty Rate\nSome part\n2\n100")
    assert fields["invoice_number"]["value"] is None
    assert fields["grand_total"]["value"] is None
    assert items == []
    assert validate_invoice(fields,items)["passed"] == 0
    assert validate_invoice(fields,items)["mismatches"] == 0
