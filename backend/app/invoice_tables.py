"""Tables require explicit headers and stable column separators. No visual guessing."""
import re
from .invoice_rules import parse_number, money

ALIASES = {"description":"description","item":"description","particulars":"description",
           "item description":"description","description of goods":"description",
           "qty":"quantity","quantity":"quantity","rate":"unit_rate",
           "unit rate":"unit_rate","unit price":"unit_rate","price":"unit_rate",
           "amount":"line_total","line total":"line_total","taxable amount":"line_total",
           "tax":"tax_amount","tax amount":"tax_amount","tax %":"tax_rate",
           "tax rate":"tax_rate","hsn":"hsn","hsn/sac":"hsn","unit":"unit","uom":"unit",
           "s.no":"serial","sr no":"serial"}
UNITS = r"(?:NOS|PCS|EA|KG|KGS|LTR|L|M|BOX|SET|HRS)"


def split_cells(line,mode):
    if mode == "pipe":
        raw = line.strip()
        raw = raw[1:-1] if raw.startswith("|") and raw.endswith("|") else raw
        return [cell.strip() for cell in raw.split("|")]
    if mode == "tab":
        return [cell.strip() for cell in line.split("\t")]
    return [cell.strip() for cell in re.split(r"\s{2,}",line.strip())]


def parse_items(text):
    items = []
    headers,mode = None,None
    for line in text.split("\n"):
        if not line.strip() or "\f" in line:
            headers,mode = None,None
            continue
        detected = "pipe" if "|" in line else "tab" if "\t" in line else "space"
        cells = split_cells(line,detected)
        names = [re.sub(r"\s*\((?:INR|Rs\.?)\)\s*$","",cell,flags=re.I).lower().rstrip(".") for cell in cells]
        normalized = [ALIASES.get(name) for name in names]
        if all(key in normalized for key in ("description","quantity","unit_rate","line_total")) and None not in normalized and len(set(normalized)) == len(normalized):
            headers,mode = normalized,detected
            continue
        if headers is None or detected != mode or len(cells) != len(headers):
            headers,mode = None,None
            continue
        row = dict(zip(headers,cells))
        description = row["description"]
        if not description or all(re.fullmatch(r"[- ]*",cell) for cell in cells):
            continue
        numeric_keys = ("quantity","unit_rate","line_total","tax_amount","tax_rate")
        if all(not row.get(key,"") for key in headers if key != "description"):
            if items:
                items[-1]["description"] = (items[-1]["description"] + " " + description)[:500]
                items[-1]["evidence"] = (items[-1]["evidence"] + "\n" + line)[:1000]
            continue
        item = {key:None for key in numeric_keys}
        item.update(description=description[:500],evidence=line[:1000])
        quantity = re.fullmatch(r"(.+?)(?:\s+"+UNITS+r")?",row["quantity"],re.I)
        number = parse_number(quantity[1]) if quantity else None
        item["quantity"] = str(number) if number is not None else None
        for key in ("unit_rate","line_total","tax_amount"):
            item[key] = money(row.get(key,""))
        rate = row.get("tax_rate","").strip()
        number = parse_number(rate[:-1].strip() if rate.endswith("%") else rate)
        item["tax_rate"] = str(number) if number is not None else None
        if any(item[k] is not None for k in ("quantity","unit_rate","line_total")):
            items.append(item)
    return items
