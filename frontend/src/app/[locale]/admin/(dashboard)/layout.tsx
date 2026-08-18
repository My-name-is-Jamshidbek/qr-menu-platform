import type {Metadata} from 'next';
import {notFound, redirect} from 'next/navigation';
import {getTranslations, setRequestLocale} from 'next-intl/server';

import {AdminShell} from '@/features/admin';
import {isAppLocale} from '@/i18n/routing';
import {getSessionUser} from '@/lib/auth';
import {adminLoginPath} from '@/middleware-auth';

/**
 * The session gate for every admin screen.
 *
 * This is a Server Component, and it is the only guard in the panel. It asks
 * the API who the cookie belongs to before rendering anything, so an
 * unauthenticated request receives a redirect rather than markup — there is no
 * moment where admin UI exists in the document and a client-side check races
 * to hide it, which is precisely how the original leaked its whole interface.
 */

export async function generateMetadata({
  params
}: LayoutProps<'/[locale]/admin'>): Promise<Metadata> {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  const t = await getTranslations({locale, namespace: 'admin'});

  // The panel must never be indexed, whatever a crawler manages to reach.
  return {title: {default: t('brand'), template: `%s · ${t('brand')}`}, robots: {index: false, follow: false}};
}

export default async function AdminDashboardLayout({children, params}: LayoutProps<'/[locale]/admin'>) {
  const {locale} = await params;
  if (!isAppLocale(locale)) notFound();

  setRequestLocale(locale);

  const user = await getSessionUser();
  if (!user) redirect(adminLoginPath(locale, null));

  return (
    <AdminShell locale={locale} user={user}>
      {children}
    </AdminShell>
  );
}
