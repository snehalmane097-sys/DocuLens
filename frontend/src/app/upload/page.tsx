import { PageHeading } from '@/components/ui';
import { UploadPreview } from '@/components/upload-preview';
export const metadata = { title:'Analyze invoice' };
export default function UploadPage() { return <><PageHeading eyebrow="" title="Analyze an invoice" description="Upload an invoice to extract its details and check the amounts."/><UploadPreview/></>; }
