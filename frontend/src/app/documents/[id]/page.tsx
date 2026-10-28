import { SavedDocument } from '@/components/saved-document';
import { notFound } from 'next/navigation';
import { documents } from '@/lib/mock-data';
import { DocumentReview } from '@/components/document-review';
export const metadata = { title:'Document review' };
export default async function DocumentDetail({params}:{params:Promise<{id:string}>}) {
  const {id} = await params;
  if(id.startsWith('real-')) return <SavedDocument id={id}/>;
  const document = documents.find(doc=>doc.id === id);
  if (!document) notFound();
  return <DocumentReview key={document.id} document={document}/>;
}
