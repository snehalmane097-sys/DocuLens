'use client';
import { useRef, useState } from 'react';
import Link from 'next/link';
import { UploadCloud, FileCheck2, X, ShieldCheck } from 'lucide-react';
import { checkSelection } from '@/lib/upload-selection.mjs';
import { submitAnalysis } from '@/lib/analyze-upload.mjs';
import type { AnalysisState } from '@/lib/analysis-types';
import { AnalysisResults } from './analysis-results';
const key = (file:File) => file.name + ':' + file.size;
export function UploadPreview() {
  const input = useRef<HTMLInputElement>(null);
  const busyRef = useRef(false);
  const [busy,setBusy] = useState(false);
  const [dragging,setDragging] = useState(false);
  const [files,setFiles] = useState<File[]>([]);
  const [errors,setErrors] = useState<string[]>([]);
  const [analyses,setAnalyses] = useState<Record<string,AnalysisState>>({});
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  async function select(incoming: FileList | File[]) {
    if (busyRef.current) return;
    busyRef.current = true; setBusy(true);
    try {
      const candidates = Array.from(incoming);
      const result = await checkSelection(files,candidates);
      const accepted = candidates.filter(file=>result.accepted.some(record=>record.name === file.name && record.size === file.size));
      // De-duplicate within the incoming batch; validation metadata intentionally contains no file content.
      setFiles(previous => [...previous,...accepted.filter((file,i)=>accepted.findIndex(f=>key(f) === key(file)) === i)]);
      setErrors(result.errors);setAnalyses({});
    } finally {busyRef.current=false;setBusy(false);if(input.current) input.current.value='';}
  }
  async function analyze(file:File) {
    if(busyRef.current) return;
    busyRef.current=true;setBusy(true);
    try { await submitAnalysis(file,apiUrl,(state:AnalysisState)=>setAnalyses(previous=>({...previous,[key(file)]:state}))); }
    finally {busyRef.current=false;setBusy(false);}
  }
  return <><div className="phase-two-column"><section className="panel"><div className="panel-heading"><div><h2>Select documents</h2><p>Analyze a text-based PDF, or preview image selection.</p></div><span className="subtle-tag">Phase 2A</span></div>
    <input ref={input} className="sr-only" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" aria-label="Select PDF, PNG or JPG documents" disabled={busy} onChange={e=>{if(e.target.files)void select(e.target.files);}}/>
    <div className={'dropzone '+(dragging?'dragging':'')} aria-busy={busy} onDragOver={e=>{e.preventDefault();if(!busy)setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);void select(e.dataTransfer.files);}}>
      <UploadCloud size={34}/><h3>Drop your documents here</h3><p>PDF, PNG or JPG/JPEG / 10 MiB each / Maximum five files</p><button className="button primary" disabled={busy} onClick={()=>input.current?.click()}>Browse files</button>
    </div>
    {errors.length > 0 && <div className="validation-error" role="alert"><ul>{errors.map((error,i)=><li key={i}>{error}</li>)}</ul></div>}
    <div className="selected-files"><h3>Selected files ({files.length}/5)</h3>{!files.length && <p className="muted">No files selected yet.</p>}{files.map(file=><div className="selected-file" key={key(file)}><FileCheck2 size={21}/><div><strong>{file.name}</strong><small>{(file.size/1024).toFixed(1)} KB / {file.name.toLowerCase().endsWith('.pdf')?'PDF analysis available':'Image preview only; OCR not supported'}</small></div>{file.name.toLowerCase().endsWith('.pdf') && <button className="button primary" disabled={busy} onClick={()=>void analyze(file)}>Analyze PDF</button>}<button className="icon-button" disabled={busy} aria-label={'Remove '+file.name} onClick={()=>{setFiles(files.filter(f=>f!==file));setErrors([]);setAnalyses(previous=>{const next={...previous};delete next[key(file)];return next;});}}><X size={18}/></button></div>)}
    <p className="form-hint" role="status">{busy ? 'Working locally. PDF analysis may take a moment…':'Files are sent only when you click Analyze PDF. Selections clear on navigation. Saved results remain in document history.'}</p></div>
    </section><aside className="panel phase-aside"><ShieldCheck size={26}/><h2>Local processing and saved analysis</h2><p>Analyze sends one PDF to the configured loopback backend: {apiUrl}. No external AI or cloud upload is used. PDF bytes are not stored. Extracted text, fields and review history are saved in local SQLite.</p><p>Digitally generated PDFs only. Images and scanned PDFs need OCR, which is not supported. Extracted fields and arithmetic checks require human review.</p><Link href="/documents/doc-001" className="text-link">Explore a separate fictional review</Link></aside></div>
    {files.map(file=>{const state=analyses[key(file)];return state ? <section key={key(file)} aria-live="polite">{state.status==='loading' ? <div className="demo-notice" role="status">Extracting text and checking arithmetic for {file.name}…</div>:state.status==='error' ? <div className="validation-error" role="alert">{file.name}: {state.message}</div>:<AnalysisResults result={state.result}/>}</section>:null;})}
  </>;
}
