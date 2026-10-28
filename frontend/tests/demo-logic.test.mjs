import { test } from 'node:test';
import assert from 'node:assert/strict';
import { summarize, volumeByDate, compareDocuments, calculateTotals, validateReview } from '../src/lib/demo-logic.mjs';
import { checkSelection } from '../src/lib/upload-selection.mjs';
test('groups by full workspace date, separates months and years, converts offsets',()=>{
  assert.deepEqual(volumeByDate([{uploadedAt:'2025-10-28T00:00:00Z'},{uploadedAt:'2026-10-28T00:00:00Z'},{uploadedAt:'2026-11-28T00:00:00Z'},{uploadedAt:'2026-10-27T23:00:00Z'}]),[
    {date:'2025-10-28',count:1},{date:'2026-10-28',count:2},{date:'2026-11-28',count:1}]);
});
test('empty analytics and summary do not require fixture counts',()=>{
  assert.deepEqual(volumeByDate([]),[]);
  assert.equal(summarize([]).total,0);
  const s=summarize([{status:'Needs review',issues:2,type:'Invoice',uploadedAt:''},{status:'Pending',issues:0,type:'Purchase order',uploadedAt:''}]);
  assert.equal(s.review,1);assert.equal(s.pending,1);assert.equal(s.discrepancies,2);assert.equal(s.orders,1);
});
test('comparison identifies only independent differing fields with consistent totals',()=>{
  const po={vendor:'Acme Technologies',quantity:10,unitPrice:10000,taxRate:18};
  const invoice={...po,unitPrice:10400,taxRate:20};
  assert.deepEqual(calculateTotals(po),{subtotal:100000,tax:18000,total:118000});
  assert.deepEqual(calculateTotals(invoice),{subtotal:104000,tax:20800,total:124800});
  assert.deepEqual(compareDocuments(invoice,po).filter(r=>!r.matched).map(r=>r.key),['unitPrice','taxRate']);
  assert.ok(compareDocuments(po,po).every(r=>r.matched));
});
test('review requires a vendor, reference, and finite non-negative amount',()=>{
  const fields={vendor:'Acme',reference:'I-1',total:'0',notes:''};
  assert.equal(validateReview(fields),null);
  for(const total of ['', '-1','NaN','Infinity']) assert.ok(validateReview({...fields,total}));
  assert.ok(validateReview({...fields,vendor:' '}));
});
const pdf=(name='a.pdf')=>({name,type:'application/pdf',size:5,slice:()=>({arrayBuffer:async()=>new Uint8Array([37,80,68,70,45]).buffer})});
test('selection enforces five-file limit across batches, handles duplicates and read failures',async()=>{
  const existing=Array.from({length:5},(_,i)=>({name:i+'.pdf',size:5}));
  assert.equal((await checkSelection(existing,[pdf()])).accepted.length,0);
  assert.match((await checkSelection(existing,[pdf()])).errors[0],/five/);
  const result=await checkSelection([],[pdf(),pdf(),{...pdf('bad.pdf'),slice:()=>{throw Error('read');}}]);
  assert.equal(result.accepted.length,1);assert.equal(result.errors.length,2);
  assert.equal((await checkSelection(existing.slice(1),[pdf()])).accepted.length,1);
});
