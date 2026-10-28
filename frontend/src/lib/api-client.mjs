export function backendUrl() {
  const url=new URL(process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000');
  if(!['http:','https:'].includes(url.protocol) || !['localhost','127.0.0.1','[::1]'].includes(url.hostname) || url.username || url.password) throw new Error('Configure a loopback NEXT_PUBLIC_API_URL.');
  return url.href.replace(/\/$/,'');
}
export async function apiRequest(path,options={},fetcher=fetch) {
  let response;
  const timeout=AbortSignal.timeout(60000);
  const signal=options.signal ? AbortSignal.any([options.signal,timeout]) : timeout;
  try { response=await fetcher(backendUrl()+path,{...options,signal}); }
  catch(error) { if(error.name==='AbortError') throw error; if(error.name==='TimeoutError') throw new Error('Local backend timed out. Check its terminal and retry.'); throw new Error('Local backend unavailable. Check its terminal, URL and CORS settings.'); }
  let body;
  try { body=await response.json(); } catch { throw new Error('Backend returned invalid JSON.'); }
  if(!response.ok) throw new Error(typeof body.detail==='string' ? body.detail : 'Request failed (HTTP '+response.status+').');
  return body;
}
export const jsonPost = body => ({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
