import Demo from '@/components/demo-documents';
import {RealWorkspace} from '@/components/real-workspace';
export const metadata={title:'Documents'};
export default async function Page({searchParams}:{searchParams:Promise<{status?:string;q?:string}>}) {
 const query=await searchParams;
 const initialStatus=['review','pending','approved','rejected'].includes(query.status||'')?query.status:'all';
 return <RealWorkspace key={initialStatus+(query.q||'')} mode="history" initialStatus={initialStatus} initialQuery={typeof query.q==='string'?query.q.slice(0,150):''} demo={<Demo/>}/>;
}
