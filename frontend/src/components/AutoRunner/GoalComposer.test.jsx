import JSZip from 'jszip';

import {
  buildImageAttachmentBlock,
  extractDocxTextFromBuffer,
  extractPdfTextFromBuffer,
  truncateAttachmentText,
} from './GoalComposer';

describe('GoalComposer attachment helpers', () => {
  test('truncateAttachmentText adds truncation marker', () => {
    const out = truncateAttachmentText('abcdef', 3);
    expect(out).toContain('abc');
    expect(out).toContain('[truncated]');
  });

  test('extractPdfTextFromBuffer recovers likely strings', () => {
    const raw = '%PDF-1.4\n1 0 obj\n(Helios Aegis Requirements)\n(Preview must pass)\n';
    const buffer = Uint8Array.from(raw.split('').map((ch) => ch.charCodeAt(0))).buffer;
    const out = extractPdfTextFromBuffer(buffer);
    expect(out).toContain('Helios Aegis Requirements');
    expect(out).toContain('Preview must pass');
  });

  test('extractDocxTextFromBuffer recovers document.xml text', async () => {
    const zip = new JSZip();
    zip.file(
      'word/document.xml',
      '<w:document><w:body><w:p><w:r><w:t>Tenant isolation</w:t></w:r></w:p><w:p><w:r><w:t>Preview verifier</w:t></w:r></w:p></w:body></w:document>',
    );
    const buffer = await zip.generateAsync({ type: 'arraybuffer' });
    const out = await extractDocxTextFromBuffer(buffer);
    expect(out).toContain('Tenant isolation');
    expect(out).toContain('Preview verifier');
  });

  test('buildImageAttachmentBlock includes real data url content', () => {
    const out = buildImageAttachmentBlock({
      fileName: 'diagram.png',
      mimeType: 'image/png',
      sizeKb: 12,
      dataUrl: 'data:image/png;base64,abc123',
    });
    expect(out).toContain('diagram.png');
    expect(out).toContain('image/png');
    expect(out).toContain('data:image/png;base64,abc123');
  });
});
