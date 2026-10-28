import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateFileMetadata, validateFileSignature, MAX_FILE_BYTES } from '../src/lib/upload-validation.mjs';
test('accepts supported metadata and uppercase extensions', () => {
  assert.equal(validateFileMetadata({ name: 'invoice.PDF', type: 'application/pdf', size: 100 }), null);
});
test('rejects oversized, empty, unsupported and mismatched files', () => {
  for (const file of [
    { name: 'x.pdf', type: 'application/pdf', size: MAX_FILE_BYTES + 1 },
    { name: 'x.pdf', type: '', size: 0 },
    { name: 'x.exe', type: '', size: 20 },
    { name: 'x.png', type: 'application/pdf', size: 20 },
  ]) assert.ok(validateFileMetadata(file));
});
test('checks signatures, renamed content and truncated headers', () => {
  assert.ok(validateFileSignature(new Uint8Array([37,80,68,70,45]), 'x.pdf'));
  assert.ok(validateFileSignature(new Uint8Array([137,80,78,71,13,10,26,10]), 'x.png'));
  assert.ok(validateFileSignature(new Uint8Array([255,216,255]), 'x.jpg'));
  assert.equal(validateFileSignature(new Uint8Array([37,80]), 'x.pdf'), false);
  assert.equal(validateFileSignature(new Uint8Array([37,80,68,70,45]), 'x.jpg'), false);
});
