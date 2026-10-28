'use client';

import {useState} from 'react';

import Link from 'next/link';

import {PageHeading,Panel,EmptyState} from './ui';

import {useApi} from './use-api';

import {ApiState} from './real-workspace';

import {apiRequest,jsonPost} from '@/lib/api-client.mjs';

import type {DocumentList,ReconciliationReport} from '@/lib/persistent-types';

import {ReconciliationPreview} from './reconciliation-preview';

export function RealReconciliation() {

  const saved=useApi<{items:ReconciliationReport[]}>('/api/reconciliations');

  async function loadReport(id:string) {setError('');setBusy(true);try{setReport(await apiRequest('/api/reconciliations/'+id));setNotes({});}catch(err){setError((err as Error).message);}finally{setBusy(false);}}

  const documents=useApi<DocumentList>('/api/documents?limit=500');

  const [expected,setExpected]=useState('');const [observed,setObserved]=useState('');

  const [showAll,setShowAll]=useState(false);
  const [report,setReport]=useState<ReconciliationReport|null>(null);

  const [notes,setNotes]=useState<Record<string,string>>({});

  const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [demo,setDemo]=useState(false);

  async function compare() {

    setBusy(true);setError('');setReport(null);

    try {setReport(await apiRequest('/api/reconciliations',jsonPost({expected_id:expected,observed_id:observed})));setNotes({});saved.reload();}

    catch(err){setError((err as Error).message);}finally{setBusy(false);}

  }

  async function save() {

    if(!report)return;

    setBusy(true);setError('');

    try {setReport(await apiRequest('/api/reconciliations/'+report.id+'/review',jsonPost({version:report.version,decisions:Object.fromEntries(Object.entries(notes).filter(([,value])=>value.trim()))})));setNotes({});saved.reload();}

    catch(err){setError((err as Error).message);}finally{setBusy(false);}

  }

  const rows=documents.value?.items||[];

  return <><PageHeading eyebrow="COMPARE SAVED EVIDENCE" title="Document reconciliation" description="Compare two saved invoices and review their differences."/><div className="workspace-tools"><span>Saved document comparisons</span><details><summary>Comparison options</summary><button className="button" onClick={()=>setDemo(!demo)}>{demo?'Return to real comparison':'View fictional example'}</button></details></div>

    {demo?<ReconciliationPreview/>:<><ApiState loading={documents.loading} error={documents.error} reload={documents.reload}/>

    {rows.length<2?<Panel title="Choose documents"><EmptyState title="Two saved documents are needed" description="Upload two different PDFs. Identical bytes intentionally reuse one record."/><div className="review-findings"><Link className="button primary" href="/upload">Upload PDF</Link></div></Panel>:<Panel title="Select a comparison pair" subtitle="Choose a reference invoice and the invoice to compare against it"><div className="compare-selectors">{[{label:'Expected document',value:expected,set:setExpected},{label:'Observed document',value:observed,set:setObserved}].map((control,i)=><label key={i}>{control.label}<select value={control.value} onChange={e=>{control.set(e.target.value);setReport(null);}}><option value="">Choose document</option>{rows.map(d=><option key={d.id} value={d.id}>{d.filename} / {d.effective_fields.invoice_number?.value||'Unknown identifier'}</option>)}</select></label>)}<button className={'button '+(report?'':'primary')} disabled={busy||!expected||!observed||expected===observed} onClick={()=>void compare()}>{busy?'Comparing...':'Compare'}</button></div></Panel>}

    <details className="panel disclosure"><summary>Saved comparisons</summary><Panel title="Comparison history" subtitle="Persisted reports; source versions are checked when opened"><div className="review-findings"><ApiState loading={saved.loading} error={saved.error} reload={saved.reload}/>{saved.value?.items.length?saved.value.items.map(r=><button key={r.id} className="button" disabled={busy} onClick={()=>void loadReport(r.id)}>{new Date(r.created_at).toLocaleDateString('en-IN')} · {r.status} · {r.mismatches} discrepancies</button>):<p className="muted">No saved comparisons yet.</p>}</div></Panel></details>

    {error&&<div className="validation-error" role="alert">{error}</div>}

    {report&&<Panel title="Reconciliation results" subtitle="Review the differences before saving a decision">

      {report.stale&&<div className="validation-error">Source records changed. Create a new comparison.</div>}

      <div className="reconciliation-summary"><span className={'badge '+(report.mismatches?'danger':'success')}>{report.mismatches} discrepancies</span><span className="badge warning">{report.unknown} unknown values</span><button className="button" onClick={()=>setShowAll(!showAll)}>{showAll?'Only review findings':'Include matched fields'}</button></div><div className="table-scroll" role="region" tabIndex={0} aria-label="Reconciliation findings"><table><thead><tr><th>Field</th><th>Expected / evidence</th><th>Observed / evidence</th><th>Finding</th><th>Human review</th></tr></thead><tbody>{report.rows.filter(row=>showAll||row.status!=='matched').map(row=><tr key={row.id}><th scope="row">{row.field}</th><td className="analysis-evidence"><strong>{row.expected??'Unknown'}</strong><details><summary>Evidence</summary><p>{row.expected_evidence}</p></details></td><td className="analysis-evidence"><strong>{row.observed??'Unknown'}</strong><details><summary>Evidence</summary><p>{row.observed_evidence}</p></details></td><td><span className={'badge '+(row.status==='matched'?'success':row.status==='mismatch'?'danger':'warning')}>{row.status}</span></td><td className="analysis-evidence">{row.review_status}<p>{row.review_note}</p>{row.status!=='matched'&&<details><summary>Add review note</summary><label>Review explanation<textarea aria-label={'Review '+row.field} minLength={5} maxLength={2000} rows={2} value={notes[row.id]||''} onChange={e=>setNotes({...notes,[row.id]:e.target.value})}/></label></details>}</td></tr>)}</tbody></table></div>

      <div className="review-findings"><button className="button primary" disabled={busy||report.stale} onClick={()=>void save()}>Save discrepancy reviews</button><p className="form-hint">Review notes do not change original mismatches. Every unknown/mismatch needs a note to reach reviewed status. Source revisions are checked again on save. Report ID: {report.id}</p></div>

    </Panel>}</>}

  </>;

}
