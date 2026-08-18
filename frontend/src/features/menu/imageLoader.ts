import type {ImageLoader} from 'next/image';

import type {MenuImage} from './types';

/**
 * Serves product photos straight from the derivatives the API already built.
 *
 * Django converts every upload to WebP at 400 / 800 / 1600 px on save, and the
 * API hands those URLs over in `image.srcset`. Letting Next's optimizer re-encode
 * them would mean a second round of lossy compression, a `/_next/image` hop in
 * front of object storage, and server CPU spent reproducing work that is already
 * done. A custom loader keeps `next/image`'s `srcset`/`sizes` machinery and CLS
 * guarantees while pointing every candidate at the real file.
 */

/** Parses the `srcset` map into widths sorted ascending, with their URLs. */
function derivativesOf(image: MenuImage): Array<{width: number; url: string}> {
  return Object.entries(image.srcset)
    .map(([width, url]) => ({width: Number(width), url}))
    .filter((entry) => Number.isFinite(entry.width) && entry.width > 0)
    .sort((a, b) => a.width - b.width);
}

/**
 * Builds a loader bound to one product photo.
 *
 * `next/image` calls this once per candidate width in the generated `srcset`.
 * We answer with the smallest derivative that still covers the requested width,
 * so the browser never downloads more pixels than it can show, and never has to
 * upscale a file it picked. Requests wider than the largest derivative get that
 * largest file — 1600px is the widest original we keep.
 */
export function createProductImageLoader(image: MenuImage): ImageLoader {
  const derivatives = derivativesOf(image);

  return ({width}) => {
    if (derivatives.length === 0) return image.src;

    const covering = derivatives.find((entry) => entry.width >= width);
    return (covering ?? derivatives[derivatives.length - 1]).url;
  };
}

/**
 * The widest derivative, used as the `src` prop.
 *
 * With a custom loader `src` is not what lands in the DOM — every candidate,
 * including the plain `src` attribute, is produced by the loader. It is the
 * canonical identity of the image, so the full-size file is the honest value,
 * and `next/image` additionally compares it against the loader's output to
 * detect loaders that ignore the width they are given.
 */
export function fullSizeUrl(image: MenuImage): string {
  const derivatives = derivativesOf(image);
  return derivatives.length > 0 ? derivatives[derivatives.length - 1].url : image.src;
}

/**
 * How wide a card image renders at each breakpoint, matching the menu grid in
 * `docs/DESIGN_SYSTEM.md` (1 column under 640px, 2 under 1024, 3 under 1280,
 * 4 above, inside a 1200px column with fluid gutters).
 *
 * Without this the browser assumes every image is viewport-wide and pulls the
 * 1600px file onto a phone — which is most of how the original page reached
 * ~10 MB.
 */
export const PRODUCT_IMAGE_SIZES = [
  '(max-width: 639px) calc(100vw - 2rem)',
  '(max-width: 1023px) calc(50vw - 2rem)',
  '(max-width: 1279px) calc(33vw - 2rem)',
  '288px'
].join(', ');
