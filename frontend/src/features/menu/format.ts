import type {AppLocale} from '@/i18n/routing';

/**
 * Price formatting.
 *
 * Prices are integer so'm (see `docs/DATA_MODEL.md`): UZS has no practical minor
 * unit, so there are never decimals to render.
 *
 * The grouping separator is spelled out per locale instead of being taken from
 * `Intl.NumberFormat`. That is deliberate, and not premature optimisation: this
 * string is produced during server rendering by Node and again in the browser
 * during hydration, and the two ship different ICU data. Node formats `uz` with
 * U+00A0, Chromium does not agree, and the mismatch made React discard and
 * re-render every price on the page. Pinning the separator makes the two passes
 * byte-identical by construction.
 *
 * The currency word likewise comes from the message catalogue rather than from
 * CLDR, which would emit "UZS" instead of the "so'm" the restaurant prints.
 */

/** Thousands separator per locale. A no-break space keeps "30 000" on one line. */
const GROUP_SEPARATOR: Record<AppLocale, string> = {
  uz: '\u00a0',
  ru: '\u00a0',
  en: ','
};

/** Used for any locale not listed above, matching the Uzbek default. */
const FALLBACK_SEPARATOR = '\u00a0';

function separatorFor(locale: string): string {
  return GROUP_SEPARATOR[locale as AppLocale] ?? FALLBACK_SEPARATOR;
}

/** `30000` → `"30 000"`, grouped in threes from the right. */
export function formatPriceAmount(price: number, locale: string): string {
  const digits = Math.round(Math.abs(price)).toString();
  const separator = separatorFor(locale);

  let grouped = '';
  for (let index = 0; index < digits.length; index += 1) {
    // A separator goes before every digit whose distance from the end is a
    // non-zero multiple of three.
    const fromEnd = digits.length - index;
    if (index > 0 && fromEnd % 3 === 0) grouped += separator;
    grouped += digits[index];
  }

  return price < 0 ? `-${grouped}` : grouped;
}

/**
 * `30000` → `"30 000 so'm"`.
 *
 * The space before the currency is a no-break one, so a price never wraps onto
 * two lines inside its badge.
 */
export function formatPrice(price: number, locale: string, currency: string): string {
  return `${formatPriceAmount(price, locale)}\u00a0${currency}`;
}
