'use client';
export default function ErrorBoundary({ reset }: { reset: () => void }) { return <div className="empty-state" role="alert"><h1>Something interrupted this view</h1><p>Please try loading the workspace again.</p><button className="button primary" onClick={reset}>Try again</button></div>; }
