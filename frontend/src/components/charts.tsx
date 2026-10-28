import { documents } from '@/lib/mock-data';
import { summarize, volumeByDate } from '@/lib/demo-logic.mjs';
import type { DocumentRecord } from '@/lib/types';
import { EmptyState } from './ui';
const shortDate = (value:string) => new Intl.DateTimeFormat('en-IN', {day:'2-digit',month:'short',year:'numeric',timeZone:'Asia/Kolkata'}).format(new Date(value + 'T00:00:00+05:30'));
export function VolumeChart({ records = documents, source = "sample" }: {records?:DocumentRecord[];source?:"sample"|"real"}) {
  const days = volumeByDate(records);
  if (!days.length) return <EmptyState title="No document activity" description="Document activity will appear here when records are available."/>;
  const max = Math.max(3, ...days.map(d => d.count));
  return <div className="volume-chart" role="img" aria-label={days.map(d => shortDate(d.date) + ': ' + d.count + ' ' + source + ' documents').join(', ')}>
    <div className="chart-scale">{[max,Math.round(max*2/3),Math.round(max/3),0].map((n,i)=><span key={i}>{n}</span>)}</div><div className="bars">{days.map(day => <div className="bar-group" key={day.date}><div className="bar-track"><div className="bar" style={{height: day.count/max*100 + '%'}}><span>{day.count}</span></div></div><span>{shortDate(day.date)}</span></div>)}</div>
  </div>;
}
export function StatusChart({ records = documents, source = "sample" }: {records?:DocumentRecord[];source?:"sample"|"real"}) {
  const s = summarize(records);
  if (!s.total) return <EmptyState title="No status data" description="Status summaries will appear when records are available."/>;
  const segments = [{label:'Processed',count:s.processed,color:'#087f73',className:'teal'}, {label:'Needs review',count:s.review,color:'#e4ad53',className:'amber'}, {label:'Pending',count:s.pending,color:'#dce3e7',className:'gray'}];
  let offset = 0;
  return <div className="status-chart"><svg viewBox="0 0 120 120" role="img" aria-label={source + ' statuses: ' + segments.map(d=>d.label + ': ' + d.count).join(', ')}>{segments.map(segment => {
    const start = offset; const percent = segment.count/s.total*100; offset += percent;
    return <circle key={segment.label} cx="60" cy="60" r="48" fill="none" stroke={segment.color} strokeWidth="13" pathLength="100" strokeDasharray={percent + ' ' + (100-percent)} strokeDashoffset={-start} transform="rotate(-90 60 60)"/>;
  })}<text x="60" y="58" textAnchor="middle" className="donut-number">{s.total}</text><text x="60" y="76" textAnchor="middle" className="donut-label">documents</text></svg><div className="chart-legend">{segments.map(d=><div key={d.label}><i className={'legend-dot ' + d.className}/><span>{d.label}</span><strong>{d.count}</strong></div>)}</div></div>;
}
