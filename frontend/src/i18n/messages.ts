import {messageCatalog} from './catalog.generated';
import {defaultLocale, type AppLocale} from './routing';

type MessageTree = {[key: string]: string | MessageTree};

/** The default-locale catalog is the source of truth for the message key type. */
export type AppMessages = (typeof messageCatalog)[typeof defaultLocale];

function isMessageTree(value: unknown): value is MessageTree {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Recursively overlays `override` on top of `base`. Keys present only in `base`
 * survive, which is what makes the fallback below work per key instead of per
 * namespace.
 */
function deepMerge(base: MessageTree, override: MessageTree): MessageTree {
  const result: MessageTree = {...base};

  for (const [key, overrideValue] of Object.entries(override)) {
    const baseValue = result[key];
    result[key] =
      isMessageTree(baseValue) && isMessageTree(overrideValue)
        ? deepMerge(baseValue, overrideValue)
        : overrideValue;
  }

  return result;
}

/**
 * All namespaces for a locale, with the default locale (`uz`) merged in
 * underneath. A key that has not been translated yet renders the Uzbek string
 * rather than the raw key — the same fallback rule the API applies to database
 * translations.
 */
export function getMessagesForLocale(locale: AppLocale): AppMessages {
  const fallback = messageCatalog[defaultLocale] as unknown as MessageTree;

  if (locale === defaultLocale) {
    return fallback as unknown as AppMessages;
  }

  const requested = messageCatalog[locale] as unknown as MessageTree;
  return deepMerge(fallback, requested) as unknown as AppMessages;
}
