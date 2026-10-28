'use client';
import {useState} from 'react';
import Link from 'next/link';
import {ArrowRight,Files,Wallet,Clock3,TriangleAlert,RefreshCw} from 'lucide-react';
import {PageHeading,Panel,UploadLink,EmptyState} from './ui';
import {VolumeChart,StatusChart} from './charts';
import {useApi} from './use-api';
import {invoiceMetrics,amountLabel} from '@/lib/workspace-metrics.mjs';
import type {DocumentList,Analytics,StoredDocument} from '@/lib/persistent-types';
import type {DocumentRecord} from '@/lib/types';

export function ApiState({loading,error,reload}:{loading:boolean;error:string;reload:()=>void}) {
 if(loading)return <p className="inline-status" role="status">Loading your workspace…</p>;
 if(error)return <div className="validation-error" role="alert">{error} <button className="button" onClick={reload}>Retry</button></div>;
 return null;
}
export function RealTable({records,compact=false,initialStatus='all',initialQuery=''}:{records:StoredDocument[];compact?:boolean;initialStatus?:string;initialQuery?:string}) {
 const [query,setQuery]=useState(initialQuery);const [status,setStatus]=useState(initialStatus);
 const filtered=records.filter(d=>[d.filename,d.effective_fields.supplier_name?.value,d.effective_fields.invoice_number?.value].join(' ').toLowerCase().includes(query.toLowerCase())&&(status==='all'||(status==='review'?(d.review_status==='pending'||d.review_validation.mismatches>0):d.review_status===status)));
 return <>{!compact&&<div className="table-toolbar"><label className="search-input"><span className="sr-only">Search invoices</span><input placeholder="Search supplier or invoice number" value={query} onChange={e=>setQuery(e.target.value)}/></label><label className="filters"><span className="sr-only">Filter invoices</span><select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All invoices</option><option value="review">Requires attention</option><option value="pending">Pending review</option><option value="approved">Approved</option><option value="rejected">Rejected</option></select></label></div>}
 {!filtered.length?<EmptyState title="No invoices to show" description={records.length?'Try another search or review filter.':'Analyze your first invoice to build your document history.'}/>:<div className="table-scroll" role="region" aria-label="Invoice list" tabIndex={0}><table className="invoice-table"><thead><tr><th>Supplier / invoice</th><th>Invoice date</th><th>Final amount</th><th>Status</th><th><span className="sr-only">Open invoice</span></th></tr></thead><tbody>{filtered.map(d=>{
 const error=d.review_validation.mismatches>0;const statusText=error?'Discrepancy':d.review_status==='approved'?'Approved':d.review_status==='rejected'?'Rejected':d.processing_status==='needs_ocr'?'Unreadable / review':'Needs review';
 return <tr key={d.id}><td><Link className="invoice-title" href={'/documents/'+d.id}>{d.effective_fields.supplier_name?.value||'Unknown supplier'}</Link><small>{d.effective_fields.invoice_number?.value||d.filename}</small></td><td>{d.effective_fields.invoice_date?.value||'Unknown'}</td><td className="tabular">{amountLabel(d.effective_fields.grand_total?.value)}</td><td><span className={'badge '+(error||d.review_status==='rejected'?'danger':d.review_status==='approved'?'success':'warning')}>{statusText}</span></td><td><Link className="icon-button" aria-label={'Review '+d.filename} href={'/documents/'+d.id}><ArrowRight size={16}/></Link></td></tr>;
 })}</tbody></table></div>}
 {!compact&&<div className="table-footer">{filtered.length} of {records.length} loaded invoices · Amounts in each invoice&apos;s stated units</div>}</>;
}
export function RealWorkspace({mode,demo,initialStatus='all',initialQuery=''}:{mode:'overview'|'history'|'analytics';demo:React.ReactNode;initialStatus?:string;initialQuery?:string}) {
 const [showDemo,setDemo]=useState(false);
 const list=useApi<DocumentList>('/api/documents?limit=500');const stats=useApi<Analytics>('/api/analytics');
 const reload=()=>{list.reload();stats.reload();};
 if(showDemo)return <><div className="demo-notice"><strong>Fictional demonstration</strong><button className="button" onClick={()=>setDemo(false)}>Back to real invoices</button></div>{demo}</>;
 const records=list.value?.items||[];const summary=stats.value;const metrics=invoiceMetrics(records);
 const loading=list.loading||stats.loading;const failed=list.error||stats.error;
 const chartRecords:DocumentRecord[]=records.map(d=>({id:d.id,filename:d.filename,reference:d.effective_fields.invoice_number?.value||'Unknown',vendor:d.effective_fields.supplier_name?.value||'Unknown',type:'Invoice',uploadedAt:d.created_at,status:d.review_status==='approved'?'Processed':d.processing_status==='needs_ocr'?'Pending':'Needs review',total:0,issues:d.review_validation.mismatches}));
 const cards=[
  {label:'Documents analyzed',value:summary?summary.total-summary.needs_ocr:undefined,note:'Readable document analyses',icon:Files,color:'teal'},
  {label:'Invoice value',value:metrics.value?metrics.currency+' '+amountLabel(metrics.value):'—',note:metrics.value?'Known totals in loaded records':'Currency is not recorded; no combined total',icon:Wallet,color:'teal'},
  {label:'Needs review',value:summary?.review_status.pending||0,note:'Waiting for a review decision',icon:Clock3,color:'amber'},
  {label:'Validation findings',value:summary?.mismatches,note:'Detected arithmetic discrepancies',icon:TriangleAlert,color:summary?.mismatches?'rose':'teal'},
 ];
 return <div className="workspace-page"><PageHeading eyebrow={mode==='overview'?'YOUR INVOICE WORKSPACE':''} title={mode==='overview'?'Welcome back':mode==='history'?'Documents':'Invoice analytics'} description={mode==='overview'?'A clear view of your invoices and what needs your attention.':mode==='history'?'Find, inspect and review your saved invoices.':'Understand activity, review progress and validation quality.'} action={<UploadLink/>}/>
  <div className="workspace-tools"><span>{summary?.total??'—'} saved documents</span><button className="button" onClick={reload} aria-label="Refresh workspace"><RefreshCw size={14}/>Refresh</button><details><summary>Workspace options</summary><button className="button" onClick={()=>setDemo(true)}>View fictional demo</button></details></div>
  <ApiState loading={loading} error={failed} reload={reload}/>
  {!failed&&!loading&&<>
   {mode!=='history'&&<div className="stats-grid">{cards.map(card=><section className="stat-card" key={card.label}><div className="stat-top"><span>{card.label}</span><span className={'stat-icon '+card.color}><card.icon size={18} strokeWidth={1.6}/></span></div><div className={'stat-number '+(card.label==='Invoice value'?'financial-kpi':'')}>{card.value??0}</div><p>{card.note}</p></section>)}</div>}
   {mode!=='history'&&<div className="dashboard-composition"><Panel title="Invoice activity" subtitle="Last seven active dates"><VolumeChart records={chartRecords} source="real"/><div className="chart-caption">{records.length} latest loaded records · Asia/Kolkata</div></Panel>
    {mode==='overview'?<section className="focus-card"><span className="eyebrow">NEXT UP</span><h2>{summary?.review_status.pending?'A little review. More confidence.':'Your workspace is up to date.'}</h2><p>{summary?.review_status.pending?`${summary.review_status.pending} invoices are waiting for a human review. Check uncertain fields and confirm the source.`:'Keep your evidence and decisions together as you analyze new invoices.'}</p><Link className="text-link" href="/documents?status=review">Review flagged invoices <ArrowRight size={16}/></Link><div className="focus-footnote"><span>{summary?.unknown_checks||0}</span> checks need supporting evidence</div></section>:<Panel title="Review progress" subtitle="Status of loaded documents"><StatusChart records={chartRecords} source="real"/></Panel>}
   </div>}
   {mode==='analytics'?<div className="analytics-detail-grid"><Panel title="Validation breakdown" subtitle="Current reviewed values"><div className="review-findings">{Object.entries(summary?.discrepancies||{}).map(([name,count])=><div className="breakdown-row" key={name}><span>{name}</span><meter min={0} max={Math.max(1,summary?.mismatches||0)} value={count}/><strong>{count}</strong></div>)}{!summary?.mismatches&&<EmptyState title="No arithmetic discrepancies" description="Unknown values and pending reviews still need source verification."/>}</div></Panel><Panel title="Extraction coverage" subtitle="Known final totals in loaded records"><div className="coverage-body"><strong>{metrics.coverage}%</strong><p>{metrics.known} of {records.length} invoices have an extracted final total.</p><meter min={0} max={100} value={metrics.coverage} aria-label="Final total extraction coverage"/><p className="muted">Currency is not assumed. Totals with unknown or mixed currencies are never added together.</p></div></Panel></div>:<Panel title={mode==='history'?'Invoice history':'Recent invoices'} action={mode==='overview'?<Link href="/documents" className="text-link">View all <ArrowRight size={14}/></Link>:undefined}><RealTable compact={mode==='overview'} records={mode==='history'?records:records.slice(0,5)} initialStatus={initialStatus} initialQuery={initialQuery}/></Panel>}
  </>}
 </div>;
}
