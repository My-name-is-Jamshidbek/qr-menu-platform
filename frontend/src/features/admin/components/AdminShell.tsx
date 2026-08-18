import {getTranslations} from 'next-intl/server';
import type {ReactNode} from 'react';

import {Container} from '@/components/layout';
import {Link} from '@/i18n/navigation';
import type {AppLocale} from '@/i18n/routing';
import type {SessionUser} from '@/lib/auth';

import {AdminNav} from './AdminNav';
import {LogoutButton} from './LogoutButton';

/**
 * Chrome shared by every admin screen: who you are, where you are, and the way
 * out. Deliberately *not* sticky — the public header already occupies the top
 * layer, and a second sticky bar is exactly how a primary action ends up
 * underneath something the person cannot see.
 */
export interface AdminShellProps {
  locale: AppLocale;
  user: SessionUser;
  children: ReactNode;
}

export async function AdminShell({locale, user, children}: AdminShellProps) {
  const t = await getTranslations({locale, namespace: 'admin'});

  return (
    <Container as="div" className="flex flex-col gap-8 py-8">
      <header className="flex flex-col gap-5 border-b border-ground-border pb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="text-label text-gold-300 uppercase">{t('brand')}</p>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/"
              className="text-label text-cream/70 uppercase hover:text-gold-200"
            >
              {t('nav.backToSite')}
            </Link>
            <span className="text-label text-muted normal-case">
              {t('nav.signedInAs', {username: user.username})}
            </span>
            <LogoutButton locale={locale} />
          </div>
        </div>

        <AdminNav />
      </header>

      <main className="flex flex-col gap-8">{children}</main>
    </Container>
  );
}
