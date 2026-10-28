'use client';
import { useState } from 'react';
import { Search, SlidersHorizontal } from 'lucide-react';
import { documents, date, money } from '@/lib/mock-data';
import { Badge, DetailLink, EmptyState, FileIcon } from './ui';
export function DocumentTable({ compact = false }: { compact?: boolean }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All statuses');
  const [type, setType] = useState('All types');
  const rows = documents.filter(d => (d.filename + ' ' + d.vendor).toLowerCase().includes(query.toLowerCase()) && (status === 'All statuses' || d.status === status) && (type === 'All types' || d.type === type));
  return <><div className="table-toolbar"><label className="search-input"><Search size={17} /><span className="sr-only">Search documents</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search documents or vendors…" /></label><div className="filters"><SlidersHorizontal size={16} aria-hidden="true" /><label><span className="sr-only">Filter by type</span><select value={type} onChange={e => setType(e.target.value)}><option>All types</option><option>Invoice</option><option>Purchase order</option></select></label><label><span className="sr-only">Filter by status</span><select value={status} onChange={e => setStatus(e.target.value)}><option>All statuses</option><option>Processed</option><option>Needs review</option><option>Pending</option></select></label></div></div>
    {rows.length ? <div className="table-scroll"><table><caption className="sr-only">Fictional sample documents</caption><thead><tr><th>Document name</th><th>Type</th><th>Upload date</th>{!compact && <th>Amount</th>}<th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{rows.map(d => <tr key={d.id}><td><div className="document-cell"><FileIcon type={d.type} /><div><a href={'/documents/' + d.id} className="file-name">{d.filename}</a><small>{d.vendor}</small></div></div></td><td><span className="type-label">{d.type}</span></td><td className="muted nowrap">{date(d.uploadedAt)}</td>{!compact && <td className="tabular">{money(d.total)}</td>}<td><Badge status={d.status} /></td><td><DetailLink id={d.id} /></td></tr>)}</tbody></table></div> : <EmptyState title="No documents found" description="Try another search or reset the filters." />}
    <div className="table-footer"><span>Showing {rows.length} of {documents.length} sample documents</span><span>Preview data only</span></div></>;
}
