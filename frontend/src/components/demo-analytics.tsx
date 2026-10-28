import { EmptyState, PageHeading, Panel } from '@/components/ui';
import { StatusChart, VolumeChart } from '@/components/charts';
import { documents, summary, attentionItems } from '@/lib/mock-data';
import { sampleIssues } from '@/lib/reconciliation-data';
export const metadata = { title:'Analytics' };
export default function AnalyticsPage() {
  const categories = [...new Set(sampleIssues.map(issue=>issue.category))].map(category=>({category,count:sampleIssues.filter(issue=>issue.category === category).length}));
  return <><PageHeading eyebrow="THE BIGGER PICTURE" title="Workspace analytics" description="Explore sample document activity and the findings awaiting review."/><div className="demo-notice">Fixture-derived analytics · All records and discrepancies are fictional. These are not model evaluation metrics.</div>
    <div className="analytics-stats">{[{label:'Sample documents',value:summary.total,note:summary.invoices+' invoices / '+summary.orders+' purchase orders'},{label:'Awaiting processing',value:summary.pending,note:'Sample status only'},{label:'Sample discrepancies',value:summary.discrepancies,note:'Across '+attentionItems.length+' documents'}].map(stat=><div className="stat-card" key={stat.label}><span className="muted">{stat.label}</span><div className="stat-number">{stat.value}</div><p>{stat.note}</p></div>)}</div>
    <div className="overview-grid"><Panel title="Document activity" subtitle="Grouped by full date in Asia/Kolkata"><VolumeChart records={documents}/><div className="chart-caption">{summary.total} sample documents</div></Panel><Panel title="Document status" subtitle="Derived from the shared document library"><StatusChart records={documents}/></Panel></div>
    <Panel title="Discrepancy breakdown" subtitle="Two deterministic comparison findings and one authored missing-field finding">{categories.length ? <div className="review-findings">{categories.map(row=><div className="breakdown-row" key={row.category}><span>{row.category}</span><meter min={0} max={sampleIssues.length} value={row.count} aria-label={row.category + ': ' + row.count + ' of ' + sampleIssues.length}/><strong>{row.count}</strong></div>)}</div> : <EmptyState title="No sample discrepancies" description="There are no findings to summarize."/>}<div className="table-footer">Severity and categories describe the demo scenario. No accuracy or confidence scores are claimed.</div></Panel>
  </>;
}
