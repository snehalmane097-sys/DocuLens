import type { AnalysisResult } from './analysis-types';
export interface StoredDocument {
  id:string;filename:string;created_at:string;updated_at:string;version:number;
  processing_status:'analyzed'|'needs_ocr';review_status:'pending'|'approved'|'rejected';
  analysis:AnalysisResult;effective_fields:AnalysisResult['fields'];review_validation:AnalysisResult['validation'];
  review:{fields:Record<string,string|null>;notes:string};
  duplicate_candidates?:Array<{id:string;filename:string;reason:string}>;
}
export interface DocumentList {mode:'persistent';items:StoredDocument[];total:number}
export interface Analytics {total:number;review_status:Record<string,number>;needs_ocr:number;mismatches:number;unknown_checks:number;volume:Array<{date:string;count:number}>;discrepancies:Record<string,number>}
export interface ReconciliationReport { created_at:string;id:string;version:number;status:string;stale?:boolean;expected_id:string;observed_id:string;mismatches:number;unknown:number;rows:Array<{id:string;field:string;expected:string|null;observed:string|null;expected_evidence:string|null;observed_evidence:string|null;status:string;review_status:string;review_note:string}>}
