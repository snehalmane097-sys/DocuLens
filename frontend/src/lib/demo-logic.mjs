/** @param {Array<{status:string, issues:number, type:string, uploadedAt:string}>} records */
export function summarize(records) {
  return { total: records.length, processed: records.filter(d => d.status === 'Processed').length,
    review: records.filter(d => d.status === 'Needs review').length, pending: records.filter(d => d.status === 'Pending').length,
    discrepancies: records.reduce((sum,d) => sum + d.issues,0),
    invoices: records.filter(d => d.type === 'Invoice').length, orders: records.filter(d => d.type === 'Purchase order').length };
}
/** Group by full calendar date in the workspace timezone, including offset-crossing timestamps.
 * @param {Array<{uploadedAt:string}>} records */
export function volumeByDate(records) {
  const groups = new Map();
  const formatter = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year:'numeric', month:'2-digit', day:'2-digit' });
  for (const record of records) {
    const parts = formatter.formatToParts(new Date(record.uploadedAt));
    const part = type => parts.find(p => p.type === type)?.value;
    const key = part('year') + '-' + part('month') + '-' + part('day');
    groups.set(key, (groups.get(key) ?? 0) + 1);
  }
  return [...groups.entries()].sort(([a],[b]) => a.localeCompare(b)).map(([date,count]) => ({date,count}));
}
/** @param {{quantity:number, unitPrice:number, taxRate:number}} doc */
export function calculateTotals(doc) {
  const subtotal = Math.round(doc.quantity * doc.unitPrice * 100) / 100;
  const tax = Math.round(subtotal * doc.taxRate) / 100;
  return { subtotal, tax, total: Math.round((subtotal + tax) * 100) / 100 };
}
/** Deterministic field comparison for the explicitly selected fictional pair. No ML.
 * @param {{vendor:string, quantity:number, unitPrice:number, taxRate:number}} invoice
 * @param {{vendor:string, quantity:number, unitPrice:number, taxRate:number}} order */
export function compareDocuments(invoice, order) {
  const fields = [
    {key:'vendor', label:'Vendor', severity:'High', explanation:'Supplier names differ.'},
    {key:'quantity', label:'Quantity', severity:'High', explanation:'Invoice quantity differs from the purchase order.'},
    {key:'unitPrice', label:'Unit price', severity:'High', explanation:'Invoice unit price differs from the agreed price.'},
    {key:'taxRate', label:'Tax rate', severity:'Medium', explanation:'Invoice tax rate differs from the purchase order. Confirm the correct rate with a reviewer.'},
  ];
  return fields.map(field => ({...field, invoice:invoice[field.key], order:order[field.key], matched:invoice[field.key] === order[field.key]}));
}
/** @param {{vendor:string, reference:string, total:string, notes:string}} fields */
export function validateReview(fields) {
  if (!fields.vendor.trim() || !fields.reference.trim()) return 'Vendor and reference are required.';
  if (!fields.total.trim() || !Number.isFinite(Number(fields.total)) || Number(fields.total) < 0) return 'Enter a valid non-negative total.';
  return null;
}
