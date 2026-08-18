'use client';

import {useTranslations} from 'next-intl';

import {Link, usePathname} from '@/i18n/navigation';
import {cn} from '@/lib/cn';

/**
 * Section tabs. Real links, so a section is bookmarkable and opens in a new tab
 * the way a link is expected to; the active state is derived from the URL
 * rather than from component state, so a browser Back keeps it honest.
 *
 * `usePathname` from `@/i18n/navigation` returns the path *without* the locale
 * prefix, which is why the hrefs here are locale-free too.
 */

const SECTIONS = [
  {href: '/admin', key: 'dashboard'},
  {href: '/admin/products', key: 'products'},
  {href: '/admin/tables', key: 'tables'}
] as const;

export function AdminNav() {
  const t = useTranslations('admin.nav');
  const pathname = usePathname();

  return (
    <nav aria-label={t('sectionLabel')}>
      <ul className="flex flex-wrap items-center gap-2">
        {SECTIONS.map((section) => {
          const isActive =
            section.href === '/admin'
              ? pathname === '/admin'
              : pathname === section.href || pathname.startsWith(`${section.href}/`);

          return (
            <li key={section.href}>
              <Link
                href={section.href}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'inline-flex min-h-11 items-center rounded-md px-4 text-label uppercase',
                  'transition-colors duration-[var(--motion-fast)]',
                  isActive
                    ? 'bg-gold-gradient text-ink'
                    : 'border border-ground-border text-cream/75 hover:border-gold-700 hover:text-gold-200'
                )}
              >
                {t(section.key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
