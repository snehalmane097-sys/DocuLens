import test from 'node:test';
import assert from 'node:assert/strict';
import {apiRequest,jsonPost,backendUrl} from '../src/lib/api-client.mjs';

test('review submission preserves version, null overrides and server evidence',async()=>{
 const payload={version:2,fields:{cgst:null},notes:'Source checked',status:'pending'};
 const result=await apiRequest('/api/documents/real-test/review',jsonPost(payload),async(url,options)=>{
  assert.equal(url,backendUrl()+'/api/documents/real-test/review');assert.equal(options.method,'POST');assert.deepEqual(JSON.parse(options.body),payload);
  return new Response(JSON.stringify({version:3,effective_fields:{cgst:{value:null,evidence:'Source checked'}}}));
 });assert.equal(result.version,3);assert.equal(result.effective_fields.cgst.value,null);
});
test('API conflicts, unavailable server and invalid JSON are actionable errors',async()=>{
 await assert.rejects(apiRequest('/api/documents',{},async()=>new Response(JSON.stringify({detail:'Document changed; reload'}),{status:409})),/reload/);
 await assert.rejects(apiRequest('/api/documents',{},async()=>{throw new Error('network');}),/backend unavailable/);
 await assert.rejects(apiRequest('/api/documents',{},async()=>new Response('not json')),/invalid JSON/);
});
test('API URL remains loopback only',()=>{
 const previous=process.env.NEXT_PUBLIC_API_URL;
 try{process.env.NEXT_PUBLIC_API_URL='https://example.com';assert.throws(()=>backendUrl(),/loopback/);}
 finally{if(previous===undefined)delete process.env.NEXT_PUBLIC_API_URL;else process.env.NEXT_PUBLIC_API_URL=previous;}
});


test('caller cancellation retains timeout and timeout errors explain recovery',async()=>{
 const controller=new AbortController();
 await apiRequest('/api/documents',{signal:controller.signal},async(url,options)=>{
  assert.notEqual(options.signal,controller.signal);
  controller.abort();assert.equal(options.signal.aborted,true);
  return new Response('{}');
 });
 await assert.rejects(apiRequest('/api/documents',{},async()=>{throw new DOMException('expired','TimeoutError');}),/timed out/);
});
