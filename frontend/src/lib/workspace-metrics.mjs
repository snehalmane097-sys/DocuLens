/** Financial totals are comparable only with explicit shared ISO currency evidence. */
export function invoiceMetrics(records) {
 const known=records.filter(d=>/^\d+(?:\.\d{1,2})?$/.test(d.effective_fields?.grand_total?.value||''));
 const currencies=new Set(known.map(d=>d.effective_fields?.currency?.value).filter(v=>/^[A-Z]{3}$/.test(v||'')));
 const comparable=known.length>0&&currencies.size===1&&known.every(d=>/^[A-Z]{3}$/.test(d.effective_fields?.currency?.value||''));
 const cents=comparable?known.reduce((sum,d)=>{const [whole,fraction='']=d.effective_fields.grand_total.value.split('.');return sum+BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'));},0n):null;
 const currency=comparable?[...currencies][0]:null;
 const value=cents===null?null:`${cents/100n}.${String(cents%100n).padStart(2,'0')}`;
 return {known:known.length,missing:records.length-known.length,currency,value,coverage:records.length?Math.round(known.length/records.length*100):0};
}
export function amountLabel(raw) {
 if(!/^\d+(?:\.\d{1,2})?$/.test(raw||''))return 'Unknown';
 const [whole,fraction='']=raw.split('.');
 return whole.replace(/\B(?=(\d{3})+(?!\d))/g,',')+'.'+fraction.padEnd(2,'0');
}
