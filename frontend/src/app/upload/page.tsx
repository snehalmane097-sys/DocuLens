import { PageHeading } from '@/components/ui';
import { UploadPreview } from '@/components/upload-preview';
export const metadata = { title:'PDF invoice analysis' };
export default function UploadPage() { return <><PageHeading eyebrow="BRING YOUR DOCUMENTS TOGETHER" title="Upload documents" description="Extract labelled fields and check arithmetic in a digitally generated PDF invoice."/><div className="demo-notice">Real PDF analysis through your local backend / PDF bytes are not stored; extracted analysis is saved locally. Sample documents elsewhere remain fictional and separate.</div><UploadPreview/></>; }
