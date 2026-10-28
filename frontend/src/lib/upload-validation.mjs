export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const MAX_FILES = 5;
const formats = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg' };
// Usability checks only. Real uploads will require server validation.
export function validateFileMetadata(file) {
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!extension || !formats[extension]) return 'Use a PDF, PNG, or JPG file.';
  if (file.type && file.type !== formats[extension]) return 'File type does not match its extension.';
  if (file.size === 0) return 'Empty files are not supported.';
  if (file.size > MAX_FILE_BYTES) return 'File exceeds the 10 MB limit.';
  return null;
}
export function validateFileSignature(bytes, filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return bytes.length >= 5 && [37,80,68,70,45].every((v,i) => bytes[i] === v);
  if (ext === 'png') return bytes.length >= 8 && [137,80,78,71,13,10,26,10].every((v,i) => bytes[i] === v);
  if (ext === 'jpg' || ext === 'jpeg') return bytes.length >= 3 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  return false;
}
