'use client';
import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, FileText, Save, RotateCcw } from 'lucide-react';
import type { DocumentRecord } from '@/lib/types';
import { sampleIssues } from '@/lib/reconciliation-data';
import { validateReview } from '@/lib/demo-logic.mjs';
import { date, money } from '@/lib/mock-data';
import { Badge, PageHeading, Panel } from './ui';
export function DocumentReview({ document:doc }: {document:DocumentRecord}) {
  const initial = {vendor:doc.vendor,reference:doc.reference,total:String(doc.total),notes:''};
  const [fields,setFields] = useState(initial);
  const [snapshot,setSnapshot] = useState(initial);
  const [saved,setSaved] = useState(false);
  const [error,setError] = useState('');
  const dirty = JSON.stringify(fields) !== JSON.stringify(snapshot);
  function update(key:keyof typeof initial,value:string) { setFields({...fields,[key]:value}); setError(''); }
  const issues = sampleIssues.filter(issue=>issue.documentId === doc.id);
  return <><Link className="back-link" href="/documents"><ArrowLeft size={15}/>Back to documents</Link><PageHeading eyebrow="DOCUMENT REVIEW" title={doc.reference} description={doc.filename} action={<Badge status={doc.status}/>}/><div className="demo-notice">Fictional fixture · Fields are manually authored, not OCR results. All edits and saved snapshots disappear on refresh or navigation.</div>
    <div className="phase-two-column"><div className="review-side"><Panel title="Document metadata" subtitle="Original sample record"><dl className="metadata-grid"><dt>Vendor</dt><dd>{doc.vendor}</dd><dt>Type</dt><dd>{doc.type}</dd><dt>Uploaded</dt><dd>{date(doc.uploadedAt)}</dd><dt>Total</dt><dd>{money(doc.total)}</dd><dt>Source ID</dt><dd>{doc.id}</dd></dl><div className="document-placeholder"><FileText size={40}/><h3>Sample record only</h3><p>No original PDF or image is bundled. This area is reserved for a document viewer in a later phase.</p></div></Panel>
    <Panel title="Sample review findings" subtitle="Scenario notes, not automated validation"><div className="review-findings">{issues.length ? issues.map(issue=><div key={issue.category}><span className="badge warning">{issue.severity}</span><h3>{issue.category}</h3><p>{issue.explanation}</p></div>) : <p>{doc.status === 'Pending' ? 'Sample awaiting processing; no extracted fields are available.' : 'No discrepancies assigned to this fixture.'}</p>}{doc.id === 'doc-001' && <Link href="/reconciliation" className="text-link">Compare with sample purchase order →</Link>}</div></Panel></div>
    <Panel title="Review demo fields" subtitle="Edits affect this form only"><form className="review-form" onSubmit={e=>{e.preventDefault();const message=validateReview(fields);setError(message ?? '');if(!message){setSnapshot({...fields});setSaved(true);}}}>
      <div role="status" className={'save-status ' + (dirty ? 'unsaved':'')}>{dirty ? 'Unsaved changes' : saved ? 'Saved in this page only' : 'Original sample fields'}</div>
      <label>Vendor<input required maxLength={200} value={fields.vendor} onChange={e=>update('vendor',e.target.value)}/></label><label>Reference<input required maxLength={100} value={fields.reference} onChange={e=>update('reference',e.target.value)}/></label><label>Total (INR)<input required type="number" min="0" step="0.01" value={fields.total} onChange={e=>update('total',e.target.value)}/></label><label>Review notes<textarea rows={5} maxLength={2000} value={fields.notes} placeholder="Add a temporary review note…" onChange={e=>update('notes',e.target.value)}/></label>
      {error && <div className="validation-error" role="alert">{error}</div>}<div className="form-actions"><button type="submit" className="button primary"><Save size={16}/>Save demo edits</button><button type="button" className="button" onClick={()=>{setFields({...initial});setSnapshot({...initial});setSaved(false);setError('');}}><RotateCcw size={16}/>Reset to sample</button></div><p className="form-hint">Saving marks a temporary snapshot as saved. It does not change the library, comparison, analytics, or any server record.</p>
    </form></Panel></div></>;
}
