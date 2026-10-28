export interface AnalysisResult {
  filename: string; status: 'analyzed' | 'needs_ocr'; method: string; pages: number; stored: boolean; document_id?:string; version?:number; review_status?:string;
  fields: Record<string,{value:string|null;evidence:string|null;method:string}>;
  gstin_candidates?: Array<{value:string;party:"supplier"|"buyer"|"unknown";evidence:string;method:string;line:number}>;
  line_items: Array<{description:string;quantity:string|null;unit_rate:string|null;line_total:string|null;tax_amount:string|null;tax_rate:string|null;evidence:string}>;
  validation: {tolerance:string;mismatches:number;unknown:number;passed:number;checks:Array<{name:string;status:'pass'|'mismatch'|'unknown';calculated:string|null;extracted:string|null;explanation:string}>};
  warnings:string[]; text_excerpt:string;
}
export type AnalysisState = {status:'loading'} | {status:'error';message:string} | {status:'success';result:AnalysisResult};
