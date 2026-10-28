import type { Metadata } from 'next';
import { Shell } from '@/components/shell';
import './globals.css';
export const metadata: Metadata = { title: { default: 'DocuLens AI', template: '%s | DocuLens AI' }, description: 'Local invoice analysis, evidence-led review and reconciliation.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Shell>{children}</Shell></body></html>;
}
