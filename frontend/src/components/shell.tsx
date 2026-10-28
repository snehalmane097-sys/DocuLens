'use client';
import Link from 'next/link';
import {useApi} from './use-api';
import type {DocumentList} from '@/lib/persistent-types';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { LayoutDashboard, Files, GitCompareArrows, ChartNoAxesCombined, ScanLine, ChevronRight, Menu, X, FlaskConical, Upload, ArrowUpRight } from 'lucide-react';
const nav = [
  { href: '/', label: 'Overview', icon: LayoutDashboard },
  { href: '/documents', label: 'Documents', icon: Files },
  { href: '/reconciliation', label: 'Reconciliation', icon: GitCompareArrows },
  { href: '/analytics', label: 'Analytics', icon: ChartNoAxesCombined },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const records = useApi<DocumentList>('/api/documents?limit=1',pathname);
  const [open, setOpen] = useState(false);
  const current = nav.find(n => n.href === '/' ? pathname === '/' : pathname.startsWith(n.href))?.label ?? (pathname === '/upload' ? 'Upload document' : 'Workspace');
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    {open && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <aside className={'sidebar ' + (open ? 'is-open' : '')}>
      <Link href="/" className="brand" onClick={() => setOpen(false)}><span className="brand-mark"><ScanLine size={24} /></span><span>DocuLens<span className="brand-ai">AI</span></span></Link>
      <button className="mobile-close icon-button" aria-label="Close navigation" onClick={() => setOpen(false)}><X size={20} /></button>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">{nav.map(n => <Link key={n.href} href={n.href} className={'nav-link ' + ((n.href === '/' ? pathname === '/' : pathname.startsWith(n.href)) ? 'active' : '')} aria-current={(n.href === '/' ? pathname === '/' : pathname.startsWith(n.href)) ? 'page' : undefined} onClick={() => setOpen(false)}><n.icon size={19} />{n.label}{n.href === '/documents' && <span className="nav-count">{records.value?.total??'-'}</span>}</Link>)}</nav>
      <div className="sidebar-bottom"><div className="sandbox-card"><FlaskConical size={20} /><h3>Your local documents</h3><p>Saved analyses and reviews. Fictional examples are labelled separately.</p><Link href="/upload" onClick={() => setOpen(false)}>Open PDF analysis <ArrowUpRight size={15} /></Link></div><div className="workspace-user"><span className="avatar">DL</span><div><strong>Project workspace</strong><small>Local development</small></div><span className="online-dot" /></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="mobile-menu icon-button" aria-label="Open navigation" aria-expanded={open} onClick={() => setOpen(!open)}><Menu size={20} /></button><span>Workspace</span><ChevronRight size={14} /><strong>{current}</strong></div><div className="topbar-right"><span className="demo-chip"><FlaskConical size={13} /> Local workspace</span><Link href="/upload" className="icon-button" aria-label="Upload document"><Upload size={18} /></Link><span className="avatar small" aria-label="DocuLens workspace">DL</span></div></header>
    <main id="main" tabIndex={-1}>{children}<footer className="footer"><span>DocuLens AI <span className="muted">/</span> Document intelligence, made clear.</span><span>Real local records / demos labelled separately</span></footer></main></div>
  </div>;
}
