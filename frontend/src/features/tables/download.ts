/**
 * Hands a generated file to the browser.
 *
 * The QR artwork lives behind an authenticated API the browser cannot reach, so
 * the bytes arrive through a Server Action and are turned into a download here
 * rather than linked to directly.
 */

/** Triggers a download of `data` under `filename`. Browser-only. */
export function downloadBlob(data: BlobPart, filename: string, mimeType: string): void {
  const url = URL.createObjectURL(new Blob([data], {type: mimeType}));
  const link = document.createElement('a');

  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.append(link);
  link.click();
  link.remove();

  // Revoking synchronously can cancel the download in Safari; one frame is
  // enough for the navigation to have been queued.
  requestAnimationFrame(() => URL.revokeObjectURL(url));
}

/** Decodes a base64 payload carried across the RSC boundary into raw bytes. */
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return buffer;
}
