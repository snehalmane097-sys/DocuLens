import copy
from pathlib import Path
import pytest
from app.pdf_analysis import analyze_pdf
from app.storage import DocumentStore, Conflict
from app.reconciliation import create_report, get_report, review_report
from app.invoice import parse_invoice, validate_invoice
from app.pdf_fonts import financial_glyph_map
from test_pdf_analysis import make_pdf

def analysis(total="118"):
    return analyze_pdf("test.pdf", make_pdf(["Supplier: Synthetic Supplies", "Invoice No: TEST-1", "Invoice Date: 2026-10-28", "Subtotal: 100", "IGST: 18", "GST Total: 18", "Grand Total: "+total]))

def test_restart_idempotency_review_and_reprocess(tmp_path):
    path=tmp_path/"records.sqlite3"
    store=DocumentStore(path)
    original=store.save(analysis(),b"pdf-one")
    assert DocumentStore(path).get(original["id"])["analysis"]==original["analysis"]
    assert store.save(analysis("999"),b"pdf-one")["id"]==original["id"]
    assert len(store.list())==1
    reviewed=store.review_document(original["id"],1,{},"Verified source evidence","approved")
    assert reviewed["version"]==2
    assert reviewed["review_status"]=="approved"
    with pytest.raises(Conflict):
        store.review_document(original["id"],1,{},"Stale review attempt","pending")
    assert len(store.history(original["id"]))==1
    with pytest.raises(Conflict):
        store.save(analysis(),b"pdf-one",1)
    reprocessed=store.save(analysis(),b"pdf-one",2)
    assert reprocessed["version"]==3 and reprocessed["review_status"]=="pending"
    assert len(store.list())==1

def test_override_preserves_original_and_revalidates(tmp_path):
    store=DocumentStore(tmp_path/"records.sqlite3")
    doc=store.save(analysis("119"),b"pdf")
    assert doc["review_validation"]["mismatches"]==1
    reviewed=store.review_document(doc["id"],1,{"grand_total":"118"},"Verified against original PDF","approved")
    assert reviewed["analysis"]["fields"]["grand_total"]["value"]=="119.00"
    assert reviewed["effective_fields"]["grand_total"]["value"]=="118.00"
    assert reviewed["review_validation"]["mismatches"]==0
    with pytest.raises(ValueError):
        store.review_document(doc["id"],2,{"grand_total":"1e6"},"Invalid numeric token","pending")

def test_duplicates_reconciliation_review_and_stale_versions(tmp_path):
    store=DocumentStore(tmp_path/"records.sqlite3")
    a=store.save(analysis(),b"one"); b=store.save(analysis("119"),b"two")
    assert store.duplicates(a["id"])[0]["id"]==b["id"]
    report=create_report(store,a["id"],b["id"])
    mismatch=next(r for r in report["rows"] if r["field"]=="grand_total")
    assert mismatch["status"]=="mismatch" and mismatch["expected_evidence"]
    saved=review_report(store,report["id"],1,{r["id"]:"Verified comparison evidence" for r in report["rows"] if r["status"]!="matched"})
    assert saved["status"]=="reviewed" and saved["mismatches"]==1
    with pytest.raises(Conflict):
        review_report(store,report["id"],1,{})
    store.review_document(a["id"],1,{},"Source independently reviewed","approved")
    assert get_report(store,report["id"])["stale"]
    with pytest.raises(Conflict):
        review_report(store,report["id"],2,{})

def test_unrecoverable_font_does_not_guess():
    assert financial_glyph_map(b"invalid embedded font")=={}

@pytest.mark.parametrize("ending",["004","006"])
def test_actual_pdf_and_exact_text_regression(ending):
    path=Path("C:/ACCUTECH BILLS/AE262709"+ending+".pdf")
    if not path.exists(): pytest.skip("Private original PDF is not available on this machine")
    result=analyze_pdf(path.name,path.read_bytes())
    fields=result["fields"]
    expected={"004":{"invoice_number":"AE 26-27/09/004","invoice_date":"2026-09-09","quantity":"36","unit_rate":"365.00","subtotal":"13140.00","cgst":"1182.60","sgst":"1182.60","gst_total":"2365.20","round_off":"-0.20","grand_total":"15505.00"}, "006":{"invoice_number":"AE 26-27/09/006","subtotal":"53767.50","gst_total":"9822.16","shipping_amount":"800.00","round_off":"0.34","grand_total":"64390.00"}}[ending]
    for key,value in expected.items():
        assert fields[key]["value"]==value,(key,fields[key])
        assert fields[key]["evidence"]
    fixture=Path(__file__).parent/"fixtures"/("AE262709"+ending+".decoded.txt")
    text=fixture.read_text(encoding="utf-8")
    parsed,items,_=parse_invoice(text)
    for key,value in expected.items(): assert parsed[key]["value"]==value
    assert any(c["status"]=="pass" and c["name"] in ("Grand total","Payable using stated tax total") for c in validate_invoice(parsed,items)["checks"])
    assert fields["pre_round_total"]["value"] is None
    if ending=="006":
        assert fields.get("quantity",{}).get("value") is None # first row is not document total
        assert fields["cgst"]["value"] is None # incomplete repeated-HSN tax table remains unsupported


@pytest.mark.parametrize("ending",["004","006"])
def test_saved_decoded_text_without_original_pdf(ending):
    fixture=Path(__file__).parent/"fixtures"/("AE262709"+ending+".decoded.txt")
    fields,items,_=parse_invoice(fixture.read_text(encoding="utf-8"))
    validation=validate_invoice(fields,items)
    assert fields["invoice_number"]["value"].endswith("/"+ending)
    assert fields["grand_total"]["value"]==("15505.00" if ending=="004" else "64390.00")
    assert validation["mismatches"]==0
    if ending=="006":
        assert fields["subtotal"]["value"]=="53767.50"
        assert fields["shipping_amount"]["value"]=="800.00"
        check=next(c for c in validation["checks"] if c["name"]=="Payable using stated tax total")
        assert check["calculated"]=="64390.00" and check["status"]=="pass"
        fields["grand_total"]["value"]="64391.00"
        assert validate_invoice(fields,items)["mismatches"]==1
    assert all(f["evidence"] for f in fields.values() if f["value"] is not None)

def test_raw_extraction_fixture_preserves_original_bytes():
    import hashlib
    raw=(Path(__file__).parent/"fixtures"/"AE262709004.extracted.txt").read_bytes()
    assert hashlib.sha256(raw).hexdigest()=="14a9ba1fbf21159f3349e20caeabd48ccfcf956af72fe216f69f1ff9c49d41ab"


def test_actual_006_stale_analysis_requires_explicit_reprocess(tmp_path):
    text=(Path(__file__).parent/'fixtures'/'AE262709006.decoded.txt').read_text(encoding='utf-8')
    fields,items,warnings=parse_invoice(text)
    current=analysis()
    current.update(filename='AE262709006.pdf',fields=fields,line_items=items,warnings=warnings,text_excerpt=text)
    current['validation']=validate_invoice(fields,items)
    old=copy.deepcopy(current)
    del old['fields']['shipping_amount']
    old['validation']=validate_invoice(old['fields'],items)
    assert old['validation']['mismatches']==1
    store=DocumentStore(tmp_path/'records.sqlite3')
    original=store.save(old,b'identical-pdf-bytes')
    # Ordinary reuploads cannot overwrite historical extraction or reviewer work.
    assert store.save(current,b'identical-pdf-bytes')['analysis']==old
    refreshed=store.save(current,b'identical-pdf-bytes',1)
    assert refreshed['id']==original['id'] and refreshed['version']==2
    assert refreshed['effective_fields']['subtotal']['value']=='53767.50'
    assert refreshed['effective_fields']['shipping_amount']['value']=='800.00'
    assert refreshed['effective_fields']['shipping_amount']['evidence']
    assert refreshed['review_validation']['mismatches']==0
    assert len(store.list())==1
    import json
    archive=json.loads(store.history(original['id'])[0]['payload'])
    assert archive['previous_analysis']==old
    # A genuinely incorrect subtotal is detected, never repaired by arithmetic.
    invalid=copy.deepcopy(fields);invalid['subtotal']['value']='5767.50'
    assert validate_invoice(invalid,items)['mismatches']==1
    assert invalid['subtotal']['value']=='5767.50'


def test_future_review_revision_is_rejected_before_field_validation(tmp_path):
    store=DocumentStore(tmp_path/'records.sqlite3')
    doc=store.save(analysis(),b'pdf')
    with pytest.raises(Conflict):
        store.review_document(doc['id'],2,{'grand_total':'invalid'},'Future revision request','pending')
    assert store.get(doc['id'])['version']==1
    assert store.history(doc['id'])==[]
