export type DocumentStatus = 'Processed' | 'Needs review' | 'Pending';
export type DocumentType = 'Invoice' | 'Purchase order';
export interface DocumentRecord {
  id: string; filename: string; reference: string; vendor: string;
  type: DocumentType; uploadedAt: string; status: DocumentStatus; total: number; issues: number;
}
