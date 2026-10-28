import Link from 'next/link';
export default function NotFound() { return <div className="empty-state"><h1>Document or page not found</h1><p>This item is not part of the sample workspace.</p><Link href="/documents" className="button primary">Back to documents</Link></div>; }
