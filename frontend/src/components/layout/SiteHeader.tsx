'use client';

import {useTranslations} from 'next-intl';

import {Link, usePathname} from '@/i18n/navigation';
import {cn} from '@/lib/cn';

import {Container} from './Container';
import {LocaleSwitcher} from './LocaleSwitcher';

/** Route, and the `common.nav` key that labels it. */
const NAV_ITEMS = [
  {href: '/', key: 'home'},
  {href: '/menu', key: 'menu'}
] as const;

/**
 * Sticky 64px header: a blurred veil over the ground rather than an opaque bar,
 * so the page keeps reading as one continuous dark room while scrolling. The
 * gold hairline underneath is the only accent it carries.
 */
export function SiteHeader() {
  const t = useTranslations('common.nav');
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-ground-border/80 bg-ground-base/80 backdrop-blur-[12px]">
      <Container as="div" className="flex h-header items-center justify-between gap-2 sm:gap-4">
        <Link
          href="/"
          className="group flex shrink-0 items-center gap-2.5"
          aria-label={t('home')}
        >
          <span className="flex size-9 items-center justify-center rounded-pill bg-gold-gradient text-ink shadow-card">
            <span className="font-display text-[1.0625rem] leading-none font-semibold" aria-hidden="true">
              B
            </span>
          </span>
          <span className="font-display text-[1.0625rem] leading-none font-semibold tracking-[0.14em] text-cream uppercase">
            Boss<span className="text-gold-300"> Kafe</span>
          </span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-4">
          {/*
            The nav is hidden on phones: the monogram already returns home and
            the menu is the page a QR scan lands on, so both links are
            redundant there. Keeping them wraps the labels onto two lines and
            crowds the locale switcher.
          */}
          <nav aria-label={t('menu')} className="hidden items-center gap-0.5 sm:flex">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.href === '/' ? pathname === '/' : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'relative rounded-sm px-2.5 py-2 text-label uppercase',
                    'transition-colors duration-[var(--motion-fast)] ease-out',
                    isActive ? 'text-gold-200' : 'text-cream/65 hover:text-cream'
                  )}
                >
                  {t(item.key)}
                  <span
                    aria-hidden="true"
                    className={cn(
                      'absolute inset-x-2.5 -bottom-px h-px bg-gold-gradient transition-opacity duration-[var(--motion-base)]',
                      isActive ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                </Link>
              );
            })}
          </nav>

          <LocaleSwitcher />
        </div>
      </Container>

      {/* Gold hairline seam between the header and the page. */}
      <span aria-hidden="true" className="absolute inset-x-0 -bottom-px block rule-gold opacity-60" />
    </header>
  );
}
