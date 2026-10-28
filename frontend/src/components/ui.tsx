import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowUpRight, FileText, Inbox } from 'lucide-react';
import type { DocumentStatus } from '@/lib/types';

export function Badge({ status }: { status: DocumentStatus }) {
  return <span className={'badge ' + (status === 'Processed' ? 'success' : status === 'Needs review' ? 'warning' : 'neutral')}><span className="status-dot" />{status}</span>;
}
export function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
export function Panel({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={'panel ' + className}><div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><Inbox size={30} /><h3>{title}</h3><p>{description}</p></div>;
}
export function FileIcon({ type = 'Invoice' }: { type?: string }) {
  return <span className={'file-icon ' + (type === 'Purchase order' ? 'purple' : '')}><FileText size={19} /></span>;
}
export function UploadLink() {
  return <Link className="button primary" href="/upload"><span aria-hidden="true">+</span> Upload document</Link>;
}
export function DetailLink({ id }: { id: string }) {
  return <Link className="icon-button" href={'/documents/' + id} aria-label="Review document"><ArrowUpRight size={18} /></Link>;
}
