/** Submit exactly one PDF; no fixture fallback. State notifications are testable without a browser. */
export async function submitAnalysis(file, apiUrl, onState, fetcher = fetch) {
  onState({status:'loading'});
  try {
    const url = new URL(apiUrl);
    if (!['http:', 'https:'].includes(url.protocol) || !['localhost','127.0.0.1','[::1]'].includes(url.hostname) || url.username || url.password) throw new Error('Configure NEXT_PUBLIC_API_URL to a loopback backend URL.');
    if (!file.name.toLowerCase().endsWith('.pdf')) throw new Error('Real analysis supports PDF only. Images remain selection previews; OCR is not supported.');
    const body = new FormData(); body.append('file', file, file.name);
    let response;
    try {
      response = await fetcher(url.href.replace(/\/$/,'') + '/api/documents/analyze', {method:'POST',body,signal:AbortSignal.timeout(60000)});
    } catch { throw new Error('Cannot reach the local backend or the request timed out. Check its terminal, URL, and CORS configuration.'); }
    let result;
    try { result = await response.json(); } catch { throw new Error('Backend returned an invalid response. Check the backend terminal.'); }
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Analysis failed (HTTP ' + response.status + ').');
    if (!['analyzed','needs_ocr'].includes(result.status) || !result.fields || !Array.isArray(result.line_items) || !Array.isArray(result.validation?.checks) || !Array.isArray(result.warnings) || typeof result.stored !== "boolean" || (result.stored === true && typeof result.document_id !== "string")) throw new Error('Backend returned an unsupported analysis response.');
    onState({status:'success',result});
  } catch(error) {
    onState({status:'error',message:error instanceof Error ? error.message : 'Analysis failed.'});
  }
}
