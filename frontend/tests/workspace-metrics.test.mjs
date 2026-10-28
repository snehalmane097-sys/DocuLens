import {test} from 'node:test';
import assert from 'node:assert/strict';
import {invoiceMetrics,amountLabel} from '../src/lib/workspace-metrics.mjs';
const row=(amount,currency)=>({effective_fields:{grand_total:{value:amount},currency:{value:currency}}});
test('financial summary never assumes a currency or combines mixed currencies',()=>{
 assert.equal(invoiceMetrics([row('100.00'),row('200.00')]).value,null);
 assert.equal(invoiceMetrics([row('100.00','INR'),row('200.00','USD')]).value,null);
 assert.equal(invoiceMetrics([row('100.00','INR'),row('200.00')]).value,null);
 assert.equal(invoiceMetrics([]).coverage,0);
});
test('explicit shared currency totals use exact decimal cents',()=>{
 const metrics=invoiceMetrics([row('0.10','INR'),row('0.20','INR'),row(null,'INR')]);
 assert.equal(metrics.value,'0.30');assert.equal(metrics.currency,'INR');assert.equal(metrics.known,2);assert.equal(metrics.missing,1);
 assert.equal(amountLabel('64390.00'),'64,390.00');assert.equal(amountLabel(null),'Unknown');
});
