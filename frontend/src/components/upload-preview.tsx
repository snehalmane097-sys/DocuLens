'use client';

import { useRef, useState } from 'react';

import { UploadCloud, FileCheck2, X } from 'lucide-react';

import { checkSelection } from '@/lib/upload-selection.mjs';

import { submitAnalysis } from '@/lib/analyze-upload.mjs';

import type { AnalysisState } from '@/lib/analysis-types';

import {useApi} from './use-api';

import { AnalysisResults } from './analysis-results';

const key = (file:File) => file.name + ':' + file.size;

export function UploadPreview() {

  const input = useRef<HTMLInputElement>(null);

  const busyRef = useRef(false);

  const [activeKey,setActiveKey]=useState('');

  const [busy,setBusy] = useState(false);

  const [dragging,setDragging] = useState(false);

  const [files,setFiles] = useState<File[]>([]);

  const [errors,setErrors] = useState<string[]>([]);

  const [analyses,setAnalyses] = useState<Record<string,AnalysisState>>({});

  const ocr=useApi<{engine_found:boolean;pdf_renderer_found:boolean;handwriting_verified:boolean}>('/api/ocr/status');

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

  const active=files.find(file=>key(file)===activeKey)||files[0];

  return <div className="upload-flow"><section className="panel upload-card" aria-label="Invoice upload">

    <input ref={input} className="sr-only" type="file" multiple accept=".pdf,.png,.jpg,.jpeg" aria-label="Select invoice files" disabled={busy} onChange={e=>{if(e.target.files)void select(e.target.files);}}/>

    <div className={'dropzone '+(dragging?'dragging':'')} aria-busy={busy} onDragOver={e=>{e.preventDefault();if(!busy)setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);void select(e.dataTransfer.files);}}>

      <UploadCloud size={28} aria-hidden="true"/><h2>Drop your invoice here</h2><p>Or choose a file from your device.</p><button className={'button '+(!files.length?'primary':'')} disabled={busy} onClick={()=>input.current?.click()}>Choose file</button>

    </div>

    {!!errors.length&&<div className="validation-error" role="alert">{errors.map((error,i)=><p key={i}>{error}</p>)}</div>}

    {!!files.length&&<div className="selected-files" role="group" aria-label="Selected invoices">{files.map(file=><div className="selected-file" key={key(file)}><FileCheck2 size={20} aria-hidden="true"/><label className="file-choice">{files.length>1&&<input type="radio" name="active-invoice" checked={active===file} disabled={busy} onChange={()=>setActiveKey(key(file))}/>}<span><strong>{file.name}</strong><small>{(file.size/1024).toFixed(1)} KB</small></span></label><button className="icon-button" disabled={busy} aria-label={'Remove '+file.name} onClick={()=>{setFiles(files.filter(f=>f!==file));setErrors([]);setAnalyses(previous=>{const next={...previous};delete next[key(file)];return next;});}}><X size={18}/></button></div>)}

      <div className="upload-actions"><button className={'button '+(active&&analyses[key(active)]?.status==='success'?'':'primary')} disabled={busy||!active} onClick={()=>active&&void analyze(active)}>{busy?'Analyzing…':'Analyze invoice'}</button>{files.length>1&&<small className="muted">One invoice at a time · select a file above</small>}</div>

    </div>}

    <p className="upload-note">PDF, PNG or JPEG · Up to 10 MB each · Processed locally</p>

    <details className="processing-note"><summary>Privacy & OCR availability</summary><p>Original files are not stored. Extracted results and reviews are saved locally. Scanned PDFs and images need local Tesseract. Handwriting is unverified; all results need review.</p><p>{ocr.loading?'Checking OCR setup…':ocr.error?'OCR status unavailable. Analysis will report setup errors.':ocr.value?.engine_found?`OCR executable found. ${ocr.value.pdf_renderer_found?'PDF renderer found.':'PDF renderer missing.'} Recognition is checked during analysis.`:'OCR engine not installed. Text PDFs still work; install Tesseract with English data for images.'}</p></details>

    </section>

    {files.map(file=>{const state=analyses[key(file)];return state?<section key={key(file)} aria-live="polite">{state.status==='loading'?<p className="inline-status" role="status">Analyzing {file.name} · extracting text and checking amounts…</p>:state.status==='error'?<div className="validation-error" role="alert"><strong>Unable to analyze {file.name}</strong><p>{state.message}</p></div>:<AnalysisResults result={state.result}/>}</section>:null;})}

  </div>;

}
