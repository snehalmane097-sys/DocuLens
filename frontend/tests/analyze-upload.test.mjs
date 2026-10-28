import {test} from 'node:test';
import assert from 'node:assert/strict';
import {submitAnalysis} from '../src/lib/analyze-upload.mjs';
const file = new File(['%PDF-test'],'invoice.pdf',{type:'application/pdf'});
const result = {status:'analyzed',fields:{},line_items:[],validation:{checks:[]},warnings:[],stored:false};
test('submits one multipart PDF and emits loading then actual result',async()=>{
  const states=[];
  await submitAnalysis(file,'http://127.0.0.1:8000',s=>states.push(s),async(url,options)=>{
    assert.equal(states[0].status,'loading');assert.equal(url,'http://127.0.0.1:8000/api/documents/analyze');
    assert.equal(options.method,'POST');assert.ok(options.body instanceof FormData);assert.equal(options.body.get('file').name,'invoice.pdf');
    assert.equal(options.headers,undefined);
    return {ok:true,json:async()=>result};
  });
  assert.deepEqual(states,[{status:'loading'},{status:'success',result}]);
});
test('empty-text is a real needs_ocr result, with no sample fallback',async()=>{
  const states=[];await submitAnalysis(file,'http://localhost:8000',s=>states.push(s),async()=>({ok:true,json:async()=>({...result,status:'needs_ocr'})}));
  assert.equal(states[1].result.status,'needs_ocr');
});
test('server validation, missing dependencies and connection errors become error states',async()=>{
  for(const fetcher of [async()=>({ok:false,status:415,json:async()=>({detail:'Invalid PDF signature'})}),async()=>({ok:false,status:503,json:async()=>({detail:'Missing dependencies'})}),async()=>{throw Error('network');},async()=>({ok:true,json:async()=>({})})]){
    const states=[];await submitAnalysis(file,'http://localhost:8000',s=>states.push(s),fetcher);assert.equal(states[1].status,'error');assert.ok(states[1].message);
  }
});
test('images and non-local backend configuration are not submitted',async()=>{
  for(const [input,url] of [[new File(['png'],'a.png'),'http://localhost:8000'],[file,'https://external.example']]){
    let called=false;const states=[];await submitAnalysis(input,url,s=>states.push(s),async()=>{called=true;});assert.equal(called,false);assert.equal(states[1].status,'error');
  }
});
