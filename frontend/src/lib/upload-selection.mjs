import { MAX_FILES, validateFileMetadata, validateFileSignature } from './upload-validation.mjs';
/** Local preview checks. Never sends file contents anywhere.
 * @param {Array<{name:string,size:number}>} existing
 * @param {Array<{name:string,size:number,type:string,slice:Function}>} incoming */
export async function checkSelection(existing, incoming) {
  const accepted = [];
  const errors = [];
  if (existing.length + incoming.length > MAX_FILES) return { accepted, errors:['Select no more than five files in total. Remove a file before adding more.'] };
  for (const file of incoming) {
    const error = validateFileMetadata(file);
    if (error) { errors.push(file.name + ': ' + error); continue; }
    if ([...existing,...accepted].some(f => f.name === file.name && f.size === file.size)) { errors.push(file.name + ': Already selected.'); continue; }
    try {
      const bytes = new Uint8Array(await file.slice(0,8).arrayBuffer());
      if (!validateFileSignature(bytes,file.name)) { errors.push(file.name + ': Header does not match the file extension.'); continue; }
      accepted.push({ name:file.name, size:file.size });
    } catch { errors.push(file.name + ': Could not read file. Please try again.'); }
  }
  return { accepted, errors };
}
