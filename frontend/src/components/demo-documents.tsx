import type { Metadata } from 'next';
import { PageHeading, Panel, UploadLink } from '@/components/ui';
import { summary } from '@/lib/mock-data';
import { DocumentTable } from '@/components/document-table';
export const metadata: Metadata = { title: 'Documents' };
export default function Documents() { return <><PageHeading eyebrow="DOCUMENT LIBRARY" title="All documents" description="Find the right document. Keep the important details in view." action={<UploadLink />} /><div className="demo-notice">Sample library · These fictional records are for UI exploration only.</div><Panel title="Document library" subtitle={"Invoices and purchase orders / " + summary.total + " sample records"}><DocumentTable /></Panel></>; }
