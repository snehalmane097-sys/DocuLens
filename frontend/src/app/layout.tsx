import type { Metadata } from 'next';
import { Shell } from '@/components/shell';
import './globals.css';
export const metadata: Metadata = { title: { default: 'DocuLens AI · Overview', template: '%s · DocuLens AI' }, description: 'A document understanding, validation, and reconciliation workspace. Phase 1 demo.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Shell>{children}</Shell></body></html>;
}
