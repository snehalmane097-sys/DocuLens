'use client';
import {useState} from 'react';
import Link from 'next/link';
import {ArrowRight,Files,CircleCheck,Clock3,TriangleAlert} from 'lucide-react';
import {PageHeading,Panel,UploadLink,EmptyState} from './ui';
import {VolumeChart,StatusChart} from './charts';
import {useApi} from './use-api';
import type {DocumentList,Analytics,StoredDocument} from '@/lib/persistent-types';
import type {DocumentRecord} from '@/lib/types';
import {date} from '@/lib/mock-data';

export function ApiState({loading,error,reload}:{loading:boolean;error:string;reload:()=>void}) {
  if(loading)return <div className="demo-notice" role="status">Loading saved local records...</div>;
  if(error)return <div className="validation-error" role="alert">{error} <button className="button" onClick={reload}>Retry</button></div>;
  return null;
}
export function RealTable({records}:{records:StoredDocument[]}) {
  const [query,setQuery]=useState('');const [status,setStatus]=useState('all');
  const filtered=records.filter(d=>(d.filename+' '+(d.effective_fields.supplier_name?.value||'')+' '+(d.effective_fields.invoice_number?.value||'')).toLowerCase().includes(query.toLowerCase()) && (status==='all'||d.review_status===status));
  return <><div className="table-toolbar"><label className="search-input"><span className="sr-only">Search saved documents</span><input placeholder="Search documents or suppliers..." value={query} onChange={e=>setQuery(e.target.value)}/></label><label className="filters">Review status <select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option>{['pending','approved','rejected'].map(s=><option key={s}>{s}</option>)}</select></label></div>
    {!filtered.length?<EmptyState title="No saved documents found" description="Upload a PDF or adjust the search and status filter."/>:<div className="table-scroll"><table><thead><tr><th>Document</th><th>Supplier</th><th>Saved</th><th>Processing / review</th><th>Final amount</th><th>Action</th></tr></thead><tbody>{filtered.map(d=><tr key={d.id}><td>{d.filename}<small className="muted"> / {d.effective_fields.invoice_number?.value||'Unknown identifier'}</small></td><td>{d.effective_fields.supplier_name?.value||'Unknown'}</td><td>{date(d.created_at)}</td><td><span className={'badge '+(d.review_status==='approved'?'success':'warning')}>{d.processing_status} / {d.review_status}</span></td><td>{d.effective_fields.grand_total?.value||'Unknown'}</td><td><Link className="text-link" href={'/documents/'+d.id}>Review <ArrowRight size={14}/></Link></td></tr>)}</tbody></table></div>}<div className="table-footer">{filtered.length} shown / {records.length} loaded. Amounts use the document&apos;s stated monetary units.</div></>;
}
export function RealWorkspace({mode,demo}:{mode:'overview'|'history'|'analytics';demo:React.ReactNode}) {
  const [showDemo,setDemo]=useState(false);
  const list=useApi<DocumentList>('/api/documents?limit=500');
  const stats=useApi<Analytics>('/api/analytics');
  const reload=()=>{list.reload();stats.reload();};
  if(showDemo)return <><div className="demo-notice"><button className="button" onClick={()=>setDemo(false)}>Return to real local records</button>Fictional demo view; excludes saved uploads.</div>{demo}</>;
  const records=list.value?.items||[];
  const summary=stats.value;
  const chartRecords:DocumentRecord[]=records.map(d=>({id:d.id,filename:d.filename,reference:d.effective_fields.invoice_number?.value||'Unknown',vendor:d.effective_fields.supplier_name?.value||'Unknown',type:'Invoice',uploadedAt:d.created_at,status:d.review_status==='approved'?'Processed':d.processing_status==='needs_ocr'?'Pending':'Needs review',total:0,issues:d.review_validation.mismatches}));
  const cards=[{label:'Total documents',value:summary?.total,icon:Files,note:'Saved local analyses',color:'teal'},{label:'Analyzed documents',value:summary?summary.total-summary.needs_ocr:undefined,icon:CircleCheck,note:'Text extraction available',color:'blue'},{label:'Pending reviews',value:summary?.review_status.pending||0,icon:Clock3,note:'Awaiting human review',color:'amber'},{label:'Detected discrepancies',value:summary?.mismatches,icon:TriangleAlert,note:'Current arithmetic mismatches',color:'rose'}];
  return <><PageHeading eyebrow="YOUR LOCAL WORKSPACE" title={mode==='overview'?'Document overview':mode==='history'?'All documents':'Workspace analytics'} description="Real saved analyses and review results. Fictional fixtures are kept in a separate demo view." action={<UploadLink/>}/>
    <div className="demo-notice"><strong>Real local records</strong><span>SQLite history / PDF bytes are not stored</span><button className="button" onClick={reload}>Refresh</button><button className="button" onClick={()=>setDemo(true)}>View fictional demo</button></div>
    <ApiState loading={list.loading||stats.loading} error={list.error||stats.error} reload={reload}/>
    {!list.error&&!stats.error&&<><div className="stats-grid">{cards.map(s=><section className="stat-card" key={s.label}><div className="stat-top"><span>{s.label}</span><span className={'stat-icon '+s.color}><s.icon size={18}/></span></div><div className="stat-number">{list.loading||stats.loading?'...':s.value??0}</div><p>{s.note}</p></section>)}</div>
    {mode!=='history'&&<div className="overview-grid"><Panel title="Document activity" subtitle="Latest loaded records / full date in Asia/Kolkata"><VolumeChart records={chartRecords} source="real"/></Panel><Panel title="Review distribution" subtitle="Approved, pending and extraction-limited records"><StatusChart records={chartRecords} source="real"/><div className="chart-caption">Latest {records.length} loaded of {list.value?.total||0}; rejected reviews are shown as needing review.</div></Panel></div>}
    {mode==='analytics'?<Panel title="Arithmetic discrepancy breakdown" subtitle="Derived from current reviewed values, not demo fixtures"><div className="review-findings">{Object.entries(summary?.discrepancies||{}).map(([name,count])=><div className="breakdown-row" key={name}><span>{name}</span><meter min={0} max={Math.max(1,summary?.mismatches||0)} value={count}/><strong>{count}</strong></div>)}{!summary?.mismatches&&<EmptyState title="No arithmetic mismatches recorded" description="Unknown checks and unreviewed records still require human review."/>}</div><div className="table-footer">{summary?.unknown_checks||0} checks remain unknown across all saved records.</div></Panel>:<Panel title={mode==='history'?'Saved document history':'Recent saved documents'} subtitle="Click Review for original extraction, evidence and versioned review"><RealTable records={mode==='history'?records:records.slice(0,8)}/></Panel>}</>}
  </>;
}
