"""Conservative field/table extraction and separate arithmetic checks."""
from decimal import Decimal, ROUND_HALF_UP
from .invoice_rules import parse_fields, parse_number
from .invoice_tables import parse_items

TOLERANCE = Decimal("0.02")

def decimal(value):
    return parse_number(value)


def amount(value):
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_invoice(text):
    fields, _, warnings = parse_fields(text)
    items = parse_items(text)
    if not items:
        warnings.append("No supported line-item table found. Supported tables require Description/Qty/Rate/Amount headers and pipe, tab, or stable double-space columns; optional Tax/Tax % columns. No rows are inferred from loose text.")
    warnings.append("Label and bounded party-position rules require review; GSTIN identity, GST compliance, and legal correctness are not verified. Dates using slashes are interpreted day/month/year.")
    return fields, items, warnings


def validate_invoice(fields, items):
    checks = []
    def value(key):
        raw = fields[key]["value"]
        return Decimal(raw) if raw is not None else None
    def add(name, expected, actual, explanation):
        status = "unknown" if expected is None or actual is None else ("pass" if abs(expected-actual) <= TOLERANCE else "mismatch")
        checks.append({"name": name, "status": status, "calculated": amount(expected) if expected is not None else None, "extracted": amount(actual) if actual is not None else None, "explanation": explanation})
    for index, item in enumerate(items):
        qty, rate, total = (Decimal(item[k]) if item[k] is not None else None for k in ("quantity", "unit_rate", "line_total"))
        add("Line " + str(index+1) + " amount", qty*rate if qty is not None and rate is not None else None, total, "Quantity x unit rate versus stated pre-tax line amount; discounts and tax-inclusive rates are unsupported.")
        if item["tax_rate"] is not None:
            base = total
            tax = Decimal(item["tax_amount"]) if item["tax_amount"] is not None else None
            add("Line " + str(index+1) + " tax", base*Decimal(item["tax_rate"])/100 if base is not None else None, tax, "Stated pre-tax line amount x stated tax percentage versus line tax amount.")
    line_sum = sum((Decimal(i["line_total"]) for i in items), Decimal(0)) if items and all(i["line_total"] is not None for i in items) else None
    add("Line amounts versus subtotal", line_sum, value("subtotal"), "Sum of recognized line amounts only. Completeness of the table cannot be guaranteed; discounts/charges are not inferred.")

    cgst, sgst, igst = value("cgst"), value("sgst"), value("igst")
    split_present = cgst is not None or sgst is not None
    mixed = split_present and igst is not None and igst != 0 and ((cgst or 0) != 0 or (sgst or 0) != 0)
    component_unknown = any(fields[k]["value"] is None and fields[k]["method"] != "not_found_or_ambiguous" for k in ("cgst", "sgst", "igst"))
    tax = None
    if not mixed and not component_unknown:
        if split_present and cgst is not None and sgst is not None and (igst is None or igst == 0):
            tax = cgst + sgst
        elif igst is not None and not ((cgst or 0) != 0 or (sgst or 0) != 0):
            tax = igst
    add("GST components versus stated GST total", tax, value("gst_total"), "CGST + SGST OR IGST, never both; missing counterpart or mixed non-zero structures are unknown.")
    if mixed:
        checks.append({"name":"Tax structure", "status":"unknown", "calculated":None, "extracted":None, "explanation":"Both split GST and IGST have non-zero values. Tax structure is ambiguous; no components were summed."})
    # Explicit GST total can be used when no component labels are found, but not to hide an ambiguous structure.
    if tax is None and not split_present and igst is None and not component_unknown:
        tax = value("gst_total")
    subtotal = value("subtotal")
    shipping_field = fields.get("shipping_amount", {"value":None,"method":"not_found_or_ambiguous"})
    shipping = Decimal(shipping_field["value"]) if shipping_field["value"] is not None else Decimal(0) if shipping_field["method"] == "not_found_or_ambiguous" else None
    before_round = subtotal+tax+shipping if subtotal is not None and tax is not None and shipping is not None else None
    if fields.get("pre_round_total", {}).get("method", "not_found_or_ambiguous") != "not_found_or_ambiguous":
        add("Pre-round total", before_round, value("pre_round_total"), "Subtotal + selected tax + explicit shipping (if present) versus explicitly labelled pre-round total.")
    round_field = fields.get("round_off", {"value":None,"method":"not_found_or_ambiguous"})
    if round_field["value"] is not None:
        expected = before_round + Decimal(round_field["value"]) if before_round is not None else None
        explanation = "Subtotal + selected tax + explicit shipping (if present) + explicitly extracted signed round-off versus final payable total. Other charges/discounts are not inferred."
    elif round_field["method"] != "not_found_or_ambiguous":
        expected = None
        explanation = "Round-off label was present but its value is unknown; final total cannot be checked."
    else:
        expected = before_round
        explanation = "Subtotal + selected tax + explicit shipping (if present); no round-off label was found. Unrecognized charges or adjustments require human review."
    add("Grand total", expected, value("grand_total"), explanation)
    # Independent stated-total check does not resolve unknown/conflicting tax components.
    if tax is None and value("gst_total") is not None and subtotal is not None and shipping is not None and not mixed:
        adjustment = Decimal(round_field["value"]) if round_field["value"] is not None else Decimal(0) if round_field["method"] == "not_found_or_ambiguous" else None
        add("Payable using stated tax total", subtotal+value("gst_total")+shipping+adjustment if adjustment is not None else None, value("grand_total"), "Independent subtotal + explicitly stated tax total + shipping + round-off check. Does not verify unknown tax components or replace extracted values.")
    missing = [key for key in ("invoice_number", "invoice_date", "supplier_name", "subtotal", "grand_total") if fields[key]["value"] is None]
    for key in missing:
        checks.append({"name":key, "status":"unknown", "calculated":None, "extracted":None, "explanation":"Required review field could not be extracted reliably."})
    return {"tolerance":str(TOLERANCE), "checks":checks, "mismatches":sum(c["status"] == "mismatch" for c in checks), "unknown":sum(c["status"] == "unknown" for c in checks), "passed":sum(c["status"] == "pass" for c in checks)}
