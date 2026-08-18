import {defaultLocale, isAppLocale, type AppLocale} from '@/i18n/routing';

/**
 * Picks the language a QR scan should land in.
 *
 * The scan route sits outside the `[locale]` segment — the printed code carries
 * a token and nothing else — so it has to repeat the negotiation the locale
 * proxy normally performs: an explicit earlier choice (`NEXT_LOCALE`) wins over
 * the phone's `Accept-Language`, which wins over the default locale.
 */

/** Cookie the locale proxy writes when a visitor picks a language. */
export const LOCALE_COOKIE_NAME = 'NEXT_LOCALE';

/**
 * Best supported match from an `Accept-Language` header.
 *
 * Only the primary subtag is compared, so `ru-RU` matches `ru`. Entries are
 * ordered by their `q` value; a malformed `q` sinks the entry rather than
 * failing the parse, because a guest's browser is not worth a 500.
 */
function fromAcceptLanguage(header: string | null): AppLocale | null {
  if (!header) return null;

  const ranked = header
    .split(',')
    .map((part) => {
      const [tag, ...parameters] = part.trim().split(';');
      const quality = parameters
        .map((parameter) => /^\s*q=([0-9.]+)\s*$/.exec(parameter))
        .find(Boolean)?.[1];

      return {
        language: tag.trim().toLowerCase().split('-')[0],
        quality: quality === undefined ? 1 : (Number.parseFloat(quality) || 0)
      };
    })
    .filter((entry) => entry.language.length > 0 && entry.quality > 0)
    .sort((a, b) => b.quality - a.quality);

  for (const entry of ranked) {
    if (isAppLocale(entry.language)) return entry.language;
  }

  return null;
}

export function negotiateLocale(
  cookieValue: string | undefined,
  acceptLanguage: string | null
): AppLocale {
  if (isAppLocale(cookieValue)) return cookieValue;
  return fromAcceptLanguage(acceptLanguage) ?? defaultLocale;
}
