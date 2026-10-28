'use client';
import {useState} from 'react';
import Link from 'next/link';
import {useApi} from './use-api';
import {ApiState} from './real-workspace';
import {AnalysisResults} from './analysis-results';
import {PageHeading,Panel} from './ui';
import {apiRequest,jsonPost} from '@/lib/api-client.mjs';
import type {StoredDocument} from '@/lib/persistent-types';

function ReviewForm({document:doc,reload}:{document:StoredDocument;reload:()=>void}) {
  const initial=Object.fromEntries(Object.entries(doc.effective_fields).map(([key,field])=>[key,field.value||'']));
  const [fields,setFields]=useState(initial);
  const [notes,setNotes]=useState(doc.review.notes||'');
  const [status,setStatus]=useState(doc.review_status);
  const [error,setError]=useState('');const [saving,setSaving]=useState(false);
  const dirty=JSON.stringify(fields)!==JSON.stringify(initial)||notes!==doc.review.notes||status!==doc.review_status;
  async function save(e:React.FormEvent) {
    e.preventDefault();setSaving(true);setError('');
    const changed=Object.fromEntries(Object.entries(fields).filter(([key,value])=>value!==initial[key]).map(([key,value])=>[key,value||null]));
    try {await apiRequest('/api/documents/'+doc.id+'/review',jsonPost({version:doc.version,fields:changed,notes,status}));reload();}
    catch(err){setError((err as Error).message);}
    finally{setSaving(false);}
  }
  return <Panel title="Human review" subtitle={'Saved revision '+doc.version+' / original extraction is preserved'}><form className="review-form" onSubmit={save}><div className={'save-status '+(dirty?'unsaved':'')} role="status">{dirty?'Unsaved review changes':'Saved state / '+doc.review_status}</div>
    <p className="form-hint">Override only values verified against the source. Notes are retained as review evidence. Approval requires known key fields and no arithmetic mismatch; unknown line checks still need human assessment.</p>
    {Object.entries(fields).map(([key,value])=><label key={key}>{key.replaceAll('_',' ')}<input value={value} maxLength={250} placeholder="Unknown" onChange={e=>setFields({...fields,[key]:e.target.value})}/></label>)}
    <label>Review notes / evidence<textarea required minLength={5} maxLength={2000} rows={4} value={notes} onChange={e=>setNotes(e.target.value)}/></label><label>Review status<select value={status} onChange={e=>setStatus(e.target.value as StoredDocument['review_status'])}><option value="pending">Pending review</option><option value="approved">Approved by reviewer</option><option value="rejected">Rejected by reviewer</option></select></label>
    {error&&<div className="validation-error" role="alert">{error}</div>}<div className="form-actions"><button className="button primary" disabled={saving}>{saving?'Saving...':'Save review'}</button><button type="button" className="button" disabled={saving} onClick={()=>{setFields(initial);setNotes(doc.review.notes);setStatus(doc.review_status);setError('');}}>Reset unsaved edits</button></div></form></Panel>;
}
function Reprocess({doc,reload}:{doc:StoredDocument;reload:()=>void}) {
  const [file,setFile]=useState<File|null>(null);
  const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  async function submit(e:React.FormEvent) {
    e.preventDefault();if(!file)return;setBusy(true);setError('');
    try {
      if(!file.name.toLowerCase().endsWith('.pdf')||file.size>10*1024*1024||file.size===0)throw new Error('Choose a non-empty PDF up to 10 MiB.');
      const body=new FormData();body.append('file',file,file.name);
      await apiRequest('/api/documents/'+doc.id+'/reprocess?version='+doc.version,{method:'POST',body});setFile(null);reload();
    }catch(err){setError((err as Error).message);}finally{setBusy(false);}
  }
  return <Panel title="Explicit reprocessing" subtitle="Re-upload the identical PDF; previous extraction and review stay in the audit trail"><form className="review-form" onSubmit={submit}><p className="form-hint">This resets the current review to pending and increments the version. Ordinary repeated uploads reuse the saved record without changing reviews.</p><label>Original PDF<input type="file" accept="application/pdf,.pdf" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>{error&&<p role="alert" className="validation-error">{error}</p>}<button className="button" disabled={!file||busy}>{busy?'Reprocessing...':'Reprocess and reset review'}</button></form></Panel>;
}
export function SavedDocument({id}:{id:string}) {
  const data=useApi<StoredDocument>('/api/documents/'+id);
  const history=useApi<{items:Array<{created_at:string;version:number}>}>('/api/documents/'+id+'/history');
  const doc=data.value;
  const reload=()=>{data.reload();history.reload();};
  return <><Link href="/documents" className="back-link">Back to saved history</Link><ApiState loading={data.loading} error={data.error} reload={data.reload}/>
    {doc&&!data.loading&&<><PageHeading eyebrow="SAVED LOCAL DOCUMENT" title={doc.filename} description={'Revision '+doc.version+' / '+doc.processing_status+' / review '+doc.review_status}/>
      <div className="demo-notice">Real persisted record. Original extraction and review overrides are stored separately. Original PDF bytes are not retained.</div>
      {!!doc.duplicate_candidates?.length&&<Panel title="Possible duplicate invoices" subtitle="Identifier and supplier identity matches; requires review"><div className="review-findings">{doc.duplicate_candidates.map(candidate=><div key={candidate.id}><Link className="text-link" href={'/documents/'+candidate.id}>{candidate.filename}</Link><p>{candidate.reason}</p></div>)}</div></Panel>}
      <div className="phase-two-column"><Panel title="Current reviewed values" subtitle="Source and reviewer evidence remain visible"><div className="review-findings">{Object.entries(doc.effective_fields).map(([key,field])=><div key={key}><h3>{key.replaceAll('_',' ')}: {field.value??'Unknown'}</h3><p>{field.evidence||'No reliable evidence'}</p><small className="muted">{field.method}</small></div>)}<h3>Current arithmetic checks</h3>{doc.review_validation.checks.map((check,i)=><div key={i}><span className={'badge '+(check.status==='pass'?'success':check.status==='mismatch'?'warning':'neutral')}>{check.status}</span><strong> {check.name}</strong><p>Calculated {check.calculated??'Unknown'} / observed {check.extracted??'Unknown'}. {check.explanation}</p></div>)}</div></Panel><ReviewForm key={doc.version} document={doc} reload={reload}/></div>
      <details className="panel"><summary className="panel-heading">Original extraction (immutable)</summary><AnalysisResults result={{...doc.analysis,stored:true,document_id:doc.id}}/></details>
      <Panel title="Review and reprocessing history" subtitle="Versioned local audit trail"><div className="review-findings">{history.error&&<p role="alert">{history.error}</p>}{history.value?.items.length?history.value.items.map((event,i)=><p key={i}>Revision {event.version} / {event.created_at}</p>):<p className="muted">No review changes yet. Initial extraction is revision 1.</p>}</div></Panel>
      <Reprocess key={doc.version} doc={doc} reload={reload}/>
      <Link className="button" href="/reconciliation">Reconcile saved documents</Link>
    </>}
  </>;
}
