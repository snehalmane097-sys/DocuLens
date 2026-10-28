import { calculateTotals, compareDocuments } from './demo-logic.mjs';
// Fictional Acme pair. INR: 10 x 10,400 + 20% = 124,800;
// purchase order: 10 x 10,000 + 18% = 118,000. Two independent differences.
export const reconciliationExample = {
  invoiceId: 'doc-001', orderId: 'doc-002',
  invoice: { vendor:'Acme Technologies', quantity:10, unitPrice:10400, taxRate:20 },
  order: { vendor:'Acme Technologies', quantity:10, unitPrice:10000, taxRate:18 },
};
export const comparison = compareDocuments(reconciliationExample.invoice, reconciliationExample.order);
export const invoiceTotals = calculateTotals(reconciliationExample.invoice);
export const orderTotals = calculateTotals(reconciliationExample.order);
export const sampleIssues = [
  ...comparison.filter(row => !row.matched).map(row => ({ documentId:'doc-001', category:row.label + ' difference', severity:row.severity, explanation:row.explanation })),
  { documentId:'doc-006', category:'Missing supplier reference', severity:'Medium', explanation:'A supplier reference is absent in this fictional review scenario.' },
];
