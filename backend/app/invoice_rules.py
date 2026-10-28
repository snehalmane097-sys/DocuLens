"""Bounded label and party rules. Positional associations always require review."""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

GSTIN = r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]"
GROUPED = r"(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})"
NUMBER = GROUPED + r"(?:\.\d{1,6})?"
LABELS = {
    "invoice_number": r"(?:tax\s*)?(?:invoice|inv\.?)\s*(?:no\.?|number|num\.?|#|id)",
    "invoice_date": r"(?:(?:tax\s*)?invoice\s*(?:date|dt\.?)|inv\.?\s*date|dated|date)",
    "supplier_name": r"(?:supplier|seller|vendor|from)(?:\s*(?:name|details))?",
    "buyer_name": r"(?:bill\s*to|billed\s*to|buyer(?:\s*name)?|customer(?:\s*name)?)",
    "subtotal": r"(?:sub[ -]?total|taxable\s*(?:amount|value|total)|total\s*taxable\s*(?:amount|value))",
    "cgst": r"C\.?G\.?S\.?T\.?(?:\s*amount)?",
    "sgst": r"S\.?G\.?S\.?T\.?(?:\s*amount)?",
    "igst": r"I\.?G\.?S\.?T\.?(?:\s*amount)?",
    "gst_total": r"(?:total\s*GST|GST\s*total|total\s*tax(?:\s*amount)?|tax\s*(?:total|amount)|GST\s*amount)(?:\s*\(\+\))?",
    "grand_total": r"(?:final\s*(?:invoice\s*)?total|rounded\s*total|grand\s*total|invoice\s*total|total\s*amount|amount\s*(?:payable|due)|net\s*payable)",
    "pre_round_total": r"(?:pre[ -]?round(?:ing|off)?\s*total|total\s*before\s*round(?:ing|[ -]?off)?|amount\s*before\s*round[ -]?off)",
    "shipping_amount": r"(?:shipping|freight)(?:\s*(?:amount|charges?))?(?:\s*\(\+\))?",
    "round_off": r"(?:round[ -]?off(?:\s*amount)?|rounding(?:\s*adjustment)?)(?:\s*\([+-]\))?",
}
NUMERIC = {"shipping_amount", "subtotal", "cgst", "sgst", "igst", "gst_total", "grand_total", "round_off", "pre_round_total"}
CURRENCY = r"(?:INR|Rs\.?|\u20b9)"


def parse_number(raw):
    if not isinstance(raw, str):
        return None
    raw = raw.strip().replace("\u00a0", " ").replace("\u202f", " ")
    if len(raw) > 40 or not re.fullmatch(r"\+?" + NUMBER, raw):
        return None
    try:
        value = Decimal(raw.replace(",", ""))
        return value if value.is_finite() and 0 <= value <= Decimal("1000000000000") else None
    except InvalidOperation:
        return None



def money(raw, signed=False):
    """Consume the ENTIRE monetary value; a tax percentage alone is never an amount."""
    raw = raw.strip().replace("\u2212", "-")
    sign = ""
    if signed:
        prefix = re.match(r"^([+-])\s*",raw)
        if prefix:
            sign, raw = prefix[1], raw[prefix.end():]
    pattern = (r"(?:" + CURRENCY + r"\s*)?" +
               (r"([+-]?\s*" if signed and not sign else r"(") +
               NUMBER + r")(?:\s*/-)?")
    match = re.fullmatch(pattern,raw,re.I)
    if not match:
        return None
    token = match[1].replace(" ", "")
    if signed and token.startswith(("+","-")):
        if sign:
            return None
        sign, token = token[0], token[1:]
    number = parse_number(token)
    if number is None:
        return None
    if sign == "-":
        number = -number
    return str(number.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))


def tax_money(raw):
    # A rate must be a complete percentage token, separated from a complete amount.
    rate = re.match(r"^@?\s*\d+(?:\.\d+)?\s*%(?:\s*[:=]\s*|\s+)",raw)
    return money(raw[rate.end():]) if rate else money(raw)


def parse_date(raw):
    weekday = None
    prefix = re.match(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s*,?\s+",raw,re.I)
    if prefix:
        weekday = prefix[1].lower()
        raw = raw[prefix.end():]
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%d.%m.%Y",
                "%d %b %Y","%d %B %Y","%d-%b-%Y"):
        try:
            value = datetime.strptime(raw,fmt)
            if weekday and value.strftime("%A").lower() != weekday:
                return None
            return value.date().isoformat()
        except ValueError:
            pass
    return None


def unknown(method="not_found_or_ambiguous", evidence=None):
    return {"value":None,"evidence":evidence,"method":method}


def choose(candidates, key, warnings):
    unique = {c["value"] for c in candidates}
    if len(unique) > 1:
        warnings.append("Conflicting values for " + key + "; left unknown.")
        return unknown("conflicting_evidence", "\n".join(c["evidence"] for c in candidates)[:500])
    return candidates[0] if candidates else unknown()


def is_label(line):
    return any(re.match(r"^(?:" + label + r")(?:\s*[:=]|\s*$)", line, re.I) for label in LABELS.values()) or bool(re.match(r"^(?:(?:supplier|buyer|customer)\s*)?GST(?:IN|\s*(?:no\.?|number))\b",line,re.I))


def values_for(lines, label):
    """Match complete labels, then at most two bounded value lines."""
    full_label = r"(?:" + label + r")(?:\s*\(" + CURRENCY + r"\))?"
    for i,line in enumerate(lines):
        if not line or line == "\f":
            continue
        for width in (1,2):
            combined = " ".join(lines[i:i+width])
            if width == 2 and (i+1 >= len(lines) or not lines[i+1] or lines[i+1] == "\f"):
                continue
            label_only = bool(re.fullmatch(full_label + r"\s*[:=\-]?",combined,re.I))
            if width == 2 and not label_only:
                continue
            same = None if label_only or width == 2 else re.fullmatch(full_label + r"(?:\s*[:=]\s*|\s+)(.+)",line,re.I)
            if same:
                raw = same[1].strip()
                # Do not let a generic label prefix consume a longer, unrelated label.
                if is_label(raw):
                    continue
                if (re.fullmatch(CURRENCY,raw,re.I) or re.fullmatch(r"@?\s*\d+(?:\.\d+)?\s*%\s*[:=]?",raw)) and i+1 < len(lines) and lines[i+1] and lines[i+1] != "\f" and not is_label(lines[i+1]):
                    raw += " " + lines[i+1]
                    combined += "\n" + lines[i+1]
                yield raw,combined,"labelled_text_rule",i
                continue
            if not label_only:
                continue
            j = i+width
            if j >= len(lines) or not lines[j] or lines[j] == "\f" or is_label(lines[j]) or "|" in lines[j] or "\t" in lines[j]:
                # Keep evidence that the label was present, even when its value was absent.
                yield "",combined,"wrapped_label_rule",i
                continue
            raw = lines[j]
            evidence = lines[i:j+1]
            if re.fullmatch(CURRENCY,raw,re.I) and j+1 < len(lines) and lines[j+1] and not is_label(lines[j+1]) and lines[j+1] != "\f":
                raw += " " + lines[j+1]
                evidence = lines[i:j+2]
            yield raw,"\n".join(evidence),"wrapped_label_rule",i


def name_like(value):
    if not 3 <= len(value) <= 160 or len(value.split()) < 2:
        return False
    if re.search(r"[\d:@|/]", value) or is_label(value):
        return False
    return not re.search(r"\b(invoice|GSTIN|address|road|street|estate|area|phone|email|contact|district|state|pin|india only)\b",value,re.I)




def vertical_tax_summary(lines):
    """Single explicit HSN/rate/amount/tax row; never associate arbitrary nearby numbers."""
    found = {}
    consumed = set()
    for i in range(len(lines)):
        for headers,keys in [
            (["HSN/SAC","GST%","AMOUNT","CGST","SGST"],["hsn","rate","base","cgst","sgst"]),
            (["HSN/SAC","GST%","AMOUNT","IGST"],["hsn","rate","base","igst"]),
        ]:
            n=len(headers)
            if [l.upper() for l in lines[i:i+n]] != headers or i+2*n > len(lines):
                continue
            values=lines[i+n:i+2*n]
            if not all(parse_number(v) is not None for v in values):
                continue
            if not Decimal(0) <= parse_number(values[1]) <= Decimal(100):
                continue
            if i+2*n < len(lines) and not is_label(lines[i+2*n]):
                continue
            evidence="\n".join(lines[i:i+2*n])
            for offset,key in enumerate(keys):
                if key in ("cgst","sgst","igst"):
                    found.setdefault(key,[]).append({"value":money(values[offset]),"evidence":evidence,"method":"explicit_vertical_tax_summary_rule"})
            consumed.update(range(i,i+n))
    return found,consumed



def vertical_item_fields(lines):
    headers=["S.NO.","PARTICULARS","HSN/SAC","QTY","UNIT PRICE","GST","AMOUNT"]
    found={}
    for i in range(len(lines)):
        if [l.upper() for l in lines[i:i+7]] != headers:
            continue
        row=lines[i+7:i+16]
        if len(row)<8 or not row[0].isdigit() or not row[2].isdigit():
            continue
        qty= parse_number(row[3])
        if qty is None or not re.fullmatch(r"NOS|PCS|EA|KG|SET|HRS",row[4],re.I):
            continue
        rate=money(row[5])
        if rate is None or not re.fullmatch(r"\d+(?:\.\d+)?%",row[6]) or money(row[7]) is None:
            continue
        # A document-level quantity/rate is supported only for one row.
        if i+15 < len(lines) and lines[i+15].isdigit():
            continue
        evidence="\n".join(lines[i:i+15])
        for key,value in (("quantity",str(qty)),("unit_rate",rate)):
            found.setdefault(key,[]).append({"value":value,"evidence":evidence,"method":"explicit_vertical_item_columns_rule"})
    return found


def parse_fields(text):
    lines = [line.strip() for line in text.replace("\r\n","\n").replace("\r","\n").replace("\f","\n\f\n").split("\n")]
    fields,warnings = {},[]
    summary, consumed = vertical_tax_summary(lines)
    for key,label in LABELS.items():
        candidates,invalid = list(summary.get(key,[])),[]
        soft_invalid = []
        for raw,evidence,method,index in values_for(lines,label):
            if index in consumed:
                continue
            value = raw
            if key in NUMERIC:
                if key == "round_off":
                    value = money(raw,signed=True)
                    if value is not None and re.search(r'\(-\)', evidence.split('\n')[0]):
                        value = str(-abs(Decimal(value)))
                elif key in ("cgst","sgst","igst"):
                    value = tax_money(raw)
                else:
                    value = money(raw)
                # Bare next-line integers may be row indexes, counts, or GSTIN fragments.
                if method == "wrapped_label_rule" and re.fullmatch(r"\d+",raw):
                    value = None
            elif key == "invoice_date":
                value = parse_date(raw)
            elif key == "invoice_number":
                value = raw if (re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/_. -]{0,79}",raw)
                                and re.search(r"\d",raw) and not is_label(raw)) else None
            elif key in ("supplier_name","buyer_name"):
                value = raw if name_like(raw) else None
            if value is not None:
                candidates.append({"value":value,"evidence":evidence[:500],"method":method})
            elif key in NUMERIC or key in ("invoice_number", "invoice_date"):
                (soft_invalid if method == "wrapped_label_rule" else invalid).append(evidence[:500])
        if key == "invoice_number":
            for line in lines:
                match = re.fullmatch(r"INVOICE\s+([A-Za-z0-9][A-Za-z0-9/_. -]{0,79})",line,re.I)
                if match and re.search(r"\d",match[1]) and not re.match(r"(?:date|dated|GSTIN)\b",match[1],re.I):
                    candidates.append({"value":match[1],"evidence":line,"method":"explicit_invoice_heading_rule"})
        if not candidates:
            invalid += soft_invalid
        elif soft_invalid:
            warnings.append("Ignored incomplete wrapped/header candidates for " + key + "; explicit complete evidence was retained for human review.")
        if key == "grand_total" and candidates:
            def priority(candidate):
                label_line = candidate["evidence"].split("\n")[0]
                if re.match(r"^(?:final|rounded)",label_line,re.I):
                    return 3
                if re.match(r"^(?:grand|amount\s*(?:due|payable)|net\s*payable)",label_line,re.I):
                    return 2
                return 1
            highest = max(map(priority,candidates))
            excluded = [c for c in candidates if priority(c) < highest]
            candidates = [c for c in candidates if priority(c) == highest]
            if excluded:
                warnings.append("Final total uses the strongest explicit final/payable label; other total labels are retained for human review: " + "; ".join(c["evidence"] for c in excluded)[:400])
        if invalid and (key in NUMERIC or key in ("invoice_number", "invoice_date")):
            fields[key] = unknown("label_present_unparsed", "\n".join(invalid)[:500])
            warnings.append("A value for " + key + " is missing or is not a complete supported token; left unknown.")
        else:
            fields[key] = choose(candidates,key,warnings)
    for key, choices in vertical_item_fields(lines).items():
        fields[key] = choose(choices,key,warnings)
    parties,candidates,party_warnings = identify_parties(lines,fields)
    fields.update(parties)
    warnings += party_warnings
    return fields,candidates,warnings


def identify_parties(lines,fields):
    warnings = []
    supplier_positions = [i for i,line in enumerate(lines) if re.match(r"^(?:supplier|seller|vendor|from)\s*[:=]",line,re.I)]
    bill_positions = [i for i,line in enumerate(lines) if re.match(r"^(?:bill\s*to|billed\s*to|buyer|customer)(?:\s*[:=]|\s*$)",line,re.I)]
    bill = bill_positions[0] if len(bill_positions) == 1 else None
    supplier = fields["supplier_name"]
    buyer = fields["buyer_name"]
    if supplier["value"] is None and supplier["method"] == "not_found_or_ambiguous" and not supplier_positions:
        # Header name must be directly followed by a GSTIN (optional GSTIN label).
        header_candidates = []
        for i,line in enumerate(lines[:6]):
            if name_like(line) and i+1 < len(lines) and re.search(r"\b"+GSTIN+r"\b",lines[i+1],re.I) and (bill is None or i < bill-1):
                header_candidates.append({"value":line,"evidence":line+"\n"+lines[i+1],"method":"header_position_rule_requires_review","position":i})
        # Multiple plausible company headers never select the first silently.
        public = [{k:v for k,v in c.items() if k != "position"} for c in header_candidates]
        supplier = choose(public,"supplier_name",warnings)
        if supplier["value"] is not None:
            supplier_positions = [next(c["position"] for c in header_candidates if c["value"] == supplier["value"])]
    if bill is not None:
        nearby = []
        # Support a company heading immediately before Bill To OR a name after it.
        for i in (bill-1,bill+1):
            if i >= 0 and i < len(lines) and name_like(lines[i]):
                nearby.append({"value":lines[i],"evidence":"\n".join(lines[min(i,bill):max(i,bill)+1]),"method":"bill_to_position_rule_requires_review"})
        if buyer["value"] is not None:
            nearby.append(buyer)
        buyer = choose(nearby,"buyer_name",warnings)
    supplier_pos = supplier_positions[0] if len(supplier_positions) == 1 else None
    gstins = []
    for i,line in enumerate(lines):
        for match in re.finditer(r"\b"+GSTIN+r"\b",line.upper()):
            party,method = "unknown","unassociated_text_candidate"
            if re.search(r"\b(?:supplier|seller|vendor)\s*GST",line,re.I) or (i > 0 and re.fullmatch(r"(?:supplier|seller|vendor)\s*GST(?:IN|\s*no\.?)\s*:?",lines[i-1],re.I)):
                party,method = "supplier","explicit_party_gstin_label"
            elif re.search(r"\b(?:buyer|customer|recipient)\s*GST",line,re.I) or (i > 0 and re.fullmatch(r"(?:buyer|customer|recipient)\s*GST(?:IN|\s*no\.?)\s*:?",lines[i-1],re.I)):
                party,method = "buyer","explicit_party_gstin_label"
            elif bill is not None and bill <= i <= bill+12 and not any(is_label(l) and not re.match(r"^GST",l,re.I) for l in lines[bill+1:i]):
                party,method = "buyer","bill_to_block_rule_requires_review"
            elif supplier_pos is not None and supplier_pos <= i <= supplier_pos+3 and (bill is None or i < bill-1) and supplier["value"] is not None:
                party,method = "supplier","supplier_block_rule_requires_review"
            gstins.append({"value":match[0],"party":party,"evidence":"\n".join(lines[max(0,i-1):i+1])[:500],"method":method,"line":i+1})
    result = {"supplier_name":supplier,"buyer_name":buyer}
    for party in ("supplier","buyer"):
        choices = [{"value":c["value"],"evidence":c["evidence"],"method":c["method"]} for c in gstins if c["party"] == party]
        result[party+"_gstin"] = choose(choices,party+"_gstin",warnings)
    # Legacy generic field stays unknown whenever different GSTINs exist, even when parties differ.
    result["gstin"] = choose([{"value":c["value"],"evidence":c["evidence"],"method":"gstin_format_candidate"} for c in gstins],"GSTIN candidates",warnings)
    if len({c["value"] for c in gstins}) > 1:
        warnings.append("Multiple GSTIN candidates retained with party evidence; the generic GSTIN field is unknown. Review associations; no GSTIN identity or checksum verification is performed.")
    if any("requires_review" in f["method"] for f in result.values()):
        warnings.append("Party names/GSTINs associated by document position are hypotheses requiring human review.")
    return result,gstins,warnings
