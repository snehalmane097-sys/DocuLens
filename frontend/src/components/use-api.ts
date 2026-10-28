'use client';
import {useCallback,useEffect,useState} from 'react';
import {apiRequest} from '@/lib/api-client.mjs';
export function useApi<T>(path:string,refreshKey='') {
  const [value,setValue]=useState<T|null>(null);
  const [error,setError]=useState('');
  const [generation,setGeneration]=useState(0);
  const [loaded,setLoaded]=useState('');
  const key=JSON.stringify([path,refreshKey,generation]);
  useEffect(()=>{
    const abort=new AbortController();
    apiRequest(path,{signal:abort.signal}).then((data:T)=>{if(!abort.signal.aborted){setValue(data);setError('');setLoaded(key);}}).catch((err:Error)=>{if(!abort.signal.aborted){setValue(null);setError(err.message);setLoaded(key);}});
    return ()=>abort.abort();
  },[path,key]);
  const reload=useCallback(()=>setGeneration(n=>n+1),[]);
  return {value,error,loading:loaded!==key,reload};
}
