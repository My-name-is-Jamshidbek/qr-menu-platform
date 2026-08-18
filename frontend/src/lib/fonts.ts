import {Inter, Playfair_Display} from 'next/font/google';

/**
 * Fonts are self-hosted by `next/font`: the files are downloaded at build time
 * and served from our own origin, so there is no request to fonts.gstatic.com,
 * no layout shift and nothing to allow in the CSP.
 *
 * Both families ship `cyrillic` alongside `latin`, which the Russian locale needs.
 */

/** Display face — headings, product names, prices. Exposed as `--font-display`. */
export const displayFont = Playfair_Display({
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  variable: '--font-display',
  fallback: ['Georgia', 'Times New Roman', 'serif']
});

/** Body face — everything else. Exposed as `--font-body`. */
export const bodyFont = Inter({
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  variable: '--font-body',
  fallback: ['system-ui', 'Segoe UI', 'Helvetica Neue', 'sans-serif']
});

/** Class list that puts both CSS variables in scope. Apply once, on `<html>`. */
export const fontVariables = `${displayFont.variable} ${bodyFont.variable}`;
