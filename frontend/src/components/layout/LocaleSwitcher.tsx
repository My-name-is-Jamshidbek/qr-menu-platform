'use client';

import {useLocale, useTranslations} from 'next-intl';

import {Link, usePathname} from '@/i18n/navigation';
import {locales} from '@/i18n/routing';
import {cn} from '@/lib/cn';

export interface LocaleSwitcherProps {
  className?: string;
}

/**
 * Segmented language control.
 *
 * Each option is a real link to the *same* route in another language, so the
 * choice is bookmarkable, crawlable and survives JavaScript being unavailable.
 * `usePathname` from the i18n navigation helpers returns the current path with
 * its locale prefix stripped, so the same value re-prefixed with another locale
 * turns `/uz/menu/desserts` into `/ru/menu/desserts` — the visitor stays where
 * they were instead of being dropped on the home page.
 */
export function LocaleSwitcher({className}: LocaleSwitcherProps) {
  const t = useTranslations('common.language');
  const activeLocale = useLocale();
  const pathname = usePathname();

  return (
    <nav
      aria-label={t('switch')}
      className={cn(
        'flex items-center gap-0.5 rounded-pill border border-ground-border bg-ground-surface p-0.5',
        className
      )}
    >
      {locales.map((locale) => {
        const isActive = locale === activeLocale;

        return (
          <Link
            key={locale}
            href={pathname}
            locale={locale}
            hrefLang={locale}
            aria-current={isActive ? 'true' : undefined}
            className={cn(
              'rounded-pill px-2.5 py-1.5 text-label uppercase',
              'transition-colors duration-[var(--motion-fast)] ease-out',
              isActive
                ? 'bg-gold-gradient text-ink'
                : 'text-cream/60 hover:bg-ground-elevated hover:text-gold-200'
            )}
          >
            <span aria-hidden="true">{locale}</span>
            <span className="sr-only">{t(locale)}</span>
          </Link>
        );
      })}
    </nav>
  );
}
