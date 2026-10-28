'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useEffect,useRef,useState} from 'react';
import {LayoutDashboard,Files,GitCompareArrows,ChartNoAxesCombined,ScanLine,Menu,X,Upload,ShieldCheck,Search} from 'lucide-react';
import {useApi} from './use-api';
import type {DocumentList} from '@/lib/persistent-types';
const nav=[
 {href:'/',label:'Overview',icon:LayoutDashboard},
 {href:'/documents',label:'Documents',icon:Files},
 {href:'/upload',label:'Analyze invoice',icon:Upload},
 {href:'/reconciliation',label:'Reconciliation',icon:GitCompareArrows},
 {href:'/analytics',label:'Analytics',icon:ChartNoAxesCombined},
];
export function Shell({children}:{children:React.ReactNode}) {
 const pathname=usePathname();
 const records=useApi<DocumentList>('/api/documents?limit=1',pathname);
 const [open,setOpen]=useState(false);
 const drawer=useRef<HTMLElement>(null);const menu=useRef<HTMLButtonElement>(null);
 const close=()=>{setOpen(false);menu.current?.focus();};
 useEffect(()=>{
  if(!open)return;
  const previous=document.body.style.overflow;document.body.style.overflow='hidden';
  drawer.current?.querySelector<HTMLElement>('a')?.focus();
  const handle=(event:KeyboardEvent)=>{
   if(event.key==='Escape'){setOpen(false);menu.current?.focus();}
   if(event.key==='Tab'){
    const items=Array.from(drawer.current?.querySelectorAll<HTMLElement>('a,button')||[]).filter(el=>el.getClientRects().length);
    const first=items[0],last=items[items.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
   }
  };
  document.addEventListener('keydown',handle);
  return ()=>{document.body.style.overflow=previous;document.removeEventListener('keydown',handle);};
 },[open]);
 const current=nav.find(n=>n.href==='/'?pathname==='/':pathname.startsWith(n.href))?.label||'Workspace';
 return <div className="app-shell"><a className="skip-link" href="#main">Skip to content</a>
  {open&&<button className="nav-backdrop" aria-label="Close navigation" onClick={close}/>}
  <aside ref={drawer} id="workspace-navigation" className={'sidebar '+(open?'is-open':'')}>
   <Link href="/" className="brand" onClick={()=>setOpen(false)}><span className="brand-mark"><ScanLine size={22}/></span><span>DocuLens<span className="brand-ai">AI</span></span></Link>
   <button className="mobile-close icon-button" aria-label="Close navigation" onClick={close}><X size={20}/></button>
   <div className="workspace-label">WORKSPACE</div>
   <nav aria-label="Main navigation">{nav.map(n=>{const active=n.href==='/'?pathname==='/':pathname.startsWith(n.href);return <Link key={n.href} href={n.href} className={'nav-link '+(active?'active':'')} aria-current={active?'page':undefined} onClick={()=>setOpen(false)}><n.icon size={18} strokeWidth={1.6}/>{n.label}{n.href==='/documents'&&<span className="nav-count">{records.value?.total??'—'}</span>}</Link>;})}</nav>
   <div className="sidebar-bottom"><div className="local-workspace"><ShieldCheck size={17}/><div><strong>Private by design</strong><small>Processing stays on your device</small></div></div><div className="workspace-user"><span className="avatar">DL</span><div><strong>Your workspace</strong><small>Local documents</small></div></div></div>
  </aside>
  <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button ref={menu} className="mobile-menu icon-button" aria-label="Open navigation" aria-controls="workspace-navigation" aria-expanded={open} onClick={()=>setOpen(!open)}><Menu size={20}/></button><span className="header-section">Workspace <span aria-hidden="true">/</span></span><strong>{current}</strong></div><div className="topbar-right"><form className="header-search" action="/documents" method="get"><Search size={14} aria-hidden="true"/><label className="sr-only" htmlFor="workspace-search">Search invoices</label><input id="workspace-search" name="q" placeholder="Search invoices…" maxLength={150}/></form><span className="local-indicator"><i aria-hidden="true"/>Local workspace</span><span className="avatar small" aria-label="DocuLens workspace">DL</span></div></header>
   <main id="main" tabIndex={-1}>{children}<footer className="footer"><span>DocuLens AI</span><span>Local processing · Evidence-led review</span></footer></main>
  </div>
 </div>;
}
