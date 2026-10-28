import { summarize, volumeByDate } from './demo-logic.mjs';
import { sampleIssues } from './reconciliation-data';
import type { DocumentRecord } from './types';
// Fictional UI fixtures. No OCR or model has produced these values.
const baseDocuments: DocumentRecord[] = [
  { id: 'doc-001', filename: 'INV-2026-0842.pdf', reference: 'INV-2026-0842', vendor: 'Acme Technologies', type: 'Invoice', uploadedAt: '2026-10-28T09:42:00+05:30', status: 'Needs review', total: 124800, issues: 2 },
  { id: 'doc-002', filename: 'PO-2026-0318.pdf', reference: 'PO-2026-0318', vendor: 'Acme Technologies', type: 'Purchase order', uploadedAt: '2026-10-28T09:38:00+05:30', status: 'Processed', total: 118000, issues: 0 },
  { id: 'doc-003', filename: 'INV-NW-1026.pdf', reference: 'INV-NW-1026', vendor: 'Northwind Supplies', type: 'Invoice', uploadedAt: '2026-10-27T16:15:00+05:30', status: 'Processed', total: 47200, issues: 0 },
  { id: 'doc-004', filename: 'office-equipment.jpg', reference: 'INV-OS-091', vendor: 'Orbit Office', type: 'Invoice', uploadedAt: '2026-10-27T14:20:00+05:30', status: 'Pending', total: 23600, issues: 0 },
  { id: 'doc-005', filename: 'PO-2026-0316.pdf', reference: 'PO-2026-0316', vendor: 'Northwind Supplies', type: 'Purchase order', uploadedAt: '2026-10-26T11:05:00+05:30', status: 'Processed', total: 47200, issues: 0 },
  { id: 'doc-006', filename: 'INV-ST-448.png', reference: 'INV-ST-448', vendor: 'Studio Stationery', type: 'Invoice', uploadedAt: '2026-10-26T10:30:00+05:30', status: 'Needs review', total: 15700, issues: 1 },
];
export const documents: DocumentRecord[] = baseDocuments.map(doc => ({ ...doc, issues: sampleIssues.filter(issue => issue.documentId === doc.id).length }));
export const attentionItems = documents.filter(doc => doc.issues > 0).map(doc => ({ ...doc, title: doc.id === 'doc-001' ? 'Invoice totals differ' : 'A field needs a closer look' }));
export const activity = volumeByDate(documents);
export const activityRange = activity.length ? activity[0].date + ' to ' + activity[activity.length - 1].date : 'No activity';
export const money = (value: number) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(value);
export const date = (value: string) => new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(new Date(value));
export const summary = summarize(documents);
